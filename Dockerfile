FROM python:3.8

# Copy project
WORKDIR /buildingmotif
COPY ./buildingmotif ./buildingmotif
COPY ./libraries ./libraries

# Install Dependices
RUN pip install poetry && poetry config virtualenvs.create false
COPY ./poetry.lock .
COPY ./pyproject.toml .
COPY ./README.md .
RUN poetry install --no-dev