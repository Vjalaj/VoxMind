ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build deps only when needed, install requirements if present
COPY requirements.txt ./
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential gcc \
 && pip install --upgrade pip setuptools wheel \
 && if [ -s requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi \
 && apt-get purge -y --auto-remove build-essential gcc \
 && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . .

# Create a non-root user
RUN groupadd -r app && useradd --no-log-init -r -g app app \
 && chown -R app:app /app
USER app

# Default command — change to your app entrypoint (e.g. python -m jd.main)
CMD ["python", "main.py"]
