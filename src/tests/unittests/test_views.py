import json
from datetime import datetime

from django.apps import apps
from django.contrib.auth.models import Group, User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tests.controllers.resources.test_resource import TestResource
from tests.controllers.storagemethods.test_storage import TestStorage
from tests.controllers.userauthenticationmethods.test_user_authentication import (
    TestUserAuthentication,
)
from user_workspaces_server.models import Job, SharedWorkspaceMapping, Workspace


class UserWorkspacesAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Initialize test controllers
        test_user_auth = TestUserAuthentication(
            **{
                "config": {
                    "name": "Test Auth",
                    "user_authentication_type": "TestAuthentication",
                    "connection_details": {},
                }
            }
        )
        test_storage = TestStorage(
            **{
                "config": {
                    "name": "Test Storage",
                    "storage_type": "TestStorage",
                    "user_authentication": "test_auth",
                    "root_dir": ".",
                    "connection_details": {},
                },
                "storage_user_authentication": test_user_auth,
            }
        )
        test_resource = TestResource(
            **{
                "config": {
                    "name": "Test Resource",
                    "resource_type": "TestResource",
                    "storage": "test_storage",
                    "user_authentication": "test_auth",
                    "passthrough_domain": "127.0.0.1:8000",
                    "connection_details": {},
                },
                "resource_storage": test_storage,
                "resource_user_authentication": test_user_auth,
            }
        )

        # Override existing controllers
        apps.get_app_config("user_workspaces_server").available_user_authentication_methods = {
            "test_user_auth": test_user_auth
        }
        apps.get_app_config("user_workspaces_server").available_storage_methods = {
            "test_storage": test_storage
        }
        apps.get_app_config("user_workspaces_server").available_resources = {
            "test_resource": test_resource
        }
        apps.get_app_config("user_workspaces_server").api_user_authentication = test_user_auth
        apps.get_app_config("user_workspaces_server").main_storage = test_storage
        apps.get_app_config("user_workspaces_server").main_resource = test_resource
        cls.user = User.objects.create_user("test", email="test@test.com")

    def assertValidResponse(self, response, status_code, success=None, message=""):
        self.assertEqual(response.status_code, status_code)
        self.assertContains(response, "success", status_code=status_code)
        self.assertContains(response, "message", status_code=status_code)
        parsed_response = json.loads(response.content)
        if success is not None:
            self.assertEqual(parsed_response["success"], success)
        if message:
            self.assertEqual(parsed_response["message"], message)


class TokenAPITests(UserWorkspacesAPITestCase):
    tokens_url = reverse("tokens")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        api_user = User.objects.create_user("api_user")
        api_clients_group = Group.objects.create(name="api_clients")
        api_clients_group.user_set.add(api_user)
        cls.client_token = Token(**{"user": api_user})
        cls.client_token.save()

    def test_get_new_user_token(self):
        body = {
            "client_token": self.client_token.key,
            "user_info": {"username": "fake_user", "email": "fake@fake.com"},
        }
        response = self.client.post(self.tokens_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Successful authentication.",
        )

    def test_get_user_token(self):
        body = {
            "client_token": self.client_token.key,
            "user_info": {"username": self.user.username, "email": "test@test.com"},
        }
        response = self.client.post(self.tokens_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Successful authentication.",
        )


class StatusAPITests(UserWorkspacesAPITestCase):
    status_url = reverse("status")

    def test_get_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.status_url)
        self.assertValidResponse(response, status.HTTP_200_OK)
        self.assertContains(response, "version")
        self.assertContains(response, "build")


class UserAPITests(UserWorkspacesAPITestCase):
    users_url = reverse("users")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_user = User.objects.create_user(
            "search_user", first_name="Search", last_name="User", email="search_user@querying.com"
        )

    def test_get_all_users(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.users_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")

    def test_get_user_search_email(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.users_url}?search=querying")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        self.assertEqual(len(response.json()["data"]["users"]), 1)

    def test_get_user_search_first_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.users_url}?search=Search")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        self.assertEqual(len(response.json()["data"]["users"]), 1)

    def test_get_user_search_last_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.users_url}?search=User")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        self.assertEqual(len(response.json()["data"]["users"]), 1)

    def test_get_user_search_first_and_last_name(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.users_url}?search=Search+User")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        self.assertEqual(len(response.json()["data"]["users"]), 1)

    def test_get_user_search_none_found(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.users_url}?search=Fake")
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Users matching given parameters could not be found.",
        )


