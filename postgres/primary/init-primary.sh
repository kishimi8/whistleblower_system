#!/bin/bash
set -e

echo ">>> Initializing PostgreSQL Primary for HA Streaming Replication..."

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${REPLICATION_USER:-replicator}') THEN
            CREATE ROLE ${REPLICATION_USER:-replicator} WITH REPLICATION LOGIN ENCRYPTED PASSWORD '${REPLICATION_PASSWORD}';
        END IF;
    END
    \$\$;
EOSQL

# Append replication rules to pg_hba.conf if not already present
if ! grep -q "replication ${REPLICATION_USER:-replicator}" "$PGDATA/pg_hba.conf"; then
    echo "host replication ${REPLICATION_USER:-replicator} 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
    echo "host replication ${REPLICATION_USER:-replicator} all md5" >> "$PGDATA/pg_hba.conf"
    echo "host all all 0.0.0.0/0 md5" >> "$PGDATA/pg_hba.conf"
fi

# Reload configuration
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "SELECT pg_reload_conf();"
echo ">>> Primary replication initialization completed successfully."
