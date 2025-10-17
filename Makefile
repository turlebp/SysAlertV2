.PHONY: help install test lint run clean docker-build docker-run init-db

help:
	@echo "Available targets:"
	@echo "  install       - Install Python dependencies"
	@echo "  test          - Run test suite"
	@echo "  lint          - Run linters"
	@echo "  run           - Run bot locally"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-run    - Start via docker-compose"
	@echo "  init-db       - Initialize database"
	@echo "  clean         - Remove temporary files"

install:
	pip install --upgrade pip
	pip install -r requirements.txt

test:
	pytest -v --tb=short

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	mypy --ignore-missing-imports bot.py db.py models.py

run:
	python bot.py

docker-build:
	docker-compose build

docker-run:
	docker-compose up -d

docker-logs:
	docker-compose logs -f bot

docker-stop:
	docker-compose down

init-db:
	mkdir -p data
	python scripts/bootstrap.sh

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	rm -f *.log