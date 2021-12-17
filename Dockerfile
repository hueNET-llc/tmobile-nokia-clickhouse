FROM python:3.9-slim

COPY . /exporter

WORKDIR /exporter

RUN pip install -r requirements.txt

ENTRYPOINT ["python", "-u", "exporter.py"]