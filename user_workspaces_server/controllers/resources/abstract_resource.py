from abc import ABC, abstractmethod


class AbstractResource(ABC):
    def __init__(self, config, resource_storage, resource_user_authentication):
        self.config = config
        self.resource_storage = resource_storage
        self.resource_user_authentication = resource_user_authentication
        self.passthrough_domain = config.get('passthrough_domain', '')

    @abstractmethod
    def launch_job(self, job, workspace):
        # Should return resource_job_id
        pass

    @abstractmethod
    def get_resource_job(self, job):
        # Should get the resource's job information
        pass
