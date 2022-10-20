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
from django.urls import path, include
from . import views
from . import ws_consumers

token_view_patterns = [
    path('', views.UserWorkspacesServerTokenView.as_view(), name='tokens')
]

workspace_view_patterns = [
    path('', views.WorkspaceView.as_view(), name='workspaces'),
    path('<int:workspace_id>/', views.WorkspaceView.as_view(), name='workspaces_with_id'),
    path('<int:workspace_id>/<str:put_type>/', views.WorkspaceView.as_view(), name='workspaces_put_type'),
]

job_view_patterns = [
    path('', views.JobView.as_view(), name='jobs'),
    path('<int:job_id>/', views.JobView.as_view(), name='jobs_with_id'),
    path('<int:job_id>/<str:put_type>/', views.JobView.as_view(), name='jobs_put_type'),
]

job_type_view_patterns = [
    path('', views.JobTypeView.as_view(), name='job_types'),
]

passthrough_view_patterns = [
    path('<str:hostname>/<int:job_id>/', views.PassthroughView.as_view(), name='passthrough'),
    path('<str:hostname>/<int:job_id>/<path:remainder>', views.PassthroughView.as_view(), name='passthrough_remainder')
]

urlpatterns = [
    path('tokens/', include(token_view_patterns)),
    path('workspaces/', include(workspace_view_patterns)),
    path('jobs/', include(job_view_patterns)),
    path('job_types/', include(job_type_view_patterns)),
    path('passthrough/', include(passthrough_view_patterns)),
    path('status/', views.StatusView.as_view(), name='status')
]

ws_urlpatterns = [
    path('passthrough/<str:hostname>/<int:job_id>/<path:remainder>', ws_consumers.PassthroughConsumer.as_asgi(), name='ws_passthrough'),
    path('jobs/', ws_consumers.JobStatusConsumer.as_asgi(), name='ws_jobs'),
    path('jobs/<int:job_id>/', ws_consumers.JobStatusConsumer.as_asgi(), name='ws_job'),
]
