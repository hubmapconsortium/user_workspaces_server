Controllers
============

Controller Layer Details
------------------------

The Controller Layer implements a plugin-based architecture where each controller type has an abstract base class with concrete implementations. This diagram shows the extensibility pattern:

.. mermaid::

   graph TB
       subgraph "Job Types"
           JobAbstract[AbstractJob]
           LocalTestJob
           JobOther[Other Job Types...]

           JobAbstract -.->|implements| LocalTestJob
           JobAbstract -.->|can implement| JobOther
       end

       subgraph "Resources"
           ResourceAbstract[AbstractResource]
           LocalResource
           ResourceOther[Other Resources...]

           ResourceAbstract -.->|implements| LocalResource
           ResourceAbstract -.->|can implement| ResourceOther
       end

       subgraph "Storage Methods"
           StorageAbstract[AbstractStorage]
           LocalFileSystemStorage
           StorageOther[Other Storage Methods...]

           StorageAbstract -.->|implements| LocalFileSystemStorage
           StorageAbstract -.->|can implement| StorageOther
       end

       subgraph "Authentication Methods"
           AuthAbstract[AbstractUserAuthentication]
           LocalUserAuthentication
           AuthOther[Other Auth Methods...]

           AuthAbstract -.->|implements| LocalUserAuthentication
           AuthAbstract -.->|can implement| AuthOther
       end

       ResourceAbstract -->|depends on| StorageAbstract
       ResourceAbstract -->|depends on| AuthAbstract
       StorageAbstract -->|depends on| AuthAbstract

       style JobAbstract fill:#e1f5ff
       style ResourceAbstract fill:#e1f5ff
       style StorageAbstract fill:#e1f5ff
       style AuthAbstract fill:#e1f5ff
       style JobOther fill:#ffe1e1,stroke-dasharray: 5 5
       style ResourceOther fill:#ffe1e1,stroke-dasharray: 5 5
       style StorageOther fill:#ffe1e1,stroke-dasharray: 5 5
       style AuthOther fill:#ffe1e1,stroke-dasharray: 5 5

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

Adding New Controllers
----------------------

1. Implement the appropriate abstract base class
2. Add class name mapping in ``utils.translate_class_to_module()``
3. Add new JSON schema in ``schemas`` directory
4. Update configuration JSON files to register the new controller
5. The system will automatically discover and load the controller at startup