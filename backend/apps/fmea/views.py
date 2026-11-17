from django.db import transaction
from django.http import HttpResponse
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminRole, IsEngineerOrAbove, IsQualityOrAdmin

from .attachments import delete_attachment, get_download_url
from .audit import log_action
from .filters import FMEAItemFilter
from .llm import apply_suggestion, reject_suggestion
from .models import (
    Attachment,
    FMEAItem,
    FMEARevision,
    LLMSuggestion,
    RiskDependency,
)
from .reports import build_report, build_xlsx
from .serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    BulkItemsSerializer,
    CloneRevisionSerializer,
    FMEAItemSerializer,
    RejectRevisionSerializer,
    ReportQuerySerializer,
    RevisionCreateSerializer,
    RevisionGraphSerializer,
    RevisionReportSerializer,
    RevisionSerializer,
    RiskDependencySerializer,
    SuggestionRequestSerializer,
    SuggestionSerializer,
)
from .services import (
    approve_revision,
    archive_revision,
    clone_revision,
    ensure_revision_editable,
    reject_revision,
    submit_review,
)

ACTION_PERMISSIONS = {
    "create": IsEngineerOrAbove,
    "clone": IsEngineerOrAbove,
    "submit": IsEngineerOrAbove,
    "approve": IsQualityOrAdmin,
    "reject": IsQualityOrAdmin,
    "archive": IsAdminRole,
}

ITEM_ORDERING_FIELDS = {
    "rpn",
    "severity",
    "occurrence",
    "detection",
    "action_priority",
    "created_at",
    "failure_mode",
}


def apply_item_filters(queryset, request):
    queryset = FMEAItemFilter(request.query_params, queryset=queryset).qs
    raw_ordering = request.query_params.get("ordering", "")
    ordering = []
    for token in raw_ordering.split(","):
        token = token.strip()
        field = token.lstrip("-")
        if field in ITEM_ORDERING_FIELDS:
            ordering.append(f"-{field}" if token.startswith("-") else field)
    if ordering:
        queryset = queryset.order_by(*ordering)
    return queryset


