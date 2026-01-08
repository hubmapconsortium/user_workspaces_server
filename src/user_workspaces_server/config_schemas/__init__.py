"""
Configuration schema definitions and validation for User Workspaces Server.

This module provides a JSON Schema-based system for validating configuration
files (config.json) at startup time.
"""

from user_workspaces_server.config_schemas.json_schema_loader import (
    JSONSchemaLoader,
    JSONSchemaWrapper,
    get_schema_loader,
)
from user_workspaces_server.config_schemas.json_schema_validator import (
    JSONSchemaConfigValidator,
    ValidationError,
)

__all__ = [
    "JSONSchemaWrapper",
    "JSONSchemaLoader",
    "JSONSchemaConfigValidator",
    "get_schema_loader",
    "ValidationError",
]
