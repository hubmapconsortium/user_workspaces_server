"""
JSON Schema loader for configuration validation.

This module loads JSON Schema files for validation and documentation generation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class JSONSchemaWrapper:
    """Wrapper around a JSON Schema providing convenient access methods."""

    def __init__(self, schema: Dict[str, Any], file_path: str):
        """
        Initialize a JSONSchemaWrapper.

        Args:
            schema: The parsed JSON Schema dictionary
            file_path: Path to the schema file
        """
        self.schema = schema
        self.file_path = file_path
        self.controller_name = schema.get("$id", schema.get("title", ""))
        self.category = schema.get("x-category", "")
        self.description = schema.get("description", "")
        self.properties = schema.get("properties", {})
        self.required_fields = schema.get("required", [])
        self.examples = schema.get("examples", [])

    @property
    def fields(self) -> Dict[str, Dict[str, Any]]:
        """Get all fields (properties) from the schema."""
        return self.properties

    def get_required_fields(self) -> List[str]:
        """Get list of required field names."""
        return self.required_fields.copy()

    def get_optional_fields(self) -> List[str]:
        """Get list of optional field names."""
        return [
            name for name in self.properties.keys() if name not in self.required_fields
        ]

    def get_field(self, field_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific field definition.

        Args:
            field_name: Name of the field

        Returns:
            Field definition dict or None if not found
        """
        return self.properties.get(field_name)

    @property
    def example(self) -> Dict[str, Any]:
        """Get the first example (for backwards compatibility with YAML schemas)."""
        return self.examples[0] if self.examples else {}


class JSONSchemaLoader:
    """Loads and manages JSON Schema files."""

    def __init__(self, schemas_dir: str = None):
        """
        Initialize the JSON Schema loader.

        Args:
            schemas_dir: Path to directory containing JSON schemas.
                        Defaults to schemas/ subdirectory of this module.
        """
        if schemas_dir is None:
            module_dir = Path(__file__).parent
            schemas_dir = module_dir / "schemas"

        self.schemas_dir = Path(schemas_dir)
        self._schemas = {
            "resources": {},
            "storage": {},
            "authentication": {},
            "job_types": {},
        }
        self._load_all_schemas()

    def _load_json_file(self, file_path: Path) -> JSONSchemaWrapper:
        """Load a single JSON Schema file."""
        with open(file_path, "r") as f:
            schema_data = json.load(f)

        return JSONSchemaWrapper(schema_data, str(file_path))

    def _load_all_schemas(self):
        """Load all JSON Schema files from the schemas directory."""
        for category in ["resources", "storage", "authentication", "job_types"]:
            category_dir = self.schemas_dir / category
            if not category_dir.exists():
                continue

            for json_file in category_dir.glob("*.json"):
                try:
                    schema = self._load_json_file(json_file)
                    self._schemas[category][schema.controller_name] = schema
                except Exception as e:
                    print(f"Warning: Failed to load schema {json_file}: {e}")

    def get_schema(self, category: str, controller_name: str) -> Optional[JSONSchemaWrapper]:
        """
        Get a schema by category and controller name.

        Args:
            category: Schema category (resources, storage, authentication, job_types)
            controller_name: Name of the controller

        Returns:
            JSONSchemaWrapper object or None if not found
        """
        return self._schemas.get(category, {}).get(controller_name)

    def get_all_schemas(self) -> Dict[str, Dict[str, JSONSchemaWrapper]]:
        """Get all loaded schemas organized by category."""
        return self._schemas.copy()

    def get_resource_schema(self, controller_name: str) -> Optional[JSONSchemaWrapper]:
        """Get a resource schema by controller name."""
        return self.get_schema("resources", controller_name)

    def get_storage_schema(self, controller_name: str) -> Optional[JSONSchemaWrapper]:
        """Get a storage schema by controller name."""
        return self.get_schema("storage", controller_name)

    def get_authentication_schema(self, controller_name: str) -> Optional[JSONSchemaWrapper]:
        """Get an authentication schema by controller name."""
        return self.get_schema("authentication", controller_name)

    def get_job_type_schema(self, controller_name: str) -> Optional[JSONSchemaWrapper]:
        """Get a job type schema by controller name."""
        return self.get_schema("job_types", controller_name)


# Global schema loader instance
_schema_loader = None


def get_schema_loader() -> JSONSchemaLoader:
    """Get the global schema loader instance."""
    global _schema_loader
    if _schema_loader is None:
        _schema_loader = JSONSchemaLoader()
    return _schema_loader
