FROM python:3.8

# Copy project
RUN mkdir /buildingmotif
COPY ./buildingmotif /buildingmotif/buildingmotif
COPY ./libraries /buildingmotif/libraries

# Install Dependices
COPY ./poetry.lock /buildingmotif
COPY ./pyproject.toml /buildingmotif
COPY ./README.md /buildingmotif
RUN pip install poetry
RUN poetry config virtualenvs.create false
RUN cd /buildingmotif && poetry install --no-dev