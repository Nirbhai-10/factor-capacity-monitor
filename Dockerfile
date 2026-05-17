FROM python:3.11-slim AS base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[serve,viz]"

COPY web ./web
COPY web-app ./web-app

EXPOSE 8000
ENV AEGIS_HOST=0.0.0.0 AEGIS_PORT=8000
HEALTHCHECK --interval=20s --timeout=4s --retries=4 \
  CMD python -c "import urllib.request,sys; \
  sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else sys.exit(1)"

CMD ["aegis-serve"]
