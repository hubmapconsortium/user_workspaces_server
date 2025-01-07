import logging

from django.contrib.auth.models import User
from django.http import JsonResponse
from rest_framework.authtoken.views import APIView
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class UserView(APIView):
    permission_classes = [IsAuthenticated]
    filter_user_fields = ["first_name", "last_name", "username", "email"]
    return_user_fields = ["id", "first_name", "last_name", "username", "email"]

    def get(self, request):
        users = User.objects.all()

        if params := request.GET:
            for key in set(params.keys()).intersection(set(self.filter_user_fields)):
                users = users.filter(**{key: params[key]})

        users = list(users.all().values(*self.return_user_fields))

        response = {"message": "Successful.", "success": True, "data": {"users": []}}

        if users:
            response["data"]["users"] = users
        else:
            response["message"] = "Users matching given parameters could not be found."

        return JsonResponse(response)
