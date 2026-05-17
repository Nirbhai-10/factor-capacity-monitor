.PHONY: install test lint sim

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check src tests

sim:
	aegis-sim all
