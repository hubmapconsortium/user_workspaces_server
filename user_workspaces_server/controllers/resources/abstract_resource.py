from abc import ABC, abstractmethod


class AbstractResource(ABC):
    def __init__(self, resource_storage, resource_user_authentication):
        self.resource_storage = resource_storage
        self.resource_user_authentication = resource_user_authentication

    @abstractmethod
    def get_current_job(self):
        pass
