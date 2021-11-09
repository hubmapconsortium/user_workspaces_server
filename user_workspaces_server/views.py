from django.shortcuts import render

# Create your views here.
from django.http import JsonResponse
from django.views import View


class WorkspaceView(View):
    def get(self, request, workspace_uuid=None):
        return JsonResponse({'message': 'Successful!', 'success': True})

    def post(self, request):
        return JsonResponse({'message': 'Successful!', 'success': True})

    def put(self, request, workspace_uuid, put_type):
        if put_type.lower() == 'start':
            return JsonResponse({'message': 'Successful start!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobView(View):
    def get(self, request, job_uuid=None):
        return JsonResponse({'message': 'Successful!', 'success': True})

    def put(self, request, job_uuid, put_type):
        if put_type.lower() == 'stop':
            return JsonResponse({'message': 'Successful stop!', 'success': True})
        else:
            return JsonResponse({'message': 'Invalid type passed.', 'success': False})


class JobTypeView(View):
    def get(self, request):
        return JsonResponse({'message': 'Successful!', 'success': True})
