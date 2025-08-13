FROM python:3.11
# install 'uv'
# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh
# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh
# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy project
ADD buildingmotif /opt/buildingmotif
ADD libraries /opt/libraries
ADD migrations /opt/migrations
COPY alembic.ini /opt/
COPY pyproject.toml /opt/
COPY poetry.lock /opt/
ADD docs /opt/docs
ADD buildingmotif/api/start.sh /opt/start.sh
WORKDIR /opt/

ENV UV_SYSTEM_PYTHON=1
RUN uv  pip install -r /opt/pyproject.toml --pre
RUN uv pip install -e '.[postgres, topquadrant]' --pre
ENV PATH="/opt/.venv/bin:$PATH"


# Install dpeendencies
RUN chmod +x /opt/start.sh

CMD /opt/start.sh
