import django_filters

from .models import FMEAItem


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
