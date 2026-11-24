# 02. Доменная модель

## 1. Обзор

Домен строится вокруг изделия, его структуры и версионных FMEA-ревизий. Компоненты изделия анализируются в пунктах FMEA; пункты связываются направленными зависимостями для графа; вложения и LLM-предложения привязаны к изделию, ревизии или компоненту.

Основные сущности:
`User`, `MedicalProduct`, `ProductVariant`, `Component`, `FMEARevision`, `FMEAItem`, `RiskDependency`, `Attachment`, `LLMSuggestion`, `AuditLog`.

## 2. ER-диаграмма

```mermaid
erDiagram
    USER ||--o{ MEDICAL_PRODUCT : creates
    USER ||--o{ FMEA_REVISION : creates
    USER ||--o{ FMEA_ITEM : creates
    USER ||--o{ ATTACHMENT : uploads
    USER ||--o{ LLM_SUGGESTION : requests
    USER ||--o{ AUDIT_LOG : performs

    MEDICAL_PRODUCT ||--o{ PRODUCT_VARIANT : has
    MEDICAL_PRODUCT ||--o{ COMPONENT : contains
    PRODUCT_VARIANT ||--o{ COMPONENT : variant
    COMPONENT ||--o{ COMPONENT : parent

    MEDICAL_PRODUCT ||--o{ FMEA_REVISION : has
    PRODUCT_VARIANT ||--o{ FMEA_REVISION : variant
    FMEA_REVISION ||--o{ FMEA_ITEM : contains
    COMPONENT ||--o{ FMEA_ITEM : analyzed_in

    FMEA_REVISION ||--o{ RISK_DEPENDENCY : has
    FMEA_ITEM ||--o{ RISK_DEPENDENCY : source
    FMEA_ITEM ||--o{ RISK_DEPENDENCY : target

    MEDICAL_PRODUCT ||--o{ ATTACHMENT : has
    FMEA_REVISION ||--o{ ATTACHMENT : has
    FMEA_ITEM ||--o{ ATTACHMENT : has

    COMPONENT ||--o{ LLM_SUGGESTION : for
    FMEA_REVISION ||--o{ LLM_SUGGESTION : context
    LLM_SUGGESTION ||--o| FMEA_ITEM : applied_as
```

## 3. Перечисления

| Перечисление | Значения |
|---|---|
| `Role` | `engineer`, `quality`, `admin` |
| `ProductStatus` | `active`, `archived` |
| `Criticality` | `low`, `medium`, `high`, `critical` |
| `RevisionStatus` | `draft`, `review`, `approved`, `archived` |
| `ItemStatus` | `open`, `in_progress`, `done`, `accepted` |
| `ItemSource` | `manual`, `llm` |
| `DependencyType` | `causes`, `affects`, `mitigates` |
| `SuggestionStatus` | `new`, `applied`, `rejected` |
| `ActionPriority` | `low`, `medium`, `high`, `critical` |

## 4. Сущности

### 4.1 User

Пользователь системы. Аутентификация по email, пароль хранится в виде хеша Django.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `email` | varchar(254) | unique, not null | Логин |
| `password` | varchar(128) | not null | Хеш пароля |
| `full_name` | varchar(255) | blank | ФИО |
| `role` | enum `Role` | not null, default `engineer` | Роль |
| `position` | varchar(255) | blank | Должность |
| `is_active` | boolean | default true | Активность |
| `last_login` | timestamptz | null | Последний вход |

Правила:
- email приводится к нижнему регистру и уникален без учёта регистра.
- Пользователи создаются и деактивируются в Django admin; отдельный users API не входит в MVP.
- Смена роли доступна администратору через Django admin.

### 4.2 MedicalProduct

Изделие медицинского назначения.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `code` | varchar(100) | unique, not null | Обозначение, например `HUM-001` |
| `name` | varchar(255) | not null | Наименование |
| `manufacturer` | varchar(255) | blank | Изготовитель; в демо-данных пусто |
| `tu_code` | varchar(100) | blank | Обозначение ТУ |
| `description` | text | blank | Назначение и особенности |
| `status` | enum `ProductStatus` | default `active` | Статус |
| `created_by` | FK `User` | not null, protect | Автор |
| `created_at` | timestamptz | auto | Создан |
| `updated_at` | timestamptz | auto | Изменён |

