import logging
from pathlib import Path
from uuid import uuid4

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.exceptions import PermissionDenied, ValidationError
from storages.backends.s3 import S3Storage

from apps.accounts.permissions import is_quality_or_admin

from .audit import log_action
from .models import Attachment
from .services import ensure_revision_editable

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "image/png",
    "image/jpeg",
}
ALLOWED_SUFFIXES = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}


def get_download_url(key: str, *, expires_in: int = 3600) -> str:
    endpoint = getattr(settings, "MINIO_PUBLIC_ENDPOINT", "")
    if not isinstance(default_storage, S3Storage) or not endpoint:
        return default_storage.url(key)

    options = settings.STORAGES["default"]["OPTIONS"]
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=options["access_key"],
        aws_secret_access_key=options["secret_key"],
        region_name=options.get("region_name"),
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": options.get("addressing_style", "path")},
        ),
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": options["bucket_name"], "Key": key},
        ExpiresIn=expires_in,
    )


def build_storage_key(product_id: int, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"attachments/{product_id}/{uuid4().hex}{suffix}"


def validate_attachment_file(file) -> str:
    if file.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError({"file": "Размер файла не должен превышать 20 МБ"})

    content_type = getattr(file, "content_type", "") or ""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError({"file": "Недопустимый тип файла"})

    suffix = Path(file.name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValidationError({"file": "Недопустимое расширение файла"})

    return content_type


def save_attachment(*, file, user, product=None, revision=None, item=None, request=None):
    if item is not None:
        revision = revision or item.revision
    if revision is not None:
        product = product or revision.product
    if product is None:
        raise ValidationError({"product": "Не удалось определить изделие вложения"})

    content_type = validate_attachment_file(file)
    size = file.size
    original_name = Path(file.name).name
    key = default_storage.save(build_storage_key(product.pk, original_name), file)

    attachment = Attachment.objects.create(
        product=product,
        revision=revision,
        item=item,
        file=key,
        original_name=original_name,
        content_type=content_type,
        size=size,
        uploaded_by=user,
    )
    log_action(
        user=user,
        action="upload",
        entity=attachment,
        payload={
            "product_id": product.pk,
            "revision_id": revision.pk if revision else None,
            "item_id": item.pk if item else None,
            "size": size,
        },
        request=request,
    )
    return attachment


def delete_attachment(*, attachment: Attachment, user, request=None) -> None:
    if attachment.item_id:
        ensure_revision_editable(attachment.item.revision, user)
    elif attachment.revision_id:
        ensure_revision_editable(attachment.revision, user)

    if attachment.uploaded_by_id != getattr(user, "pk", None) and not is_quality_or_admin(user):
        raise PermissionDenied(
            "Удалять вложение может автор, менеджер по качеству или администратор"
        )

    payload = {
        "product_id": attachment.product_id,
        "revision_id": attachment.revision_id,
        "item_id": attachment.item_id,
    }
    try:
        default_storage.delete(attachment.file)
    except Exception:
        logger.exception("Не удалось удалить файл вложения из хранилища")

    log_action(
        user=user,
        action="delete",
        entity=attachment,
        payload=payload,
        request=request,
    )
    attachment.delete()
