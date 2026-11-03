.PHONY: up down build logs ps migrate makemigrations seed test lint fmt shell dbshell frontend-install frontend-build

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

ps:
	docker compose ps

migrate:
	docker compose exec backend python manage.py migrate

makemigrations:
	docker compose exec backend python manage.py makemigrations

seed:
	docker compose exec backend python manage.py seed_demo

test:
	docker compose exec backend pytest
	docker compose exec frontend npm run lint

lint:
	docker compose exec backend ruff check .
	docker compose exec backend ruff format --check .
	docker compose exec frontend npm run lint

fmt:
	docker compose exec backend ruff check --fix .
	docker compose exec backend ruff format .

shell:
	docker compose exec backend python manage.py shell

dbshell:
	docker compose exec backend python manage.py dbshell

frontend-install:
	npm --prefix frontend install

frontend-build:
	npm --prefix frontend run build
