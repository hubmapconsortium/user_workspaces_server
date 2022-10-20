from user_workspaces_server.models import Workspace, Job, UserQuota, ExternalUserMapping
from django.urls import reverse
from rest_framework import status
from datetime import datetime
from rest_framework.test import APITestCase
from django.contrib.auth.models import User, Group
from rest_framework.authtoken.models import Token
import json


class UserWorkspacesAPITestCase(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('jpuerto')

    def assertValidResponse(self, response, status_code, success=None, message=''):
        self.assertEqual(response.status_code, status_code)
        self.assertContains(response, 'success', status_code=status_code)
        self.assertContains(response, 'message', status_code=status_code)
        parsed_response = json.loads(response.content)
        if success is not None:
            self.assertEqual(parsed_response['success'], success)
        if message:
            self.assertEqual(parsed_response['message'], message)


class TokenAPITests(UserWorkspacesAPITestCase):
    tokens_url = reverse('tokens')

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        api_user = User.objects.create_user('api_user')
        api_clients_group = Group.objects.create(name='api_clients')
        api_clients_group.user_set.add(api_user)
        cls.client_token = Token.objects.create(user=api_user)

    # TODO: Mocking
    def test_get_invalid_user_token(self):
        body = {
            "client_token": self.client_token.key,
            "user_info": {
                "username": "fake_user",
                "email": "fake@fake.com"
            }
        }
        # response = self.client.post(self.tokens_url, body)
        # print(response.content)

    # TODO: Mocking
    def test_get_user_token(self):
        body = {
            "client_token": self.client_token.key,
            "user_info": {
                "username": self.user.username,
                "email": "test@test.com"
            }
        }
        # response = self.client.post(self.tokens_url, body)
        # print(response.content)
        # self.assertValidResponse(response, status.HTTP_200_OK, success=True)


class StatusAPITests(UserWorkspacesAPITestCase):
    status_url = reverse('status')

    def test_get_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.status_url)
        self.assertValidResponse(response, status.HTTP_200_OK)
        self.assertContains(response, 'version')
        self.assertContains(response, 'build')


class WorkspaceAPITestCase(UserWorkspacesAPITestCase):
    workspaces_url = reverse('workspaces')

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
                "request_workspace_details": {'files': [], 'symlinks': []},
                "current_workspace_details": {'files': [], 'symlinks': []}
            },
            "file_path": "test/1"
        }
        cls.workspace = Workspace(**workspace_data)
        cls.workspace.save()


class WorkspaceGETAPITests(WorkspaceAPITestCase):
    def test_workspace_id_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('workspaces_with_id', args=[self.workspace.id]))
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)
        parsed_content = json.loads(response.content)
        workspace_to_check = Workspace.objects.filter(id=self.workspace.id).values(*Workspace.get_dict_fields()).get()
        # print(workspace_to_check)
        # self.assertDictEqual(parsed_content['data']['workspaces'][0], workspace_to_check)

    def test_workspace_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{self.workspaces_url}?name={self.workspace.name}')
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
        body = {'description': 'Test'}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Missing required fields.')

    def test_missing_description_body_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test'}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Missing required fields.')

    def test_malformed_workspace_details_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': 'invalid'}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Workspace details not JSON.')

    # TODO: Mocking.
    def test_minimum_valid_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': {}}
        # response = self.client.post(self.workspaces_url, body)
        # print(response)
        # self.assertValidResponse(response, status.HTTP_200_OK)

    def test_invalid_symlinks_structure_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': {
            'symlinks': ''
        }}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message="'symlinks' index must contain a list.")

    def test_invalid_files_structure_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': {
            'files': ''
        }}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message="'files' index must contain a list.")

    def test_invalid_file_name_post(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': {
            'files': [{'name': '../file.txt', 'content': 'Hello World'}]
        }}
        response = self.client.post(self.workspaces_url, body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message="File name cannot contain double dots.")