Правила:
- Изделие с ревизиями не удаляется, а переводится в `archived`.
- Код изделия уникален.

### 4.3 ProductVariant

Исполнение изделия с отличающимися параметрами.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `product_id` | FK `MedicalProduct` | not null, cascade | Изделие |
| `code` | varchar(100) | not null | Обозначение исполнения |
| `name` | varchar(255) | not null | Название |
| `settings` | jsonb | default `{}` | Параметры: температуры, влажность, поток |
| `is_default` | boolean | default false | Исполнение по умолчанию |
| `created_at` | timestamptz | auto | Создан |

Ограничения:
- `unique(product_id, code)`.
- В рамках изделия только одно исполнение может быть `is_default`.

Пример `settings`:
```json
{
  "output_temperature_c": [28, 38],
  "humidity_percent": [50, 75, 100],
  "flow_l_min": [2, 50],
  "warmup_min": 20,
  "chamber_volume_ml": 150,
  "ip_rating": "IPX1"
}
```

### 4.4 Component

Компонент или функциональный узел изделия. Поддерживает иерархию.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `product_id` | FK `MedicalProduct` | not null, cascade | Изделие |
| `variant_id` | FK `ProductVariant` | null, set null | Исполнение, если компонент специфичен |
| `parent_id` | FK `Component` | null, protect | Родительский узел |
| `code` | varchar(100) | not null | Обозначение |
| `name` | varchar(255) | not null | Наименование |
| `component_type` | varchar(100) | blank | Тип: механический, электрический, ПО и т.п. |
| `description` | text | blank | Назначение |
| `criticality` | enum `Criticality` | default `medium` | Критичность |
| `is_active` | boolean | default true | Активен |
| `created_at` | timestamptz | auto | Создан |
| `updated_at` | timestamptz | auto | Изменён |

Ограничения:
- `unique(product, variant, code)`; для демо-компонентов `variant` не заполняется.
- `parent_id != id`.
- Родитель принадлежит тому же изделию.
- Удаление запрещено, если есть `FMEAItem`; используется архивирование.

### 4.5 FMEARevision

Версия FMEA-таблицы для изделия и исполнения.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `product_id` | FK `MedicalProduct` | not null, cascade | Изделие |
| `variant_id` | FK `ProductVariant` | null, set null | Исполнение |
| `version` | varchar(20) | not null | Версия, например `1.0` |
| `status` | enum `RevisionStatus` | default `draft` | Статус |
| `based_on` | FK `FMEARevision` | null, set null | Ревизия-основа |
| `change_reason` | text | blank | Причина изменения |
| `created_by` | FK `User` | not null, protect | Автор |
| `approved_by` | FK `User` | null, protect | Утвердивший |
| `approved_at` | timestamptz | null | Дата утверждения |
| `created_at` | timestamptz | auto | Создана |
| `updated_at` | timestamptz | auto | Изменена |

Ограничения:
- `unique(product, variant, version)`.
- `approved_by` и `approved_at` заполняются одновременно.
- `based_on_id` не может ссылаться на саму ревизию.

Переходы статусов:

```text
draft --submit--> review --approve--> approved --archive--> archived
  ^                  |
  |-----reject-------|
```

| Переход | Кто | Условие |
|---|---|---|
| `draft -> review` | engineer, quality | Есть хотя бы один пункт FMEA |
| `review -> draft` | quality, admin | Причина отклонения заполнена |
| `review -> approved` | quality, admin | Нет пустых обязательных полей, S/O/D валидны |
| `approved -> archived` | admin | Ревизия больше не используется |
| `draft -> archived` | admin | Отмена черновика |

Правила:
- В `approved` ревизия доступна только для чтения.
- Новая ревизия создаётся клонированием предыдущей; пункты и связи копируются.

### 4.6 FMEAItem