class WorkspaceAPITestCase(UserWorkspacesAPITestCase):
    workspaces_url = reverse("workspaces")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        workspace_data = {
            "user_id": cls.user,
            "name": "Test Name",
            "description": "Test Description",
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": {
                "request_workspace_details": {"files": [], "symlinks": []},
                "current_workspace_details": {"files": [], "symlinks": []},
            },
            "file_path": "test/1",
        }
        cls.workspace = Workspace(**workspace_data)
        cls.workspace.save()


class WorkspaceGETAPITests(WorkspaceAPITestCase):
    # TODO: Check body
    def test_workspace_id_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("workspaces_with_id", args=[self.workspace.id]))
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_workspace_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.workspaces_url}?name={self.workspace.name}")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_workspace_query_param_name_get_none_found(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.workspaces_url}?name=FakeWorkspace")
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Workspace matching given parameters could not be found.",
        )

    def test_workspaces_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.workspaces_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)


class WorkspacePOSTAPITests(WorkspaceAPITestCase):
    def test_unauthenticated(self):
        response = self.client.get(self.workspaces_url, {})
        self.assertValidResponse(response, status.HTTP_401_UNAUTHORIZED, success=False)

    def test_empty_post(self):
        self.client.force_authenticate(user=self.user)
        body = {}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_missing_body_post(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.workspaces_url)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_missing_name_body_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"description": "Test"}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing required fields.",
        )

    def test_missing_description_body_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"name": "Test"}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing required fields.",
        )

    def test_malformed_workspace_details_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"name": "Test", "description": "Test", "workspace_details": "invalid"}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Workspace details not JSON.",
        )

    def test_minimum_valid_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"name": "Test", "description": "Test", "workspace_details": {}}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        # TODO: Check body

    def test_invalid_job_type_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "invalid",
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="invalid is not in the list of available job types.",
        )

    def test_empty_job_type_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "",
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")

    def test_valid_job_type_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "test_job",
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")

    def test_invalid_symlinks_structure_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"symlinks": ""},
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="'symlinks' index must contain a list.",
        )

    def test_invalid_files_structure_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"files": ""},
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="'files' index must contain a list.",
        )

    def test_invalid_file_name_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"files": [{"name": "../file.txt", "content": "Hello World"}]},
        }
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="File name cannot contain double dots.",
        )


