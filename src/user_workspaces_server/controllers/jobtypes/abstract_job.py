from abc import ABC, abstractmethod


class AbstractJob(ABC):
    def __init__(self, config, job_details):
        self.config = config
        self.job_details = job_details
        self.script_template_name = None

    @abstractmethod
    def get_script(self, template_params=None) -> str:
        pass

    @abstractmethod
    def status_check(self, job_model):
        # Should return job_details information
        pass
