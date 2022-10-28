FROM python:3.8

# Copy project
WORKDIR /buildingmotif
COPY ./buildingmotif ./buildingmotif
COPY ./libraries ./libraries

# Install Dependices
RUN pip install poetry && poetry config virtualenvs.create false
COPY ./poetry.lock /buildingmotif
COPY ./pyproject.toml /buildingmotif
COPY ./README.md /buildingmotif
RUN cd /buildingmotif && poetry install --no-dev