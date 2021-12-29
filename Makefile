.PHONY: update install isort black pylint mypy test build publish clean lint all ci
.DEFAULT_GOAL := all

lint: isort black pylint mypy
all: install lint test build
ci: all

PROJECT = cattrs-extras
PACKAGE = cattrs_extras
DEV ?= 1

update:
	poetry update

install:
	poetry install --remove-untracked --extras tortoise `if [ "${DEV}" = "0" ]; then echo "--no-dev"; fi`

isort:
	poetry run isort --recursive src tests

black:
	poetry run black --skip-string-normalization src tests

pylint:
	poetry run pylint src tests || poetry run pylint-exit $$?

mypy:
	poetry run mypy src tests


test:
	poetry run pytest --cov-report=term-missing --cov=cattrs_extras --cov-report=xml -v tests

build:
	poetry build

publish:
	poetry publish --build

clean:
	rm -rf build dist .venv poetry.lock .mypy_cache
