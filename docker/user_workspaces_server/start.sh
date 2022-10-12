#!/bin/bash

bash ./docker/user_workspaces_server/wait-for-postgres.sh postgres python manage.py migrate

python manage.py qcluster&
uvicorn --host 0.0.0.0 --port 5050 --workers 8 user_workspaces_server_project.asgi:application