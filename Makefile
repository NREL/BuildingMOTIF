.PHONY: test format

test:
	poetry run pytest -s -vvvv -o log_cli=true

format:
	poetry run black .
	poetry run isort .
	poetry run pylama
	poetry run mypy buildingmotif/*.py tests/*.py migrations/*.py
