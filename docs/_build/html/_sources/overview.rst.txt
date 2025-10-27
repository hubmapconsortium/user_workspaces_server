Overview
========

User Workspaces Server (UWS) is a REST API service that manages user workspaces and computational jobs in scientific computing environments. It provides a unified interface for workspace lifecycle management, job execution, and resource allocation across different authentication providers and compute platforms.

Key Features
------------

* **Multi-tenant Workspace Management**: Create, manage, and share user workspaces with configurable quotas
* **Pluggable Authentication**: Support for multiple authentication backends (Globus, PSC API, LDAP, Local)
* **Flexible Storage**: Configurable storage backends (Local Filesystem, HuBMAP-specific storage)
* **Compute Resource Integration**: Support for different job execution environments (Local, SLURM)
* **Real-time Updates**: WebSocket support for live job status updates
* **Background Task Processing**: Asynchronous task handling with Django-Q
* **Collaborative Features**: Workspace sharing and collaborative access

Core Concepts
-------------

Workspaces
~~~~~~~~~~

Workspaces are containerized user environments that provide:

* Isolated file storage with configurable quotas
* User-specific configuration and state
* Integration with compute resources for job execution
* Support for sharing between users

Jobs
~~~~

Jobs represent computational tasks that:

* Execute within the context of a workspace
* Can be of different types (JupyterLab, custom applications)
* Provide real-time status updates
* Track resource usage (CPU hours, memory)

Users and Authentication
~~~~~~~~~~~~~~~~~~~~~~~~

The system supports:

* External authentication provider integration
* User quota management (disk space, compute hours)
* Role-based access control
* External user mapping for identity federation

Architecture Principles
-----------------------

* **Configuration-Driven**: Components are loaded dynamically based on JSON configuration
* **Plugin Architecture**: Extensible through abstract base classes and implementations
* **Dependency Injection**: Controllers receive dependencies during initialization
* **Asynchronous Processing**: Background tasks for long-running operations
* **RESTful API**: Standard HTTP methods with JSON payloads
* **Real-time Communication**: WebSocket support for interactive features