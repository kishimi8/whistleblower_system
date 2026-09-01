#!/bin/bash
set -e

DB_HOST="${DB_HOST:-db-primary}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"

echo ">>> [Entrypoint] Checking database availability at ${DB_HOST}:${DB_PORT}..."

# Wait for PostgreSQL to be ready before starting Gunicorn/Uvicorn
python - <<END
import socket
import time
import sys

host = "${DB_HOST}"
port = int("${DB_PORT}")
timeout = 60
start = time.time()

while True:
    try:
        with socket.create_connection((host, port), timeout=2):
            print(f">>> Database {host}:{port} is reachable.")
            sys.exit(0)
    except Exception as e:
        if time.time() - start > timeout:
            print(f">>> Timeout waiting for database {host}:{port}")
            sys.exit(1)
        time.sleep(1)
END

echo ">>> Starting application: $@"
exec "$@"
