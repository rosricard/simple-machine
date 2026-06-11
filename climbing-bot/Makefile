# climbing-bot — build / test / run shortcuts.
# TODO: flesh out as the package takes shape.

.PHONY: help install run test lint

help:
	@echo "install - poetry install"
	@echo "run     - run the bot (demo: home + 3-waypoint trajectory)"
	@echo "test    - run the test suite"
	@echo "lint    - static checks"

install:
	poetry install

run:
	poetry run env PYTHONPATH=src python -m main

test:
	poetry run pytest

lint:
	poetry run ruff check src/ test/