Строка FMEA-таблицы.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `revision_id` | FK `FMEARevision` | not null, cascade | Ревизия |
| `component_id` | FK `Component` | not null, protect | Компонент |
| `failure_mode` | varchar(255) | not null | Вид отказа |
| `failure_cause` | text | not null | Причина |
| `failure_effect` | text | not null | Последствие |
| `severity` | smallint | 1–10 | S |
| `occurrence` | smallint | 1–10 | O |
| `detection` | smallint | 1–10 | D |
| `rpn` | integer | вычисляется в `save()` | `S × O × D` |
| `action_priority` | enum `ActionPriority` | not null | Приоритет действий |
| `recommended_action` | text | blank | Рекомендуемое действие |
| `responsible_id` | FK `User` | null, set null | Ответственный |
| `due_date` | date | null | Срок |
| `status` | enum `ItemStatus` | default `open` | Статус |
| `source` | enum `ItemSource` | default `manual` | Источник |
| `source_reference` | varchar(255) | blank | Ссылка на источник; для LLM — `Демонстрационная LLM-заглушка` |
| `created_by` | FK `User` | not null, protect | Автор |
| `created_at` | timestamptz | auto | Создан |
| `updated_at` | timestamptz | auto | Изменён |

Правила:
- `rpn` — вычисляется как `severity * occurrence * detection` при сохранении; вручную не редактируется.
- `action_priority` пересчитывается при изменении S/O/D.
- Компонент должен принадлежать изделию ревизии.
- В ревизии `approved` пункт доступен только для чтения.
- В ревизии `review` оценки и действия может менять только quality/admin.
- Пункты с `source=llm` создаются только после подтверждения предложения.

### 4.7 RiskDependency

Направленная связь между пунктами FMEA для графа.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `revision_id` | FK `FMEARevision` | not null, cascade | Ревизия |
| `source_item_id` | FK `FMEAItem` | not null, cascade | Источник |
| `target_item_id` | FK `FMEAItem` | not null, cascade | Цель |
| `relation_type` | enum `DependencyType` | not null | Тип связи |
| `description` | text | blank | Пояснение |
| `created_at` | timestamptz | auto | Создана |

Ограничения:
- `source_item_id != target_item_id`.
- Оба пункта принадлежат одной ревизии.
- `unique(revision_id, source_item_id, target_item_id, relation_type)`.

Семантика:
- `causes` — отказ-источник вызывает отказ-цель.
- `affects` — отказ-источник усиливает последствие цели.
- `mitigates` — действие по источнику снижает риск цели.

### 4.8 Attachment

Файл, привязанный к изделию, ревизии или пункту.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `product_id` | FK `MedicalProduct` | null, cascade | Изделие |
| `revision_id` | FK `FMEARevision` | null, cascade | Ревизия |
| `item_id` | FK `FMEAItem` | null, cascade | Пункт FMEA |
| `file` | varchar(500) | not null | Ключ объекта в MinIO |
| `original_name` | varchar(255) | not null | Исходное имя |
| `content_type` | varchar(100) | not null | MIME-тип |
| `size` | bigint | not null | Размер, байт |
| `uploaded_by` | FK `User` | not null, protect | Загрузивший |
| `created_at` | timestamptz | auto | Загружен |

Ограничения:
- Ровно один из `product_id`, `revision_id`, `item_id` заполнен.
- Размер не более 20 МБ.
- Разрешённые MIME: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `image/png`, `image/jpeg`.
- Имя файла очищается от путей и опасных символов; физический ключ генерируется UUID.

### 4.9 LLMSuggestion

Предложение, сгенерированное LLM-провайдером (в MVP — заглушкой).

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `product_id` | FK `MedicalProduct` | not null, cascade | Изделие |
| `revision_id` | FK `FMEARevision` | null, set null | Контекст ревизии |
| `component_id` | FK `Component` | not null, cascade | Компонент |
| `prompt` | text | not null | Запрос |
| `response` | jsonb | not null | Структурированные предложения |
| `provider` | varchar(50) | not null | `stub`, позже `webllm` / `rag` |
| `model_name` | varchar(100) | blank | Название модели |
| `status` | enum `SuggestionStatus` | default `new` | Статус |
| `created_by` | FK `User` | not null, protect | Автор запроса |
| `applied_item_id` | FK `FMEAItem` | null, set null | Созданный пункт |
| `created_at` | timestamptz | auto | Создано |

