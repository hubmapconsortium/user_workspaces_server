from abc import ABC, abstractmethod


class AbstractStorage(ABC):
    def __init__(self, config, storage_user_authentication):
        self.config = config
        self.storage_user_authentication = storage_user_authentication
        self.root_dir = config['root_dir']

    @abstractmethod
    def create_dir(self, path):
        pass

    @abstractmethod
    def get_dir_size(self, path):
        pass

    @abstractmethod
    def get_dir_tree(self, path):
        pass

    @abstractmethod
    def set_ownership(self, path, owner_mapping):
        pass

    @abstractmethod
    def create_symlink(self, path, symlink):
        pass

    @abstractmethod
    def create_file(self, path, file):
        pass
