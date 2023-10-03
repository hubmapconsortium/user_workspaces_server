import logging
import os
from pathlib import Path

from django.http import JsonResponse
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class StatusView(APIView):
    permission_classes = []

    def get(self, request):
        base_dir = Path(__file__).resolve().parent.parent
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

        response_data = {
            "message": "",
            "success": True,
            "version": version,
            "build": build,
        }

        return JsonResponse(response_data)
