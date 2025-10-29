Testing
=======

The User Workspaces Server includes comprehensive unit and integration tests to ensure code quality and functionality.

Test Structure
--------------

The test suite is organized into two main categories:

* **Unit Tests**: ``tests/unittests/`` - Isolated component testing
* **Integration Tests**: ``tests/integrationtests/`` - End-to-end workflow testing (**to be implemented**)
* **Controller Tests**: Dedicated test modules for each controller type

Test Configuration
------------------

Tests use separate configuration files:

* ``tests/test_config.json`` & ``tests/test_django_config.json`` - Local test configuration
* ``tests/github_test_config.json`` & ``tests/github_test_django_config.json`` - GitHub Actions configuration

Running Tests
-------------

Local Testing
~~~~~~~~~~~~~

From the ``src/`` directory, run the Django test suite:

.. code-block:: bash
   # Initialize a test environment
   virtualenv test_venv --python=3.10
   source test_venv/bin/activate
   pip install -r requirements/test_requirements.txt

   # Run all tests
   cd src && python manage.py test --settings=tests.settings

   # Run specific test modules
   python manage.py test tests.unittests --settings=tests.settings

   # Run specific test classes
   python manage.py test tests.unittests.test_models.WorkspaceModelTests --settings=tests.settings

   # Run with verbose output
   python manage.py test --verbosity=2

Test Types
----------

Unit Tests
~~~~~~~~~~

**Model Tests** (``tests/unittests/test_models.py``)
   * Database model validation
   * Model method functionality
   * Constraint testing

**View Tests** (``tests/unittests/test_views.py``)
   * API endpoint testing
   * Authentication testing
   * Input validation

Coverage Reporting
------------------

Code coverage is tracked using the ``coverage`` package:

.. code-block:: bash

   # Run tests with coverage
   coverage run manage.py test tests.unittests --settings=tests.settings

   # Generate coverage report
   coverage report -m

   # Generate HTML coverage report
   coverage html