Формат `response`:
```json
{
  "disclaimer": "Демонстрационная заглушка на правилах, не реальная языковая модель.",
  "suggestions": [
    {
      "failure_mode": "Отказ компонента HEATER",
      "failure_cause": "Потенциальный дефект или износ элемента HEATER",
      "failure_effect": "Нарушение функции компонента HEATER в составе изделия",
      "severity": 7,
      "occurrence": 4,
      "detection": 5,
      "recommended_action": "Проверить проектную документацию и добавить контроль параметра",
      "source_reference": "Демонстрационная LLM-заглушка"
    }
  ]
}
```

Правила:
- Предложение не создаёт пункт FMEA автоматически.
- При применении создаётся `FMEAItem` с `source=llm`, а предложение получает ссылку `applied_item_id`.
- Связь односторонняя: `LLMSuggestion -> FMEAItem`, обратного внешнего ключа нет, чтобы избежать циклической зависимости миграций.
- Отклонённое предложение сохраняется для аудита.

### 4.10 AuditLog

Журнал значимых действий.

| Поле | Тип | Ограничения | Описание |
|---|---|---|---|
| `id` | bigint | PK | Идентификатор |
| `user_id` | FK `User` | null, set null | Пользователь |
| `action` | varchar(50) | not null | `create`, `update`, `delete`, `archive`, `clone`, `submit`, `approve`, `reject`, `bulk_update`, `upload`, `export`, `request`, `apply` |
| `entity_type` | varchar(50) | not null | Имя сущности |
| `entity_id` | varchar(50) | not null | Идентификатор |
| `payload` | jsonb | default `{}` | Изменённые поля без секретов |
| `ip_address` | inet | null | IP клиента |
| `created_at` | timestamptz | auto | Время |

Правила:
- Пароли, токены и содержимое файлов в `payload` не попадают.
- Запись создаётся в сервисном слое, а не в сигналах модели.

## 5. Расчёт риска

```text
RPN = S × O × D
```

Диапазон: `1 ≤ S, O, D ≤ 10`, `1 ≤ RPN ≤ 1000`.

Приоритет действий:

| Условие | Приоритет |
|---|---|
| `RPN >= 250` | `critical` |
| `126 <= RPN < 250` | `high` |
| `51 <= RPN < 126` | `medium` |
| `RPN <= 50` | `low` |

Цвета в UI:
- `critical` — тёмно-красный;
- `high` — красный;
- `medium` — жёлтый;
- `low` — зелёный.

## 6. Матрица прав

| Действие | engineer | quality | admin |
|---|---|---|---|
| Просмотр изделий и FMEA | да | да | да |
| Создание/редактирование изделия | да | да | да |
| Архивирование изделия | нет | да | да |
| Управление компонентами | да | да | да |
| Создание черновика ревизии | да | да | да |
| Редактирование черновика | да | да | да |
| Редактирование ревизии в `review` | нет | да | да |
| Отправка на проверку | да | да | да |
| Утверждение ревизии | нет | да | да |
| Возврат на доработку | нет | да | да |
| Удаление пункта FMEA в черновике | да | да | да |
| Запрос LLM-подсказки | да | да | да |
| Применение LLM-подсказки | да | да | да |
| Отклонение LLM-подсказки | да (автор) | да | да |
| Просмотр отчётов | да | да | да |
| Экспорт отчётов | да | да | да |
| Управление пользователями | нет | нет | да |
| Просмотр аудита | нет | нет | да |

## 7. Инварианты и бизнес-правила

1. Компонент, ревизия и пункт FMEA не могут ссылаться на разные изделия.
2. В утверждённой ревизии запрещены любые изменения, кроме архивирования.
3. RPN не хранится в пользовательском вводе и всегда вычисляется.
4. Связь не может соединять пункт с самим собой или пункты разных ревизий.
5. Изделие не удаляется физически через API: оно переводится в `archived`.
6. Компонент не удаляется физически через API: он деактивируется (`is_active=false`).
7. Вложение имеет ровно одного владельца: изделие, ревизию или пункт.
8. LLM-предложение не влияет на FMEA без явного применения пользователем.
9. Ключевые действия (создание, изменение, утверждение, экспорт) фиксируются в аудите без секретов.
10. Редактирование возможно только в ревизиях `draft` и `review`; в `review` правки доступны quality/admin.

