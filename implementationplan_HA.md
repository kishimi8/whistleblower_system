# High Availability (HA) & Production Deployment Implementation Plan

This document outlines the architecture, configuration, and step-by-step roadmap for deploying the Whistleblower System in a High Availability (HA) production environment with load balancing, zero-downtime replication, shared media storage, and isolated build pipelines.

---

## 1. High Availability Architecture Overview

```
                          [ Public Traffic ]
                                 │
                         ┌───────▼───────┐
                         │   TLS / HTTPS │ Port 80 / 443
                         │  Nginx Load   │ (Static & Media
                         │    Balancer   │  Direct Serving)
                         └───────┬───────┘
                                 │ Round-Robin Proxy (Port 8000)
             ┌───────────────────┼───────────────────┐
             ▼                   ▼                   ▼
      ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
      │  web-app-1  │     │  web-app-2  │     │  web-app-3  │
      │ (Gunicorn + │     │ (Gunicorn + │     │ (Gunicorn + │
      │   Uvicorn)  │     │   Uvicorn)  │     │   Uvicorn)  │
      └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
             │                   │                   │
             └─────────────┬─────┴─────┬─────────────┘
                           │           │
              Shared Media │           │ Central Cache / Sessions
              ┌────────────▼───┐   ┌───▼───────────┐
              │  media_data    │   │  Redis Cache  │
              │ (Named Volume/ │   │ (2FA & State) │
              │ Object Storage)│   └───────────────┘
              └────────────────┘
                           │ Write & Read Traffic
                           ▼
                  ┌─────────────────┐
                  │   db-primary    │ (PostgreSQL 15 Primary)
                  │   Port: 5432    │
                  └────────┬────────┘
                           │ Streaming Replication
                           │ (WAL Streaming via replicator)
                           ▼
                  ┌─────────────────┐
                  │   db-standby    │ (PostgreSQL 15 Standby)
                  │ (Hot Standby /  │
                  │  Failover Node) │
                  └─────────────────┘
```

### Key Architectural Decisions

| Aspect | Implementation | Benefit |
| :--- | :--- | :--- |
| **Scalability** | Multi-replica Django app containers behind Nginx | Horizontal scale, zero single-point-of-failure at the app tier |
| **Static & Media Serving** | Nginx serves `/static/` and `/media/` directly via shared volumes | Offloads heavy I/O from Python Gunicorn workers |
| **Evidence Storage** | Shared named volume `media_data` (or S3/Blob in cloud) | Prevents 404s when evidence files are uploaded across different replicas |
| **Database HA** | PostgreSQL 15 Streaming Replication (`pg_basebackup -R`) | Real-time WAL streaming to standby node for failover readiness |
| **Migration Safety** | Dedicated `migration` runner service in compose | Prevents concurrent migration race conditions on multi-replica startup |
| **State Consistency** | Redis for centralized caching, sessions, and 2FA OTP state | Prevents broken login wizards and desynchronized user sessions |
| **Build Optimization** | Multi-stage Docker build (Node.js for Tailwind -> Slim Python) | Minimal container footprint (~350MB vs ~1GB), no Node in production runtime |

---

## 2. Directory Structure of HA Configuration

```
whistleblower_system/
├── Dockerfile.app                     # Multi-stage Django + Gunicorn/Uvicorn image
├── Dockerfile.nginx                   # Lightweight Nginx reverse proxy & load balancer
├── .dockerignore                      # Build context optimization
├── docker-compose.prod.yml            # Production HA orchestration
├── .env.production.example            # Production environment template
├── nginx/
│   ├── nginx.conf                     # Main Nginx configuration with upstream pooling
│   └── conf.d/
│       └── default.conf               # Virtual host, SSL termination, and static/media routing
├── postgres/
│   ├── primary/
│   │   ├── postgresql.conf            # Primary WAL replication settings
│   │   └── init-primary.sh            # Replicator user & pg_hba.conf initialization
│   └── standby/
│       └── entrypoint-standby.sh      # Automated pg_basebackup and standby runner
└── scripts/
    ├── failover.sh                    # Standby promotion script
    ├── check-replication-status.sh    # Replication lag monitoring
    └── entrypoint.sh                  # Application runtime startup script
```

---

## 3. Step-by-Step Implementation Plan

### Phase 1: Build Pipeline & Containerization

