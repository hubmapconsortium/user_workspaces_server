Architecture
============

The User Workspaces Server follows a modular, plugin-based architecture that allows for flexible configuration and extensibility. This section describes the core architectural patterns and components.

System Architecture Overview
-----------------------------

.. mermaid::

   graph TB
       subgraph "Client Layer"
           Client[REST API Client]
           WSClient[WebSocket Client]
       end

       subgraph "API Layer"
           REST[REST API Endpoints]
           WS[WebSocket Consumers]
           Auth[Token Authentication]
       end

       subgraph "Application Layer"
           Views[Views/ViewSets]
           Serializers[Serializers]
           Models[Django Models]
       end

       subgraph "Controller Layer"
           JobTypes[Job Types]
           Resources[Resources]
           StorageMethods[Storage Methods]
           AuthMethods[Authentication Methods]
       end

       subgraph "Background Processing"
           DjangoQ[Django-Q Queue]
           Redis[Redis Broker]
           Tasks[Background Tasks]
       end

       subgraph "Data Layer"
           FileSystem[(File System)]
           PostgreSQL[(PostgreSQL Database)]
       end

       Client -->|HTTP/HTTPS| REST
       WSClient -->|WebSocket| WS
       REST --> Auth
       WS --> Auth
       Auth --> Views
       Views --> Serializers
       Serializers --> Models
       Models --> PostgreSQL

       Views --> JobTypes
       Views --> Resources
       Views --> StorageMethods
       Views --> AuthMethods

       Resources -->|depends on| StorageMethods
       Resources -->|depends on| AuthMethods
       Resources --> JobTypes
       Resources --> Models
       StorageMethods -->|depends on| AuthMethods
       StorageMethods --> FileSystem
       StorageMethods --> Models
       AuthMethods --> Models
       JobTypes --> Models

       Views --> DjangoQ
       DjangoQ --> Redis
       Redis --> Tasks
       Tasks --> Models
       Tasks --> Resources
       Tasks --> StorageMethods

       style JobTypes fill:#e1f5ff
       style Resources fill:#e1f5ff
       style StorageMethods fill:#e1f5ff
       style AuthMethods fill:#e1f5ff

Configuration-Driven Plugin System
-----------------------------------

The system uses dynamic configuration to load controllers at runtime:

* **Configuration Files**: ``config.json`` and ``django_config.json`` in the ``src/`` directory
* **Dynamic Loading**: ``utils.generate_controller_object()`` instantiates controllers based on class names
* **Controller Registry**: ``apps.py`` loads and registers all configured components during Django startup

Controllers are composed with dependencies injected during initialization based on the configuration. All controllers receive configuration dictionaries.

Background Tasks
----------------------------

* **Task Registration**: All background tasks defined in ``tasks.py``
* **Job Status Monitoring**: Continuous polling of job states via ``update_job_status()``
* **Workspace Management**: Directory synchronization and quota tracking
* **User Quota Updates**: Real-time disk space and core hours calculation
* **Shared Workspace Creation**: Asynchronous workspace copying and email notifications

Database Design
---------------

Core Models
~~~~~~~~~~~

* **Workspace**: User workspace containers with status tracking and JSON metadata
* **Job**: Execution units linking workspaces to compute resources
* **UserQuota**: Resource limits and usage tracking
* **ExternalUserMapping**: Links Django users to external authentication systems
* **SharedWorkspaceMapping**: Workspace sharing relationships

API Structure
-------------

RESTful Endpoints
~~~~~~~~~~~~~~~~~

More information can be found at the `SmartAPI docs <https://smart-api.info/ui/bf965a56ce398f8b37de68c05b4ef125#>`_.

WebSocket Integration
~~~~~~~~~~~~~~~~~~~~~

* **Real-time Updates**: Job status changes broadcasted via Django Channels
* **Passthrough Support**: WebSocket proxying for interactive sessions
* **Channel Groups**: Per-job status update channels

Security Model
--------------

Custom Authentication
~~~~~~~~~~~~~~~~~~~~~

* **Token System**: ``UserWorkspacesTokenAuthentication`` with custom ``UWS-Authorization`` header
* **Multi-Provider Support**: Pluggable authentication backends
* **External User Mapping**: Links internal Django users with external identity providers

Permission Validation
~~~~~~~~~~~~~~~~~~~~~

* Storage methods validate user ownership of workspaces
* Resource methods enforce user authentication for job execution
* Path traversal protection prevents directory escape attacks

Development Patterns
--------------------

Background Task Development
~~~~~~~~~~~~~~~~~~~~~~~~~~~

* All tasks must be idempotent and handle failures gracefully
* Use ``async_task()`` for queueing with optional hooks for task chaining
* Tasks automatically retry on failure based on Django-Q configuration

WebSocket Development
~~~~~~~~~~~~~~~~~~~~~

* Consumer classes in ``ws_consumers.py`` handle WebSocket connections
* Use channel groups for broadcasting updates to multiple clients
* Passthrough consumers proxy WebSocket connections to running jobs