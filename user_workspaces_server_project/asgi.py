"""
ASGI config for user_workspaces_server_project project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.routing import ProtocolTypeRouter
from django.core.asgi import get_asgi_application
import user_workspaces_server.urls

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_workspaces_server_project.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            user_workspaces_server.urls.ws_urlpatterns
        )
    ),
})
