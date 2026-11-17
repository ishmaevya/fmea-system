from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.permissions import is_quality_or_admin

from .models import Component, MedicalProduct, ProductVariant


class ProductSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    variants_count = serializers.IntegerField(source="variants.count", read_only=True)
    components_count = serializers.IntegerField(source="components.count", read_only=True)
    revisions_count = serializers.IntegerField(source="revisions.count", read_only=True)

    class Meta:
        model = MedicalProduct
        fields = (
            "id",
            "code",
            "name",
            "manufacturer",
            "tu_code",
            "description",
            "status",
            "created_by",
            "created_by_email",
            "variants_count",
            "components_count",
            "revisions_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        if new_status != instance.status:
            request = self.context.get("request")
            if not is_quality_or_admin(getattr(request, "user", None)):
                raise PermissionDenied(
                    "Изменение статуса изделия доступно менеджеру по качеству или администратору"
                )
        return super().update(instance, validated_data)


class ProductVariantSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=MedicalProduct.objects.all(), required=False
    )
    components_count = serializers.IntegerField(source="components.count", read_only=True)

    class Meta:
        model = ProductVariant
        fields = (
            "id",
            "product",
            "code",
            "name",
            "settings",
            "is_default",
            "components_count",
            "created_at",
        )
        read_only_fields = ("id", "created_at")
        validators = []

    def validate(self, attrs):
        product = attrs.get("product") or getattr(self.instance, "product", None)
        fixed_product = self.context.get("product")
        if fixed_product is not None:
            if product is not None and product.pk != fixed_product.pk:
                raise serializers.ValidationError(
                    {"product": "Исполнение должно относиться к изделию из URL"}
                )
            product = fixed_product
        if product is None:
            raise serializers.ValidationError({"product": "Обязательное поле"})
        attrs["product"] = product

        code = attrs.get("code") or getattr(self.instance, "code", None)
        if code:
            duplicates = ProductVariant.objects.filter(product=product, code=code)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"code": "Исполнение с таким обозначением уже существует у изделия"}
                )
        return attrs


class ComponentSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=MedicalProduct.objects.all(), required=False
    )
    children_count = serializers.IntegerField(source="children.count", read_only=True)
    fmea_items_count = serializers.IntegerField(source="fmea_items.count", read_only=True)

    class Meta:
        model = Component
        fields = (
            "id",
            "product",
            "variant",
            "parent",
            "code",
            "name",
            "component_type",
            "description",
            "criticality",
            "is_active",
            "children_count",
            "fmea_items_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        validators = []

    def validate(self, attrs):
        product = attrs.get("product") or getattr(self.instance, "product", None)
        fixed_product = self.context.get("product")
        if fixed_product is not None:
            if product is not None and product.pk != fixed_product.pk:
                raise serializers.ValidationError(
                    {"product": "Компонент должен относиться к изделию из URL"}
                )
            product = fixed_product
        if product is None:
            raise serializers.ValidationError({"product": "Обязательное поле"})
        attrs["product"] = product

        variant = attrs.get("variant", getattr(self.instance, "variant", None))
        if variant is not None and variant.product_id != product.pk:
            raise serializers.ValidationError(
                {"variant": "Исполнение должно принадлежать выбранному изделию"}
            )

        parent = attrs.get("parent", getattr(self.instance, "parent", None))
        if parent is not None:
            if parent.product_id != product.pk:
                raise serializers.ValidationError(
                    {"parent": "Родительский узел должен принадлежать выбранному изделию"}
                )
            if self.instance is not None and parent.pk == self.instance.pk:
                raise serializers.ValidationError(
                    {"parent": "Компонент не может быть родителем сам себе"}
                )
            self._check_cycle(parent)

        code = attrs.get("code") or getattr(self.instance, "code", None)
        if code:
            duplicates = Component.objects.filter(product=product, variant=variant, code=code)
            if self.instance is not None:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                raise serializers.ValidationError(
                    {"code": "Компонент с таким обозначением уже существует"}
                )

        return attrs

    def _check_cycle(self, parent: Component) -> None:
        if self.instance is None:
            return
        seen = set()
        node = parent
        while node is not None and node.pk not in seen:
            if node.pk == self.instance.pk:
                raise serializers.ValidationError(
                    {"parent": "Обнаружена циклическая иерархия компонентов"}
                )
            seen.add(node.pk)
            node = node.parent
