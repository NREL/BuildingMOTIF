.PHONY: test format

test:
	poetry run pytest -s -vvvv

format:
	poetry run black .
	poetry run isort .
	poetry run pylama building_motif tests
	poetry run mypy building_motif/*.py tests/*.py
