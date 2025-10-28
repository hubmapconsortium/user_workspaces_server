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

       subgraph "Controller Layer - Plugin System"
           subgraph "Job Types"
               JobAbstract[AbstractJob]
               JupyterJob[JupyterLabJob]
               TestJob[LocalTestJob]
               AppyterJob[AppyterJob]
           end

           subgraph "Resources"
               ResourceAbstract[AbstractResource]
               LocalRes[LocalResource]
               SlurmRes[SlurmAPIResource]
           end

           subgraph "Storage Methods"
               StorageAbstract[AbstractStorage]
               LocalStorage[LocalFileSystemStorage]
               HubmapStorage[HubmapLocalFileSystemStorage]
           end

           subgraph "Authentication Methods"
               AuthAbstract[AbstractUserAuthentication]
               GlobusAuth[GlobusUserAuthentication]
               PSCAuth[PSCAPIUserAuthentication]
               LocalAuth[LocalUserAuthentication]
           end
       end

       subgraph "Background Processing"
           DjangoQ[Django-Q Queue]
           Redis[Redis Broker]
           Tasks[Background Tasks]
       end

       subgraph "Data Layer"
           PostgreSQL[(PostgreSQL Database)]
           FileSystem[(File System)]
       end

       Client -->|HTTP/HTTPS| REST
       WSClient -->|WebSocket| WS
       REST --> Auth
       WS --> Auth
       Auth --> Views
       Views --> Serializers
       Serializers --> Models
       Models --> PostgreSQL

       Views --> JobAbstract
       JobAbstract -.->|implements| JupyterJob
       JobAbstract -.->|implements| TestJob
       JobAbstract -.->|implements| AppyterJob

       Views --> ResourceAbstract
       ResourceAbstract -.->|implements| LocalRes
       ResourceAbstract -.->|implements| SlurmRes
       ResourceAbstract -->|depends on| StorageAbstract
       ResourceAbstract -->|depends on| AuthAbstract

       Views --> StorageAbstract
       StorageAbstract -.->|implements| LocalStorage
       StorageAbstract -.->|implements| HubmapStorage
       StorageAbstract -->|depends on| AuthAbstract
       StorageAbstract --> FileSystem

       Views --> AuthAbstract
       AuthAbstract -.->|implements| GlobusAuth
       AuthAbstract -.->|implements| PSCAuth
       AuthAbstract -.->|implements| LocalAuth

       Views --> DjangoQ
       DjangoQ --> Redis
       Redis --> Tasks
       Tasks --> Models
       Tasks --> ResourceAbstract
       Tasks --> StorageAbstract

       style JobAbstract fill:#e1f5ff
       style ResourceAbstract fill:#e1f5ff
       style StorageAbstract fill:#e1f5ff
       style AuthAbstract fill:#e1f5ff

Configuration-Driven Plugin System
-----------------------------------

The system uses dynamic configuration to load controllers at runtime:

* **Configuration Files**: ``config.json`` and ``django_config.json`` in the ``src/`` directory
* **Dynamic Loading**: ``utils.generate_controller_object()`` instantiates controllers based on class names
* **Controller Registry**: ``apps.py`` loads and registers all configured components during Django startup

Abstract Controller Pattern
----------------------------

All major components follow an abstract base class pattern for extensibility:

Authentication Methods
~~~~~~~~~~~~~~~~~~~~~~

Located in ``controllers/userauthenticationmethods/``:

* **Abstract**: ``AbstractUserAuthentication``
* **Implementations**:

  * ``GlobusUserAuthentication`` - Globus OAuth integration
  * ``PSCAPIUserAuthentication`` - Pittsburgh Supercomputing Center API
  * ``LocalUserAuthentication`` - Local user management

Storage Methods
~~~~~~~~~~~~~~~

Located in ``controllers/storagemethods/``:

* **Abstract**: ``AbstractStorage``
* **Implementations**:

  * ``LocalFileSystemStorage`` - Standard filesystem storage
  * ``HubmapLocalFileSystemStorage`` - HuBMAP-specific storage with custom features

Resources
~~~~~~~~~

Located in ``controllers/resources/``:

* **Abstract**: ``AbstractResource``
* **Implementations**:

  * ``LocalResource`` - Local process execution
  * ``SlurmAPIResource`` - SLURM cluster integration

Job Types
~~~~~~~~~

Located in ``controllers/jobtypes/``:

* **Abstract**: ``AbstractJob``
* **Implementations**:

  * ``JupyterLabJob`` - JupyterLab notebook environment
  * ``LocalTestJob`` - Testing and development jobs
  * ``AppyterJob`` - Appyter application support

Dependency Injection Chain
---------------------------

Controllers are composed with dependencies injected during initialization:

.. code-block:: text

    Resources → depend on → Storage + UserAuthentication
    Storage → depends on → UserAuthentication
    All controllers receive configuration dictionaries

Background Task Architecture
----------------------------

Django-Q Integration
~~~~~~~~~~~~~~~~~~~~

* **Queue Management**: Uses Redis as message broker
* **Task Registration**: All background tasks defined in ``tasks.py``
* **Automatic Recovery**: On qcluster startup, automatically queues monitoring for active jobs
* **Hook System**: Tasks can specify completion hooks for chaining operations

Key Background Operations
~~~~~~~~~~~~~~~~~~~~~~~~~

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

Status Management
~~~~~~~~~~~~~~~~~

Both Workspaces and Jobs use TextChoices enums for status tracking:

* **Workspace States**: ``initializing``, ``idle``, ``active``, ``deleting``, ``error``
* **Job States**: ``pending``, ``running``, ``complete``, ``failed``, ``stopping``

API Structure
-------------

RESTful Endpoints
~~~~~~~~~~~~~~~~~

* ``/tokens/`` - Authentication token management
* ``/workspaces/`` - Workspace CRUD operations
* ``/jobs/`` - Job lifecycle management
* ``/users/`` - User information and quotas
* ``/shared_workspaces/`` - Collaborative workspace features
* ``/status/`` - System health checks

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

Adding New Controllers
~~~~~~~~~~~~~~~~~~~~~~

1. Implement the appropriate abstract base class
2. Add class name mapping in ``utils.translate_class_to_module()``
3. Update configuration JSON files to register the new controller
4. The system will automatically discover and load the controller at startup

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