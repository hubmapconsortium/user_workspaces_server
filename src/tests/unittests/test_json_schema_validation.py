"""
Tests for JSON Schema-based configuration validation system.

Tests schema loading, validation logic, and error reporting
for config.json using JSON schemas.
"""

import copy

from django.test import TestCase

from user_workspaces_server.config_schemas.json_schema_loader import get_schema_loader
from user_workspaces_server.config_schemas.json_schema_validator import (
    JSONSchemaConfigValidator,
    ValidationError,
)


class JSONSchemaConfigValidatorTests(TestCase):
    """Tests for the JSONSchemaConfigValidator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = JSONSchemaConfigValidator()

        # Valid minimal config for testing
        self.valid_config = {
            "api_user_authentication": "main_auth",
            "main_storage": "main_storage",
            "main_resource": "main_resource",
            "available_user_authentication": {
                "main_auth": {
                    "name": "Local Auth",
                    "user_authentication_type": "LocalUserAuthentication",
                    "connection_details": {"operating_system": "linux"},
                }
            },
            "available_storage": {
                "main_storage": {
                    "name": "Local Storage",
                    "storage_type": "LocalFileSystemStorage",
                    "user_authentication": "main_auth",
                    "root_dir": "/tmp/workspaces",
                }
            },
            "available_resources": {
                "main_resource": {
                    "name": "Local Resource",
                    "resource_type": "LocalResource",
                    "storage": "main_storage",
                    "user_authentication": "main_auth",
                    "passthrough_domain": "127.0.0.1:8000",
                    "connection_details": {},
                }
            },
            "available_job_types": {
                "test_job": {
                    "name": "Test Job",
                    "job_type": "LocalTestJob",
                    "environment_details": {},
                }
            },
            "parameters": [],
        }

    def test_valid_config_passes(self):
        """Test that a valid configuration passes validation."""
        result = self.validator.validate_uws_config(self.valid_config)
        self.assertTrue(result)

    def test_missing_top_level_field_fails(self):
        """Test that missing required top-level fields cause validation to fail."""
        config = copy.deepcopy(self.valid_config)
        del config["api_user_authentication"]

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn(
            "Missing required top-level field: api_user_authentication",
            context.exception.errors,
        )

    def test_invalid_reference_fails(self):
        """Test that invalid references between config sections fail validation."""
        config = copy.deepcopy(self.valid_config)
        config["api_user_authentication"] = "nonexistent_auth"

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn("not found in available_user_authentication", str(context.exception.errors))

    def test_missing_controller_type_fails(self):
        """Test that missing controller type field fails validation."""
        config = copy.deepcopy(self.valid_config)
        del config["available_resources"]["main_resource"]["resource_type"]

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn("Missing 'resource_type'", str(context.exception.errors))

    def test_unknown_controller_type_fails(self):
        """Test that unknown controller types fail validation."""
        config = copy.deepcopy(self.valid_config)
        config["available_resources"]["main_resource"]["resource_type"] = "UnknownResource"

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn("Unknown resource_type", str(context.exception.errors))

    def test_missing_required_field_fails(self):
        """Test that missing required fields in controller config fail validation."""
        config = copy.deepcopy(self.valid_config)
        del config["available_storage"]["main_storage"]["root_dir"]

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn("Missing required field 'root_dir'", str(context.exception.errors))

    def test_invalid_storage_reference_fails(self):
        """Test that invalid storage reference in resource config fails."""
        config = copy.deepcopy(self.valid_config)
        config["available_resources"]["main_resource"]["storage"] = "nonexistent_storage"

        with self.assertRaises(ValidationError) as context:
            self.validator.validate_uws_config(config)

        self.assertIn("not found in available_storage", str(context.exception.errors))


class JSONSchemaLoaderTests(TestCase):
    """Tests for the JSON schema loader."""

    def setUp(self):
        """Set up test fixtures."""
        self.schema_loader = get_schema_loader()

    def test_resource_schemas_loaded(self):
        """Test that resource schemas are properly loaded."""
        schema = self.schema_loader.get_resource_schema("LocalResource")
        self.assertIsNotNone(schema)
        self.assertEqual(schema.controller_name, "LocalResource")
        self.assertEqual(schema.category, "resource")

    def test_storage_schemas_loaded(self):
        """Test that storage schemas are properly loaded."""
        schema = self.schema_loader.get_storage_schema("LocalFileSystemStorage")
        self.assertIsNotNone(schema)
        self.assertEqual(schema.controller_name, "LocalFileSystemStorage")
        self.assertEqual(schema.category, "storage")

    def test_authentication_schemas_loaded(self):
        """Test that authentication schemas are properly loaded."""
        schema = self.schema_loader.get_authentication_schema("GlobusUserAuthentication")
        self.assertIsNotNone(schema)
        self.assertEqual(schema.controller_name, "GlobusUserAuthentication")
        self.assertEqual(schema.category, "authentication")

    def test_job_type_schemas_loaded(self):
        """Test that job type schemas are properly loaded."""
        schema = self.schema_loader.get_job_type_schema("JupyterLabJob")
        self.assertIsNotNone(schema)
        self.assertEqual(schema.controller_name, "JupyterLabJob")
        self.assertEqual(schema.category, "job_type")

    def test_get_all_schemas(self):
        """Test that get_all_schemas returns all loaded schemas."""
        all_schemas = self.schema_loader.get_all_schemas()

        self.assertIn("resources", all_schemas)
        self.assertIn("storage", all_schemas)
        self.assertIn("authentication", all_schemas)
        self.assertIn("job_types", all_schemas)

        # Check that we have some schemas in each category
        self.assertGreater(len(all_schemas["resources"]), 0)
        self.assertGreater(len(all_schemas["storage"]), 0)
        self.assertGreater(len(all_schemas["authentication"]), 0)
        self.assertGreater(len(all_schemas["job_types"]), 0)

    def test_schema_has_required_fields(self):
        """Test that schemas correctly identify required fields."""
        schema = self.schema_loader.get_storage_schema("LocalFileSystemStorage")
        required_fields = schema.get_required_fields()

        self.assertIn("name", required_fields)
        self.assertIn("storage_type", required_fields)
        self.assertIn("user_authentication", required_fields)
        self.assertIn("root_dir", required_fields)

    def test_schema_has_optional_fields(self):
        """Test that schemas correctly identify optional fields."""
        schema = self.schema_loader.get_resource_schema("LocalResource")
        optional_fields = schema.get_optional_fields()

        self.assertIn("passthrough_domain", optional_fields)
        self.assertIn("parameter_mapping", optional_fields)
        self.assertIn("connection_details", optional_fields)


class SpecificControllerTests(TestCase):
    """Tests for specific controller schemas."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = JSONSchemaConfigValidator()
        self.schema_loader = get_schema_loader()

    def test_slurm_resource_requires_connection_details(self):
        """Test that SlurmAPIResource validates connection_details."""
        schema = self.schema_loader.get_resource_schema("SlurmAPIResource")
        self.assertIsNotNone(schema)

        config = {
            "name": "SLURM Resource",
            "resource_type": "SlurmAPIResource",
            "storage": "main_storage",
            "user_authentication": "main_auth",
            # Missing connection_details
        }

        result = self.validator.validate_controller_config(config, schema, "slurm_resource")
        self.assertFalse(result)
        self.assertTrue(any("connection_details" in error for error in self.validator.errors))

    def test_globus_auth_validates_authentication_type_choices(self):
        """Test that GlobusUserAuthentication validates authentication_type choices."""
        schema = self.schema_loader.get_authentication_schema("GlobusUserAuthentication")
        self.assertIsNotNone(schema)

        # Check that authentication_type field has enum
        connection_details = schema.get_field("connection_details")
        self.assertIsNotNone(connection_details)
        auth_type_field = connection_details.get("properties", {}).get("authentication_type")
        self.assertIsNotNone(auth_type_field)
        self.assertIn("enum", auth_type_field)
        self.assertIn("oauth", auth_type_field["enum"])
        self.assertIn("token", auth_type_field["enum"])

    def test_jupyter_lab_job_requires_environment_details(self):
        """Test that JupyterLabJob requires environment_details."""
        schema = self.schema_loader.get_job_type_schema("JupyterLabJob")
        self.assertIsNotNone(schema)

        required_fields = schema.get_required_fields()
        self.assertIn("environment_details", required_fields)