@extend_schema_view(
    list=extend_schema(tags=["Ревизии"], summary="Список ревизий"),
    retrieve=extend_schema(tags=["Ревизии"], summary="Ревизия"),
)
class RevisionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = FMEARevision.objects.select_related(
        "product", "variant", "created_by", "approved_by", "based_on"
    ).prefetch_related("items", "dependencies")
    filterset_fields = ("product", "variant", "status", "based_on")
    search_fields = ("version", "product__code", "product__name", "change_reason")
    ordering_fields = ("version", "status", "created_at", "updated_at")
    ordering = ("-created_at",)

    def get_permissions(self):
        permission = ACTION_PERMISSIONS.get(self.action)
        if permission is None:
            return [IsAuthenticated()]
        return [permission()]

    def get_serializer_class(self):
        if self.action == "create":
            return RevisionCreateSerializer
        return RevisionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        revision = serializer.save()
        output = RevisionSerializer(revision, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def paginated_items(self, queryset, serializer_class, context=None):
        context = context or self.get_serializer_context()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
        serializer = serializer_class(queryset, many=True, context=context)
        return Response(serializer.data)

    @extend_schema(
        tags=["Ревизии"],
        summary="Клонировать ревизию",
        request=CloneRevisionSerializer,
        responses={201: RevisionSerializer},
    )
    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        source = self.get_object()
        input_serializer = CloneRevisionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data
        target = clone_revision(
            source=source,
            user=request.user,
            version=data.get("version"),
            change_reason=data.get("change_reason", ""),
            request=request,
        )
        output = RevisionSerializer(target, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["Ревизии"],
        summary="Отправить на проверку",
        request=None,
        responses={200: RevisionSerializer},
    )
    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        revision = submit_review(revision=self.get_object(), user=request.user, request=request)
        return Response(RevisionSerializer(revision, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=["Ревизии"],
        summary="Утвердить ревизию",
        request=None,
        responses={200: RevisionSerializer},
    )
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        revision = approve_revision(revision=self.get_object(), user=request.user, request=request)
        return Response(RevisionSerializer(revision, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=["Ревизии"],
        summary="Отклонить ревизию",
        request=RejectRevisionSerializer,
        responses={200: RevisionSerializer},
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        input_serializer = RejectRevisionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        revision = reject_revision(
            revision=self.get_object(),
            user=request.user,
            reason=input_serializer.validated_data["reason"],
            request=request,
        )
        return Response(RevisionSerializer(revision, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=["Ревизии"],
        summary="Архивировать ревизию",
        request=None,
        responses={200: RevisionSerializer},
    )
    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        revision = archive_revision(revision=self.get_object(), user=request.user, request=request)
        return Response(RevisionSerializer(revision, context=self.get_serializer_context()).data)

    @extend_schema(
        tags=["Пункты FMEA"],
        summary="Пункты ревизии",
        request=FMEAItemSerializer,
        responses=FMEAItemSerializer,
    )
    @action(detail=True, methods=["get", "post"], url_path="items")
    def items(self, request, pk=None):
        revision = self.get_object()
        if request.method == "POST":
            ensure_revision_editable(revision, request.user)
            context = self.get_serializer_context()
            context["revision"] = revision
            serializer = FMEAItemSerializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            item = serializer.save(revision=revision, created_by=request.user)
            log_action(
                user=request.user,
                action="create",
                entity=item,
                payload={"revision_id": revision.pk, "component_id": item.component_id},
                request=request,
            )
            return Response(
                FMEAItemSerializer(item, context=context).data,
                status=status.HTTP_201_CREATED,
            )

        queryset = revision.items.select_related("component", "responsible")
        queryset = apply_item_filters(queryset, request)
        return self.paginated_items(queryset, FMEAItemSerializer)

    @extend_schema(
        tags=["Пункты FMEA"],
        summary="Массовое сохранение пунктов",
        request=BulkItemsSerializer,
        responses={200: OpenApiResponse(description="Сохранённые пункты и счётчики изменений")},
    )
    @action(detail=True, methods=["post"], url_path="items/bulk")
    def bulk_items(self, request, pk=None):
        revision = self.get_object()
        context = self.get_serializer_context()
        context["revision"] = revision
        serializer = BulkItemsSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            result = serializer.save()
        output = FMEAItemSerializer(result["items"], many=True, context=context)
        return Response(
            {
                "items": output.data,
                "created": result["created"],
                "updated": result["updated"],
                "deleted": result["deleted"],
            }
        )

    @extend_schema(
        tags=["Пункты FMEA"],
        summary="Граф связей ревизии",
        responses={200: RevisionGraphSerializer},
    )
    @action(detail=True, methods=["get"], url_path="graph")
    def graph(self, request, pk=None):
        revision = self.get_object()
        items = revision.items.select_related("component")
        dependencies = revision.dependencies.select_related("source_item", "target_item")
        nodes = [
            {
                "id": item.pk,
                "component_id": item.component_id,
                "component_code": item.component.code,
                "component_name": item.component.name,
                "failure_mode": item.failure_mode,
                "rpn": item.rpn,
                "action_priority": item.action_priority,
                "action_priority_display": item.get_action_priority_display(),
                "severity": item.severity,
                "status": item.status,
            }
            for item in items
        ]
        edges = [
            {
                "id": dependency.pk,
                "source": dependency.source_item_id,
                "target": dependency.target_item_id,
                "relation_type": dependency.relation_type,
                "relation_type_display": dependency.get_relation_type_display(),
                "description": dependency.description,
            }
            for dependency in dependencies
        ]
        data = {"revision": revision.pk, "nodes": nodes, "edges": edges}
        return Response(RevisionGraphSerializer(data).data)

    @extend_schema(
        tags=["Связи рисков"],
        summary="Связи ревизии",
        request=RiskDependencySerializer,
        responses=RiskDependencySerializer,
    )
    @action(detail=True, methods=["get", "post"], url_path="dependencies")
    def dependencies(self, request, pk=None):
        revision = self.get_object()
        if request.method == "POST":
            ensure_revision_editable(revision, request.user)
            context = self.get_serializer_context()
            context["revision"] = revision
            serializer = RiskDependencySerializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            dependency = serializer.save(revision=revision)
            log_action(
                user=request.user,
                action="create",
                entity=dependency,
                payload={"revision_id": revision.pk},
                request=request,
            )
            return Response(
                RiskDependencySerializer(dependency, context=context).data,
                status=status.HTTP_201_CREATED,
            )

        queryset = revision.dependencies.select_related("source_item", "target_item")
        return self.paginated_items(queryset, RiskDependencySerializer)

    def report_limit(self, request) -> int:
        serializer = ReportQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data["limit"]

    @extend_schema(
        tags=["Отчёты"],
        summary="Сводный отчёт и топ рисков",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Количество пунктов в топе рисков (1–100)",
            )
        ],
        responses={200: RevisionReportSerializer},
    )
    @action(detail=True, methods=["get"], url_path="report")
    def report(self, request, pk=None):
        revision = self.get_object()
        data = build_report(revision, limit=self.report_limit(request))
        return Response(data)

    @extend_schema(
        tags=["Отчёты"],
        summary="Экспорт отчёта в XLSX",
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Количество пунктов в топе рисков (1–100)",
            )
        ],
        responses={200: OpenApiResponse(description="XLSX-файл")},
    )
    @action(detail=True, methods=["get"], url_path="report/xlsx")
    def report_xlsx(self, request, pk=None):
        revision = self.get_object()
        limit = self.report_limit(request)
        report = build_report(revision, limit=limit)
        content = build_xlsx(report)
        log_action(
            user=request.user,
            action="export",
            entity=revision,
            payload={"format": "xlsx", "limit": limit},
            request=request,
        )
        response = HttpResponse(
            content.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f"fmea-report-{revision.product.code}-{revision.version}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


@extend_schema_view(
    list=extend_schema(tags=["Пункты FMEA"], summary="Список пунктов FMEA"),
    retrieve=extend_schema(tags=["Пункты FMEA"], summary="Пункт FMEA"),
    update=extend_schema(tags=["Пункты FMEA"], summary="Изменить пункт FMEA"),
    partial_update=extend_schema(tags=["Пункты FMEA"], summary="Изменить пункт частично"),
    destroy=extend_schema(tags=["Пункты FMEA"], summary="Удалить пункт FMEA"),
)
class ItemViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = FMEAItem.objects.select_related("revision", "component", "responsible")
    serializer_class = FMEAItemSerializer
    filterset_class = FMEAItemFilter
    search_fields = (
        "failure_mode",
        "failure_cause",
        "failure_effect",
        "component__code",
        "component__name",
    )
    ordering_fields = (
        "rpn",
        "severity",
        "occurrence",
        "detection",
        "action_priority",
        "created_at",
    )
    ordering = ("-rpn", "component_id")
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        current = self.get_object()
        ensure_revision_editable(current.revision, self.request.user)
        item = serializer.save()
        log_action(
            user=self.request.user,
            action="update",
            entity=item,
            payload={"revision_id": item.revision_id, "rpn": item.rpn},
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        item = self.get_object()
        ensure_revision_editable(item.revision, request.user)
        log_action(
            user=request.user,
            action="delete",
            entity=item,
            payload={"revision_id": item.revision_id, "failure_mode": item.failure_mode},
            request=request,
        )
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=["Связи рисков"], summary="Список связей"),
    retrieve=extend_schema(tags=["Связи рисков"], summary="Связь рисков"),
    destroy=extend_schema(tags=["Связи рисков"], summary="Удалить связь"),
)
class DependencyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = RiskDependency.objects.select_related("revision", "source_item", "target_item")
    serializer_class = RiskDependencySerializer
    filterset_fields = ("revision", "source_item", "target_item", "relation_type")
    ordering = ("revision_id", "id")
    permission_classes = (IsAuthenticated,)

    def destroy(self, request, *args, **kwargs):
        dependency = self.get_object()
        ensure_revision_editable(dependency.revision, request.user)
        log_action(
            user=request.user,
            action="delete",
            entity=dependency,
            payload={"revision_id": dependency.revision_id},
            request=request,
        )
        dependency.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=["Вложения"], summary="Список вложений"),
    retrieve=extend_schema(tags=["Вложения"], summary="Вложение"),
    create=extend_schema(
        tags=["Вложения"],
        summary="Загрузить вложение",
        request=AttachmentUploadSerializer,
        responses={201: AttachmentSerializer},
    ),
    destroy=extend_schema(tags=["Вложения"], summary="Удалить вложение"),
    download=extend_schema(
        tags=["Вложения"],
        summary="Ссылка на скачивание вложения",
        responses={200: OpenApiResponse(description="Presigned URL и срок жизни")},
    ),
)
class AttachmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Attachment.objects.select_related("product", "revision", "item", "uploaded_by")
    serializer_class = AttachmentSerializer
    filterset_fields = ("product", "revision", "item")
    search_fields = ("original_name",)
    ordering = ("-created_at",)
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        if self.action == "create":
            return [IsEngineerOrAbove()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return AttachmentUploadSerializer
        return AttachmentSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("revision") is not None:
            ensure_revision_editable(data["revision"], request.user)
        if data.get("item") is not None:
            ensure_revision_editable(data["item"].revision, request.user)

        attachment = serializer.save()
        output = AttachmentSerializer(attachment, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def destroy(self, request, *args, **kwargs):
        attachment = self.get_object()
        delete_attachment(attachment=attachment, user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        attachment = self.get_object()
        url = get_download_url(attachment.file)
        return Response({"url": url, "expires_in": 3600})


@extend_schema_view(
    list=extend_schema(
        tags=["LLM-подсказки"],
        summary="Список подсказок",
        description="Предложения формируются демонстрационной заглушкой, не реальной языковой моделью.",
    ),
    retrieve=extend_schema(tags=["LLM-подсказки"], summary="Подсказка"),
    create=extend_schema(
        tags=["LLM-подсказки"],
        summary="Запросить подсказку",
        description="Возвращает предложение заглушки; на FMEA оно не влияет до явного применения.",
        request=SuggestionRequestSerializer,
        responses={201: SuggestionSerializer},
    ),
    apply=extend_schema(
        tags=["LLM-подсказки"],
        summary="Применить подсказку",
        responses={200: FMEAItemSerializer},
    ),
    reject=extend_schema(
        tags=["LLM-подсказки"],
        summary="Отклонить подсказку",
        responses={200: SuggestionSerializer},
    ),
)
class SuggestionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = LLMSuggestion.objects.select_related(
        "product", "revision", "component", "created_by", "applied_item"
    )
    serializer_class = SuggestionSerializer
    filterset_fields = ("product", "revision", "component", "status", "provider")
    search_fields = ("prompt", "component__code", "component__name")
    ordering = ("-created_at",)
    permission_classes = (IsAuthenticated,)

    def get_permissions(self):
        if self.action in ("create", "apply", "reject"):
            return [IsEngineerOrAbove()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "create":
            return SuggestionRequestSerializer
        return SuggestionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        suggestion = serializer.save()
        output = SuggestionSerializer(suggestion, context=self.get_serializer_context())
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        suggestion = self.get_object()
        item = apply_suggestion(suggestion, user=request.user, request=request)
        output = FMEAItemSerializer(item, context=self.get_serializer_context())
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        suggestion = self.get_object()
        suggestion = reject_suggestion(suggestion, user=request.user, request=request)
        return Response(self.get_serializer(suggestion).data)
