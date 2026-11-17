from collections import Counter
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from .models import ActionPriority, FMEAItem, ItemStatus


def _risk_row(item: FMEAItem) -> dict:
    return {
        "id": item.pk,
        "component_id": item.component_id,
        "component_code": item.component.code,
        "component_name": item.component.name,
        "failure_mode": item.failure_mode,
        "failure_cause": item.failure_cause,
        "failure_effect": item.failure_effect,
        "severity": item.severity,
        "occurrence": item.occurrence,
        "detection": item.detection,
        "rpn": item.rpn,
        "action_priority": item.action_priority,
        "action_priority_display": item.get_action_priority_display(),
        "recommended_action": item.recommended_action,
        "responsible_email": item.responsible.email if item.responsible_id else None,
        "due_date": item.due_date,
        "status": item.status,
        "status_display": item.get_status_display(),
        "source": item.source,
    }


def build_report(revision, *, limit: int = 10) -> dict:
    items = list(
        FMEAItem.objects.filter(revision=revision)
        .select_related("component", "responsible")
        .order_by("-rpn", "-id")
    )
    priority_counts = Counter(item.action_priority for item in items)
    status_counts = Counter(item.status for item in items)

    return {
        "revision": {
            "id": revision.pk,
            "product": revision.product_id,
            "product_code": revision.product.code,
            "product_name": revision.product.name,
            "variant_code": revision.variant.code if revision.variant_id else None,
            "version": revision.version,
            "status": revision.status,
            "status_display": revision.get_status_display(),
        },
        "summary": {
            "items_count": len(items),
            "components_count": len({item.component_id for item in items}),
            "avg_rpn": round(sum(item.rpn for item in items) / len(items), 1) if items else 0,
            "max_rpn": max((item.rpn for item in items), default=0),
            "counts_by_priority": {
                value: priority_counts.get(value, 0) for value, _ in ActionPriority.choices
            },
            "counts_by_status": {
                value: status_counts.get(value, 0) for value, _ in ItemStatus.choices
            },
        },
        "top_risks": [_risk_row(item) for item in items[:limit]],
        "generated_at": timezone.now(),
    }


XLSX_HEADERS = (
    "ID",
    "Компонент",
    "Вид отказа",
    "Причина",
    "Последствие",
    "S",
    "O",
    "D",
    "RPN",
    "Приоритет",
    "Рекомендуемое действие",
    "Ответственный",
    "Срок",
    "Статус",
)
XLSX_WIDTHS = (8, 26, 36, 36, 36, 6, 6, 6, 9, 14, 40, 26, 14, 16)


def build_xlsx(report: dict) -> BytesIO:
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Сводка"
    summary.append(["Параметр", "Значение"])
    revision = report["revision"]
    summary_data = (
        ("Изделие", f"{revision['product_code']} — {revision['product_name']}"),
        ("Исполнение", revision["variant_code"] or "—"),
        ("Ревизия", revision["version"]),
        ("Статус", revision["status_display"]),
        ("Сформирован", report["generated_at"].strftime("%Y-%m-%d %H:%M")),
        ("Пунктов FMEA", report["summary"]["items_count"]),
        ("Компонентов", report["summary"]["components_count"]),
        ("Средний RPN", report["summary"]["avg_rpn"]),
        ("Максимальный RPN", report["summary"]["max_rpn"]),
    )
    for row in summary_data:
        summary.append(list(row))
    for priority, count in report["summary"]["counts_by_priority"].items():
        label = dict(ActionPriority.choices)[priority]
        summary.append([f"Приоритет: {label}", count])
    summary["A1"].font = Font(bold=True)
    summary["B1"].font = Font(bold=True)
    summary.column_dimensions["A"].width = 30
    summary.column_dimensions["B"].width = 60

    risks = workbook.create_sheet("Топ рисков")
    risks.append(list(XLSX_HEADERS))
    for item in report["top_risks"]:
        risks.append(
            [
                item["id"],
                f"{item['component_code']} — {item['component_name']}",
                item["failure_mode"],
                item["failure_cause"],
                item["failure_effect"],
                item["severity"],
                item["occurrence"],
                item["detection"],
                item["rpn"],
                item["action_priority_display"],
                item["recommended_action"],
                item["responsible_email"] or "",
                item["due_date"],
                item["status_display"],
            ]
        )
    for index, width in enumerate(XLSX_WIDTHS, start=1):
        risks.column_dimensions[get_column_letter(index)].width = width
    for cell in risks[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="center")
    risks.freeze_panes = "A2"
    risks.auto_filter.ref = f"A1:{get_column_letter(len(XLSX_HEADERS))}{risks.max_row}"

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output
