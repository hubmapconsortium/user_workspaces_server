#!/bin/bash

./docker/wait-for-it.sh -t 0 postgres:5432 -- python manage.py migrate

python manage.py qcluster&
daphne -b 0.0.0.0 -p 5050 user_workspaces_server_project.asgi:application