#!/bin/bash
set -ex
poetry run alembic upgrade head
poetry run python buildingmotif/api/app.py
