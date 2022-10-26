import grp
import logging
import os
import pwd
import shutil

from django.forms import model_to_dict

from user_workspaces_server.controllers.storagemethods.abstract_storage import \
    AbstractStorage
from user_workspaces_server.exceptions import WorkspaceClientException

logger = logging.getLogger(__name__)


class LocalFileSystemStorage(AbstractStorage):
    def is_valid_path(self, path):
        # The correct way to do this is to make sure that path_to_delete is a child of self.root_dir
        # IE, path_to_delete should not be a parent of root_dir (as is the case for if path is /)
        # it should not be a sibling of root_dir, nor should it be equal to root_dir
        abs_root_dir = os.path.abspath(self.root_dir)
        workspace_path = os.path.abspath(os.path.join(abs_root_dir, path))
        if not os.path.commonpath([abs_root_dir]) == os.path.commonpath(
            [abs_root_dir, workspace_path]
        ):
            logger.error("Workspace path is not a child of the root_dir")
            return False
        elif workspace_path == abs_root_dir:
            logger.error("Workspace path is equal to root_dir")
            return False
        else:
            return True

    def create_dir(self, path):
        os.makedirs(os.path.join(self.root_dir, path), exist_ok=True)

    def delete_dir(self, path, owner_mapping):
        if not self.is_valid_path(path):
            raise Exception("Cannot delete this workspace")
        else:
            if self.check_is_owner(path, owner_mapping):
                shutil.rmtree(os.path.join(self.root_dir, path), ignore_errors=True)
            else:
                raise Exception(f"User {owner_mapping} does not own {path}")

    def get_dir_size(self, path):
        total = 0
        full_path = os.path.join(self.root_dir, path)
        try:
            for entry in os.scandir(full_path):
                if entry.is_symlink():
                    pass
                elif entry.is_file():
                    # if it's a file, use stat() function
                    total += entry.stat().st_size
                elif entry.is_dir():
                    # if it's a directory, recursively call this function
                    total += self.get_dir_size(entry.path)
        except NotADirectoryError:
            # if `directory` isn't a directory, get the file size then
            return os.path.getsize(full_path)
        except PermissionError:
            # if for whatever reason we can't open the folder, return 0
            return 0
        return total

    def get_dir_tree(self, path):
        return os.fwalk(os.path.join(self.root_dir, path))

    def check_is_owner(self, path, owner_mapping):
        external_user = self.storage_user_authentication.get_external_user(
            model_to_dict(owner_mapping)
        )
        uid = (
            pwd.getpwnam(external_user["external_username"])[2]
            if type(external_user["external_user_uid"]) == str
            else external_user["external_user_uid"]
        )
        owner_uid = os.stat(os.path.join(self.root_dir, path)).st_uid
        return uid == owner_uid

    def set_ownership(self, path, owner_mapping, recursive=False):
        external_user = self.storage_user_authentication.get_external_user(
            model_to_dict(owner_mapping)
        )

        uid = (
            pwd.getpwnam(external_user["external_username"])[2]
            if type(external_user["external_user_uid"]) == str
            else external_user["external_user_uid"]
        )
        gid = (
            grp.getgrnam(external_user["external_user_gid"])[2]
            if type(external_user["external_user_gid"]) == str
            else external_user["external_user_gid"]
        )

        os.chown(os.path.join(self.root_dir, path), uid, gid)

        if recursive:
            for dirpath, dirnames, filenames, dirfd in self.get_dir_tree(path):
                os.chown(dirpath, uid, gid)
                for filename in filenames:
                    os.chown(os.path.join(dirpath, filename), uid, gid)

    def create_symlink(self, path, symlink):
        symlink_name = symlink.get("name", "")
        symlink_source_path = symlink.get("source_path", "")

        # Detect the relative path from symlink name so that it more closely mirrors the file name functionality
        symlink_path_list = symlink_name.split("/")
        symlink_name = symlink_path_list[-1]
        symlink_dest_path = symlink_path_list[:-1]

        symlink_full_dest_path = os.path.join(
            self.root_dir, path, "/".join(symlink_dest_path)
        )

        if not self.is_valid_path(os.path.join(path, symlink_name)):
            logger.error(f"Symlink {symlink_name} cannot be created in {path}.")
            raise WorkspaceClientException(
                f"Invalid symlink destination path specified {symlink_name}"
            )

        os.makedirs(symlink_full_dest_path, exist_ok=True)

        if os.path.exists(symlink_source_path):
            if os.path.exists(os.path.join(symlink_full_dest_path, symlink_name)):
                os.remove(os.path.join(symlink_full_dest_path, symlink_name))
            os.symlink(
                symlink_source_path, os.path.join(symlink_full_dest_path, symlink_name)
            )
        else:
            raise NotADirectoryError

    def create_file(self, path, file):
        file_path_list = file.name.split("/")
        file_name = file_path_list[-1]
        file_dest_path = file_path_list[:-1]

        if not self.is_valid_path(os.path.join(path, file.name)):
            logger.error(f"File {file.name} cannot be created in {path}")
            raise WorkspaceClientException(f"Invalid file path specified {file.name}")

        file_full_dest_path = os.path.join(
            self.root_dir, path, "/".join(file_dest_path)
        )

        os.makedirs(file_full_dest_path, exist_ok=True)

        if os.path.exists(os.path.join(file_full_dest_path, file_name)):
            os.remove(os.path.join(file_full_dest_path, file_name))

        with open(os.path.join(file_full_dest_path, file_name), "wb") as new_file:
            for chunk in file.chunks():
                new_file.write(chunk)
