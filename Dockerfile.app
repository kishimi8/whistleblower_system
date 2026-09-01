# ====================================================
# Stage 1: Build Tailwind CSS Assets
# ====================================================
FROM node:18-alpine AS css-builder
WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm install

COPY static ./static
COPY templates ./templates
COPY reports ./reports
COPY WhistleBlower ./WhistleBlower

RUN npx @tailwindcss/cli -i ./static/src/input.css -o ./static/src/output.css --minify || npx tailwindcss -i ./static/src/input.css -o ./static/src/output.css --minify

# ====================================================
# Stage 2: Production Python Application Layer
# ====================================================
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /code

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    poppler-utils \
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /code/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /code/

# Copy compiled CSS from Stage 1
COPY --from=css-builder /build/static/src/output.css /code/static/src/output.css

# Prepare directories for static files and user uploads
RUN mkdir -p /code/staticfiles /code/media \
    && chmod -R 755 /code/staticfiles /code/media

COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "WhistleBlower.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "--timeout", "300"]
