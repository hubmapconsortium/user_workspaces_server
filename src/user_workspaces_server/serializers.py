from django.contrib.auth.models import User
from rest_framework import serializers
from user_workspaces_server.models import SharedWorkspaceMapping, Workspace


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class WorkspaceSerializer(serializers.ModelSerializer):
    user_id = UserSerializer(read_only=True)

    class Meta:
        model = Workspace
        fields = Workspace.get_dict_fields()
        fields.append("user_id")

    def __init__(self, *args, **kwargs):
        workspace_type = kwargs.pop("workspace_type", None)
        super().__init__(*args, **kwargs)

        if workspace_type == "shared_workspace":
            for field_name in set(self.fields) - {"id", "user_id", "name", "description"}:
                self.fields.pop(field_name)


class SharedWorkspaceMappingSerializer(serializers.ModelSerializer):
    original_workspace_id = WorkspaceSerializer(read_only=True, workspace_type="shared_workspace")
    shared_workspace_id = WorkspaceSerializer(read_only=True, workspace_type="shared_workspace")

    class Meta:
        model = SharedWorkspaceMapping
        fields = "__all__"