#### 1. Multi-Stage `Dockerfile.app`
Avoid installing Node.js/npm in the production Python container. Build Tailwind CSS in a temporary Node stage and copy only the compiled output into the slim Python image.

```dockerfile
# ----------------------------------------------------
# Stage 1: Build Tailwind CSS Assets
# ----------------------------------------------------
FROM node:18-alpine AS css-builder
WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm install

COPY static ./static
COPY templates ./templates
COPY reports ./reports
COPY WhistleBlower ./WhistleBlower

RUN npx tailwindcss -i ./static/src/input.css -o ./static/src/output.css --minify

# ----------------------------------------------------
# Stage 2: Production Python Application Layer
# ----------------------------------------------------
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /code

# Install system dependencies for libpq, poppler, libmagic
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
```

#### 2. `Dockerfile.nginx`
```dockerfile
FROM nginx:1.25-alpine

# Remove default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom reverse proxy & virtual host configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf
COPY nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf

# Create directories for static, media, and SSL certs
RUN mkdir -p /var/www/static /var/www/media /etc/nginx/ssl

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
```

#### 3. `.dockerignore`
```gitignore
.git
.gitignore
.github
.idea
.vs
venv
__pycache__
*.pyc
*.pyo
*.pyd
.Python
db.sqlite3
media/
staticfiles/
node_modules/
tests/
*.log
.env
.env.*
!.env.production.example
```

---

### Phase 2: PostgreSQL 15 Streaming Replication Setup

> [!IMPORTANT]
> **PostgreSQL 12+ Removed `recovery.conf`**: Standby mode in PostgreSQL 15 requires an empty `standby.signal` file and configuration in `postgresql.conf` / `postgresql.auto.conf`. Running `pg_basebackup -R` automatically handles this configuration.

#### 1. `postgres/primary/postgresql.conf`
```ini
# Network & Connections
listen_addresses = '*'
max_connections = 100

# Write Ahead Log (WAL) for Replication
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
wal_keep_size = 1GB
hot_standby = on
archive_mode = on
archive_command = '/bin/true'  # Replace with actual WAL archive command for offsite backup if needed
```

#### 2. `postgres/primary/init-primary.sh`
This initialization script runs once on primary DB first-boot to configure authentication and create the dedicated replication user.

```bash
#!/bin/bash
set -e

echo ">>> Configuring PostgreSQL Primary for Streaming Replication..."

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${REPLICATION_USER:-replicator} WITH REPLICATION ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';
EOSQL

# Allow replication connections from the standby host in pg_hba.conf
echo "host replication ${REPLICATION_USER:-replicator} 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"
echo "host all all 0.0.0.0/0 scram-sha-256" >> "$PGDATA/pg_hba.conf"

# Reload configuration
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT pg_reload_conf();"
echo ">>> Primary replication configuration completed successfully."
```

#### 3. `postgres/standby/entrypoint-standby.sh`
This script handles the standby initialization cleanly without conflicting with `initdb`.

```bash
#!/bin/bash
set -e

echo ">>> Starting Standby Database Setup..."

# Wait until primary database is healthy and ready to accept connections
until pg_isready -h "${PRIMARY_HOST:-db-primary}" -p "${PRIMARY_PORT:-5432}" -U "${POSTGRES_USER:-postgres}"; do
  echo ">>> Waiting for primary database (${PRIMARY_HOST:-db-primary}:5432) to become available..."
  sleep 2
done

# If the standby data directory is not already initialized, clone from primary
if [ ! -s "$PGDATA/PG_VERSION" ]; then
  echo ">>> Standby data directory is empty. Cloning primary with pg_basebackup..."
  rm -rf "${PGDATA:?}"/*
  
  PGPASSWORD="${REPLICATION_PASSWORD}" pg_basebackup \
    -h "${PRIMARY_HOST:-db-primary}" \
    -p "${PRIMARY_PORT:-5432}" \
    -U "${REPLICATION_USER:-replicator}" \
    -D "$PGDATA" \
    -Fp \
    -Xs \
    -R \
    -v

  # Ensure correct permissions
  chmod 700 "$PGDATA"
  echo ">>> Base backup completed. standby.signal created."
fi

echo ">>> Starting PostgreSQL Standby server..."
exec postgres
```

---

### Phase 3: Nginx Reverse Proxy & Load Balancer Configuration

