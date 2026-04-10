.PHONY: help install test lint format clean

help:
	@echo "Available targets:"
	@echo "  install  - Install package with dev dependencies"
	@echo "  test     - Run pytest"
	@echo "  lint     - Run ruff check"
	@echo "  format   - Run ruff format"
	@echo "  clean    - Remove build artifacts and caches"

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check src tests

format:
	ruff format src tests

clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
