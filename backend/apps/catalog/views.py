from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsQualityOrAdmin
from apps.fmea.audit import log_action

from .models import Component, MedicalProduct, ProductStatus, ProductVariant
from .serializers import ComponentSerializer, ProductSerializer, ProductVariantSerializer


class PaginatedActionMixin:
    def paginated_response(self, queryset, serializer_class, context=None):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(
                page, many=True, context=context or self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = serializer_class(
            queryset, many=True, context=context or self.get_serializer_context()
        )
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(tags=["Каталог"], summary="Список изделий"),
    create=extend_schema(tags=["Каталог"], summary="Создать изделие"),
    retrieve=extend_schema(tags=["Каталог"], summary="Карточка изделия"),
    update=extend_schema(tags=["Каталог"], summary="Изменить изделие"),
    partial_update=extend_schema(tags=["Каталог"], summary="Изменить изделие частично"),
    destroy=extend_schema(
        tags=["Каталог"],
        summary="Архивировать изделие",
        description="Физического удаления нет: изделие переводится в статус «Архивное».",
    ),
)
class ProductViewSet(PaginatedActionMixin, viewsets.ModelViewSet):
    queryset = MedicalProduct.objects.select_related("created_by").prefetch_related(
        "variants", "components", "revisions"
    )
    serializer_class = ProductSerializer
    filterset_fields = ("status",)
    search_fields = ("code", "name", "manufacturer")
    ordering_fields = ("code", "name", "status", "created_at")
    ordering = ("code",)

    def get_permissions(self):
        if self.action == "destroy":
            return [IsQualityOrAdmin()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        product = serializer.save(created_by=self.request.user)
        log_action(
            user=self.request.user,
            action="create",
            entity=product,
            payload={"code": product.code, "name": product.name},
            request=self.request,
        )

    def perform_update(self, serializer):
        product = serializer.save()
        log_action(
            user=self.request.user,
            action="update",
            entity=product,
            payload={"code": product.code, "status": product.status},
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.status != ProductStatus.ARCHIVED:
            product.status = ProductStatus.ARCHIVED
            product.save(update_fields=["status", "updated_at"])
            log_action(
                user=request.user,
                action="archive",
                entity=product,
                payload={"code": product.code},
                request=request,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(tags=["Каталог"], summary="Исполнения изделия")
    @action(detail=True, methods=["get", "post"], url_path="variants")
    def variants(self, request, pk=None):
        product = self.get_object()
        if request.method == "POST":
            context = self.get_serializer_context()
            context["product"] = product
            serializer = ProductVariantSerializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            variant = serializer.save()
            log_action(
                user=request.user,
                action="create",
                entity=variant,
                payload={"product_id": product.pk, "code": variant.code},
                request=request,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = product.variants.all()
        return self.paginated_response(queryset, ProductVariantSerializer)

    @extend_schema(tags=["Каталог"], summary="Компоненты изделия")
    @action(detail=True, methods=["get", "post"], url_path="components")
    def components(self, request, pk=None):
        product = self.get_object()
        if request.method == "POST":
            context = self.get_serializer_context()
            context["product"] = product
            serializer = ComponentSerializer(data=request.data, context=context)
            serializer.is_valid(raise_exception=True)
            component = serializer.save()
            log_action(
                user=request.user,
                action="create",
                entity=component,
                payload={"product_id": product.pk, "code": component.code},
                request=request,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        queryset = product.components.select_related("variant", "parent")
        return self.paginated_response(queryset, ComponentSerializer)


@extend_schema_view(
    list=extend_schema(tags=["Каталог"], summary="Список исполнений"),
    create=extend_schema(tags=["Каталог"], summary="Создать исполнение"),
    retrieve=extend_schema(tags=["Каталог"], summary="Исполнение"),
    update=extend_schema(tags=["Каталог"], summary="Изменить исполнение"),
    partial_update=extend_schema(tags=["Каталог"], summary="Изменить исполнение частично"),
    destroy=extend_schema(tags=["Каталог"], summary="Удалить исполнение без связей"),
)
class ProductVariantViewSet(viewsets.ModelViewSet):
    queryset = ProductVariant.objects.select_related("product").prefetch_related("components")
    serializer_class = ProductVariantSerializer
    filterset_fields = ("product", "is_default")
    search_fields = ("code", "name")
    ordering_fields = ("code", "name", "created_at")
    ordering = ("product_id", "code")
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        variant = serializer.save()
        log_action(
            user=self.request.user,
            action="create",
            entity=variant,
            payload={"product_id": variant.product_id, "code": variant.code},
            request=self.request,
        )

    def perform_update(self, serializer):
        variant = serializer.save()
        log_action(
            user=self.request.user,
            action="update",
            entity=variant,
            payload={"product_id": variant.product_id, "code": variant.code},
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        variant = self.get_object()
        if variant.revisions.exists():
            raise ValidationError(
                {"detail": "Нельзя удалить исполнение, к которому привязаны ревизии"}
            )
        if variant.components.exists():
            raise ValidationError(
                {"detail": "Нельзя удалить исполнение, к которому привязаны компоненты"}
            )
        log_action(
            user=request.user,
            action="delete",
            entity=variant,
            payload={"product_id": variant.product_id, "code": variant.code},
            request=request,
        )
        variant.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema_view(
    list=extend_schema(tags=["Каталог"], summary="Список компонентов"),
    create=extend_schema(tags=["Каталог"], summary="Создать компонент"),
    retrieve=extend_schema(tags=["Каталог"], summary="Компонент"),
    update=extend_schema(tags=["Каталог"], summary="Изменить компонент"),
    partial_update=extend_schema(tags=["Каталог"], summary="Изменить компонент частично"),
    destroy=extend_schema(
        tags=["Каталог"],
        summary="Деактивировать компонент",
        description="Компонент не удаляется физически: устанавливается is_active=false.",
    ),
)
class ComponentViewSet(viewsets.ModelViewSet):
    queryset = Component.objects.select_related("product", "variant", "parent").prefetch_related(
        "children"
    )
    serializer_class = ComponentSerializer
    filterset_fields = ("product", "variant", "parent", "criticality", "is_active")
    search_fields = ("code", "name", "component_type")
    ordering_fields = ("code", "name", "criticality", "created_at")
    ordering = ("product_id", "code")
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        component = serializer.save()
        log_action(
            user=self.request.user,
            action="create",
            entity=component,
            payload={"product_id": component.product_id, "code": component.code},
            request=self.request,
        )

    def perform_update(self, serializer):
        component = serializer.save()
        log_action(
            user=self.request.user,
            action="update",
            entity=component,
            payload={"product_id": component.product_id, "code": component.code},
            request=self.request,
        )

    def destroy(self, request, *args, **kwargs):
        component = self.get_object()
        if component.is_active:
            component.is_active = False
            component.save(update_fields=["is_active", "updated_at"])
            log_action(
                user=request.user,
                action="archive",
                entity=component,
                payload={"product_id": component.product_id, "code": component.code},
                request=request,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
