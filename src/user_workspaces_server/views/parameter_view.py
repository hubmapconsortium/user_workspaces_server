from django.apps import apps
from django.http import JsonResponse
from rest_framework.views import APIView


class ParameterView(APIView):

    def get(self, request):
        full_param_info = apps.get_app_config("user_workspaces_server").parameters
        return JsonResponse(
            {
                "message": "Successful.",
                "success": True,
                "data": {"parameters": full_param_info},
            }
        )