class WorkspacePUTAPITests(WorkspaceAPITestCase):
    def test_workspace_not_found_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('workspaces_with_id', args=[9999]))
        self.assertValidResponse(response, status.HTTP_404_NOT_FOUND, success=False,
                                 message='Workspace 9999 not found for user.')

    def test_workspace_data_update_missing_body_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('workspaces_with_id', args=[self.workspace.id]))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_workspace_data_update_invalid_workspace_details_put(self):
        self.client.force_authenticate(user=self.user)
        body = {'name': 'Test', 'description': 'Test', 'workspace_details': ''}
        response = self.client.put(reverse('workspaces_with_id', args=[self.workspace.id]), body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Workspace details not JSON.')

    def test_workspace_invalid_put_type_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'test']))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Invalid PUT type passed.')

    def test_workspace_start_missing_body_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'start']))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False)

    def test_workspace_start_missing_job_type_put(self):
        self.client.force_authenticate(user=self.user)
        body = {}
        response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'start']), body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Missing job_type.')

    def test_workspace_start_invalid_job_details_put(self):
        self.client.force_authenticate(user=self.user)
        body = {'job_type': 'test', 'job_details': ''}
        response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'start']), body)
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Job details not JSON.')

    def test_workspace_upload_missing_files_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'upload']))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='No files found in request.')

    # TODO: Mocking
    def test_workspace_upload_file_put(self):
        from io import StringIO
        test_file = StringIO("Test File")
        test_file.name = "test_file.txt"
        self.client.force_authenticate(user=self.user)
        # response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'upload']), {'files': [test_file]})
        test_file.close()

    # TODO: Mocking
    def test_workspace_upload_multiple_files_put(self):
        from io import StringIO
        test_file_1 = StringIO('Test File 1')
        test_file_1.name = 'test_file_1.txt'
        test_file_2 = StringIO('Test File 2')
        test_file_2.name = 'test_file_2.txt'
        self.client.force_authenticate(user=self.user)
        # response = self.client.put(reverse('workspaces_put_type', args=[self.workspace.id, 'upload']), {'files': [test_file_1, test_file_2]})
        test_file_1.close()
        test_file_2.close()


class WorkspaceDELETEAPITests(WorkspaceAPITestCase):
    def test_workspace_not_found_delete(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('workspaces_with_id', args=[9999]))
        self.assertValidResponse(response, status.HTTP_404_NOT_FOUND, success=False,
                                 message='Workspace 9999 not found for user.')

    def test_workspace_active_job_delete(self):
        job_data = {
            "workspace_id": self.workspace,
            "job_type": "TestJobType",
            "datetime_created": datetime.now(),
            "job_details": {
                'request_job_details': {},
                'current_job_details': {}
            },
            "resource_name": "TestResource",
            "status": Job.Status.PENDING,
            "resource_job_id": -1,
            "core_hours": 0
        }
        job = Job(**job_data)
        job.save()

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('workspaces_with_id', args=[self.workspace.id]))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Cannot delete workspace, jobs are running for this workspace.')

    # TODO: Add test for actually deleting (and mocking)


class JobAPITestCase(UserWorkspacesAPITestCase):
    jobs_url = reverse('jobs')

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
                "request_workspace_details": {'files': [], 'symlinks': []},
                "current_workspace_details": {'files': [], 'symlinks': []}
            },
            "file_path": "test/1"
        }
        cls.workspace = Workspace(**workspace_data)
        cls.workspace.save()


        job_data = {
            "workspace_id": cls.workspace,
            "job_type": "TestJobType",
            "datetime_created": datetime.now(),
            "job_details": {
                'request_job_details': {},
                'current_job_details': {}
            },
            "resource_name": "TestResource",
            "status": Job.Status.PENDING,
            "resource_job_id": -1,
            "core_hours": 0
        }
        cls.job = Job(**job_data)
        cls.job.save()


class JobGETAPITests(JobAPITestCase):
    def test_job_id_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('jobs_with_id', args=[self.job.id]))
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)
        parsed_content = json.loads(response.content)
        workspace_to_check = Workspace.objects.filter(id=self.workspace.id).values(*Workspace.get_dict_fields()).get()
        # print(workspace_to_check)
        # self.assertDictEqual(parsed_content['data']['workspaces'][0], workspace_to_check)

    def test_job_query_param_name_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'{self.jobs_url}?status={self.job.status}')
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)

    def test_jobs_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.jobs_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)


class JobPUTAPITests(JobAPITestCase):
    def test_workspace_not_found_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('jobs_put_type', args=[9999, 'stop']))
        self.assertValidResponse(response, status.HTTP_404_NOT_FOUND, success=False,
                                 message='Job 9999 not found for user.')

    def test_job_invalid_put_type_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('jobs_put_type', args=[self.job.id, 'test']))
        self.assertValidResponse(response, status.HTTP_400_BAD_REQUEST, success=False,
                                 message='Invalid PUT type passed.')

    def test_job_stop_resource_job_id_negative_one_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('jobs_put_type', args=[self.job.id, 'stop']))
        self.assertValidResponse(response, status.HTTP_200_OK, success=True,
                                 message='Successful stop.')

    # TODO: Mocking
    def test_job_stop_put(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.put(reverse('jobs_put_type', args=[self.job.id, 'stop']))


class JobTypeAPITestCase(UserWorkspacesAPITestCase):
    job_types_url = reverse('job_types')


class JobTypeGETAPITests(JobTypeAPITestCase):
    def test_job_types_get(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.job_types_url)
        self.assertValidResponse(response, status.HTTP_200_OK, success=True)