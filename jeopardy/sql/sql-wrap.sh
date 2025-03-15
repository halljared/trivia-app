if [ $# -ne 1 ]; then
    echo "Usage: $0 <sql_script>"
    exit 1
fi

source ../../.env
export PGPASSWORD=$DB_PASSWORD

psql -U $DB_USER -d $DB_NAME -f "$1"