class WorkspacePUTAPITests(WorkspaceAPITestCase):
    def test_workspace_not_found_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("workspaces_with_id", args=[9999]))
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message="Workspace 9999 not found for user.",
        )

    def test_workspace_data_update_missing_body_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_workspace_data_update_invalid_workspace_details_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"name": "Test", "description": "Test", "workspace_details": ""}
        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Workspace details not JSON.",
        )

    def test_workspace_data_update_invalid_symlinks_structure_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"symlinks": ""},
        }
        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="'symlinks' index must contain a list.",
        )

    def test_workspace_data_update_invalid_files_structure_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"files": ""},
        }
        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="'files' index must contain a list.",
        )

    def test_workspace_data_update_invalid_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "fake_job",
        }

        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="fake_job is not in the list of available job types.",
        )

    def test_workspace_data_update_empty_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "",
        }

        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Update successful.",
        )

    def test_workspace_data_update_valid_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {},
            "default_job_type": "test_job",
        }

        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Update successful.",
        )

    def test_workspace_data_update_minimum_valid_put(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "name": "Test",
            "description": "Test",
            "workspace_details": {"symlinks": [], "files": []},
        }
        response = self.client.put(reverse("workspaces_with_id", args=[self.workspace.id]), body)
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Update successful.",
        )

    def test_workspace_invalid_put_type_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "test"])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Invalid PUT type passed.",
        )

    def test_workspace_start_missing_body_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"])
        )
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_workspace_start_missing_job_type_no_workspace_default_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"job_details": {}}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing job_type and no default job type set on workspace.",
        )

    def test_workspace_start_invalid_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"job_type": "fake_job", "job_details": ""}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="fake_job is not in the list of available job types.",
        )

    def test_workspace_start_missing_job_type_workspace_default_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        self.workspace.default_job_type = "test_job"
        self.workspace.save()
        body = {"job_details": {}}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Successful start.",
        )

    def test_workspace_start_invalid_job_details_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"job_type": "test_job", "job_details": ""}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Job details not JSON.",
        )

    def test_workspace_start_resource_options_not_json_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"job_type": "test_job", "job_details": {}, "resource_options": ""}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Resource options not JSON.",
        )

    def test_workspace_start_invalid_file_path_put(self):
        self.client.force_authenticate(user=self.user)
        self.workspace.file_path = "."
        self.workspace.save()
        body = {"job_type": "test_job", "job_details": {}}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            success=False,
            message="Please contact a system administrator there is a failure with "
            "the workspace directory that will not allow for jobs to be created.",
        )

    def test_workspace_start_invalid_job_type_configuration(self):
        apps.get_app_config("user_workspaces_server").available_job_types["test_job"][
            "job_type"
        ] = "FakeJobType"
        self.client.force_authenticate(user=self.user)
        body = {"job_type": "test_job", "job_details": {}}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )

        apps.get_app_config("user_workspaces_server").available_job_types["test_job"][
            "job_type"
        ] = "LocalTestJob"

        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Job Type improperly configured. Please contact a system administrator to resolve this.",
        )

    def test_workspace_start_minimum_valid_put(self):
        self.client.force_authenticate(user=self.user)
        body = {"job_type": "test_job", "job_details": {}}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message="Successful start.",
        )

    def test_workspace_upload_missing_files_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "upload"])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="No files found in request.",
        )

    def test_workspace_upload_file_put(self):
        from io import StringIO

        test_file = StringIO("Test File")
        test_file.name = "test_file.txt"
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "upload"]),
            {"files": [test_file]},
            format="multipart",
        )
        self.assertValidResponse(
            response, status.HTTP_200_OK, success=True, message="Successful upload."
        )
        test_file.close()

    def test_workspace_upload_multiple_files_put(self):
        from io import StringIO

        test_file_1 = StringIO("Test File 1")
        test_file_1.name = "test_file_1.txt"
        test_file_2 = StringIO("Test File 2")
        test_file_2.name = "test_file_2.txt"
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "upload"]),
            {"files": [test_file_1, test_file_2]},
            format="multipart",
        )
        self.assertValidResponse(
            response, status.HTTP_200_OK, success=True, message="Successful upload."
        )
        test_file_1.close()
        test_file_2.close()

    def test_workspace_custom_params_validation_good(self):
        test_data_good = (
            {"num_cpus": 1, "memory_mb": 1025},
            {"time_limit_min": 480},
            {"gpu_enabled": True},
            {"unknown_param": "should_be_ignored"},
            {},
        )
        self.client.force_authenticate(user=self.user)
        body = {
            "job_type": "test_job",
            "job_details": {},
        }
        for test in test_data_good:
            with self.subTest(test=test):
                body["resource_options"] = test
                response = self.client.put(
                    reverse("workspaces_put_type", args=[self.workspace.id, "start"]),
                    body,
                )
                self.assertValidResponse(
                    response,
                    status.HTTP_200_OK,
                    success=True,
                    message="Successful start.",
                )

    def test_workspace_custom_params_validation_bad(self):
        test_data_bad = [
            (
                {"num_cpus": "one"},
                {
                    "msg": "[\"num_cpus: Value 'one' of type str does not match required type int. Skipping further validation of parameter num_cpus.\"]"
                },
            ),
            (
                {"memory_mb": 1},
                {"msg": "[\"memory_mb: Value '1' not above minimum of 1024.\"]"},
            ),
            (
                {"time_limit_min": 481},
                {
                    "msg": "[\"time_limit_min: Value '481' above maximum of 480.\"]",
                },
            ),
        ]
        self.client.force_authenticate(user=self.user)
        body = {
            "job_type": "test_job",
            "job_details": {},
        }
        for test in test_data_bad:
            with self.subTest(test=test):
                body["resource_options"] = test[0]
                response = self.client.put(
                    reverse("workspaces_put_type", args=[self.workspace.id, "start"]),
                    body,
                )
                self.assertValidResponse(
                    response,
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    success=False,
                    message=f"Invalid resource options found: {test[1]['msg']}",
                )

    def test_workspace_custom_params_validation_required(self):
        test_param = {
            "display_name": "Test Param",
            "description": "",
            "variable_name": "test_param",
            "validation": {"type": "str", "required": True},
        }
        apps.get_app_config("user_workspaces_server").parameters.append(test_param)
        self.client.force_authenticate(user=self.user)
        body = {
            "job_type": "test_job",
            "job_details": {},
        }
        response_bad = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]),
            body,
        )
        self.assertValidResponse(
            response_bad,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            success=False,
            message="Invalid resource options found: ['Missing required: test_param']",
        )
        body["resource_options"] = {"test_param": "test"}
        response_good = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]),
            body,
        )
        self.assertValidResponse(response_good, status.HTTP_200_OK, success=True)
        self.assertEqual(
            apps.get_app_config("user_workspaces_server").parameters.pop(), test_param
        )


