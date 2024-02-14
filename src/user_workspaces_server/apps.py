import os

from django.apps import AppConfig
from django.conf import settings

from . import utils


class UserWorkspacesServerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "user_workspaces_server"
    api_user_authentication = None
    main_storage = None
    main_resource = None
    available_resources = {}
    available_storage_methods = {}
    available_user_authentication_methods = {}
    available_job_types = {}

    def ready(self):
        config_user_authentication = settings.UWS_CONFIG["available_user_authentication"]
        config_storage = settings.UWS_CONFIG["available_storage"]
        config_resource = settings.UWS_CONFIG["available_resources"]
        config_job_types = settings.UWS_CONFIG["available_job_types"]

        for (
            user_authentication_name,
            user_authentication_dict,
        ) in config_user_authentication.items():
            self.available_user_authentication_methods[
                user_authentication_name
            ] = utils.generate_controller_object(
                user_authentication_dict["user_authentication_type"],
                "userauthenticationmethods",
                {"config": user_authentication_dict},
            )

        for storage_name, storage_dict in config_storage.items():
            self.available_storage_methods[storage_name] = utils.generate_controller_object(
                storage_dict["storage_type"],
                "storagemethods",
                {
                    "config": storage_dict,
                    "storage_user_authentication": self.available_user_authentication_methods[
                        storage_dict["user_authentication"]
                    ],
                },
            )

        for resource_name, resource_dict in config_resource.items():
            self.available_resources[resource_name] = utils.generate_controller_object(
                resource_dict["resource_type"],
                "resources",
                {
                    "config": resource_dict,
                    "resource_storage": self.available_storage_methods[resource_dict["storage"]],
                    "resource_user_authentication": self.available_user_authentication_methods[
                        resource_dict["user_authentication"]
                    ],
                },
            )

        self.available_job_types = config_job_types

        self.api_user_authentication = self.available_user_authentication_methods[
            settings.UWS_CONFIG["api_user_authentication"]
        ]

        self.main_storage = self.available_storage_methods[settings.UWS_CONFIG["main_storage"]]

        self.main_resource = self.available_resources[settings.UWS_CONFIG["main_resource"]]

        if os.environ.get("SUBCOMMAND", None) != "qcluster":
            return

        from django_q import brokers
        from django_q.tasks import async_task

        from . import models

        broker = brokers.get_broker()
        broker.purge_queue()
        active_jobs = models.Job.objects.filter(status__in=["pending", "running"]).all()
        for active_job in active_jobs:
            async_task(
                "user_workspaces_server.tasks.update_job_status",
                active_job.id,
                hook="user_workspaces_server.tasks.queue_job_update",
            )
