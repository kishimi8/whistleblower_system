#!/bin/bash
set -e

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
PRIMARY_HOST="${PRIMARY_HOST:-db-primary}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
REPLICATION_USER="${REPLICATION_USER:-replicator}"

echo ">>> Initializing PostgreSQL Standby..."

# Wait for primary database to be healthy
echo ">>> Polling primary database at ${PRIMARY_HOST}:${PRIMARY_PORT}..."
until pg_isready -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$POSTGRES_USER"; do
    echo ">>> Primary database is not ready yet. Waiting 2 seconds..."
    sleep 2
done

# If PG_VERSION does not exist in PGDATA, clone from primary
if [ ! -s "$PGDATA/PG_VERSION" ]; then
    echo ">>> Standby data directory is empty. Executing pg_basebackup from ${PRIMARY_HOST}..."
    rm -rf "${PGDATA:?}"/*

    PGPASSWORD="${REPLICATION_PASSWORD}" pg_basebackup \
        -h "$PRIMARY_HOST" \
        -p "$PRIMARY_PORT" \
        -U "$REPLICATION_USER" \
        -D "$PGDATA" \
        -Fp \
        -Xs \
        -R \
        -v

    chmod 700 "$PGDATA"
    echo ">>> pg_basebackup completed successfully. standby.signal created."
else
    echo ">>> Existing data directory found at $PGDATA. Skipping basebackup."
fi

echo ">>> Starting PostgreSQL Standby server..."
exec postgres -c hot_standby=on
