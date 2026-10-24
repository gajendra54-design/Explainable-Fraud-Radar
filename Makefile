.PHONY: install init seed test build up down benchmark
install:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm ci
init:
	python -m backend.app.cli init
seed:
	python -m backend.app.cli seed --transactions 3000 --seed 42
test:
	python -m pytest backend/tests -q
build:
	cd frontend && npm run build
up:
	docker compose up --build -d
down:
	docker compose down
benchmark:
	python -m ml --transactions 100000 --customers 1000 --output reports/generated
