from abc import ABC, abstractmethod
from datetime import datetime
from typing import Literal, Union

from user_workspaces_server.models import Job


class AbstractResource(ABC):
    def __init__(self, config, resource_storage, resource_user_authentication):
        self.config = config
        self.resource_storage = resource_storage
        self.resource_user_authentication = resource_user_authentication
        self.passthrough_domain = config.get("passthrough_domain", "")

    @abstractmethod
    def translate_status(self, status) -> Job.Status:
        # Should take a string and translate it into local terminology.
        pass

    @abstractmethod
    def launch_job(self, job, workspace, resource_options) -> int:
        # Should return resource_job_id
        pass

    @abstractmethod
    def get_resource_job(self, job) -> dict:
        # Should get the resource's job information
        pass

    @abstractmethod
    def get_job_core_hours(self, job) -> Union[datetime, Literal[0]]:
        # Should return time in hours
        pass

    @abstractmethod
    def stop_job(self, job) -> bool:
        # Should stop the job on the resource
        pass

    @abstractmethod
    def validate_options(self, resource_options: dict) -> bool:
        # Should determine whether the requested options are valid for a resource
        # Might be able to implement this at the abstract level once we've defined
        #   a data model for resource options.
        pass

    @abstractmethod
    def translate_options(self, resource_options: dict) -> dict:
        # Should translate the options into a format that can be used by the resource
        pass
