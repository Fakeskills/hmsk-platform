DC = docker compose -f infra/docker-compose.yml

.PHONY: up down build logs migrate rls seed test shell init

up:
	$(DC) up -d --build

down:
	$(DC) down

build:
	$(DC) build

logs:
	$(DC) logs -f backend

migrate:
	$(DC) exec backend alembic upgrade head

rls:
	$(DC) exec backend python -m app.db.init_rls

seed:
	$(DC) exec backend python -m app.db.seed

test:
	$(DC) exec backend pytest -v

shell:
	$(DC) exec backend bash

init: up migrate rls seed
	@echo "🚀  HMSK stack er klar. API: http://localhost:8000/docs"
