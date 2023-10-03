import logging

import requests as http_r
from django.http import HttpResponse
from rest_framework.exceptions import APIException
from rest_framework.views import APIView

from user_workspaces_server import models

logger = logging.getLogger(__name__)


class PassthroughView(APIView):
    permission_classes = []

    def get(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.get(url, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough GET failure")
            raise APIException

    def post(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.post(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough POST failure")
            raise APIException

    def patch(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.patch(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough PATCH failure")
            raise APIException

    def put(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.put(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough PUT failure")
            raise APIException

    def delete(self, request, hostname, job_id, remainder=None):
        try:
            job_model = models.Job.objects.get(pk=job_id)
            proxy_details = job_model.job_details["current_job_details"][
                "proxy_details"
            ]
            port = proxy_details["port"]
            url = f'{request.scheme}://{hostname}:{port}{request.path}?{request.META.get("QUERY_STRING")}'
            response = http_r.delete(url, data=request.body, cookies=request.COOKIES)
            return HttpResponse(
                response, headers=response.headers, status=response.status_code
            )
        except Exception:
            logger.exception("Passthrough DELETE failure")
            raise APIException
