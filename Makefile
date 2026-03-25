.PHONY: install dev test lint typecheck check clean

install:
	uv sync

dev:
	uv sync --group dev

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

typecheck:
	uv run mypy src/

check: lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
