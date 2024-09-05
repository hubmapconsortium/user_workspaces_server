from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from django.utils.safestring import SafeString

if TYPE_CHECKING:
    from user_workspaces_server import models


class AbstractJob(ABC):
    def __init__(self, config, job_details):
        self.config = config
        self.job_details = job_details
        self.script_template_name = None

    @abstractmethod
    def get_script(self, template_params=None) -> SafeString:
        pass

    @abstractmethod
    def status_check(self, job_model: models.Job) -> dict:
        # Should return job_details information
        pass
