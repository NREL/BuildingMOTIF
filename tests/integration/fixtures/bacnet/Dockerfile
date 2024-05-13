FROM python:3.9 as base

WORKDIR /opt

COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt --break-system-packages

COPY virtual_bacnet.py virtual_bacnet.py
COPY BACpypes.ini .
