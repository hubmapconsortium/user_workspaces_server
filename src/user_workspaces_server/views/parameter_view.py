from django.apps import apps
from django.http import JsonResponse
from rest_framework.views import APIView


class ParameterView(APIView):

    def get(self):
        full_param_info = apps.get_app_config("user_workspaces_server").parameters
        return JsonResponse({"parameters": full_param_info})