class WorkspaceDELETEAPITests(WorkspaceAPITestCase):
    def test_workspace_not_found_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("workspaces_with_id", args=[9999]))
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message="Workspace 9999 not found for user.",
        )

    def test_workspace_invalid_file_path_delete(self):
        self.client.force_authenticate(user=self.user)
        self.workspace.file_path = "."
        self.workspace.save()
        response = self.client.delete(reverse("workspaces_with_id", args=[self.workspace.id]))
        self.assertValidResponse(
            response,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            success=False,
            message="Please contact a system administrator there is a failure with "
            "the workspace directory that will not allow for this workspace to be deleted.",
        )

    def test_workspace_active_job_delete(self):
        job_data = {
            "user_id": self.workspace.user_id,
            "workspace_id": self.workspace,
            "job_type": "TestJobType",
            "datetime_created": datetime.now(),
            "job_details": {"request_job_details": {}, "current_job_details": {}},
            "resource_name": "TestResource",
            "status": Job.Status.PENDING,
            "resource_job_id": -1,
            "core_hours": 0,
            "resource_options": {},
        }
        job = Job(**job_data)
        job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("workspaces_with_id", args=[self.workspace.id]))
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Cannot delete workspace, jobs are running for this workspace.",
        )

    def test_workspace_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("workspaces_with_id", args=[self.workspace.id]))
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message=f"Workspace {self.workspace.id} queued for deletion.",
        )


class JobAPITestCase(UserWorkspacesAPITestCase):
    jobs_url = reverse("jobs")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        workspace_data = {
            "user_id": cls.user,
            "name": "Test Name",
            "description": "Test Description",
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": {
                "request_workspace_details": {"files": [], "symlinks": []},
                "current_workspace_details": {"files": [], "symlinks": []},
            },
            "file_path": "test/1",
        }
        cls.workspace = Workspace(**workspace_data)
        cls.workspace.save()

        job_data = {
            "user_id": cls.workspace.user_id,
            "workspace_id": cls.workspace,
            "job_type": "TestJobType",
            "datetime_created": datetime.now(),
            "job_details": {"request_job_details": {}, "current_job_details": {}},
            "resource_name": "TestResource",
            "status": Job.Status.PENDING,
            "resource_job_id": -1,
            "core_hours": 0,
            "resource_options": {},
        }
        cls.job = Job(**job_data)
        cls.job.save()


class JobGETAPITests(JobAPITestCase):
    # TODO: Check body
    def test_job_id_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("jobs_with_id", args=[self.job.id]))
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)
        # parsed_content = json.loads(response.content)
        # job_to_check = Job.objects.filter(id=self.job.id).values(*Job.get_dict_fields()).get()
        # print(job_to_check)
        # self.assertDictEqual(parsed_content['data']['jobs'][0], job_to_check)

    def test_job_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.jobs_url}?status={self.job.status}")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_jobs_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.jobs_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)


