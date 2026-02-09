ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for audio/display (headless mode)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    build-essential gcc \
    # For pynput/keyboard support in headless
    libx11-dev libxtst-dev \
    # For audio processing
    portaudio19-dev libsndfile1 \
    # For screen capture (headless)
    xvfb \
 && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel \
 && if [ -s requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Install cross-platform dependencies
RUN pip install --no-cache-dir \
    pyperclip \
    pynput \
    plyer \
    fastapi \
    uvicorn[standard] \
    websockets

# Copy project
COPY . .

# Create a non-root user
RUN groupadd -r app && useradd --no-log-init -r -g app app \
 && chown -R app:app /app
USER app

# Expose API port
EXPOSE 8000

# Default: run the API server (headless mode)
# For desktop mode, run on host OS directly
CMD ["python", "-m", "uvicorn", "interface.server:app", "--host", "0.0.0.0", "--port", "8000"]
