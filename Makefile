.PHONY: test format

test:
	poetry run pytest -s -vvvv

format:
	poetry run black .
	poetry run isort .
	poetry run pylama buildingmotif tests
	poetry run mypy buildingmotif/*.py tests/*.py
