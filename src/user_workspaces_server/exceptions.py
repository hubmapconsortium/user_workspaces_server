from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


def workspaces_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data = {"success": False, "message": response.data["detail"]}

    return response


class WorkspaceClientException(APIException):
    status_code = 400
    default_detail = "Error with client request."
    default_code = "client_request_error"
