API Reference
=============

The User Workspaces Server provides a RESTful API for managing workspaces, jobs, users, and system resources. All endpoints use JSON for request and response payloads.

Authentication
--------------

The API uses custom token-based authentication with the ``UWS-Authorization`` header:

.. code-block:: http

    UWS-Authorization: <token>

Authentication Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: user_workspaces_server.views.user_workspaces_server_token_view.UserWorkspacesServerTokenView
   :members:

Workspace Management
--------------------

Workspaces represent user environments with isolated storage and compute access.

.. autoclass:: user_workspaces_server.views.workspace_view.WorkspaceView
   :members:

Shared Workspace Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Collaborative workspace features for sharing between users.

.. autoclass:: user_workspaces_server.views.shared_workspace_view.SharedWorkspaceView
   :members:

Job Management
--------------

Jobs represent computational tasks executed within workspaces.

.. autoclass:: user_workspaces_server.views.job_view.JobView
   :members:

Job Type Information
~~~~~~~~~~~~~~~~~~~~

Information about available job types and their parameters.

.. autoclass:: user_workspaces_server.views.job_type_view.JobTypeView
   :members:

User Management
---------------

User information, quotas, and authentication details.

.. autoclass:: user_workspaces_server.views.user_view.UserView
   :members:

System Information
------------------

System status and configuration information.

.. autoclass:: user_workspaces_server.views.status_view.StatusView
   :members:

Parameter Validation
~~~~~~~~~~~~~~~~~~~~

Parameter and configuration validation endpoints.

.. autoclass:: user_workspaces_server.views.parameter_view.ParameterView
   :members:

WebSocket Support
-----------------

Real-time communication for job status updates and interactive sessions.

.. autoclass:: user_workspaces_server.ws_consumers.JobStatusConsumer
   :members:

.. autoclass:: user_workspaces_server.ws_consumers.PassthroughConsumer
   :members:

Passthrough Proxy
~~~~~~~~~~~~~~~~~

HTTP proxy for forwarding requests to running jobs.

.. autoclass:: user_workspaces_server.views.passthrough_view.PassthroughView
   :members:

Data Models
-----------

Core data models used by the API.

.. autoclass:: user_workspaces_server.models.Workspace
   :members:

.. autoclass:: user_workspaces_server.models.Job
   :members:

.. autoclass:: user_workspaces_server.models.UserQuota
   :members:

.. autoclass:: user_workspaces_server.models.ExternalUserMapping
   :members:

.. autoclass:: user_workspaces_server.models.SharedWorkspaceMapping
   :members:

Serializers
-----------

Request/response serialization classes.

.. automodule:: user_workspaces_server.serializers
   :members: