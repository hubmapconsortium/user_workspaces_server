import os
from typing import TYPE_CHECKING

from django.apps import AppConfig
from django.conf import settings

from . import utils


class UserWorkspacesServerConfig(AppConfig):
    if TYPE_CHECKING:
        from user_workspaces_server.controllers.resources.abstract_resource import AbstractResource
        from user_workspaces_server.controllers.storagemethods.abstract_storage import AbstractStorage
        from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import AbstractUserAuthentication

    default_auto_field = "django.db.models.BigAutoField"
    name = "user_workspaces_server"
    api_user_authentication: AbstractUserAuthentication
    main_storage: AbstractStorage
    main_resource: AbstractResource
    available_job_types: dict
    _available_resources: dict[str, AbstractResource]
    _available_storage_methods: dict[str, AbstractStorage]
    _available_user_authentication_methods: dict[str, AbstractUserAuthentication]

    def ready(self):
        config_user_authentication = settings.AVAILABLE_USER_AUTHENTICATION
        config_storage = settings.AVAILABLE_STORAGE
        config_resource = settings.AVAILABLE_RESOURCES
        config_job_types = settings.AVAILABLE_JOB_TYPES

        for (
            user_authentication_name,
            user_authentication_dict,
        ) in config_user_authentication.items():
            self._available_user_authentication_methods[user_authentication_name] = (
                utils.generate_controller_object(
                    user_authentication_dict["user_authentication_type"],
                    "userauthenticationmethods",
                    {"config": user_authentication_dict},
                )
            )

        for storage_name, storage_dict in config_storage.items():
            self._available_storage_methods[storage_name] = utils.generate_controller_object(
                storage_dict["storage_type"],
                "storagemethods",
                {
                    "config": storage_dict,
                    "storage_user_authentication": self._available_user_authentication_methods[
                        storage_dict["user_authentication"]
                    ],
                },
            )

        for resource_name, resource_dict in config_resource.items():
            self._available_resources[resource_name] = utils.generate_controller_object(
                resource_dict["resource_type"],
                "resources",
                {
                    "config": resource_dict,
                    "resource_storage": self._available_storage_methods[resource_dict["storage"]],
                    "resource_user_authentication": self._available_user_authentication_methods[
                        resource_dict["user_authentication"]
                    ],
                },
            )

        self.available_job_types = config_job_types

        self.api_user_authentication = self._available_user_authentication_methods[settings.API_USER_AUTHENTICATION]

        self.main_storage = self._available_storage_methods[settings.MAIN_STORAGE]

        self.main_resource = self._available_resources[settings.MAIN_RESOURCE]

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
