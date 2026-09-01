#!/bin/bash
set -e

COMPOSE_FILE="docker-compose.prod.yml"

echo "============================================================"
echo ">>> INITIATING STANDBY PROMOTION (FAILOVER PROCEDURE)"
echo "============================================================"

# Step 1: Promote the standby PostgreSQL instance to primary
echo ">>> Step 1: Promoting db-standby to Primary..."
docker compose -f "$COMPOSE_FILE" exec db-standby pg_ctl promote -D /var/lib/postgresql/data

echo ">>> db-standby successfully promoted to primary."

# Step 2: Reroute application replicas
echo ">>> Step 2: Updating application replica connections..."
echo ">>> To route all traffic to the newly promoted standby:"
echo "    1. Update DB_HOST=db-standby in your .env.production file"
echo "    2. Restart web app replicas with:"
echo "       docker compose -f $COMPOSE_FILE up -d --no-deps web-app-1 web-app-2 web-app-3"
echo "============================================================"
