from abc import ABC, abstractmethod
from typing import Optional

from user_workspaces_server.controllers.jobtypes.abstract_job import AbstractJob
from user_workspaces_server.models import Job, Workspace
from user_workspaces_server.validation.validate_job_params import ParamValidator


class AbstractResource(ABC):
    def __init__(self, config, resource_storage, resource_user_authentication):
        self.config = config
        self.resource_storage = resource_storage
        self.resource_user_authentication = resource_user_authentication
        self.passthrough_domain = config.get("passthrough_domain", "")

    @abstractmethod
    def translate_status(self, status: str) -> Job.Status:
        # Should take a string and translate it into local terminology.
        pass

    @abstractmethod
    def launch_job(self, job: AbstractJob, workspace: Workspace, resource_options: dict) -> int:
        # Should return resource_job_id
        pass

    @abstractmethod
    def get_resource_job(self, job) -> dict:
        # Should get the resource's job information
        pass

    @abstractmethod
    def get_job_core_hours(self, job: Job) -> int:
        # Should return time in hours
        pass

    @abstractmethod
    def stop_job(self, job: Job) -> bool:
        # Should stop the job on the resource
        pass

    @abstractmethod
    def translate_options(self, resource_options: dict) -> Optional[dict]:
        # Should translate the options into a format that can be used by the resource
        pass

    def validate_options(self, resource_options: dict) -> bool:
        return self.get_validation_result(resource_options).is_valid

    def get_validation_result(self, resource_options: dict) -> ParamValidator:
        """
        Allows subclasses to handle results in their own ways e.g. using logger.
        Assumes that all resources will use the same validator,
        could be made abstract if that needs to be flexible.
        """
        validator = ParamValidator()
        validator.validate(resource_options)
        return validator
