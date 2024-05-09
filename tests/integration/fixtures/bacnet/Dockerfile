FROM python:3.9 as base

WORKDIR /opt

COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY virtual_bacnet.py virtual_bacnet.py
COPY BACpypes.ini .
