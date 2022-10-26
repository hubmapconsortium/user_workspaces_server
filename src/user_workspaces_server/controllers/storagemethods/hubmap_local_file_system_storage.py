import logging

from user_workspaces_server.controllers.storagemethods.local_file_system_storage import (
    LocalFileSystemStorage,
)
import os
import requests as http_r
from rest_framework.exceptions import (
    ParseError,
    PermissionDenied,
    NotFound,
    APIException,
)


class HubmapLocalFileSystemStorage(LocalFileSystemStorage):
    def __init__(self, config, storage_user_authentication):
        super().__init__(config, storage_user_authentication)
        self.root_url = config["connection_details"]["root_url"]

    def create_symlinks(self, workspace, workspace_details):
        # Attempt to get a globus_groups_token
        if not (
            globus_groups_token := workspace_details.get("globus_groups_token", "")
        ):
            external_user_mapping = (
                self.storage_user_authentication.get_external_user_mapping(
                    {
                        "user_id": workspace.user_id,
                        "user_authentication_name": "GlobusUserAuthentication",
                    }
                )
            )

            globus_groups_token = (
                None
                if (
                    not external_user_mapping
                    or not external_user_mapping.external_user_details
                )
                else external_user_mapping.external_user_details.get("tokens", {}).get(
                    "groups.api.globus.org", None
                )
            )

        # Let's check here to see if there are any failure states, IE if there is an uuid but no token
        for symlink in workspace_details.get("symlinks", []):
            if "dataset_uuid" in symlink and not globus_groups_token:
                raise ParseError(
                    "No globus_groups_token passed when trying to use dataset_uuid."
                )
            if ".." in symlink.get("name", ""):
                raise ParseError("Symlink name cannot contain double dots.")

        for symlink in workspace_details.get("symlinks", []):
            self.create_symlink(workspace.file_path, symlink, globus_groups_token)

    def create_symlink(self, path, symlink, globus_groups_token=None):
        # If dataset_uuid is not in there, just create a "normal" symlink
        if "dataset_uuid" not in symlink:
            super().create_symlink(path, symlink)
        else:
            symlink_dataset_uuid = symlink.get("dataset_uuid", -1)
            symlink_name = symlink.get("name", "")
            symlink_path_list = symlink_name.split("/")
            symlink_name = symlink_path_list[-1]
            symlink_dest_path = symlink_path_list[:-1]

            if not self.is_valid_path(os.path.join(path, symlink_name)):
                logging.error(f"Symlink {symlink_name} cannot be created in {path}.")
                raise ParseError(
                    f"Invalid symlink destination path specified {symlink_name}"
                )

            symlink_full_dest_path = os.path.join(
                self.root_dir, path, "/".join(symlink_dest_path)
            )
            os.makedirs(symlink_full_dest_path, exist_ok=True)

            # {root_url}/datasets/{symlink_dataset_uuid}/file-system-abs-path
            abs_path_response = http_r.get(
                f"{self.root_url}/datasets/{symlink_dataset_uuid}/file-system-abs-path",
                headers={"Authorization": f"Bearer {globus_groups_token}"},
            )
            if abs_path_response.status_code == 401:
                raise PermissionDenied(
                    f"User does not have authorization for dataset {symlink_dataset_uuid} based on token {globus_groups_token}"
                )
            elif abs_path_response.status_code == 400:
                raise ParseError(
                    f"Error when attempting to get dataset path: {abs_path_response.text}"
                )
            elif abs_path_response.status_code == 404:
                raise NotFound(f"Dataset {symlink_dataset_uuid} could not be found.")
            if abs_path_response.status_code == 500:
                raise APIException(
                    f"Server side error: {abs_path_response.text}", code=500
                )

            abs_path_response = abs_path_response.json()
            symlink_source_path = abs_path_response.get("path")

            # Detect the relative path from symlink name so that it more closely mirrors the file name functionality
            if os.path.exists(symlink_source_path):
                if os.path.exists(os.path.join(symlink_full_dest_path, symlink_name)):
                    os.remove(os.path.join(symlink_full_dest_path, symlink_name))
                os.symlink(
                    symlink_source_path,
                    os.path.join(symlink_full_dest_path, symlink_name),
                )
            else:
                raise APIException(f"Symlink path not found: {symlink_source_path}")
