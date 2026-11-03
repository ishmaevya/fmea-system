from django.contrib import admin

from .models import AuditLog, Attachment, FMEAItem, FMEARevision, LLMSuggestion, RiskDependency


@admin.register(FMEARevision)
class FMEARevisionAdmin(admin.ModelAdmin):
    list_display = ("product", "variant", "version", "status", "created_by", "approved_by", "approved_at")
    list_filter = ("status", "product")
    search_fields = ("version",)
    readonly_fields = ("created_at", "updated_at", "approved_at")


@admin.register(FMEAItem)
class FMEAItemAdmin(admin.ModelAdmin):
    list_display = ("revision", "component", "failure_mode", "severity", "occurrence", "detection", "rpn", "action_priority", "status", "source")
    list_filter = ("revision", "action_priority", "status", "source")
    search_fields = ("failure_mode", "failure_cause", "failure_effect")
    readonly_fields = ("rpn", "action_priority", "created_at", "updated_at")


@admin.register(RiskDependency)
class RiskDependencyAdmin(admin.ModelAdmin):
    list_display = ("revision", "source_item", "target_item", "relation_type")
    list_filter = ("revision", "relation_type")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_name", "product", "revision", "item", "content_type", "size", "uploaded_by", "created_at")
    list_filter = ("content_type",)
    search_fields = ("original_name",)


@admin.register(LLMSuggestion)
class LLMSuggestionAdmin(admin.ModelAdmin):
    list_display = ("component", "product", "provider", "status", "created_by", "applied_item", "created_at")
    list_filter = ("status", "provider")
    readonly_fields = ("created_at",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity_type", "entity_id", "user", "ip_address", "created_at")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_id",)
    readonly_fields = ("created_at",)
