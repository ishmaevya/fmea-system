# FMEA System

Интеллектуальная система анализа видов и последствий отказов медицинских изделий.

Текущий этап: **backend Этапа 3 готов**. Реализованы каталог, версионные FMEA-ревизии, пункты и связи, граф, вложения через MinIO, демонстрационная LLM-заглушка, отчёты/XLSX и журнал аудита. Frontend-интерфейс — следующий этап.

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.13, Django 5.2, DRF, SimpleJWT, django-filter, drf-spectacular |
| База данных | PostgreSQL 16, SQLite для локального запуска без Docker |
| Кэш | Redis 7 |
| Файлы | MinIO (S3-совместимое хранилище), `django-storages` |
| Отчёты | `openpyxl` (XLSX) |
| Frontend | React 19, TypeScript, Vite 6, React-Bootstrap, axios |
| Инфраструктура | Docker Compose |

## Структура

```text
fmea-system/
├── backend/
│   ├── apps/accounts/     # пользователь, роли, JWT
│   ├── apps/core/         # health-check
│   ├── apps/catalog/      # изделия, исполнения, компоненты
│   ├── apps/fmea/         # ревизии, пункты, связи, вложения, LLM, отчёты, аудит
│   ├── config/            # settings, urls, wsgi/asgi
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/api/           # axios-клиент
│   ├── src/components/    # общие компоненты
│   ├── src/pages/         # страницы
│   └── package.json
├── docs/                  # живая документация проекта
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

Документация: [область проекта](docs/01_scope.md), [доменная модель](docs/02_domain_model.md), [API](docs/03_api.md), [архитектура](docs/05_architecture.md).

## Быстрый старт в Docker

```bash
cp .env.example .env
make up
make migrate
make seed
```

После запуска:

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost:5173 |
| API health | http://localhost:8000/api/health/ |
| Swagger | http://localhost:8000/api/docs/ |
| OpenAPI schema | http://localhost:8000/api/schema/ |
| Admin | http://localhost:8000/admin/ |
| MinIO Console | http://localhost:9001 |

Демо-пользователи после `make seed`:

| Email | Пароль | Роль |
|---|---|---|
| `engineer@example.com` | `Pass12345!` | engineer |
| `quality@example.com` | `Pass12345!` | quality |

Администратор создаётся отдельно:

```bash
docker compose exec backend python manage.py createsuperuser
```

Логин выполняется по email. В Swagger в Authorize вставляйте только значение `access` без префикса `Bearer`.

## Локальный запуск без Docker

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
python manage.py migrate
python manage.py runserver
```

По умолчанию используется SQLite. Для PostgreSQL задайте `POSTGRES_HOST=localhost` и остальные `POSTGRES_*`; для Redis — `REDIS_URL=redis://localhost:6379/0`; для MinIO — `USE_S3=true` и `MINIO_ENDPOINT=http://localhost:9000`. Presigned URL для браузера формируются через `MINIO_PUBLIC_ENDPOINT`.

### Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Vite проксирует `/api` на `http://localhost:8000`.

## Команды

| Команда | Действие |
|---|---|
| `make up` | Собрать и запустить все сервисы |
| `make down` | Остановить сервисы |
| `make logs` | Логи всех сервисов |
| `make ps` | Статус контейнеров |
| `make migrate` | Применить миграции |
| `make makemigrations` | Создать миграции |
| `make seed` | Создать анонимизированные демо-данные (идемпотентно) |
| `make test` | Тесты backend и lint frontend |
| `make lint` | ruff и eslint |
| `make fmt` | Автоформатирование backend |
| `make shell` | Django shell |
| `make dbshell` | Оболочка PostgreSQL |
| `make frontend-build` | Сборка frontend |

## API

Основные группы эндпоинтов:

| Группа | Примеры |
|---|---|
| Health/auth | `/api/health/`, `/api/auth/token/`, `/api/auth/token/refresh/`, `/api/auth/me/` |
| Каталог | `/api/products/`, `/api/variants/`, `/api/components/` |
| Ревизии | `/api/revisions/`, `/api/revisions/{id}/clone/`, `/submit/`, `/approve/`, `/reject/`, `/archive/` |
| Пункты и связи | `/api/items/`, `/api/revisions/{id}/items/bulk/`, `/api/dependencies/`, `/api/revisions/{id}/graph/` |
| Вложения | `/api/attachments/`, `/api/attachments/{id}/download/` |
| LLM-заглушка | `/api/suggestions/`, `/api/suggestions/{id}/apply/`, `/reject/` |
| Отчёты | `/api/revisions/{id}/report/`, `/api/revisions/{id}/report/xlsx/` |
| Аудит | `/api/audit/` (только admin) |

Пример входа:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@example.com","password":"Pass12345!"}'
```

Полное описание — в [docs/03_api.md](docs/03_api.md).

## Демонстрационный сценарий

1. Войти как `engineer@example.com`, открыть список изделий и карточку `HUM-001`.
2. Создать черновую ревизию или клонировать существующую, добавить пункт FMEA, проверить пересчёт RPN.
3. Запросить LLM-подсказку для компонента и применить её.
4. Отправить ревизию на проверку.
5. Войти как `quality@example.com`, утвердить ревизию, построить отчёт и выгрузить XLSX.
6. Войти как администратор, созданный через `createsuperuser`, открыть `/api/audit/` и проверить журнал действий.

## Безопасность

- Секреты не хранятся в репозитории: используется `.env` и `.env.example`.
- Пароли хранятся только в виде хеша Django.
- JWT access-токен живёт 15 минут, refresh — 7 дней.
- Вложения ограничены размером 20 МБ и whitelist MIME-типов; bucket MinIO приватный.
- Аудит и ошибки API не содержат паролей, токенов и содержимого файлов.
- Демо-данные анонимизированы: реальные обозначения, изготовитель и документация не используются.

## Следующий шаг

Frontend в отдельной ветке: логин, каталог, карточка изделия, FMEA-таблица, граф, отчёты и экспорт XLSX.
