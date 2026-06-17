FROM python:3.12-slim

WORKDIR /workspace

COPY pyproject.toml /workspace/pyproject.toml
COPY src /workspace/src

RUN pip install --no-cache-dir -e .