## 8. Ограничения и поля фильтрации

| Таблица | Ограничение или поле | Назначение |
|---|---|---|
| `MedicalProduct` | `unique(code)` | Уникальное обозначение изделия |
| `ProductVariant` | `unique(product, code)` | Уникальное обозначение исполнения |
| `Component` | `unique(product, variant, code)` | Уникальный код компонента |
| `FMEARevision` | `unique(product, variant, version)` | Уникальная версия ревизии |
| `RiskDependency` | `unique(revision, source_item, target_item, relation_type)` | Защита от дублей связей |
| `FMEAItem` | `revision`, `component`, `status`, `source`, `action_priority`, `rpn` | Фильтры и сортировка таблицы |
| `LLMSuggestion` | `component`, `status`, `provider` | История подсказок |
| `AuditLog` | `user`, `action`, `entity_type`, `entity_id`, `created_at` | Фильтры журнала |

## 9. Справочник компонентов для seed

Демонстрационный набор не содержит реальных обозначений и воспроизведён в обобщённом виде.

| Код | Компонент | Тип | Критичность |
|---|---|---|---|
| `BU` | Блок управления | Электронный | critical |
| `PANEL` | Панель индикации и управления | Электронный | high |
| `HEATER` | Нагреватель воды | Электрический | critical |
| `THERMOSTAT` | Термостат защиты | Электрический | critical |
| `SENSOR_TH` | Датчик температуры/влажности | Электронный | critical |
| `SENSOR_CONN` | Разъём датчика | Электрический | medium |
| `CHAMBER` | Камера увлажнителя | Механический | high |
| `CHAMBER_BASE` | Основание камеры | Механический | high |
| `AUTOFILL` | Система автозаполнения | Механический | medium |
| `POWER_CABLE` | Кабель питания | Электрический | high |
| `HEATER_ADAPTER` | Адаптер нагревательного провода | Электрический | medium |
| `CIRCUIT` | Дыхательный контур | Аксессуар | high |
| `BRACKET` | Кронштейн | Механический | low |
| `THERMOMETER` | Термометр | Механический | low |
| `VENTS` | Вентиляционные отверстия | Механический | medium |
| `HOUSING` | Корпус | Механический | low |
| `LIMIT_BTN` | Кнопка-ограничитель | Механический | low |
| `POWER_BTN` | Кнопка включения | Электрический | low |
| `TEST_CONN` | Разъём для тестирования | Электрический | low |

## 10. Демонстрационные коды отказов

| Код | Условная причина | Последствие | Связанные компоненты |
|---|---|---|---|
| `E1` | Превышение температуры, перегрев нагревательного элемента | Перегрев, повреждение контура | `HEATER`, `SENSOR_TH`, `THERMOSTAT` |
| `E2` | Нет потока, неисправен нагреватель или датчик | Отсутствие увлажнения, отказ терапии | `HEATER`, `SENSOR_TH`, `CIRCUIT` |
| `E3` | Разрыв цепи датчика | Некорректное управление температурой | `SENSOR_TH`, `SENSOR_CONN` |
| `HUM` | Влажность не достигает уровня, нет воды в камере | Сухость дыхательной смеси | `CHAMBER`, `AUTOFILL`, `HEATER` |

## 11. Источники доменных данных

| Источник | Что берём |
|---|---|
| Демонстрационное описание изделия | устройство, органы управления, условные коды отказов |
| Демонстрационные технические параметры | характеристики, комплектность, ресурсы |
| Демонстрационные требования | требования безопасности, приёмка, методы контроля |
| ГОСТ ISO 8185-2012 | требования к увлажнителям дыхательных смесей |
| ГОСТ Р МЭК 60601-1-2022 | общая безопасность медицинских электрических изделий |
| ГОСТ Р ИСО 14971 | менеджмент риска медицинских изделий |
| ГОСТ IEC 60601-1-8-2022 | сигнализация в медицинских изделиях |
