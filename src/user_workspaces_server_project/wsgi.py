"""
WSGI config for user_workspaces_server_project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

settings_file = "settings_example" if os.environ.get("GITHUB_WORKFLOW") else "settings_default"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"user_workspaces_server_project.{settings_file}")

application = get_wsgi_application()
