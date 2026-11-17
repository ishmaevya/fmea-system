from io import BytesIO

import pytest
from openpyxl import load_workbook

from apps.fmea.models import AuditLog


@pytest.fixture
def scored_items(revision, component, item_factory):
    return [
        item_factory(
            revision,
            component,
            failure_mode=f"Отказ {index}",
            severity=severity,
            occurrence=occurrence,
            detection=detection,
        )
        for index, (severity, occurrence, detection) in enumerate(
            ((10, 10, 10), (7, 6, 5), (9, 6, 3), (4, 3, 2)), start=1
        )
    ]


@pytest.mark.django_db
def test_report_requires_authentication(api_client, revision):
    assert api_client.get(f"/api/revisions/{revision.pk}/report/").status_code == 401
    assert api_client.get(f"/api/revisions/{revision.pk}/report/xlsx/").status_code == 401


@pytest.mark.django_db
def test_report_summary_and_top_risks(api_client, engineer, revision, scored_items):
    api_client.force_authenticate(engineer)
    response = api_client.get(f"/api/revisions/{revision.pk}/report/?limit=2")

    assert response.status_code == 200
    data = response.json()
    assert data["revision"]["version"] == "1.0"
    assert data["revision"]["product_code"] == "HUM-001"
    assert data["summary"]["items_count"] == 4
    assert data["summary"]["components_count"] == 1
    assert data["summary"]["max_rpn"] == 1000
    assert data["summary"]["avg_rpn"] == 349.0
    assert data["summary"]["counts_by_priority"]["critical"] == 1
    assert data["summary"]["counts_by_priority"]["high"] == 2
    assert data["summary"]["counts_by_priority"]["low"] == 1

    top_rpns = [item["rpn"] for item in data["top_risks"]]
    assert top_rpns == [1000, 210]
    assert [item["id"] for item in data["top_risks"]] == [
        scored_items[0].pk,
        scored_items[1].pk,
    ]
    assert data["top_risks"][0]["component_code"] == "HEATER"


@pytest.mark.django_db
def test_report_for_empty_revision(api_client, engineer, revision):
    api_client.force_authenticate(engineer)
    data = api_client.get(f"/api/revisions/{revision.pk}/report/").json()

    assert data["summary"]["items_count"] == 0
    assert data["summary"]["avg_rpn"] == 0
    assert data["summary"]["max_rpn"] == 0
    assert data["top_risks"] == []


@pytest.mark.django_db
def test_report_limit_validation(api_client, engineer, revision, scored_items):
    api_client.force_authenticate(engineer)
    assert api_client.get(f"/api/revisions/{revision.pk}/report/?limit=0").status_code == 400
    assert api_client.get(f"/api/revisions/{revision.pk}/report/?limit=101").status_code == 400


@pytest.mark.django_db
def test_xlsx_export(api_client, engineer, revision, scored_items):
    api_client.force_authenticate(engineer)
    response = api_client.get(f"/api/revisions/{revision.pk}/report/xlsx/?limit=3")

    assert response.status_code == 200
    assert response["Content-Type"] == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'filename="fmea-report-HUM-001-1.0.xlsx"' in response["Content-Disposition"]

    workbook = load_workbook(BytesIO(response.content))
    assert workbook.sheetnames == ["Сводка", "Топ рисков"]

    summary = workbook["Сводка"]
    assert summary["A1"].value == "Параметр"
    assert dict(summary.values)["Пунктов FMEA"] == 4

    risks = workbook["Топ рисков"]
    assert risks.max_row == 4
    assert risks["A1"].value == "ID"
    assert risks["I1"].value == "RPN"
    assert risks["I2"].value == 1000
    assert risks["C2"].value == "Отказ 1"
    assert risks.freeze_panes == "A2"

    assert AuditLog.objects.filter(
        action="export", entity_type="FMEARevision", entity_id=str(revision.pk)
    ).exists()


@pytest.mark.django_db
def test_report_available_to_quality(api_client, quality, revision, scored_items):
    api_client.force_authenticate(quality)
    assert api_client.get(f"/api/revisions/{revision.pk}/report/").status_code == 200
    assert api_client.get(f"/api/revisions/{revision.pk}/report/xlsx/").status_code == 200
