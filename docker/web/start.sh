#!/bin/bash

bash ./docker/wait-for-postgres.sh postgres python manage.py migrate

daphne -b 0.0.0.0 -p 5050 user_workspaces_server_project.asgi:application