class JobPUTAPITests(JobAPITestCase):
    def test_workspace_not_found_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("jobs_put_type", args=[9999, "stop"]))
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message="Job 9999 not found for user.",
        )

    def test_job_invalid_put_type_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("jobs_put_type", args=[self.job.id, "test"]))
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Invalid PUT type passed.",
        )

    def test_job_stop_resource_job_id_negative_one_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("jobs_put_type", args=[self.job.id, "stop"]))
        self.assertValidResponse(
            response, status.HTTP_200_OK, success=True, message="Successful stop."
        )

    def test_job_stop_complete_status_failed_put(self):
        self.client.force_authenticate(user=self.user)
        self.job.resource_job_id = 1
        self.job.status = Job.Status.COMPLETE
        self.job.save()
        response = self.client.put(reverse("jobs_put_type", args=[self.job.id, "stop"]))
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="This job is not running or pending.",
        )

    def test_job_stop_put(self):
        self.client.force_authenticate(user=self.user)
        self.job.resource_job_id = 1
        self.job.save()
        response = self.client.put(reverse("jobs_put_type", args=[self.job.id, "stop"]))
        self.assertValidResponse(
            response, status.HTTP_200_OK, success=True, message="Job queued to stop."
        )


class JobTypeAPITestCase(UserWorkspacesAPITestCase):
    job_types_url = reverse("job_types")


class JobTypeGETAPITests(JobTypeAPITestCase):
    def test_job_types_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.job_types_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")


class SharedWorkspaceAPITestCase(UserWorkspacesAPITestCase):
    shared_workspaces_url = reverse("shared_workspaces")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user_2 = User.objects.create_user("test_2", email="test_2@test.com")
        # Create a Workspace first that we can share from
        workspace_data = {
            "user_id": cls.user,
            "name": "Test Name",
            "description": "Test Description",
            "disk_space": 0,
            "datetime_created": datetime.now(),
            "workspace_details": {
                "request_workspace_details": {"files": [], "symlinks": []},
                "current_workspace_details": {"files": [], "symlinks": []},
            },
            "file_path": "test/1",
        }
        cls.original_workspace = Workspace(**workspace_data)
        cls.original_workspace.save()

        workspace_data["user_id"] = cls.user_2
        workspace_data["file_path"] = "test/2"
        cls.shared_workspace = Workspace(**workspace_data)
        cls.shared_workspace.save()

        shared_workspace_data = {
            "original_workspace_id": cls.original_workspace,
            "shared_workspace_id": cls.shared_workspace,
            "datetime_share_created": datetime.now(),
        }
        cls.shared_workspace_mapping = SharedWorkspaceMapping(**shared_workspace_data)
        cls.shared_workspace_mapping.save()


class SharedWorkspaceGETAPITests(SharedWorkspaceAPITestCase):
    def test_shared_workspace_id_get_original_workspace_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.id])
        )
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_shared_workspace_id_get_shared_workspace_user(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.get(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.id])
        )
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_shared_workspace_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.shared_workspaces_url}?is_accepted=False")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_shared_workspaces_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.shared_workspaces_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_shared_workspaces_get_none_found(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.shared_workspaces_url}?is_accepted=True")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)


