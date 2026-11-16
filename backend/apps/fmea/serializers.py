from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import MedicalProduct, ProductVariant

from .attachments import get_download_url, save_attachment, validate_attachment_file
from .audit import log_action
from .models import Attachment, FMEAItem, FMEARevision, RiskDependency
from .services import create_revision, ensure_revision_editable


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


class FMEAItemSerializer(serializers.ModelSerializer):
    component_code = serializers.CharField(source="component.code", read_only=True)
    component_name = serializers.CharField(source="component.name", read_only=True)
    revision_status = serializers.CharField(source="revision.status", read_only=True)
    action_priority_display = serializers.CharField(
        source="get_action_priority_display", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    responsible_email = serializers.SerializerMethodField()

    class Meta:
        model = FMEAItem
        fields = (
            "id",
            "revision",
            "revision_status",
            "component",
            "component_code",
            "component_name",
            "failure_mode",
            "failure_cause",
            "failure_effect",
            "severity",
            "occurrence",
            "detection",
            "rpn",
            "action_priority",
            "action_priority_display",
            "recommended_action",
            "responsible",
            "responsible_email",
            "due_date",
            "status",
            "status_display",
            "source",
            "source_display",
            "source_reference",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "revision",
            "revision_status",
            "component_code",
            "component_name",
            "rpn",
            "action_priority",
            "action_priority_display",
            "status_display",
            "source",
            "source_display",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_responsible_email(self, obj) -> str | None:
        return obj.responsible.email if obj.responsible_id else None

    def validate(self, attrs):
        revision = self.context.get("revision") or getattr(self.instance, "revision", None)
        if revision is None:
            raise serializers.ValidationError({"revision": "Ревизия не определена"})

        component = attrs.get("component") or getattr(self.instance, "component", None)
        if component is None:
            raise serializers.ValidationError({"component": "Обязательное поле"})
        if component.product_id != revision.product_id:
            raise serializers.ValidationError(
                {"component": "Компонент должен принадлежать изделию ревизии"}
            )

        for field in ("failure_mode", "failure_cause", "failure_effect"):
            value = attrs.get(field, getattr(self.instance, field, ""))
            if not str(value).strip():
                raise serializers.ValidationError({field: "Поле не может быть пустым"})

        for field in ("severity", "occurrence", "detection"):
            value = attrs.get(field, getattr(self.instance, field, None))
            if value is None or not 1 <= value <= 10:
                raise serializers.ValidationError({field: "Значение должно быть от 1 до 10"})

        return attrs


class BulkItemRowSerializer(FMEAItemSerializer):
    id = serializers.IntegerField(required=False, min_value=1)

    class Meta(FMEAItemSerializer.Meta):
        read_only_fields = tuple(
            field for field in FMEAItemSerializer.Meta.read_only_fields if field != "id"
        )


class BulkItemsSerializer(serializers.Serializer):
    items = BulkItemRowSerializer(many=True, required=False, default=list)
    deleted_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )

    def validate(self, attrs):
        revision = self.context.get("revision")
        request = self.context.get("request")
        if revision is None or request is None:
            raise serializers.ValidationError({"detail": "Не передан контекст ревизии"})

        ensure_revision_editable(revision, request.user)

        rows = attrs.get("items", [])
        row_ids = [row["id"] for row in rows if row.get("id") is not None]
        deleted_ids = attrs.get("deleted_ids", [])

        duplicates = {pk for pk in row_ids if row_ids.count(pk) > 1}
        if duplicates:
            raise serializers.ValidationError(
                {"items": f"Повторяющиеся идентификаторы пунктов: {sorted(duplicates)}"}
            )

        overlap = set(row_ids) & set(deleted_ids)
        if overlap:
            raise serializers.ValidationError(
                {"deleted_ids": f"Нельзя одновременно изменить и удалить: {sorted(overlap)}"}
            )

        all_ids = set(row_ids) | set(deleted_ids)
        existing = set(revision.items.filter(pk__in=all_ids).values_list("pk", flat=True))
        missing = sorted(all_ids - existing)
        if missing:
            raise serializers.ValidationError(
                {"items": f"Пункты не найдены в ревизии: {missing}"}
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        revision = self.context["revision"]
        request = self.context["request"]
        user = request.user
        rows = validated_data.get("items", [])
        deleted_ids = validated_data.get("deleted_ids", [])

        existing = {
            item.pk: item
            for item in revision.items.filter(
                pk__in=[row["id"] for row in rows if row.get("id")] + deleted_ids
            )
        }

        created = 0
        updated = 0
        for row in rows:
            data = dict(row)
            pk = data.pop("id", None)
            if pk:
                item = existing[pk]
                for field, value in data.items():
                    setattr(item, field, value)
                item.save()
                updated += 1
            else:
                FMEAItem.objects.create(revision=revision, created_by=user, **data)
                created += 1

        for pk in deleted_ids:
            existing[pk].delete()

        log_action(
            user=user,
            action="bulk_update",
            entity=revision,
            payload={
                "created": created,
                "updated": updated,
                "deleted": len(deleted_ids),
            },
            request=request,
        )

        items = revision.items.select_related("component", "responsible")
        return {
            "items": list(items),
            "created": created,
            "updated": updated,
            "deleted": len(deleted_ids),
        }


class RiskDependencySerializer(serializers.ModelSerializer):
    source_mode = serializers.CharField(source="source_item.failure_mode", read_only=True)
    target_mode = serializers.CharField(source="target_item.failure_mode", read_only=True)
    relation_type_display = serializers.CharField(
        source="get_relation_type_display", read_only=True
    )

    class Meta:
        model = RiskDependency
        fields = (
            "id",
            "revision",
            "source_item",
            "source_mode",
            "target_item",
            "target_mode",
            "relation_type",
            "relation_type_display",
            "description",
            "created_at",
        )
        read_only_fields = (
            "id",
            "revision",
            "source_mode",
            "target_mode",
            "relation_type_display",
            "created_at",
        )

    def validate(self, attrs):
        revision = self.context.get("revision") or getattr(self.instance, "revision", None)
        if revision is None:
            raise serializers.ValidationError({"revision": "Ревизия не определена"})

        source = attrs.get("source_item") or getattr(self.instance, "source_item", None)
        target = attrs.get("target_item") or getattr(self.instance, "target_item", None)
        relation_type = attrs.get("relation_type") or getattr(
            self.instance, "relation_type", None
        )

        if source is None:
            raise serializers.ValidationError({"source_item": "Обязательное поле"})
        if target is None:
            raise serializers.ValidationError({"target_item": "Обязательное поле"})
        if source.pk == target.pk:
            raise serializers.ValidationError(
                {"target_item": "Связь не может указывать на тот же пункт"}
            )
        if source.revision_id != revision.pk:
            raise serializers.ValidationError(
                {"source_item": "Пункт должен принадлежать той же ревизии"}
            )
        if target.revision_id != revision.pk:
            raise serializers.ValidationError(
                {"target_item": "Пункт должен принадлежать той же ревизии"}
            )

        duplicates = RiskDependency.objects.filter(
            revision=revision,
            source_item=source,
            target_item=target,
            relation_type=relation_type,
        )
        if self.instance is not None:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({"detail": "Такая связь уже существует"})

        return attrs


class GraphNodeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    component_id = serializers.IntegerField()
    component_code = serializers.CharField()
    component_name = serializers.CharField()
    failure_mode = serializers.CharField()
    rpn = serializers.IntegerField()
    action_priority = serializers.CharField()
    action_priority_display = serializers.CharField()
    severity = serializers.IntegerField()
    status = serializers.CharField()


class GraphEdgeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    source = serializers.IntegerField()
    target = serializers.IntegerField()
    relation_type = serializers.CharField()
    relation_type_display = serializers.CharField()
    description = serializers.CharField(allow_blank=True)


class RevisionGraphSerializer(serializers.Serializer):
    revision = serializers.IntegerField()
    nodes = GraphNodeSerializer(many=True)
    edges = GraphEdgeSerializer(many=True)


class AttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.CharField(source="uploaded_by.email", read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = (
            "id",
            "product",
            "revision",
            "item",
            "original_name",
            "content_type",
            "size",
            "uploaded_by",
            "uploaded_by_email",
            "download_url",
            "created_at",
        )
        read_only_fields = fields

    def get_download_url(self, obj) -> str | None:
        try:
            return get_download_url(obj.file)
        except Exception:
            return None


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    product = serializers.PrimaryKeyRelatedField(
        queryset=MedicalProduct.objects.all(), required=False, allow_null=True
    )
    revision = serializers.PrimaryKeyRelatedField(
        queryset=FMEARevision.objects.all(), required=False, allow_null=True
    )
    item = serializers.PrimaryKeyRelatedField(
        queryset=FMEAItem.objects.all(), required=False, allow_null=True
    )

    def validate(self, attrs):
        targets = [
            name for name in ("product", "revision", "item") if attrs.get(name) is not None
        ]
        if len(targets) != 1:
            raise serializers.ValidationError(
                {"target": "Укажите ровно один объект: product, revision или item"}
            )
        validate_attachment_file(attrs["file"])
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        return save_attachment(
            user=request.user,
            request=request,
            file=validated_data["file"],
            product=validated_data.get("product"),
            revision=validated_data.get("revision"),
            item=validated_data.get("item"),
        )
