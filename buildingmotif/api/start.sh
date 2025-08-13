#!/bin/bash
set -ex
alembic upgrade head
python buildingmotif/api/app.py