#### 1. `nginx/nginx.conf`
```nginx
user nginx;
worker_processes auto;
pid /var/run/nginx.pid;
error_log /var/log/nginx/error.log warn;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;

    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 25M; # Supports evidence file uploads

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml image/svg+xml;

    include /etc/nginx/conf.d/*.conf;
}
```

#### 2. `nginx/conf.d/default.conf`
```nginx
upstream django_app {
    least_conn; # Route to app replica with fewest active connections
    server web-app-1:8000 max_fails=3 fail_timeout=10s;
    server web-app-2:8000 max_fails=3 fail_timeout=10s;
    server web-app-3:8000 max_fails=3 fail_timeout=10s;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name whistle.finance.gov.ng localhost;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name whistle.finance.gov.ng localhost;

    ssl_certificate /etc/nginx/ssl/live.crt;
    ssl_certificate_key /etc/nginx/ssl/live.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Static Files Serving (Direct from shared volume)
    location /static/ {
        alias /var/www/static/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000, immutable";
        access_log off;
    }

    # Media Files (Uploaded evidence)
    location /media/ {
        alias /var/www/media/;
        expires 7d;
        add_header Cache-Control "private, max-age=604800";
    }

    # Proxy to Django App Replicas
    location / {
        proxy_pass http://django_app;
        proxy_http_version 1.1;
        
        # Pass essential proxy headers for Django HTTPS/CSRF
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;

        # WebSocket / ASGI support
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 60s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

---

### Phase 4: Production Orchestration (`docker-compose.prod.yml`)

```yaml
version: '3.8'

