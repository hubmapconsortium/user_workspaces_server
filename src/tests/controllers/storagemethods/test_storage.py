import logging

from user_workspaces_server.controllers.storagemethods.abstract_storage import (
    AbstractStorage,
)

logger = logging.getLogger(__name__)


class TestStorage(AbstractStorage):
    def is_valid_path(self, path):
        # The correct way to do this is to make sure that path_to_delete is a child of self.root_dir
        # IE, path_to_delete should not be a parent of root_dir (as is the case for if path is /)
        # it should not be a sibling of root_dir, nor should it be equal to root_dir
        return False if path == "." else True

    def create_dir(self, path):
        pass

    def delete_dir(self, path, owner_mapping):
        pass

    def get_dir_size(self, path):
        return 0

    def get_dir_tree(self, path):
        return {}

    def check_is_owner(self, path, owner_mapping):
        return True

    def set_ownership(self, path, owner_mapping, recursive=False):
        pass

    def create_symlink(self, path, symlink):
        pass

    def create_file(self, path, file):
        pass

    def health_check(self):
        pass
