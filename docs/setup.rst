Development Setup
=================

This guide walks you through setting up a development environment for the User Workspaces Server.

Prerequisites
-------------

* Docker

Docker Development
------------------

For a containerized development environment:

.. code-block:: bash

   # Build and start Docker Compose cluster
   cd docker
   docker compose build
   docker compose up -d

Configuration Files
-------------------

The server requires two configuration files in the ``src/`` directory. Example templates are provided that you can copy and customize.

config.json
~~~~~~~~~~~

Contains UWS-specific configuration including controller types, authentication, storage, resources, and job types.

To get started, copy the example configuration:

.. code-block:: bash

   cp src/example_config.json src/config.json

The configuration file defines:

* **Authentication Methods**: User authentication backends (e.g., Globus, local)
* **Storage Methods**: File system storage backends
* **Resources**: Compute resource providers (e.g., local execution, SLURM)
* **Job Types**: Available job types (e.g., JupyterLab, test jobs)
* **Parameters**: User-configurable job parameters (CPUs, memory, time limits)

See ``src/example_config.json`` for the complete structure and available options.

django_config.json
~~~~~~~~~~~~~~~~~~

Contains Django application settings including database configuration, Redis settings, email configuration, and logging.

To get started, copy the example configuration:

.. code-block:: bash

   cp src/example_django_config.json src/django_config.json

The configuration file defines:

* **SECRET_KEY**: Django secret key for cryptographic signing
* **DATABASES**: Database connection settings
* **Q_CLUSTER**: Django-Q task queue configuration with Redis
* **CHANNEL_LAYERS**: Django Channels WebSocket configuration
* **EMAIL_HOST**: Email server settings for notifications
* **LOGGING**: Application logging configuration

See ``src/example_django_config.json`` for the complete structure and available options.

Development Tools
-----------------

Code Formatting and Linting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Format code
   black --line-length 99 src
   isort --profile black src

   # Check code quality
   flake8 --ignore=E501,W503 src

Common Issues
---------------

**Permission Errors**
   The application requires root privileges for user management. Ensure you're running with ``sudo`` in development.