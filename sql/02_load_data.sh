#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "Loading initial data from trivia_data.sql into database $POSTGRES_DB"

DUMP_FILE="/docker-entrypoint-initdb.d/trivia_data.sql"
sed 's/\r//g; /^SET transaction_timeout = 0;$/d' "$DUMP_FILE" | psql -v ON_ERROR_STOP=1 --dbname="$POSTGRES_DB" --username="$POSTGRES_USER"

echo "Initial data loading complete."