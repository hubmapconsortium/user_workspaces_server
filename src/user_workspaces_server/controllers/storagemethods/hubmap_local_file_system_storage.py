import logging
import os

import requests as http_r
from rest_framework.exceptions import (
    APIException,
    NotFound,
    ParseError,
    PermissionDenied,
)

from user_workspaces_server.controllers.storagemethods.local_file_system_storage import (
    LocalFileSystemStorage,
)


class HubmapLocalFileSystemStorage(LocalFileSystemStorage):
    def __init__(self, config, storage_user_authentication):
        super().__init__(config, storage_user_authentication)
        self.root_url = config["connection_details"]["root_url"]

    def create_symlinks(self, workspace, workspace_details):
        # Attempt to get a globus_groups_token
        if not (globus_groups_token := workspace_details.get("globus_groups_token", "")):
            external_user_mapping = self.storage_user_authentication.get_external_user_mapping(
                {
                    "user_id": workspace.user_id,
                    "user_authentication_name": "GlobusUserAuthentication",
                }
            )

            globus_groups_token = (
                None
                if (not external_user_mapping or not external_user_mapping.external_user_details)
                else external_user_mapping.external_user_details.get("tokens", {}).get(
                    "groups.api.globus.org", None
                )
            )

        symlinks = workspace_details.get("symlinks", [])

        if type(symlinks) != list:
            raise ParseError("'symlinks' index must contain a list.")

        if not symlinks:
            return

        # Let's check here to see if there are any failure states, IE if there is an uuid but no token
        dataset_uuids = {}
        for symlink in symlinks:
            if "dataset_uuid" in symlink:
                if not globus_groups_token:
                    raise ParseError(
                        "No globus_groups_token passed when trying to use dataset_uuid."
                    )
                else:
                    # Build the dataset_uuids dictionary while we're in here to avoid iterating again
                    dataset_uuids[symlink.get("dataset_uuid")] = symlink
            if ".." in symlink.get("name", ""):
                raise ParseError("Symlink name cannot contain double dots.")

        if dataset_uuids:
            # If there are dataset_uuids passed, grab all the abs-paths
            abs_path_response = http_r.post(
                f"{self.root_url}/datasets/file-system-abs-path",
                headers={"Authorization": f"Bearer {globus_groups_token}"},
                json=dataset_uuids.keys(),
            )

            if abs_path_response.status_code == 500:
                raise APIException(f"Server side error: {abs_path_response.text}", code=500)

            abs_path_errors = []
            for abs_path in abs_path_response.json():
                uuid = abs_path.get("uuid")
                if "error" in abs_path:
                    abs_path_errors.append(abs_path)
                    dataset_uuids.pop(uuid)
                else:
                    dataset_uuids[uuid].update({"source_path": abs_path.get("path")})
            if abs_path_errors:
                raise APIException(
                    f"Errors encountered when attempting to gather UUID information: {abs_path_errors}",
                    code=500,
                )

        for symlink in symlinks:
            if "dataset_uuid" not in symlink:
                super().create_symlink(workspace.file_path, symlink)

        for symlink in dataset_uuids.values():
            super().create_symlink(workspace.file_path, symlink)
