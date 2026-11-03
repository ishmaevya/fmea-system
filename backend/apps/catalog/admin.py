from django.contrib import admin

from .models import Component, MedicalProduct, ProductVariant


@admin.register(MedicalProduct)
class MedicalProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "manufacturer", "status", "created_by", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "name", "manufacturer")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "code", "name", "is_default")
    list_filter = ("product",)
    search_fields = ("code", "name")


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ("product", "code", "name", "component_type", "criticality", "parent", "is_active")
    list_filter = ("product", "criticality", "is_active")
    search_fields = ("code", "name")
