up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api python manage.py migrate

makemigrations:
	docker compose exec api python manage.py makemigrations

seed:
	docker compose exec api python manage.py seed_kyc_tiers
	docker compose exec api python manage.py seed_asset_types

test:
	docker compose exec api pytest -q

lint:
	docker compose exec api ruff check .

format:
	docker compose exec api ruff format .

check:
	docker compose exec api python manage.py check

shell:
	docker compose exec api python manage.py shell

bootstrap:
	docker compose up -d
	docker compose exec api python manage.py migrate
	docker compose exec api python manage.py seed_kyc_tiers
	docker compose exec api python manage.py seed_asset_types
	docker compose exec api python manage.py check

reset:
	docker compose down -v
	docker compose up -d
	docker compose exec api python manage.py migrate
	docker compose exec api python manage.py seed_kyc_tiers
	docker compose exec api python manage.py seed_asset_types

.PHONY: up down logs migrate makemigrations seed test lint format check shell bootstrap reset
