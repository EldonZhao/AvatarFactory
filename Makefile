SHELL := /bin/bash
COMPOSE_DEV := docker compose -f docker-compose.dev.yml

.PHONY: help setup up down restart logs ps dev-api dev-admin dev-journal test lint format check web-build

help:
	@echo "Available targets (Docker-only local workflow):"
	@echo "  make setup       - Build development containers"
	@echo "  make up          - Start API + admin + journal in containers"
	@echo "  make down        - Stop and remove development containers"
	@echo "  make restart     - Restart development containers"
	@echo "  make logs        - Tail logs from all services"
	@echo "  make ps          - Show container status"
	@echo "  make dev-api     - Start API container only"
	@echo "  make dev-admin   - Start admin container only"
	@echo "  make dev-journal - Start journal container only"
	@echo "  make test        - Run Python tests inside api container"
	@echo "  make lint        - Run ruff + mypy inside api container"
	@echo "  make format      - Run black inside api container"
	@echo "  make check       - Run format check + lint + tests inside api container"
	@echo "  make web-build   - Build web-admin and web-journal inside containers"

setup:
	@$(COMPOSE_DEV) build

up:
	@$(COMPOSE_DEV) up -d

down:
	@$(COMPOSE_DEV) down

restart:
	@$(COMPOSE_DEV) down
	@$(COMPOSE_DEV) up -d

logs:
	@$(COMPOSE_DEV) logs -f --tail=200

ps:
	@$(COMPOSE_DEV) ps

dev-api:
	@$(COMPOSE_DEV) up -d api

dev-admin:
	@$(COMPOSE_DEV) up -d admin

dev-journal:
	@$(COMPOSE_DEV) up -d journal

test:
	@$(COMPOSE_DEV) run --rm api pytest tests/ -v

lint:
	@$(COMPOSE_DEV) run --rm api ruff check avatarfactory tests
	@$(COMPOSE_DEV) run --rm api mypy avatarfactory

format:
	@$(COMPOSE_DEV) run --rm api black avatarfactory tests

check:
	@$(COMPOSE_DEV) run --rm api black --check avatarfactory tests
	@$(COMPOSE_DEV) run --rm api ruff check avatarfactory tests
	@$(COMPOSE_DEV) run --rm api mypy avatarfactory
	@$(COMPOSE_DEV) run --rm api pytest tests/ -q

web-build:
	@$(COMPOSE_DEV) run --rm admin sh -lc "npm run build"
	@$(COMPOSE_DEV) run --rm journal sh -lc "npm run build"