class SharedWorkspacePOSTAPITests(SharedWorkspaceAPITestCase):
    def test_unauthenticated(self):
        response = self.client.get(self.shared_workspaces_url, {})
        self.assertValidResponse(response, status.HTTP_401_UNAUTHORIZED, success=False)

    def test_empty_post(self):
        self.client.force_authenticate(user=self.user)
        body = {}
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_missing_body_post(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.shared_workspaces_url)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_missing_original_workspace_id_body_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"shared_user_ids": []}
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing required fields.",
        )

    def test_missing_shared_user_ids_body_post(self):
        self.client.force_authenticate(user=self.user)
        body = {"original_workspace_id": self.original_workspace.pk}
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing required fields.",
        )

    def test_invalid_original_workspace_for_user(self):
        self.client.force_authenticate(user=self.user)
        body = {"shared_user_ids": [], "original_workspace_id": self.shared_workspace.pk}
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message=f"Workspace {body['original_workspace_id']} not found for user.",
        )

    def test_invalid_shared_user_ids_format(self):
        self.client.force_authenticate(user=self.user)
        body = {"shared_user_ids": "", "original_workspace_id": self.original_workspace.pk}
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="shared_user_ids is not a list.",
        )

    def test_invalid_shared_user_ids(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "shared_user_ids": [-9999],
            "original_workspace_id": self.original_workspace.pk,
        }
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Invalid user id provided.",
        )

    def test_minimum_valid_post(self):
        self.client.force_authenticate(user=self.user)
        body = {
            "shared_user_ids": [self.user_2.pk],
            "original_workspace_id": self.original_workspace.pk,
        }
        response = self.client.post(self.shared_workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        # TODO: Check body


class SharedWorkspacePUTAPITests(SharedWorkspaceAPITestCase):
    def test_shared_workspace_not_found_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse("shared_workspaces_put_type", args=[9999, "test"]))
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message="Shared workspace 9999 not found.",
        )

    def test_workspace_invalid_put_type_put(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.put(
            reverse("shared_workspaces_put_type", args=[self.shared_workspace.pk, "test"])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Invalid PUT type passed.",
        )

    def test_shared_workspace_put_type_accept(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.put(
            reverse("shared_workspaces_put_type", args=[self.shared_workspace.pk, "accept"])
        )
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")


class SharedWorkspaceDELETEAPITests(SharedWorkspaceAPITestCase):
    def test_shared_workspace_not_found_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse("shared_workspaces_with_id", args=[9999]))
        self.assertValidResponse(
            response,
            status.HTTP_404_NOT_FOUND,
            success=False,
            message="Shared workspace 9999 not found.",
        )

    def test_shared_workspace_delete_accepted_workspace(self):
        self.shared_workspace_mapping.is_accepted = True
        self.shared_workspace_mapping.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message=f"Shared workspace {self.shared_workspace.pk} has been accepted and cannot be deleted.",
        )

    def test_shared_workspace_delete_invalid_path(self):
        self.shared_workspace.file_path = "."
        self.shared_workspace.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            success=False,
            message="Please contact a system administrator there is a failure with "
            "the workspace directory that will not allow for this workspace to be deleted.",
        )

    def test_shared_workspace_delete_invalid_user(self):
        invalid_user = User.objects.create_user("invalid_user", email="invalid@test.com")
        self.client.force_authenticate(user=invalid_user)
        response = self.client.delete(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_403_FORBIDDEN,
            success=False,
            message=f"User does not have permissions for shared workspace {self.shared_workspace.pk}.",
        )

    def test_shared_workspace_delete_original_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message=f"Shared workspace {self.shared_workspace.pk} queued for deletion.",
        )

    def test_shared_workspace_delete_shared_user(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.delete(
            reverse("shared_workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message=f"Shared workspace {self.shared_workspace.pk} queued for deletion.",
        )


class WorkspaceAndSharedWorkspaceAPITests(SharedWorkspaceAPITestCase):
    def test_workspace_put_not_accepted_shared_workspace(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.put(reverse("workspaces_with_id", args=[self.shared_workspace.pk]))
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message=f"Workspace {self.shared_workspace.pk} is a shared workspace and has not been accepted.",
        )

    def test_workspace_delete_not_accepted_shared_workspace(self):
        self.client.force_authenticate(user=self.user_2)
        response = self.client.delete(
            reverse("workspaces_with_id", args=[self.shared_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message=f"Workspace {self.shared_workspace.pk} is a shared workspace and has not been accepted.",
        )

    def test_workspace_delete_original_workspace_with_not_accepted_shared_workspace(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            reverse("workspaces_with_id", args=[self.original_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message=f"Workspace {self.original_workspace.pk} has shared workspaces associated with it, that have not yet been accepted. Please cancel those shares to delete this workspace.",
        )

    def test_workspace_delete_original_workspace_with_accepted_shared_workspace(self):
        self.client.force_authenticate(user=self.user)
        self.shared_workspace_mapping.is_accepted = True
        self.shared_workspace_mapping.save()
        response = self.client.delete(
            reverse("workspaces_with_id", args=[self.original_workspace.pk])
        )
        self.assertValidResponse(
            response,
            status.HTTP_200_OK,
            success=True,
            message=f"Workspace {self.original_workspace.pk} queued for deletion.",
        )


class ParameterGETAPITest(UserWorkspacesAPITestCase):
    parameters_url = reverse("parameters")
    params_config = apps.get_app_config("user_workspaces_server").parameters

    def test_parameters_get(self):
        response = self.client.get(self.parameters_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True, message="Successful.")
        self.assertContains(response, "data")
        response_data = response.json()["data"]
        self.assertIn("parameters", response_data)
        self.assertEqual(response_data["parameters"], self.params_config)
