from abc import ABC, abstractmethod
from django.core.files.base import ContentFile


class AbstractStorage(ABC):
    def __init__(self, config, storage_user_authentication):
        self.config = config
        self.storage_user_authentication = storage_user_authentication
        self.root_dir = config['root_dir']

    def create_symlinks(self, workspace, workspace_details):
        for symlink in workspace_details.get('symlinks', []):
            self.create_symlink(workspace.file_path, symlink)

    def create_files(self, workspace, workspace_details):
        for file in workspace_details.get('files', []):
            # Create a file object here
            content_file = ContentFile(bytes(file.get('content', ''), 'utf-8'), name=file.get('name'))
            self.create_file(workspace.file_path, content_file)

    @abstractmethod
    def is_valid_workspace_path(self, path):
        pass

    @abstractmethod
    def create_dir(self, path):
        pass

    @abstractmethod
    def delete_dir(self, path):
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
