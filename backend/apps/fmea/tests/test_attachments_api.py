import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.fmea.attachments import MAX_ATTACHMENT_SIZE
from apps.fmea.models import Attachment, RevisionStatus


@pytest.fixture(autouse=True)
def in_memory_storage(settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


def upload(api_client, user, **target):
    api_client.force_authenticate(user)
    file = SimpleUploadedFile("protocol.pdf", b"%PDF-1.4 demo", content_type="application/pdf")
    payload = {"file": file, **{key: value.pk for key, value in target.items()}}
    return api_client.post("/api/attachments/", payload, format="multipart")


@pytest.mark.django_db
def test_upload_product_attachment(api_client, engineer, product):
    response = upload(api_client, engineer, product=product)

    assert response.status_code == 201
    data = response.json()
    assert data["original_name"] == "protocol.pdf"
    assert data["content_type"] == "application/pdf"
    assert data["size"] == len(b"%PDF-1.4 demo")
    assert data["uploaded_by_email"] == "engineer@example.com"
    assert data["download_url"]

    attachment = Attachment.objects.get(pk=data["id"])
    assert attachment.product_id == product.pk
    assert attachment.file.startswith(f"attachments/{product.pk}/")
    assert default_storage.exists(attachment.file)


@pytest.mark.django_db
def test_upload_requires_exactly_one_target(api_client, engineer, product, revision):
    api_client.force_authenticate(engineer)
    file = SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf")

    no_target = api_client.post("/api/attachments/", {"file": file}, format="multipart")
    assert no_target.status_code == 400
    assert "target" in no_target.json()

    file = SimpleUploadedFile("a.pdf", b"%PDF", content_type="application/pdf")
    two_targets = api_client.post(
        "/api/attachments/",
        {"file": file, "product": product.pk, "revision": revision.pk},
        format="multipart",
    )
    assert two_targets.status_code == 400
    assert "target" in two_targets.json()


@pytest.mark.django_db
def test_upload_rejects_bad_type_and_size(api_client, engineer, product):
    api_client.force_authenticate(engineer)

    bad_type = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
    response = api_client.post(
        "/api/attachments/",
        {"file": bad_type, "product": product.pk},
        format="multipart",
    )
    assert response.status_code == 400
    assert "file" in response.json()

    big = SimpleUploadedFile(
        "big.pdf",
        b"x" * (MAX_ATTACHMENT_SIZE + 1),
        content_type="application/pdf",
    )
    response = api_client.post(
        "/api/attachments/", {"file": big, "product": product.pk}, format="multipart"
    )
    assert response.status_code == 400
    assert "file" in response.json()


@pytest.mark.django_db
def test_review_revision_upload_permissions(api_client, engineer, quality, revision):
    revision.status = RevisionStatus.REVIEW
    revision.save(update_fields=["status"])

    forbidden = upload(api_client, engineer, revision=revision)
    assert forbidden.status_code == 403

    allowed = upload(api_client, quality, revision=revision)
    assert allowed.status_code == 201
    assert allowed.json()["revision"] == revision.pk


@pytest.mark.django_db
def test_approved_revision_is_read_only(api_client, quality, revision):
    revision.status = RevisionStatus.APPROVED
    revision.save(update_fields=["status"])

    response = upload(api_client, quality, revision=revision)
    assert response.status_code == 403


@pytest.mark.django_db
def test_delete_requires_author_or_quality(api_client, engineer, quality, product):
    created = upload(api_client, engineer, product=product)
    assert created.status_code == 201
    attachment_id = created.json()["id"]
    attachment = Attachment.objects.get(pk=attachment_id)

    other = User.objects.create_user(
        email="other@example.com",
        password="Pass12345!",
        role=User.Role.ENGINEER,
        full_name="Другой инженер",
        position="Инженер-конструктор",
    )
    api_client.force_authenticate(other)
    denied = api_client.delete(f"/api/attachments/{attachment_id}/")
    assert denied.status_code == 403
    assert Attachment.objects.filter(pk=attachment_id).exists()

    api_client.force_authenticate(quality)
    deleted = api_client.delete(f"/api/attachments/{attachment_id}/")
    assert deleted.status_code == 204
    assert not Attachment.objects.filter(pk=attachment_id).exists()
    assert not default_storage.exists(attachment.file)


@pytest.mark.django_db
def test_approved_revision_attachment_cannot_be_deleted(api_client, engineer, quality, revision):
    created = upload(api_client, engineer, revision=revision)
    assert created.status_code == 201
    attachment_id = created.json()["id"]

    revision.status = RevisionStatus.APPROVED
    revision.save(update_fields=["status"])

    api_client.force_authenticate(quality)
    response = api_client.delete(f"/api/attachments/{attachment_id}/")
    assert response.status_code == 403
    assert Attachment.objects.filter(pk=attachment_id).exists()


@pytest.mark.django_db
def test_list_filter_and_download(api_client, engineer, product, revision, component, item_factory):
    item = item_factory(revision, component)
    assert upload(api_client, engineer, product=product).status_code == 201
    assert upload(api_client, engineer, revision=revision).status_code == 201
    created = upload(api_client, engineer, item=item)
    assert created.status_code == 201

    api_client.force_authenticate(engineer)
    by_item = api_client.get(f"/api/attachments/?item={item.pk}")
    assert by_item.status_code == 200
    assert by_item.json()["count"] == 1
    assert by_item.json()["results"][0]["id"] == created.json()["id"]

    by_revision = api_client.get(f"/api/attachments/?revision={revision.pk}")
    assert by_revision.json()["count"] == 2

    download = api_client.get(f"/api/attachments/{created.json()['id']}/download/")
    assert download.status_code == 200
    assert download.json()["url"]
    assert download.json()["expires_in"] == 3600
