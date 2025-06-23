# Stage 1: build dependencies
FROM python:3.12.11-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsasl2-dev \
    libldap2-dev \
    libssl-dev \
 && rm -rf /var/lib/apt/lists/*

COPY ./code/requirements.txt /tmp/requirements.txt
RUN pip install --prefix=/install --no-cache-dir -r /tmp/requirements.txt

# Stage 2: minimal runtime image
FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsasl2-2 \
    libldap-2.5-0 \
    libssl3 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /install /usr/local

COPY ./code /code
WORKDIR /code

CMD ["python", "exporter.py"]
