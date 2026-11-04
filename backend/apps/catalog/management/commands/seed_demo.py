from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Component, Criticality, MedicalProduct, ProductStatus, ProductVariant
from apps.fmea.models import (
    ActionPriority,
    DependencyType,
    FMEAItem,
    FMEARevision,
    ItemSource,
    ItemStatus,
    RevisionStatus,
    RiskDependency,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Наполняет базу демо-данными по увлажнителю дыхательных смесей (анонимизированный вариант)"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Создание демо-данных FMEA для увлажнителя дыхательных смесей...")

        user, _ = User.objects.get_or_create(
            email="engineer@example.com",
            defaults={
                "full_name": "Ишмаев Я.Д.",
                "role": "engineer",
                "position": "Инженер-конструктор",
                "is_active": True,
            },
        )
        user.set_password("Pass12345!")
        user.position = "Инженер-конструктор"
        user.save()

        quality, _ = User.objects.get_or_create(
            email="quality@example.com",
            defaults={
                "full_name": "Менеджер по качеству",
                "role": "quality",
                "position": "Инженер по качеству",
                "is_active": True,
            },
        )
        quality.set_password("Pass12345!")
        quality.position = "Инженер по качеству"
        quality.save()

        product, created = MedicalProduct.objects.get_or_create(
            code="HUM-001",
            defaults={
                "name": "Увлажнитель дыхательных смесей",
                "manufacturer": "",
                "tu_code": "",
                "description": "Демонстрационный пример изделия для отработки методики FMEA.",
                "status": ProductStatus.ACTIVE,
                "created_by": user,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Создано изделие: {product.code}"))
        else:
            self.stdout.write(f"Изделие уже существует: {product.code}")
            product.name = "Увлажнитель дыхательных смесей"
            product.manufacturer = ""
            product.tu_code = ""
            product.description = "Демонстрационный пример изделия для отработки методики FMEA."
            product.save()

        variant_std, _ = ProductVariant.objects.get_or_create(
            product=product,
            code="V-01",
            defaults={
                "name": "Исполнение 1",
                "settings": {
                    "output_temperature_c": [28, 38],
                    "humidity_percent": [50, 75, 100],
                    "flow_l_min": [2, 50],
                    "warmup_min": 20,
                    "chamber_volume_ml": 150,
                    "ip_rating": "IPX1",
                },
                "is_default": True,
            },
        )
        if variant_std.name != "Исполнение 1":
            variant_std.name = "Исполнение 1"
            variant_std.save()

        variant_01, _ = ProductVariant.objects.get_or_create(
            product=product,
            code="V-02",
            defaults={
                "name": "Исполнение 2",
                "settings": {
                    "flow_l_min": [2, 50],
                    "warmup_min": 20,
                    "chamber_volume_ml": 150,
                    "ip_rating": "IPX1",
                },
                "is_default": False,
            },
        )
        if variant_01.name != "Исполнение 2":
            variant_01.name = "Исполнение 2"
            variant_01.save()
        self.stdout.write("Исполнения созданы/обновлены")

        components_data = [
            ("BU", "Блок управления", "Электронный", Criticality.CRITICAL, None),
            ("PANEL", "Панель индикации и управления", "Электронный", Criticality.HIGH, "BU"),
            ("HEATER", "Нагреватель воды", "Электрический", Criticality.CRITICAL, "BU"),
            ("THERMOSTAT", "Термостат защиты", "Электрический", Criticality.CRITICAL, "HEATER"),
            ("SENSOR_TH", "Датчик температуры/влажности", "Электронный", Criticality.CRITICAL, None),
            ("SENSOR_CONN", "Разъём датчика", "Электрический", Criticality.MEDIUM, "SENSOR_TH"),
            ("CHAMBER", "Камера увлажнителя", "Механический", Criticality.HIGH, None),
            ("CHAMBER_BASE", "Основание камеры", "Механический", Criticality.HIGH, "CHAMBER"),
            ("AUTOFILL", "Система автозаполнения", "Механический", Criticality.MEDIUM, "CHAMBER"),
            ("POWER_CABLE", "Кабель питания", "Электрический", Criticality.HIGH, "BU"),
            ("HEATER_ADAPTER", "Адаптер нагревательного провода", "Электрический", Criticality.MEDIUM, None),
            ("CIRCUIT", "Дыхательный контур", "Аксессуар", Criticality.HIGH, "HEATER_ADAPTER"),
            ("BRACKET", "Кронштейн", "Механический", Criticality.LOW, None),
            ("THERMOMETER", "Термометр", "Механический", Criticality.LOW, None),
            ("VENTS", "Вентиляционные отверстия", "Механический", Criticality.MEDIUM, "BU"),
            ("HOUSING", "Корпус", "Механический", Criticality.LOW, "BU"),
            ("LIMIT_BTN", "Кнопка-ограничитель", "Механический", Criticality.LOW, "PANEL"),
            ("POWER_BTN", "Кнопка включения", "Электрический", Criticality.LOW, "PANEL"),
            ("TEST_CONN", "Разъём для тестирования", "Электрический", Criticality.LOW, "BU"),
        ]
        comp_map = {}
        for code, name, ctype, crit, parent_code in components_data:
            parent = comp_map.get(parent_code) if parent_code else None
            comp, _ = Component.objects.get_or_create(
                product=product,
                code=code,
                defaults={
                    "name": name,
                    "component_type": ctype,
                    "criticality": crit,
                    "parent": parent,
                    "variant": None,
                    "is_active": True,
                },
            )
            comp.name = name
            comp.component_type = ctype
            comp.criticality = crit
            comp.parent = parent
            comp.save()
            comp_map[code] = comp
        self.stdout.write("Компоненты обновлены")

        revision, created = FMEARevision.objects.get_or_create(
            product=product,
            variant=variant_std,
            version="1.0",
            defaults={
                "status": RevisionStatus.DRAFT,
                "created_by": user,
                "change_reason": "Демонстрационная ревизия для отработки методики FMEA",
            },
        )
        revision.change_reason = "Демонстрационная ревизия для отработки методики FMEA"
        revision.save()
        if created:
            self.stdout.write(self.style.SUCCESS(f"Создана ревизия: {revision}"))
        else:
            self.stdout.write(f"Ревизия обновлена: {revision}")

        items_data = [
            ("HEATER", "Перегрев нагревательного элемента", "Отказ термостата защиты или регулятора нагрева", "Перегрев смеси, риск ожога дыхательных путей", 9, 4, 4, "Анализ функциональных отказов", "Проверка термостата защиты. Контроль работоспособности системы"),
            ("THERMOSTAT", "Отказ термостата защиты", "Заклинивание или нарушение контакта термостата", "Потеря тепловой защиты", 10, 3, 4, "Анализ функциональных отказов", "Периодическая проверка работоспособности термостата"),
            ("SENSOR_TH", "Разрыв цепи датчика температуры/влажности", "Механическое повреждение кабеля или разъёма", "Переход в аварийный режим, потеря контроля", 9, 4, 3, "Анализ функциональных отказов", "Контроль целостности кабеля и разъёма, замена при повреждении"),
            ("SENSOR_TH", "Дрейф показаний датчика", "Старение элемента, воздействие конденсата", "Некорректное регулирование", 8, 4, 5, "Анализ функциональных отказов", "Проверка соответствия параметров при контроле"),
            ("SENSOR_CONN", "Неплотный контакт в разъёме", "Окисление контактов", "Ложные срабатывания, потеря контроля", 7, 4, 4, "Анализ функциональных отказов", "Проверка надёжности контактов"),
            ("CHAMBER", "Переполнение камеры", "Ошибка пользователя", "Затекание воды в контур", 9, 5, 4, "Анализ функциональных отказов", "Соблюдение уровня заполнения, контроль конденсата"),
            ("CHAMBER", "Дефект камеры при обработке", "Износ, несоблюдение режима обработки", "Разгерметизация", 8, 4, 4, "Анализ функциональных отказов", "Осмотр перед использованием"),
            ("AUTOFILL", "Нарушение работы системы автозаполнения", "Засорение, износ уплотнений", "Снижение влажности смеси", 7, 4, 5, "Анализ функциональных отказов", "Осмотр уплотнений"),
            ("HEATER_ADAPTER", "Повреждение нагревательного провода", "Перегиб, перетирание", "Потеря подогрева, риск повреждения", 8, 4, 4, "Анализ функциональных отказов", "Осмотр изоляции, контроль параметров"),
            ("CIRCUIT", "Применение неразрешённого контура", "Несоблюдение комплектации", "Снижение безопасности", 7, 4, 5, "Анализ функциональных отказов", "Контроль комплектности"),
            ("POWER_CABLE", "Повреждение изоляции сетевого кабеля", "Механическое воздействие", "Опасность поражения электрическим током", 10, 3, 4, "Общие требования электробезопасности", "Визуальный осмотр, запрет повреждённых кабелей"),
            ("BU", "Нарушение электробезопасности", "Ослабление контактов заземления", "Превышение токов утечки", 9, 3, 3, "Общие требования электробезопасности", "Периодический контроль параметров электробезопасности"),
            ("BU", "Отказ платы управления", "Сбой элементов, помехи", "Нарушение регулирования, сбой сигнализации", 8, 3, 4, "Анализ функциональных отказов", "Проверка работоспособности при контроле"),
            ("PANEL", "Отказ звуковой сигнализации", "Неисправность излучателя", "Пропуск аварийного извещения", 10, 2, 3, "Анализ функциональных отказов", "Проверка сигнализации при контроле"),
            ("HOUSING", "Проникновение жидкости на корпус", "Пролив воды", "Короткое замыкание", 9, 3, 4, "Анализ функциональных отказов", "Исключить попадание жидкости, немедленно отключить при заливе"),
            ("VENTS", "Загрязнение вентиляционных отверстий", "Пыль", "Перегрев электронных узлов", 6, 4, 5, "Анализ функциональных отказов", "Проверка чистоты при техническом осмотре"),
            ("THERMOMETER", "Неверные показания термометра", "Загрязнение, повреждение", "Пропуск перегрева", 8, 3, 5, "Анализ функциональных отказов", "Соблюдение правил обработки, осмотр при контроле"),
            ("LIMIT_BTN", "Отказ кнопки-ограничителя", "Износ", "Неплотная фиксация", 6, 4, 5, "Анализ функциональных отказов", "Проверка фиксации при подготовке"),
            ("HEATER", "Отсутствие потока при нагреве", "Неисправен нагреватель", "Переход в аварийный режим", 8, 4, 4, "Анализ функциональных отказов", "Контроль параметров потока"),
            ("CHAMBER", "Использование недопустимых средств обработки", "Применение агрессивных веществ", "Повреждение полимерных деталей", 7, 4, 5, "Анализ функциональных отказов", "Соблюдение рекомендаций по обработке"),
        ]

        created_count = 0
        for comp_code, fmode, cause, effect, sev, occ, det, ref, action in items_data:
            comp = comp_map[comp_code]
            item, c = FMEAItem.objects.get_or_create(
                revision=revision,
                component=comp,
                failure_mode=fmode,
                defaults={
                    "failure_cause": cause,
                    "failure_effect": effect,
                    "severity": sev,
                    "occurrence": occ,
                    "detection": det,
                    "recommended_action": action,
                    "status": ItemStatus.OPEN,
                    "source": ItemSource.MANUAL,
                    "source_reference": ref,
                    "created_by": user,
                },
            )
            if c:
                created_count += 1
            else:
                item.source_reference = ref
                item.save()
        self.stdout.write(self.style.SUCCESS(f"Обновлено/создано пунктов FMEA: {created_count}"))

        items_by_mode = {item.failure_mode: item for item in FMEAItem.objects.filter(revision=revision)}
        deps = [
            (items_by_mode.get("Отказ термостата защиты"), items_by_mode.get("Перегрев нагревательного элемента"), DependencyType.CAUSES, "Потеря термозащиты"),
            (items_by_mode.get("Разрыв цепи датчика температуры/влажности"), items_by_mode.get("Перегрев нагревательного элемента"), DependencyType.AFFECTS, "Потеря обратной связи"),
            (items_by_mode.get("Переполнение камеры"), items_by_mode.get("Проникновение жидкости на корпус"), DependencyType.CAUSES, "Риск затекания воды"),
            (items_by_mode.get("Отказ термостата защиты"), items_by_mode.get("Повреждение изоляции сетевого кабеля"), DependencyType.MITIGATES, "Тепловая защита снижает риск"),
        ]
        deps_created = 0
        for src, tgt, rel, desc in deps:
            if src and tgt and src != tgt:
                _, c = RiskDependency.objects.get_or_create(
                    revision=revision,
                    source_item=src,
                    target_item=tgt,
                    relation_type=rel,
                    defaults={"description": desc},
                )
                if c:
                    deps_created += 1
        self.stdout.write(self.style.SUCCESS(f"Связей рисков: {deps_created}"))

        self.stdout.write(self.style.SUCCESS("Seed выполнен (анонимизированный)."))
        self.stdout.write("Пользователи: engineer@example.com / quality@example.com / Pass12345!")
        self.stdout.write(f"Изделие: {product.code} — {product.name}, ревизия: {revision.version}, пунктов: {FMEAItem.objects.filter(revision=revision).count()}")
