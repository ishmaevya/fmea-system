from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminRole, IsEngineerOrAbove, IsQualityOrAdmin

from .models import FMEARevision
from .serializers import (
    CloneRevisionSerializer,
    RejectRevisionSerializer,
    RevisionCreateSerializer,
    RevisionSerializer,
)
from .services import (
    approve_revision,
    archive_revision,
    clone_revision,
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
