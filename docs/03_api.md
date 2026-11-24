# 03. API

## Общие правила

- Базовый префикс: `/api/`.
- Аутентификация: JWT Bearer (`Authorization: Bearer <access>`), кроме `/api/health/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/schema/`, `/api/docs/`.
- Пагинация DRF: `count`, `next`, `previous`, `results`.
- Форматы дат: `created_at`/`updated_at` — ISO 8601, `due_date` — `YYYY-MM-DD`.
- Фильтры передаются query-параметрами; поиск — `search`, сортировка — `ordering`.

## Auth и сервис

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/health/` | public | Проверка БД и кэша. `200 ok` / `503 degraded`. |
| POST | `/api/auth/token/` | public | Логин по `email`, `password`. Возвращает `access`, `refresh`, `user`. |
| POST | `/api/auth/token/refresh/` | public | Обновление access-токена. |
| GET | `/api/auth/me/` | auth | Профиль текущего пользователя. |
| GET | `/api/schema/` | public | OpenAPI schema. |
| GET | `/api/docs/` | public | Swagger UI. |

## Каталог

### Изделия

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/products/` | auth | Список изделий. Фильтр `status`, поиск `code/name/manufacturer`, ordering. |
| POST | `/api/products/` | auth | Создать изделие. |
| GET | `/api/products/{id}/` | auth | Карточка изделия. |
| PATCH | `/api/products/{id}/` | auth | Изменить изделие. Смена `status` — quality/admin. |
| DELETE | `/api/products/{id}/` | quality/admin | Архивирование: `status=archived`, физического удаления нет. |
| GET/POST | `/api/products/{id}/variants/` | auth | Исполнения изделия. |
| GET/POST | `/api/products/{id}/components/` | auth | Компоненты изделия. |

### Исполнения

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET/POST | `/api/variants/` | auth | CRUD-список исполнений. Фильтры `product`, `is_default`. |
| GET/PATCH/DELETE | `/api/variants/{id}/` | auth | Удаление запрещено, если есть связанные ревизии/компоненты. |

### Компоненты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET/POST | `/api/components/` | auth | CRUD-список компонентов. Фильтры `product`, `variant`, `parent`, `criticality`, `is_active`. |
| GET/PATCH/DELETE | `/api/components/{id}/` | auth | DELETE деактивирует компонент (`is_active=false`). |

## Ревизии FMEA

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/revisions/` | auth | Список ревизий. Фильтры `product`, `variant`, `status`, `based_on`. |
| POST | `/api/revisions/` | engineer+ | Создать ревизию (`product`, optional `variant`, `version`, `change_reason`, `based_on`). |
| GET | `/api/revisions/{id}/` | auth | Детали ревизии. |
| POST | `/api/revisions/{id}/clone/` | engineer+ | Клонировать ревизию с пунктами и связями. |
| POST | `/api/revisions/{id}/submit/` | engineer+ | `draft -> review`. |
| POST | `/api/revisions/{id}/approve/` | quality/admin | `review -> approved`. |
| POST | `/api/revisions/{id}/reject/` | quality/admin | `review -> draft`, требует `reason`. |
| POST | `/api/revisions/{id}/archive/` | admin | Архивирование ревизии. |

## Пункты FMEA

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET/POST | `/api/revisions/{id}/items/` | auth / engineer+ | Пункты ревизии. POST создаёт пункт в редактируемой ревизии. |
| POST | `/api/revisions/{id}/items/bulk/` | engineer+ | Массовое сохранение: `items[]`, `deleted_ids[]`; возвращает `items`, `created`, `updated`, `deleted`. |
| GET | `/api/items/` | auth | Плоский список пунктов. |
| GET/PATCH/DELETE | `/api/items/{id}/` | auth / engineer+ | Изменение/удаление только в редактируемой ревизии. |

Фильтры пунктов: `revision`, `component`, `status`, `source`, `action_priority`, `responsible`, `rpn_min`, `rpn_max`, `severity_min`, `severity_max`.  
Ordering: `rpn`, `severity`, `occurrence`, `detection`, `action_priority`, `created_at`, `failure_mode` (префикс `-` для DESC).

## Связи рисков и граф

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET/POST | `/api/revisions/{id}/dependencies/` | auth / engineer+ | Связи ревизии. |
| GET | `/api/revisions/{id}/graph/` | auth | Граф: `revision`, `nodes[]`, `edges[]`. |
| GET/DELETE | `/api/dependencies/` , `/api/dependencies/{id}/` | auth / engineer+ | Плоский доступ к связям. DELETE только в редактируемой ревизии. |

Типы связей: `causes`, `affects`, `mitigates`.

## Вложения

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/attachments/` | auth | Список вложений. Фильтры `product`, `revision`, `item`. |
| POST | `/api/attachments/` | engineer+ | Загрузка `multipart/form-data`: `file` + ровно один target (`product`/`revision`/`item`). |
| GET | `/api/attachments/{id}/` | auth | Метаданные вложения. |
| GET | `/api/attachments/{id}/download/` | auth | Presigned URL (`url`, `expires_in=3600`). |
| DELETE | `/api/attachments/{id}/` | auth | Удаление вложения; для вложений ревизии/пункта ревизия должна быть редактируемой. |

Ограничения: до 20 МБ, MIME `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `image/png`, `image/jpeg`.

## LLM-подсказки

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/suggestions/` | auth | Список подсказок. Фильтры `product`, `revision`, `component`, `status`, `provider`. |
| POST | `/api/suggestions/` | engineer+ | Запрос подсказки: `revision`, `component`, optional `hints`. |
| GET | `/api/suggestions/{id}/` | auth | Детали подсказки. |
| POST | `/api/suggestions/{id}/apply/` | engineer+ | Создаёт `FMEAItem` с `source=llm`, `status` подсказки -> `applied`. |
| POST | `/api/suggestions/{id}/reject/` | engineer+/author | `status` -> `rejected`. |

Текущий provider: `stub`, `model_name=rule-based-demo-v1`. Ответ содержит `disclaimer`, что это демонстрационная заглушка.

## Отчёты

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/revisions/{id}/report/?limit=10` | auth | Сводка ревизии и топ рисков. `limit` 1..100. |
| GET | `/api/revisions/{id}/report/xlsx/?limit=10` | auth | XLSX-экспорт, листы «Сводка» и «Топ рисков». |

## Аудит

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/api/audit/` | admin | Журнал аудита. |
| GET | `/api/audit/{id}/` | admin | Детали события. |

Фильтры: `user`, `action`, `entity_type`, `entity_id`, `date_from`, `date_to` (ISO datetime, например `2026-11-24` или `2026-11-24T00:00:00Z`).  
Поиск: `action`, `entity_type`, `entity_id`. Ordering: `created_at`, `action`, `entity_type`.

## Роли и ограничения

| Роль | Основные права |
|---|---|
| `engineer` | CRUD каталога/черновиков, bulk/items/dependencies/attachments/suggestions, просмотр отчётов. |
| `quality` | Всё engineer + submit/approve/reject/review-правки, архивирование изделия. |
| `admin` | Всё quality + archive revision, аудит, Django admin. |

Редактирование пунктов/связей/вложений ревизии разрешено только в `draft` и `review`; в `review` — quality/admin. Утверждённая и архивная ревизии read-only.