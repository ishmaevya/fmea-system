from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RevisionStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    REVIEW = "review", "На проверке"
    APPROVED = "approved", "Утверждена"
    ARCHIVED = "archived", "Архивная"


class ItemStatus(models.TextChoices):
    OPEN = "open", "Открыт"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Выполнен"
    ACCEPTED = "accepted", "Принят"


class ItemSource(models.TextChoices):
    MANUAL = "manual", "Ручной"
    LLM = "llm", "LLM-предложение"


class DependencyType(models.TextChoices):
    CAUSES = "causes", "Вызывает"
    AFFECTS = "affects", "Влияет"
    MITIGATES = "mitigates", "Снижает риск"


class SuggestionStatus(models.TextChoices):
    NEW = "new", "Новое"
    APPLIED = "applied", "Применено"
    REJECTED = "rejected", "Отклонено"


class ActionPriority(models.TextChoices):
    LOW = "low", "Низкий"
    MEDIUM = "medium", "Средний"
    HIGH = "high", "Высокий"
    CRITICAL = "critical", "Критический"


class FMEARevision(models.Model):
    product = models.ForeignKey(
        "catalog.MedicalProduct",
        on_delete=models.CASCADE,
        related_name="revisions",
        verbose_name="Изделие",
    )
    variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="revisions",
        verbose_name="Исполнение",
    )
    version = models.CharField("Версия", max_length=20)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=RevisionStatus.choices,
        default=RevisionStatus.DRAFT,
    )
    based_on = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derived_revisions",
        verbose_name="Основана на",
    )
    change_reason = models.TextField("Причина изменения", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_revisions",
        verbose_name="Создал",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_revisions",
        verbose_name="Утвердил",
    )
    approved_at = models.DateTimeField("Дата утверждения", null=True, blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Изменена", auto_now=True)

    class Meta:
        verbose_name = "FMEA-ревизия"
        verbose_name_plural = "FMEA-ревизии"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["product", "variant", "version"],
                name="uniq_revision_version",
            )
        ]

    def __str__(self):
        variant_part = f"/{self.variant.code}" if self.variant else ""
        return f"{self.product.code}{variant_part} v{self.version} [{self.get_status_display()}]"


