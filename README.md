# FMEA System

Интеллектуальная система анализа видов и последствий отказов медицинских изделий.

Текущий этап: **шаг 2 — каркас проекта**. Реализованы Django 5 + DRF + SimpleJWT, кастомный пользователь, health-check, React 19 + TypeScript + Vite, Docker Compose с PostgreSQL, Redis и MinIO.

## Стек

| Слой | Технологии |
|---|---|
| Backend | Python 3.13, Django 5.2, DRF, SimpleJWT, drf-spectacular |
| База данных | PostgreSQL 16, SQLite для локального запуска без Docker |
| Кэш | Redis 7 |
| Файлы | MinIO (S3-совместимое хранилище) |
| Frontend | React 19, TypeScript, Vite 6, React-Bootstrap, axios |
| Инфраструктура | Docker Compose |

## Структура

```text
fmea-system/
├── backend/
│   ├── apps/accounts/     # пользователь, роли, JWT
│   ├── apps/core/         # health-check
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

## Быстрый старт в Docker

```bash
cp .env.example .env
make up
```

После запуска:

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost:5173 |
| API health | http://localhost:8000/api/health/ |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |
| MinIO Console | http://localhost:9001 |

Создание администратора:

```bash
docker compose exec backend python manage.py createsuperuser
```

Логин выполняется по email.

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

По умолчанию используется SQLite. Для PostgreSQL задайте `POSTGRES_HOST=localhost` и остальные `POSTGRES_*`; для Redis — `REDIS_URL=redis://localhost:6379/0`; для MinIO — `USE_S3=true` и `MINIO_ENDPOINT=http://localhost:9000`.

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
| `make test` | Тесты backend и lint frontend |
| `make lint` | ruff и eslint |
| `make fmt` | Автоформатирование backend |
| `make shell` | Django shell |
| `make dbshell` | Оболочка PostgreSQL |
| `make frontend-build` | Сборка frontend |

Команда `make seed` появится на шаге 3 вместе с демонстрационными данными.

## API

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/health/` | Проверка БД и кэша |
| `POST` | `/api/auth/token/` | Получение access/refresh JWT |
| `POST` | `/api/auth/token/refresh/` | Обновление access-токена |
| `GET` | `/api/auth/me/` | Профиль текущего пользователя |
| `GET` | `/api/schema/` | OpenAPI-схема |
| `GET` | `/api/docs/` | Swagger UI |

Пример входа:

```bash
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email":"engineer@example.com","password":"StrongPass123"}'
```

## Безопасность

- Секреты не хранятся в репозитории: используется `.env` и `.env.example`.
- Пароли хранятся только в виде хеша Django.
- JWT access-токен живёт 15 минут, refresh — 7 дней.
- Вложения ограничены по размеру и MIME-типам (будет реализовано на шаге 3).
- Демонстрационные данные не содержат персональных данных пациентов.

## Следующий шаг

Шаг 3: доменные модели `MedicalProduct`, `ProductVariant`, `Component`, `FMEARevision`, `FMEAItem`, `RiskDependency`, `Attachment`, `LLMSuggestion`, `AuditLog`; миграции, админка и `seed_demo` по документам изделия ТЕВЛАР.
