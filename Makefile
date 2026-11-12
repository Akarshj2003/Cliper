.PHONY: help up down build dev backend-dev web-dev test clean

help:
	@echo "ClipViral Development Commands:"
	@echo "  make up           - Start PostgreSQL & Redis services via docker-compose"
	@echo "  make down         - Stop docker-compose services"
	@echo "  make dev          - Run both backend & web concurrently (local)"
	@echo "  make backend-dev  - Run FastAPI backend locally"
	@echo "  make web-dev      - Run Next.js web frontend locally"
	@echo "  make test         - Run backend unit and integration tests"
	@echo "  make clean        - Remove caches, temporary files, and test artifacts"

up:
	docker compose up -d postgres redis

down:
	docker compose down

build:
	docker compose build

backend-dev:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web-dev:
	cd web && npm run dev

test:
	cd backend && pytest -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
