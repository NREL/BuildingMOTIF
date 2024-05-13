FROM python:3.10

WORKDIR /home/buildingmotif

RUN pip install poetry==1.8.2 && poetry config virtualenvs.create false

COPY pyproject.toml .
COPY poetry.lock .

RUN poetry install --no-root

COPY buildingmotif buildingmotif
COPY tests tests
COPY notebooks notebooks
COPY migrations migrations
COPY docs docs

RUN poetry install
