from rest_framework import serializers

from apps.catalog.models import MedicalProduct, ProductVariant

from .models import FMEARevision
from .services import create_revision


class RevisionSerializer(serializers.ModelSerializer):
    product_code = serializers.CharField(source="product.code", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    variant_code = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    approved_by_email = serializers.SerializerMethodField()
    items_count = serializers.IntegerField(source="items.count", read_only=True)
    dependencies_count = serializers.IntegerField(source="dependencies.count", read_only=True)

    class Meta:
        model = FMEARevision
        fields = (
            "id",
            "product",
            "product_code",
            "product_name",
            "variant",
            "variant_code",
            "version",
            "status",
            "status_display",
            "based_on",
            "change_reason",
            "created_by",
            "created_by_email",
            "approved_by",
            "approved_by_email",
            "approved_at",
            "items_count",
            "dependencies_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_variant_code(self, obj) -> str | None:
        return obj.variant.code if obj.variant_id else None

    def get_approved_by_email(self, obj) -> str | None:
        return obj.approved_by.email if obj.approved_by_id else None


class RevisionCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=MedicalProduct.objects.all())
    variant = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), required=False, allow_null=True
    )
    version = serializers.CharField(max_length=20, required=False, allow_blank=True)
    change_reason = serializers.CharField(required=False, allow_blank=True)
    based_on = serializers.PrimaryKeyRelatedField(
        queryset=FMEARevision.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        product = attrs["product"]
        variant = attrs.get("variant")
        if variant is not None and variant.product_id != product.pk:
            raise serializers.ValidationError(
                {"variant": "Исполнение должно принадлежать выбранному изделию"}
            )
        based_on = attrs.get("based_on")
        if based_on is not None and based_on.product_id != product.pk:
            raise serializers.ValidationError(
                {"based_on": "Базовая ревизия должна относиться к тому же изделию"}
            )
        if not attrs.get("version"):
            attrs.pop("version", None)
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return create_revision(
            product=validated_data["product"],
            variant=validated_data.get("variant"),
            version=validated_data.get("version"),
            change_reason=validated_data.get("change_reason", ""),
            based_on=validated_data.get("based_on"),
            user=request.user,
            request=request,
        )


class CloneRevisionSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=20, required=False, allow_blank=True)
    change_reason = serializers.CharField(required=False, allow_blank=True)

    def validate_version(self, value):
        return value or None


class RejectRevisionSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)
