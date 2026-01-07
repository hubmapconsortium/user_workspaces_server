"""
Configuration validation using JSON Schema.

This module provides validation logic for configuration files using
JSON Schema definitions.
"""

from typing import Any, Dict, List

import jsonschema
from jsonschema import Draft7Validator

from user_workspaces_server.config_schemas.json_schema_loader import get_schema_loader


class ValidationError(Exception):
    """Exception raised when configuration validation fails."""

    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)


class JSONSchemaConfigValidator:
    """Validates configuration dictionaries against JSON schemas."""

    def __init__(self):
        """Initialize the validator."""
        self.errors: List[str] = []
        self.schema_loader = get_schema_loader()

    def _format_validation_error(
        self, error: jsonschema.ValidationError, path: str = ""
    ) -> str:
        """
        Format a jsonschema validation error into a human-readable message.

        Args:
            error: The validation error from jsonschema
            path: The current path in the config (for nested validation)

        Returns:
            Formatted error message
        """
        field_path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
        full_path = f"{path}.{field_path}" if path and field_path else path or field_path

        # Handle different error types
        if error.validator == "required":
            missing_field = error.message.split("'")[1]
            return f"{full_path}: Missing required field '{missing_field}'"
        elif error.validator == "type":
            return f"{full_path}: {error.message}"
        elif error.validator == "enum":
            return f"{full_path}: {error.message}"
        elif error.validator == "minLength":
            return f"{full_path}: {error.message}"
        elif error.validator == "maxLength":
            return f"{full_path}: {error.message}"
        else:
            return f"{full_path}: {error.message}" if full_path else error.message

    def validate_with_schema(
        self,
        config: Dict[str, Any],
        schema_dict: Dict[str, Any],
        path: str = "",
    ) -> bool:
        """
        Validate a configuration dictionary against a JSON schema.

        Args:
            config: The configuration dictionary to validate
            schema_dict: The JSON Schema to validate against
            path: The current path in the config (for error messages)

        Returns:
            True if validation passes, False otherwise
        """
        validator = Draft7Validator(schema_dict)
        valid = True

        for error in validator.iter_errors(config):
            self.errors.append(self._format_validation_error(error, path))
            valid = False

        return valid

    def validate_controller_config(
        self, config: Dict[str, Any], schema_wrapper, config_key: str = ""
    ) -> bool:
        """
        Validate a controller configuration against its schema.

        Args:
            config: The configuration dictionary to validate
            schema_wrapper: The JSONSchemaWrapper to validate against
            config_key: The key in the config file (for error messages)

        Returns:
            True if validation passes, False otherwise
        """
        path = config_key if config_key else schema_wrapper.controller_name
        return self.validate_with_schema(config, schema_wrapper.schema, path)

    def validate_uws_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate the complete UWS config.json file.

        Args:
            config: The loaded config.json dictionary

        Returns:
            True if validation passes, False otherwise

        Raises:
            ValidationError: If validation fails
        """
        self.errors = []
        valid = True

        # Validate top-level required fields
        required_top_level = [
            "api_user_authentication",
            "main_storage",
            "main_resource",
            "available_user_authentication",
            "available_storage",
            "available_resources",
            "available_job_types",
            "parameters",
        ]

        for field in required_top_level:
            if field not in config:
                self.errors.append(f"Missing required top-level field: {field}")
                valid = False

        if not valid:
            raise ValidationError(self.errors)

        # Validate main references
        if config.get("api_user_authentication") not in config.get(
            "available_user_authentication", {}
        ):
            self.errors.append(
                f"api_user_authentication '{config.get('api_user_authentication')}' "
                f"not found in available_user_authentication"
            )
            valid = False

        if config.get("main_storage") not in config.get("available_storage", {}):
            self.errors.append(
                f"main_storage '{config.get('main_storage')}' not found in available_storage"
            )
            valid = False

        if config.get("main_resource") not in config.get("available_resources", {}):
            self.errors.append(
                f"main_resource '{config.get('main_resource')}' not found in available_resources"
            )
            valid = False

        # Validate authentication methods
        for auth_key, auth_config in config.get("available_user_authentication", {}).items():
            auth_type = auth_config.get("user_authentication_type")
            if not auth_type:
                self.errors.append(
                    f"available_user_authentication.{auth_key}: Missing 'user_authentication_type'"
                )
                valid = False
                continue

            schema = self.schema_loader.get_authentication_schema(auth_type)
            if schema:
                valid = (
                    self.validate_controller_config(
                        auth_config, schema, f"available_user_authentication.{auth_key}"
                    )
                    and valid
                )
            else:
                self.errors.append(
                    f"available_user_authentication.{auth_key}: "
                    f"Unknown user_authentication_type '{auth_type}'"
                )
                valid = False

        # Validate storage methods
        for storage_key, storage_config in config.get("available_storage", {}).items():
            storage_type = storage_config.get("storage_type")
            if not storage_type:
                self.errors.append(f"available_storage.{storage_key}: Missing 'storage_type'")
                valid = False
                continue

            # Validate user_authentication reference
            user_auth = storage_config.get("user_authentication")
            if user_auth and user_auth not in config.get("available_user_authentication", {}):
                self.errors.append(
                    f"available_storage.{storage_key}: "
                    f"user_authentication '{user_auth}' not found in available_user_authentication"
                )
                valid = False

            schema = self.schema_loader.get_storage_schema(storage_type)
            if schema:
                valid = (
                    self.validate_controller_config(
                        storage_config, schema, f"available_storage.{storage_key}"
                    )
                    and valid
                )
            else:
                self.errors.append(
                    f"available_storage.{storage_key}: Unknown storage_type '{storage_type}'"
                )
                valid = False

        # Validate resources
        for resource_key, resource_config in config.get("available_resources", {}).items():
            resource_type = resource_config.get("resource_type")
            if not resource_type:
                self.errors.append(f"available_resources.{resource_key}: Missing 'resource_type'")
                valid = False
                continue

            # Validate storage reference
            storage = resource_config.get("storage")
            if storage and storage not in config.get("available_storage", {}):
                self.errors.append(
                    f"available_resources.{resource_key}: "
                    f"storage '{storage}' not found in available_storage"
                )
                valid = False

            # Validate user_authentication reference
            user_auth = resource_config.get("user_authentication")
            if user_auth and user_auth not in config.get("available_user_authentication", {}):
                self.errors.append(
                    f"available_resources.{resource_key}: "
                    f"user_authentication '{user_auth}' not found in available_user_authentication"
                )
                valid = False

            schema = self.schema_loader.get_resource_schema(resource_type)
            if schema:
                valid = (
                    self.validate_controller_config(
                        resource_config, schema, f"available_resources.{resource_key}"
                    )
                    and valid
                )
            else:
                self.errors.append(
                    f"available_resources.{resource_key}: Unknown resource_type '{resource_type}'"
                )
                valid = False

        # Validate job types
        for job_key, job_config in config.get("available_job_types", {}).items():
            job_type = job_config.get("job_type")
            if not job_type:
                self.errors.append(f"available_job_types.{job_key}: Missing 'job_type'")
                valid = False
                continue

            schema = self.schema_loader.get_job_type_schema(job_type)
            if schema:
                valid = (
                    self.validate_controller_config(
                        job_config, schema, f"available_job_types.{job_key}"
                    )
                    and valid
                )
            else:
                self.errors.append(f"available_job_types.{job_key}: Unknown job_type '{job_type}'")
                valid = False

        if not valid:
            raise ValidationError(self.errors)

        return valid
