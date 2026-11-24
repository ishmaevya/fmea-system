import django_filters

from .models import AuditLog, FMEAItem


class FMEAItemFilter(django_filters.FilterSet):
    rpn_min = django_filters.NumberFilter(field_name="rpn", lookup_expr="gte")
    rpn_max = django_filters.NumberFilter(field_name="rpn", lookup_expr="lte")
    severity_min = django_filters.NumberFilter(field_name="severity", lookup_expr="gte")
    severity_max = django_filters.NumberFilter(field_name="severity", lookup_expr="lte")

    class Meta:
        model = FMEAItem
        fields = (
            "revision",
            "component",
            "status",
            "source",
            "action_priority",
            "responsible",
        )


class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    date_to = django_filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ("user", "action", "entity_type", "entity_id")
