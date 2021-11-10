"""user_workspaces_server_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from . import views

workspace_view_patterns = [
    path('', views.WorkspaceView.as_view()),
    path('<int:workspace_id>/', views.WorkspaceView.as_view()),
    path('<int:workspace_id>/<str:put_type>/', views.WorkspaceView.as_view()),
]

job_view_patterns = [
    path('', views.JobView.as_view()),
    path('<int:job_id>/', views.JobView.as_view()),
    path('<int:job_id>/<str:put_type>/', views.JobView.as_view()),
]

job_type_view_patterns = [
    path('', views.JobTypeView.as_view()),
]

urlpatterns = [
    path('workspaces/', include(workspace_view_patterns)),
    path('jobs/', include(job_view_patterns)),
    path('job_types/', include(job_type_view_patterns)),
]
