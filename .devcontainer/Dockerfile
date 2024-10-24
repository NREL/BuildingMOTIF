FROM python:3.11-slim-bookworm AS devcontainer

WORKDIR /tmp/buildingmotif

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends\
    git \
    curl \
    ca-certificates \
    xz-utils \
    openssh-client \
  ; \
  rm -rf /var/lib/apt/lists/*

# Install NREL root certs. So that vscode server can install
COPY .devcontainer/certs /usr/local/share/ca-certificates
RUN update-ca-certificates

ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt

# Install Java (this is the smallest JRE I could find)
ARG JAVA_VERSION=21.0.5+11
ARG JAVA_TYPE=jre
ARG JAVA_DIR=/usr/lib/jvm/jdk-${JAVA_VERSION}-${JAVA_TYPE}
RUN case "$(uname -m)" in \
  x86_64) ARCH='x64';; \
  aarch64) ARCH='aarch64';; \
  *) echo "unsupported architecture"; exit 1 ;; \
  esac; \
  set -eux; \
  JAVA_VERSION_=$(echo ${JAVA_VERSION} | sed 's/+/_/g'); \
  mkdir -p ${JAVA_DIR}; \
  curl -fsL https://github.com/adoptium/temurin21-binaries/releases/download/jdk-${JAVA_VERSION}/OpenJDK21U-${JAVA_TYPE}_${ARCH}_linux_hotspot_${JAVA_VERSION_}.tar.gz | tar xz -C /usr/lib/jvm/; \
  ln -s ${JAVA_DIR}/bin/java /usr/bin/java

# Install Docker (CLI only, as the engine is running on the host)
ARG DOCKER_VERSION=27.3.1
ARG BUILDX_VERSION=0.17.1
RUN case "$(uname -m)" in \
  x86_64) ARCH='amd64';; \
  aarch64) ARCH='arm64';; \
  *) echo "unsupported architecture"; exit 1 ;; \
  esac; \
  set -eux; \
  curl -fsSL -o docker-ce-cli.deb https://download.docker.com/linux/debian/dists/bookworm/pool/stable/${ARCH}/docker-ce-cli_${DOCKER_VERSION}-1~debian.12~bookworm_${ARCH}.deb; \
  curl -fsSL -o docker-buildx-plugin.deb https://download.docker.com/linux/debian/dists/bookworm/pool/stable/${ARCH}/docker-buildx-plugin_${BUILDX_VERSION}-1~debian.12~bookworm_${ARCH}.deb; \
  dpkg -i docker-ce-cli.deb; \
  dpkg -i docker-buildx-plugin.deb; \
  rm docker-ce-cli.deb docker-buildx-plugin.deb

# Install NodeJS
ARG NODE_VERSION=20.18.0
RUN case "$(uname -m)" in \
  x86_64) ARCH='x64';; \
  aarch64) ARCH='arm64';; \
  *) echo "unsupported architecture"; exit 1 ;; \
  esac; \
  curl -fsL https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${ARCH}.tar.xz | tar xJ -C /usr/local --strip-components=1

# Setup poetry without virtual environments so that dependencies persist to a mounted BuildingMOTIF workspace
ENV POETRY_VIRTUALENVS_IN_PROJECT=FALSE
ENV POETRY_VIRTUALENVS_CREATE=FALSE
RUN set -eux; \
  python -m pip install poetry; \
  rm -rf ~/.cache/pip

COPY pyproject.toml pyproject.toml
COPY poetry.lock poetry.lock

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    libpq-dev \
  ; \
  poetry install --no-root --all-extras; \
  apt-mark auto gcc libc6-dev libpq-dev; \
  apt-mark manual libpq5; \
  apt-get autoremove -y; \
  rm -rf /var/lib/apt/lists/*; \
  rm -rf ~/.cache/pypoetry/cache ~/.cache/pypoetry/artifacts

# Setup angular and install dependencies globally
RUN set -eux; \
  npm install -g @angular/cli@17; \
  echo "source <(ng completion script)" > /root/.bashrc; \
  rm -rf ~/.npm/_cacache

WORKDIR /workspaces/BuildingMOTIF
