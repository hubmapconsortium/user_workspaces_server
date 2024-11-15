#!/bin/bash
HOST=postgres

bash ./docker/user_workspaces_server/wait-for-postgres.sh $HOST python manage.py migrate

PGPASSWORD=$POSTGRES_PASSWORD psql -v --username "$POSTGRES_USER" --dbname "$HOST" -h postgres <<-EOSQL
    CREATE USER $GRAFANA_USER WITH PASSWORD '$GRAFANA_PASSWORD';
    GRANT USAGE ON SCHEMA public TO $GRAFANA_USER;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO $GRAFANA_USER;
EOSQL

python manage.py qcluster&
Q_CLUSTER_NAME=long python manage.py qcluster&
uvicorn --host 0.0.0.0 --port 5050 --workers 8 user_workspaces_server_project.asgi:application
