FROM python:3.8

WORKDIR /home/buildingmotif

RUN pip install poetry==1.4.0 && poetry config virtualenvs.create false

COPY pyproject.toml .
COPY poetry.lock .

RUN poetry install --no-root

COPY buildingmotif buildingmotif
COPY tests tests
COPY notebooks notebooks
COPY migrations migrations
COPY docs docs

RUN poetry install