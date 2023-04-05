FROM python:3.8

# Copy project
ADD buildingmotif /opt/buildingmotif
ADD libraries /opt/libraries
COPY configs.py /opt/
ADD migrations /opt/migrations
COPY alembic.ini /opt/
COPY pyproject.toml /opt/
COPY poetry.lock /opt/
ADD docs /opt/docs
WORKDIR /opt/

# Install dpeendencies
RUN pip install poetry==1.4.0 && poetry config virtualenvs.create false
RUN ls /opt && poetry install --no-dev
RUN echo "#!/bin/bash\nset -ex\nalembic upgrade head\npython buildingmotif/api/app.py" > /opt/start.sh
RUN chmod +x /opt/start.sh

#WORKDIR /opt/buildingmotif
#COPY ./libraries ./libraries
#COPY ./configs.py ./configs.py
#COPY ./migrations ./migrations
#COPY ./alembic.ini ./alembic.ini
