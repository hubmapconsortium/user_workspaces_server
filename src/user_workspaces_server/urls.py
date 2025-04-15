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

from django.urls import include, path

from . import ws_consumers
from .views import (
    job_type_view,
    job_view,
    parameter_view,
    passthrough_view,
    shared_workspace_view,
    status_view,
    user_view,
    user_workspaces_server_token_view,
    workspace_view,
)

token_view_patterns = [
    path(
        "",
        user_workspaces_server_token_view.UserWorkspacesServerTokenView.as_view(),
        name="tokens",
    )
]

workspace_view_patterns = [
    path("", workspace_view.WorkspaceView.as_view(), name="workspaces"),
    path(
        "<int:workspace_id>/",
        workspace_view.WorkspaceView.as_view(),
        name="workspaces_with_id",
    ),
    path(
        "<int:workspace_id>/<str:put_type>/",
        workspace_view.WorkspaceView.as_view(),
        name="workspaces_put_type",
    ),
]

job_view_patterns = [
    path("", job_view.JobView.as_view(), name="jobs"),
    path("<int:job_id>/", job_view.JobView.as_view(), name="jobs_with_id"),
    path("<int:job_id>/<str:put_type>/", job_view.JobView.as_view(), name="jobs_put_type"),
]

job_type_view_patterns = [
    path("", job_type_view.JobTypeView.as_view(), name="job_types"),
]

parameter_view_patterns = [
    path("", parameter_view.ParameterView.as_view(), name="parameters"),
]

passthrough_view_patterns = [
    path(
        "<str:hostname>/<int:job_id>/",
        passthrough_view.PassthroughView.as_view(),
        name="passthrough",
    ),
    path(
        "<str:hostname>/<int:job_id>/<path:remainder>",
        passthrough_view.PassthroughView.as_view(),
        name="passthrough_remainder",
    ),
]

user_view_patterns = [
    path(
        "",
        user_view.UserView.as_view(),
        name="users",
    )
]

shared_workspace_view_patterns = [
    path(
        "",
        shared_workspace_view.SharedWorkspaceView.as_view(),
        name="shared_workspaces",
    ),
    path(
        "<int:shared_workspace_id>/",
        shared_workspace_view.SharedWorkspaceView.as_view(),
        name="shared_workspaces_with_id",
    ),
    path(
        "<int:shared_workspace_id>/<str:put_type>/",
        shared_workspace_view.SharedWorkspaceView.as_view(),
        name="shared_workspaces_put_type",
    ),
]

urlpatterns = [
    path("tokens/", include(token_view_patterns)),
    path("workspaces/", include(workspace_view_patterns)),
    path("jobs/", include(job_view_patterns)),
    path("job_types/", include(job_type_view_patterns)),
    path("passthrough/", include(passthrough_view_patterns)),
    path("parameters/", include(parameter_view_patterns)),
    path("users/", include(user_view_patterns)),
    path("shared_workspaces/", include(shared_workspace_view_patterns)),
    path("status/", status_view.StatusView.as_view(), name="status"),
]

ws_urlpatterns = [
    path(
        "passthrough/<str:hostname>/<int:job_id>/<path:remainder>",
        ws_consumers.PassthroughConsumer.as_asgi(),
        name="ws_passthrough",
    ),
    path("jobs/", ws_consumers.JobStatusConsumer.as_asgi(), name="ws_jobs"),
    path("jobs/<int:job_id>/", ws_consumers.JobStatusConsumer.as_asgi(), name="ws_job"),
]
