from django.apps import AppConfig


class UserWorkspacesServerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_workspaces_server'

    def ready(self):
        # TODO: Initialize all of the resources here
        pass