services:
  # ----------------------------------------------------
  # 1. Primary Database (PostgreSQL 15)
  # ----------------------------------------------------
  db-primary:
    image: postgres:15-alpine
    container_name: whistle_db_primary
    restart: always
    environment:
      POSTGRES_DB: ${DB_NAME:-whistle}
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      REPLICATION_USER: ${REPLICATION_USER:-replicator}
      REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./postgres/primary/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./postgres/primary/init-primary.sh:/docker-entrypoint-initdb.d/init-primary.sh:ro
    command: ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf"]
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -p 5432"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  # ----------------------------------------------------
  # 2. Standby Database (PostgreSQL 15 Hot Standby)
  # ----------------------------------------------------
  db-standby:
    image: postgres:15-alpine
    container_name: whistle_db_standby
    restart: always
    environment:
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PRIMARY_HOST: db-primary
      PRIMARY_PORT: 5432
      REPLICATION_USER: ${REPLICATION_USER:-replicator}
      REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
      PGDATA: /var/lib/postgresql/data
    volumes:
      - postgres_standby_data:/var/lib/postgresql/data
      - ./postgres/standby/entrypoint-standby.sh:/entrypoint-standby.sh:ro
    entrypoint: ["/entrypoint-standby.sh"]
    ports:
      - "5433:5432" # Exposed on 5433 on host, internal 5432
    depends_on:
      db-primary:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-postgres} -p 5432"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # ----------------------------------------------------
  # 3. Redis (Cache, Sessions & 2FA State Store)
  # ----------------------------------------------------
  redis:
    image: redis:7-alpine
    container_name: whistle_redis
    restart: always
    command: ["redis-server", "--appendonly", "yes", "--requirepass", "${REDIS_PASSWORD}"]
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # ----------------------------------------------------
  # 4. Migration & Static Collection Runner (One-Off)
  # ----------------------------------------------------
  migration:
    build:
      context: .
      dockerfile: Dockerfile.app
    container_name: whistle_migration
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY}
      DB_NAME: ${DB_NAME:-whistle}
      DB_USER: ${DB_USER:-postgres}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_HOST: db-primary
      DB_PORT: 5432
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
    volumes:
      - static_data:/code/staticfiles
      - media_data:/code/media
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py collectstatic --noinput"
    depends_on:
      db-primary:
        condition: service_healthy

  # ----------------------------------------------------
  # 5. Django Application Replicas
  # ----------------------------------------------------
  web-app-1: &web-app-template
    build:
      context: .
      dockerfile: Dockerfile.app
    restart: always
    environment:
      DEBUG: "False"
      SECRET_KEY: ${SECRET_KEY}
      ALLOWED_HOSTS: ${ALLOWED_HOSTS:-whistle.finance.gov.ng,localhost,web-app-1,web-app-2,web-app-3}
      CSRF_TRUSTED_ORIGINS: ${CSRF_TRUSTED_ORIGINS:-https://whistle.finance.gov.ng}
      DB_NAME: ${DB_NAME:-whistle}
      DB_USER: ${DB_USER:-postgres}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_HOST: db-primary
      DB_PORT: 5432
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/1
      SECURE_SSL_REDIRECT: "False" # Handled by Nginx
    volumes:
      - static_data:/code/staticfiles:ro
      - media_data:/code/media
    depends_on:
      migration:
        condition: service_completed_successfully
      redis:
        condition: service_healthy

  web-app-2:
    <<: *web-app-template
    container_name: whistle_app_2

  web-app-3:
    <<: *web-app-template
    container_name: whistle_app_3

  # ----------------------------------------------------
  # 6. Nginx Reverse Proxy / Load Balancer
  # ----------------------------------------------------
  nginx:
    build:
      context: .
      dockerfile: Dockerfile.nginx
    container_name: whistle_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_data:/var/www/static:ro
      - media_data:/var/www/media:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - web-app-1
      - web-app-2
      - web-app-3

volumes:
  postgres_primary_data:
  postgres_standby_data:
  redis_data:
  static_data:
  media_data:
```

---

### Phase 5: Django Settings Adjustments (`WhistleBlower/settings.py`)

Update `WhistleBlower/settings.py` to support SSL termination via Nginx, Redis-backed sessions/caching, and dynamic environment variables:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ----------------------------------------------------
# Reverse Proxy & SSL Security Settings
# ----------------------------------------------------
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
CSRF_TRUSTED_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS', 
    'https://whistle.finance.gov.ng'
).split(',')

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ----------------------------------------------------
# Centralized Redis Cache & Sessions (HA State)
# ----------------------------------------------------
REDIS_URL = os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# ----------------------------------------------------
# Static & Media Storage
# ----------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

### Phase 6: Operational & Failover Scripts

#### 1. Standby Failover Script (`scripts/failover.sh`)
```bash
#!/bin/bash
set -e

echo "=== INITIATING STANDBY PROMOTION ==="

# Step 1: Promote the standby PostgreSQL instance to primary
docker compose -f docker-compose.prod.yml exec db-standby pg_ctl promote -D /var/lib/postgresql/data

echo "Standby promoted to primary successfully."

# Step 2: Update App container routing
echo "NOTE: Update DB_HOST=db-standby in .env.production and execute:"
echo "docker compose -f docker-compose.prod.yml up -d --no-deps web-app-1 web-app-2 web-app-3"
```

#### 2. Replication Health Monitoring Script (`scripts/check-replication-status.sh`)
```bash
#!/bin/bash
set -e

echo "=== PRIMARY REPLICATION STATUS ==="
docker compose -f docker-compose.prod.yml exec db-primary psql -U postgres -d whistle -c "
SELECT 
    client_addr AS standby_ip,
    state,
    sync_state,
    sync_priority,
    pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) AS write_lag_bytes,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;
"

echo "=== STANDBY RECOVERY STATUS ==="
docker compose -f docker-compose.prod.yml exec db-standby psql -U postgres -d whistle -c "
SELECT 
    pg_is_in_recovery() AS is_standby,
    pg_last_wal_receive_lsn() AS last_received_lsn,
    pg_last_wal_replay_lsn() AS last_replayed_lsn,
    pg_last_xact_replay_timestamp() AS last_replay_timestamp;
"
```

---

## 4. Verification & Testing Checklist

- [ ] **Image Builds**: Verify `Dockerfile.app` builds cleanly without Node.js in the final layer (`docker build -f Dockerfile.app -t whistle-app .`).
- [ ] **Streaming Replication**: Boot `db-primary` and `db-standby`; run `scripts/check-replication-status.sh` to confirm `state = streaming` and `replay_lag_bytes = 0`.
- [ ] **Migration Synchronization**: Verify the `migration` container completes successfully before `web-app-1`, `2`, and `3` start.
- [ ] **Evidence Upload Consistency**: Upload an evidence file to Report submission; verify the uploaded file is accessible via Nginx `/media/` across all 3 web instances.
- [ ] **2FA Login Consistency**: Test multi-step OTP login to verify session state is preserved across round-robin routed requests via Redis.
- [ ] **Failover Execution**: Stop `db-primary`, execute `scripts/failover.sh`, and verify `db-standby` serves read/write queries.
