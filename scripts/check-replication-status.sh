#!/bin/bash
set -e

COMPOSE_FILE="docker-compose.prod.yml"

echo "============================================================"
echo ">>> CHECKING POSTGRESQL PRIMARY REPLICATION STATUS"
echo "============================================================"
docker compose -f "$COMPOSE_FILE" exec db-primary psql -U postgres -d whistle -c "
SELECT 
    client_addr AS standby_ip,
    state,
    sync_state,
    sync_priority,
    pg_wal_lsn_diff(pg_current_wal_lsn(), write_lsn) AS write_lag_bytes,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;
"

echo "============================================================"
echo ">>> CHECKING POSTGRESQL STANDBY RECOVERY STATUS"
echo "============================================================"
docker compose -f "$COMPOSE_FILE" exec db-standby psql -U postgres -d whistle -c "
SELECT 
    pg_is_in_recovery() AS is_in_recovery,
    pg_last_wal_receive_lsn() AS last_received_lsn,
    pg_last_wal_replay_lsn() AS last_replayed_lsn,
    pg_last_xact_replay_timestamp() AS last_replay_timestamp;
"
echo "============================================================"
