FROM python:3.8

# Copy project
WORKDIR /buildingmotif
COPY ./buildingmotif ./buildingmotif

# Install Dependices
RUN pip install poetry && poetry config virtualenvs.create false
COPY ./poetry.lock .
COPY ./pyproject.toml .
COPY ./README.md .
RUN poetry install --no-dev

COPY ./libraries ./libraries
COPY ./configs.py ./configs.py
COPY ./migrations ./migrations
COPY ./alembic.ini ./alembic.ini