class FMEAItem(models.Model):
    revision = models.ForeignKey(
        FMEARevision,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Ревизия",
    )
    component = models.ForeignKey(
        "catalog.Component",
        on_delete=models.PROTECT,
        related_name="fmea_items",
        verbose_name="Компонент",
    )
    failure_mode = models.CharField("Вид отказа", max_length=255)
    failure_cause = models.TextField("Причина отказа")
    failure_effect = models.TextField("Последствие отказа")
    severity = models.PositiveSmallIntegerField(
        "Тяжесть (S)",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    occurrence = models.PositiveSmallIntegerField(
        "Вероятность (O)",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    detection = models.PositiveSmallIntegerField(
        "Вероятность обнаружения (D)",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
    )
    rpn = models.IntegerField("RPN", editable=False)
    action_priority = models.CharField(
        "Приоритет действий",
        max_length=20,
        choices=ActionPriority.choices,
    )
    recommended_action = models.TextField("Рекомендуемое действие", blank=True)
    responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsible_fmea_items",
        verbose_name="Ответственный",
    )
    due_date = models.DateField("Срок", null=True, blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.OPEN,
    )
    source = models.CharField(
        "Источник",
        max_length=20,
        choices=ItemSource.choices,
        default=ItemSource.MANUAL,
    )
    source_reference = models.CharField(
        "Ссылка на источник (РЭ/ТУ/пункт)",
        max_length=255,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_fmea_items",
        verbose_name="Создал",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        verbose_name = "Пункт FMEA"
        verbose_name_plural = "Пункты FMEA"
        ordering = ("-rpn", "component_id")

    def __str__(self):
        return f"{self.component.code}: {self.failure_mode} (RPN={self.rpn})"

    @staticmethod
    def calc_priority(rpn: int) -> str:
        if rpn >= 250:
            return ActionPriority.CRITICAL
        if rpn >= 126:
            return ActionPriority.HIGH
        if rpn >= 51:
            return ActionPriority.MEDIUM
        return ActionPriority.LOW

    def clean(self):
        super().clean()
        if self.component_id and self.revision_id:
            if self.component.product_id != self.revision.product_id:
                raise ValidationError("Компонент должен принадлежать тому же изделию, что и ревизия")

    def save(self, *args, **kwargs):
        self.rpn = self.severity * self.occurrence * self.detection
        self.action_priority = self.calc_priority(self.rpn)
        super().save(*args, **kwargs)


class RiskDependency(models.Model):
    revision = models.ForeignKey(
        FMEARevision,
        on_delete=models.CASCADE,
        related_name="dependencies",
        verbose_name="Ревизия",
    )
    source_item = models.ForeignKey(
        FMEAItem,
        on_delete=models.CASCADE,
        related_name="outgoing_dependencies",
        verbose_name="Источник",
    )
    target_item = models.ForeignKey(
        FMEAItem,
        on_delete=models.CASCADE,
        related_name="incoming_dependencies",
        verbose_name="Цель",
    )
    relation_type = models.CharField(
        "Тип связи",
        max_length=20,
        choices=DependencyType.choices,
    )
    description = models.TextField("Пояснение", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Связь рисков"
        verbose_name_plural = "Связи рисков"
        ordering = ("revision_id",)
        constraints = [
            models.UniqueConstraint(
                fields=["revision", "source_item", "target_item", "relation_type"],
                name="uniq_risk_dependency",
            )
        ]

    def __str__(self):
        return f"{self.source_item_id} -> {self.target_item_id} [{self.get_relation_type_display()}]"


class Attachment(models.Model):
    product = models.ForeignKey(
        "catalog.MedicalProduct",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name="Изделие",
    )
    revision = models.ForeignKey(
        FMEARevision,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name="Ревизия",
    )
    item = models.ForeignKey(
        FMEAItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="attachments",
        verbose_name="Пункт FMEA",
    )
    file = models.CharField("Ключ в хранилище", max_length=500)
    original_name = models.CharField("Исходное имя", max_length=255)
    content_type = models.CharField("MIME-тип", max_length=100)
    size = models.BigIntegerField("Размер, байт")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_attachments",
        verbose_name="Загрузил",
    )
    created_at = models.DateTimeField("Загружен", auto_now_add=True)

    class Meta:
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"
        ordering = ("-created_at",)

    def __str__(self):
        return self.original_name


class LLMSuggestion(models.Model):
    product = models.ForeignKey(
        "catalog.MedicalProduct",
        on_delete=models.CASCADE,
        related_name="llm_suggestions",
        verbose_name="Изделие",
    )
    revision = models.ForeignKey(
        FMEARevision,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="llm_suggestions",
        verbose_name="Ревизия",
    )
    component = models.ForeignKey(
        "catalog.Component",
        on_delete=models.CASCADE,
        related_name="llm_suggestions",
        verbose_name="Компонент",
    )
    prompt = models.TextField("Запрос")
    response = models.JSONField("Ответ")
    provider = models.CharField("Провайдер", max_length=50, default="stub")
    model_name = models.CharField("Модель", max_length=100, blank=True)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=SuggestionStatus.choices,
        default=SuggestionStatus.NEW,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="llm_suggestions",
        verbose_name="Запросил",
    )
    applied_item = models.ForeignKey(
        FMEAItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="from_suggestion",
        verbose_name="Созданный пункт",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "LLM-предложение"
        verbose_name_plural = "LLM-предложения"
        ordering = ("-created_at",)

    def __str__(self):
        return f"Предложение для {self.component.code} [{self.get_status_display()}]"


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="Пользователь",
    )
    action = models.CharField("Действие", max_length=50)
    entity_type = models.CharField("Тип сущности", max_length=50)
    entity_id = models.CharField("ID сущности", max_length=50)
    payload = models.JSONField("Данные", default=dict, blank=True)
    ip_address = models.GenericIPAddressField("IP-адрес", null=True, blank=True)
    created_at = models.DateTimeField("Время", auto_now_add=True)

    class Meta:
        verbose_name = "Журнал аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id} [{self.created_at:%Y-%m-%d %H:%M}]"
