import logging
from abc import ABC, abstractmethod

from user_workspaces_server.controllers.jobtypes.abstract_job import AbstractJob
from user_workspaces_server.exceptions import ValidationException
from user_workspaces_server.models import Job, Workspace
from user_workspaces_server.validation.validate_job_params import ParamValidator

logger = logging.getLogger(__name__)


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
    def launch_job(
        self, job: AbstractJob, workspace: Workspace, resource_options: dict
    ) -> int:
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

    def validate_options(self, resource_options: dict) -> bool:
        validator = ParamValidator()
        validator.validate(resource_options)
        if validator.errors:
            logging.error(f"Validation errors: {validator.errors}")
            raise ValidationException(
                f"Invalid resource options found: {validator.errors}"
            )
        return validator.is_valid

    def translate_option_name(self, option: str) -> str:
        return self.config.get("parameter_mapping", {}).get(option)

    def translate_options(self, resource_options: dict) -> dict:
        translated_options = {}
        for option_name, option_value in resource_options.items():
            if updated_option_name := self.translate_option_name(option_name):
                translated_options[updated_option_name] = option_value

        return translated_options
