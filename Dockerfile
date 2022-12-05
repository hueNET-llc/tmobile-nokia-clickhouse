FROM python:3.11-slim-buster

COPY . /exporter

WORKDIR /exporter

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-u", "tmobile.py"]