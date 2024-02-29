from django.test import TestCase

from user_workspaces_server.models import Job, Workspace


class WorkspaceModelTests(TestCase):
    def test_get_workspace_query_param_fields(self):
        """Check Workspace query parameters"""
        assert Workspace.get_query_param_fields() == ["name", "description", "status"]

    def test_get_workspace_dict_fields(self):
        """Check Workspace dictionary fields"""
        assert Workspace.get_dict_fields() == [
            "id",
            "name",
            "description",
            "disk_space",
            "datetime_created",
            "workspace_details",
            "status",
            "default_job_type",
        ]


class JobModelTests(TestCase):
    def test_get_workspace_query_param_fields(self):
        """Check Job query parameters"""
        assert Job.get_query_param_fields() == [
            "workspace_id",
            "resource_job_id",
            "job_type",
            "status",
        ]

    def test_get_workspace_dict_fields(self):
        """Check Job dictionary fields"""
        assert Job.get_dict_fields() == [
            "id",
            "workspace_id",
            "resource_job_id",
            "job_type",
            "status",
            "datetime_created",
            "datetime_start",
            "datetime_end",
            "core_hours",
            "job_details",
        ]
