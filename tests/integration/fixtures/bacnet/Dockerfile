FROM ubuntu:22.04 as base

WORKDIR /opt

RUN apt update \
    && apt install -y \
    python3.10 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

COPY virtual_bacnet.py virtual_bacnet.py
COPY BACpypes.ini .
