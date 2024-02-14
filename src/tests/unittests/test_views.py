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
from user_workspaces_server.models import Job, Workspace


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
        cls.client_token = Token.objects.create(user=api_user)

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
        # parsed_content = json.loads(response.content)
        # workspace_to_check = Workspace.objects.filter(id=self.workspace.id).values(*Workspace.get_dict_fields()).get()
        # print(workspace_to_check)
        # self.assertDictEqual(parsed_content['data']['workspaces'][0], workspace_to_check)

    def test_workspace_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"{self.workspaces_url}?name={self.workspace.name}")
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

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

    def test_workspace_start_missing_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {}
        response = self.client.put(
            reverse("workspaces_put_type", args=[self.workspace.id, "start"]), body
        )
        self.assertValidResponse(
            response,
            status.HTTP_400_BAD_REQUEST,
            success=False,
            message="Missing job_type and no default job type set on workspace.",
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

    def test_workspace_start_invalid_file_path_put(self):
        self.client.force_authenticate(user=self.user)
        self.workspace.file_path = "."
        self.workspace.save()
        body = {"job_type": "test", "job_details": {}}
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

    # TODO: Update this test once we allow for passing job types
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
