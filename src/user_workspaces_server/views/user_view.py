import logging

from django.contrib.auth.models import User
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import JsonResponse
from rest_framework.authtoken.views import APIView
from rest_framework.permissions import IsAuthenticated

logger = logging.getLogger(__name__)


class UserView(APIView):
    permission_classes = [IsAuthenticated]
    return_user_fields = ["id", "first_name", "last_name", "username", "email"]

    def get(self, request):
        users = User.objects.all()

        if request.GET and "search" in request.GET:
            search = request.GET["search"]
            users = users.annotate(
                first_last=Concat("first_name", Value(" "), "last_name")
            ).filter(Q(first_last__icontains=search) | Q(email__icontains=search))

        users = list(users.exclude(username=request.user.username).all().values(*self.return_user_fields))

        response = {"message": "Successful.", "success": True, "data": {"users": []}}

        if users:
            response["data"]["users"] = users
        else:
            response["message"] = "Users matching given parameters could not be found."

        return JsonResponse(response)
