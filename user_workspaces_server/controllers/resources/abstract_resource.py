from abc import ABC, abstractmethod


class AbstractResource(ABC):
    def __init__(self, resource_storage, resource_user_authentication):
        self.resource_storage = resource_storage
        self.resource_user_authentication = resource_user_authentication

    @abstractmethod
    def launch_job(self, job, workspace):
        # Should return resource_job_id
        pass

    @abstractmethod
    def get_job(self, resource_job_id):
        # Should get the resource's job information (status
        pass
