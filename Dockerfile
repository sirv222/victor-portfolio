
# ==========================================
# STAGE 1: BUILD DEPENDENCIES
# ==========================================

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Dependencies needed to compile psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create isolated Python environment
RUN python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ==========================================
# STAGE 2: PRODUCTION IMAGE
# ==========================================

FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime PostgreSQL library
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies
COPY --from=builder /opt/venv /opt/venv

# Copy project files
COPY . .

# Create non-root application user
RUN addgroup --system django && \
    adduser --system --ingroup django django && \
    mkdir -p /app/staticfiles /app/media && \
    chown -R django:django /app

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s \
    --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9000/')" || exit 1

# Collect static files and start Gunicorn
CMD ["sh", "-c", "python manage.py collectstatic --noinput && gunicorn my_portfolio.wsgi:application --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120"]