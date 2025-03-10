source credentials.sh
export PGPASSWORD=$DB_PASSWORD

psql -U $DB_USER -d $DB_NAME -f _create_import_table.sql

