import logging
import os
from pathlib import Path

from django.apps import apps
from django.http import JsonResponse
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class StatusView(APIView):
    permission_classes = []

    def get(self, request):
        base_dir = Path(__file__).resolve().parent.parent.parent
        version_file_path = os.path.join(base_dir, "VERSION")
        build_file_path = os.path.join(base_dir, "BUILD")

        version = (
            open(version_file_path).read().strip()
            if os.path.exists(version_file_path)
            else "invalid_version"
        )
        build = (
            open(build_file_path).read().strip()
            if os.path.exists(build_file_path)
            else "invalid_build"
        )

        main_resource = apps.get_app_config("user_workspaces_server").main_resource
        api_user_authentication = apps.get_app_config(
            "user_workspaces_server"
        ).api_user_authentication

        response_data = {
            "message": "",
            "success": True,
            "version": version,
            "build": build,
            "dependencies": {
                "main_resource": main_resource.health_check(),
                "api_user_authentication": api_user_authentication.health_check(),
            },
        }

        return JsonResponse(response_data)
