#!/usr/bin/env bash
# Backup/restore smoke test — see docs/performance-and-reliability.md
# #database-backup-and-restore-test.
#
# Dumps the running local/CI Postgres (docker-compose's `postgres` service),
# restores it into a throwaway database on the same server, and compares
# per-table row counts between source and restored copies. This exercises
# the actual `pg_dump`/`pg_restore` path this project would use to recover
# from a lost database, not just "Supabase says backups are enabled" —
# see docs/security-review.md#backup-access-controls for the access-control
# side of backups (this script is the "do they actually work" side).
#
# Usage: ./scripts/backup_restore_test.sh
# Requires: the postgres container from docker-compose.yml running
# (`docker compose up -d postgres`), and Docker CLI access to it.

set -euo pipefail

# Prevents Git-Bash-on-Windows from rewriting the /tmp/... path below into a
# host Windows path before it reaches `docker exec` (harmless no-op on
# Linux/macOS, where this variable doesn't affect anything).
export MSYS_NO_PATHCONV=1

CONTAINER="${POSTGRES_CONTAINER:-mehndidesignapp-postgres-1}"
DB_USER="${POSTGRES_USER:-mehndiverse}"
SOURCE_DB="${POSTGRES_DB:-mehndiverse}"
RESTORE_DB="${SOURCE_DB}_restore_test"
DUMP_FILE="/tmp/mehndiverse_backup_restore_test.dump"

echo "== Backup/restore smoke test =="
echo "Container: $CONTAINER | Source DB: $SOURCE_DB | Restore target: $RESTORE_DB"

echo "-- 1. Dumping $SOURCE_DB (custom format, compressed) --"
docker exec "$CONTAINER" pg_dump -U "$DB_USER" -d "$SOURCE_DB" -F custom -f "$DUMP_FILE"
DUMP_SIZE=$(docker exec "$CONTAINER" stat -c%s "$DUMP_FILE")
echo "Dump size: ${DUMP_SIZE} bytes"
if [ "$DUMP_SIZE" -eq 0 ]; then
  echo "FAIL: dump file is empty" >&2
  exit 1
fi

echo "-- 2. Creating throwaway restore-target database --"
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${RESTORE_DB}"
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${RESTORE_DB}"

echo "-- 3. Restoring dump into $RESTORE_DB --"
docker exec "$CONTAINER" pg_restore -U "$DB_USER" -d "$RESTORE_DB" --no-owner --no-privileges "$DUMP_FILE"

echo "-- 4. Comparing per-table row counts --"
COUNT_QUERY="SELECT table_name, (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS row_count FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

SOURCE_COUNTS=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d "$SOURCE_DB" -t -A -F',' -c "$COUNT_QUERY")
RESTORED_COUNTS=$(docker exec "$CONTAINER" psql -U "$DB_USER" -d "$RESTORE_DB" -t -A -F',' -c "$COUNT_QUERY")

echo "-- 5. Cleaning up restore-target database --"
docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${RESTORE_DB}"
docker exec "$CONTAINER" rm -f "$DUMP_FILE"

if [ "$SOURCE_COUNTS" != "$RESTORED_COUNTS" ]; then
  echo "FAIL: row counts differ between source and restored database" >&2
  diff <(echo "$SOURCE_COUNTS") <(echo "$RESTORED_COUNTS") || true
  exit 1
fi

TABLE_COUNT=$(echo "$SOURCE_COUNTS" | wc -l)
echo "PASS: restored database matches source across ${TABLE_COUNT} tables."
