from django.conf import settings
from django.db import models


class ProductStatus(models.TextChoices):
    ACTIVE = "active", "Активное"
    ARCHIVED = "archived", "Архивное"


class Criticality(models.TextChoices):
    LOW = "low", "Низкая"
    MEDIUM = "medium", "Средняя"
    HIGH = "high", "Высокая"
    CRITICAL = "critical", "Критическая"


class MedicalProduct(models.Model):
    code = models.CharField("Обозначение", max_length=100, unique=True)
    name = models.CharField("Наименование", max_length=255)
    manufacturer = models.CharField("Изготовитель", max_length=255)
    tu_code = models.CharField("Обозначение ТУ", max_length=100, blank=True)
    description = models.TextField("Описание", blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Создал",
        related_name="created_products",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        verbose_name = "Изделие"
        verbose_name_plural = "Изделия"
        ordering = ("code",)

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        MedicalProduct,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Изделие",
    )
    code = models.CharField("Обозначение исполнения", max_length=100)
    name = models.CharField("Наименование", max_length=255)
    settings = models.JSONField("Параметры", default=dict, blank=True)
    is_default = models.BooleanField("Исполнение по умолчанию", default=False)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Исполнение изделия"
        verbose_name_plural = "Исполнения изделий"
        ordering = ("product_id", "code")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "code"],
                name="uniq_product_variant_code",
            )
        ]

    def __str__(self):
        return f"{self.product.code} / {self.code}"


class Component(models.Model):
    product = models.ForeignKey(
        MedicalProduct,
        on_delete=models.CASCADE,
        related_name="components",
        verbose_name="Изделие",
    )
    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="components",
        verbose_name="Исполнение",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="Родительский узел",
    )
    code = models.CharField("Обозначение", max_length=100)
    name = models.CharField("Наименование", max_length=255)
    component_type = models.CharField("Тип", max_length=100, blank=True)
    description = models.TextField("Описание", blank=True)
    criticality = models.CharField(
        "Критичность",
        max_length=20,
        choices=Criticality.choices,
        default=Criticality.MEDIUM,
    )
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        verbose_name = "Компонент"
        verbose_name_plural = "Компоненты"
        ordering = ("product_id", "code")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "code"],
                name="uniq_component_in_variant",
            )
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"
