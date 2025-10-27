Testing
=======

The User Workspaces Server includes comprehensive unit and integration tests to ensure code quality and functionality.

Test Structure
--------------

The test suite is organized into two main categories:

* **Unit Tests**: ``tests/unittests/`` - Isolated component testing
* **Integration Tests**: ``tests/integrationtests/`` - End-to-end workflow testing
* **Controller Tests**: Dedicated test modules for each controller type

Test Configuration
------------------

Tests use separate configuration files:

* ``tests/test_django_config.json`` - Local test configuration
* ``tests/github_test_django_config.json`` - GitHub Actions configuration

Running Tests
-------------

Local Testing
~~~~~~~~~~~~~

From the ``src/`` directory, run the Django test suite:

.. code-block:: bash

   # Run all tests
   cd src && python manage.py test

   # Run specific test modules
   python manage.py test tests.unittests
   python manage.py test tests.integrationtests

   # Run specific test classes
   python manage.py test tests.unittests.test_models.WorkspaceModelTest

   # Run with verbose output
   python manage.py test --verbosity=2

GitHub Actions
~~~~~~~~~~~~~~

Tests are automatically run on GitHub Actions for:

* Pull requests
* Pushes to main branch
* Scheduled nightly builds

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

**Controller Tests**
   * Authentication method testing (``tests/controllers/userauthenticationmethods/``)
   * Storage method testing (``tests/controllers/storagemethods/``)
   * Resource testing (``tests/controllers/resources/``)

Integration Tests
~~~~~~~~~~~~~~~~~

End-to-end workflow testing that covers:

* Complete workspace lifecycle
* Job execution workflows
* User authentication flows
* Shared workspace functionality

Test Data and Fixtures
-----------------------

Test fixtures are used to provide consistent test data:

.. code-block:: python

   from django.test import TestCase
   from user_workspaces_server.models import Workspace

   class WorkspaceTestCase(TestCase):
       def setUp(self):
           self.workspace = Workspace.objects.create(
               name="test-workspace",
               user_id="testuser"
           )

Mocking External Services
-------------------------

Tests use mocking to isolate components and avoid external dependencies:

.. code-block:: python

   from unittest.mock import patch, Mock

   class AuthenticationTest(TestCase):
       @patch('globus_sdk.AuthClient')
       def test_globus_authentication(self, mock_auth_client):
           mock_auth_client.return_value.oauth2_userinfo.return_value = {
               'sub': 'user123',
               'preferred_username': 'testuser'
           }
           # Test authentication logic

Coverage Reporting
------------------

Code coverage is tracked using the ``coverage`` package:

.. code-block:: bash

   # Run tests with coverage
   coverage run --source='.' manage.py test

   # Generate coverage report
   coverage report

   # Generate HTML coverage report
   coverage html

Test Best Practices
-------------------

Writing Tests
~~~~~~~~~~~~~

1. **Test Isolation**: Each test should be independent and not rely on other tests
2. **Clear Naming**: Test method names should clearly describe what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and validation phases
4. **Mock External Dependencies**: Use mocking for external services and APIs

Example Test Structure
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from django.test import TestCase
   from unittest.mock import patch

   class WorkspaceViewTest(TestCase):
       def setUp(self):
           """Arrange - Set up test data"""
           self.user = User.objects.create_user('testuser')
           self.workspace_data = {
               'name': 'test-workspace',
               'description': 'Test workspace'
           }

       def test_create_workspace_success(self):
           """Test successful workspace creation"""
           # Act - Perform the action
           response = self.client.post('/workspaces/', self.workspace_data)

           # Assert - Verify the result
           self.assertEqual(response.status_code, 201)
           self.assertTrue(Workspace.objects.filter(name='test-workspace').exists())

       @patch('user_workspaces_server.tasks.initialize_workspace')
       def test_workspace_initialization_called(self, mock_init):
           """Test that workspace initialization task is called"""
           response = self.client.post('/workspaces/', self.workspace_data)
           mock_init.assert_called_once()

Continuous Integration
----------------------

The project uses GitHub Actions for continuous integration:

.. code-block:: yaml

   name: Tests
   on: [push, pull_request]
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v2
         - name: Set up Python
           uses: actions/setup-python@v2
           with:
             python-version: 3.10
         - name: Install dependencies
           run: |
             pip install -r requirements/test_requirements.txt
         - name: Run tests
           run: |
             cd src && python manage.py test

Debugging Tests
---------------

For debugging failing tests:

.. code-block:: bash

   # Run tests with Python debugger
   python manage.py test --debug-mode

   # Run single test with verbose output
   python manage.py test tests.unittests.test_models.WorkspaceModelTest.test_workspace_creation --verbosity=2

   # Use Django's debug toolbar in test mode
   DJANGO_SETTINGS_MODULE=tests.settings python manage.py test