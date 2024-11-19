from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Union

from django.core.files.base import ContentFile
from rest_framework.exceptions import ParseError

from user_workspaces_server.controllers.userauthenticationmethods.abstract_user_authentication import (
    AbstractUserAuthentication,
)
from user_workspaces_server.models import ExternalUserMapping, Workspace


class AbstractStorage(ABC):
    def __init__(self, config: dict, storage_user_authentication: AbstractUserAuthentication):
        self.config = config
        self.storage_user_authentication = storage_user_authentication
        self.root_dir = config["root_dir"]

    def create_symlinks(self, workspace: Workspace, workspace_details: dict):
        symlinks = workspace_details.get("symlinks", [])

        if not isinstance(symlinks, list):
            raise ParseError("'symlinks' index must contain a list.")

        if not symlinks:
            return

        for symlink in symlinks:
            if ".." in symlink.get("name", ""):
                raise ParseError("Symlink name cannot contain double dots.")
            self.create_symlink(workspace.file_path, symlink)

    def create_files(self, workspace: Workspace, workspace_details: dict) -> None:
        files = workspace_details.get("files", [])

        if not isinstance(files, list):
            raise ParseError("'files' index must contain a list.")

        if not files:
            return

        for file in files:
            # Create a file object here
            content_file = ContentFile(
                bytes(file.get("content", ""), "utf-8"), name=file.get("name")
            )
            if content_file.name and ".." in content_file.name:
                raise ParseError("File name cannot contain double dots.")

            self.create_file(workspace.file_path, content_file)

    @abstractmethod
    def is_valid_path(self, path: Union[Path, str]) -> bool:
        pass

    @abstractmethod
    def create_dir(self, path: Path):
        pass

    @abstractmethod
    def delete_dir(self, path: Path, owner_mapping: ExternalUserMapping):
        pass

    @abstractmethod
    def get_dir_size(self, path: Path) -> int:
        pass

    @abstractmethod
    def get_dir_tree(self, path: Path) -> Iterator[tuple]:
        pass

    @abstractmethod
    def check_is_owner(self, path: Path, owner_mapping: ExternalUserMapping) -> bool:
        pass

    @abstractmethod
    def set_ownership(self, path: Path, owner_mapping: ExternalUserMapping):
        pass

    @abstractmethod
    def create_symlink(self, path: Path, symlink: dict):
        pass

    @abstractmethod
    def create_file(self, path: Path, file):
        pass
