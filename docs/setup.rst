Development Setup
=================

This guide walks you through setting up a development environment for the User Workspaces Server.

Prerequisites
-------------

* Python 3.10 or higher
* PostgreSQL or SQLite (for development)
* Redis server
* Git

Local Development Setup
-----------------------

1. **Clone the Repository**

   .. code-block:: bash

      git clone <repository-url>
      cd user_workspaces_server

2. **Create Virtual Environment**

   .. code-block:: bash

      # Create virtual environment (Python 3.10+)
      virtualenv -p 3.10 venv
      source venv/bin/activate

3. **Install Dependencies**

   .. code-block:: bash

      # Install dependencies
      pip install --upgrade pip
      pip install -r requirements/requirements.txt
      pip install -r requirements/test_requirements.txt

4. **Configure the Application**

   Copy the example configuration files and customize them:

   .. code-block:: bash

      cd src
      cp example_config.json config.json
      cp example_django_config.json django_config.json

   Edit the configuration files to match your environment:

   * ``config.json`` - UWS-specific settings (controllers, resources, authentication)
   * ``django_config.json`` - Django settings (database, Redis, logging, email)

5. **Database Setup**

   .. code-block:: bash

      # Run database migrations
      cd src && python manage.py migrate

6. **Run the Development Server**

   The application requires root privileges for user and job management:

   .. code-block:: bash

      # Start the background task queue
      sudo python manage.py qcluster &

      # Start the development server
      sudo python manage.py runserver

Docker Development
------------------

For a containerized development environment:

.. code-block:: bash

   # Build and start Docker Compose cluster
   docker compose build
   docker compose up -d

Configuration Files
-------------------

config.json
~~~~~~~~~~~

Contains UWS-specific configuration:

.. code-block:: json

   {
     "storage_method": "LocalFileSystemStorage",
     "user_authentication_method": "LocalUserAuthentication",
     "resource": "LocalResource",
     "job_types": ["JupyterLabJob", "LocalTestJob"],
     "shared_workspace_enabled": true
   }

django_config.json
~~~~~~~~~~~~~~~~~~

Contains Django application settings:

.. code-block:: json

   {
     "debug": true,
     "database": {
       "ENGINE": "django.db.backends.sqlite3",
       "NAME": "db.sqlite3"
     },
     "redis": {
       "host": "localhost",
       "port": 6379
     }
   }

Environment Variables
--------------------

The following environment variables can be used to override configuration:

* ``DJANGO_SETTINGS_MODULE`` - Django settings module (default: ``user_workspaces_server_project.settings``)
* ``UWS_CONFIG_PATH`` - Path to config.json file
* ``UWS_DJANGO_CONFIG_PATH`` - Path to django_config.json file

Development Tools
-----------------

Code Formatting and Linting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Format code
   black .
   isort .

   # Check code quality
   flake8

IDE Setup
~~~~~~~~~

For VS Code or PyCharm, ensure your Python interpreter points to the virtual environment and configure the project root correctly for module imports.

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Permission Errors**
   The application requires root privileges for user management. Ensure you're running with ``sudo`` in development.

**Module Import Errors**
   Ensure the ``src/`` directory is in your Python path and that Django is properly configured.

**Database Connection Errors**
   Check that your database settings in ``django_config.json`` are correct and that the database server is running.

**Redis Connection Errors**
   Verify that Redis is running and accessible at the configured host and port.