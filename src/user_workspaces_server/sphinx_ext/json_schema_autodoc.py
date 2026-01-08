"""
Sphinx extension for automatic configuration documentation from JSON schemas.

This extension generates RST documentation from JSON Schema definitions,
keeping documentation in sync with validation rules automatically.
"""

import json
import os
from typing import Any, Dict

from sphinx.application import Sphinx
from sphinx.util import logging

from user_workspaces_server.config_schemas.json_schema_loader import (
    JSONSchemaWrapper,
    get_schema_loader,
)

logger = logging.getLogger(__name__)


def generate_field_doc(
    field_name: str, field_def: Dict[str, Any], is_required: bool, indent: int = 0
) -> str:
    """
    Generate RST documentation for a single configuration field.

    Args:
        field_name: Name of the field
        field_def: JSON Schema field definition
        is_required: Whether the field is required
        indent: Indentation level

    Returns:
        RST formatted string documenting the field
    """
    indent_str = "  " * indent
    lines = []

    # Field name and type
    field_type = field_def.get("type", "any")
    required_badge = "**[Required]**" if is_required else "*[Optional]*"
    lines.append(f"{indent_str}**{field_name}** ({field_type}) {required_badge}")
    lines.append("")

    # Description
    if "description" in field_def:
        lines.append(f"{indent_str}  {field_def['description']}")
        lines.append("")

    # Default value
    if not is_required and "default" in field_def:
        default_val = field_def["default"]
        if isinstance(default_val, str):
            lines.append(f'{indent_str}  *Default:* ``"{default_val}"``')
        else:
            lines.append(f"{indent_str}  *Default:* ``{default_val}``")
        lines.append("")

    # Enum choices
    if "enum" in field_def:
        choices_str = ", ".join(f'``"{c}"``' for c in field_def["enum"])
        lines.append(f"{indent_str}  *Allowed values:* {choices_str}")
        lines.append("")

    # Numeric constraints
    constraints = []
    if "minimum" in field_def:
        constraints.append(f"minimum: {field_def['minimum']}")
    if "maximum" in field_def:
        constraints.append(f"maximum: {field_def['maximum']}")
    if "pattern" in field_def:
        constraints.append(f"pattern: ``{field_def['pattern']}``")

    if constraints:
        lines.append(f"{indent_str}  *Constraints:* {', '.join(constraints)}")
        lines.append("")

    # Nested object properties
    if field_type == "object" and "properties" in field_def:
        lines.append(f"{indent_str}  *Nested fields:*")
        lines.append("")
        nested_required = field_def.get("required", [])
        for nested_name, nested_def in field_def["properties"].items():
            nested_is_required = nested_name in nested_required
            lines.append(
                generate_field_doc(nested_name, nested_def, nested_is_required, indent + 2)
            )

    return "\n".join(lines)


def generate_controller_doc(schema: JSONSchemaWrapper) -> str:
    """
    Generate RST documentation for a controller schema.

    Args:
        schema: The JSON schema wrapper

    Returns:
        RST formatted string documenting the controller
    """
    lines = []

    # Section header
    class_name = schema.controller_name
    lines.append(class_name)
    lines.append("^" * len(class_name))
    lines.append("")

    # Description
    if schema.description:
        lines.append(schema.description)
        lines.append("")

    # Configuration type field
    type_field_name = {
        "resource": "resource_type",
        "storage": "storage_type",
        "authentication": "user_authentication_type",
        "job_type": "job_type",
    }.get(schema.category)

    if type_field_name:
        lines.append(f'**Configuration value:** ``"{class_name}"``')
        lines.append("")
        lines.append(f'Set ``{type_field_name}`` to ``"{class_name}"`` to use this controller.')
        lines.append("")

    # Required fields
    required_fields = schema.get_required_fields()
    if required_fields:
        lines.append("Required Configuration Fields")
        lines.append("~" * 30)
        lines.append("")
        for field_name in required_fields:
            field_def = schema.get_field(field_name)
            if field_def:
                lines.append(generate_field_doc(field_name, field_def, True))
                lines.append("")

    # Optional fields
    optional_fields = schema.get_optional_fields()
    if optional_fields:
        lines.append("Optional Configuration Fields")
        lines.append("~" * 30)
        lines.append("")
        for field_name in optional_fields:
            field_def = schema.get_field(field_name)
            if field_def:
                lines.append(generate_field_doc(field_name, field_def, False))
                lines.append("")

    # Example configuration
    if schema.example:
        lines.append("Example Configuration")
        lines.append("~" * 30)
        lines.append("")
        lines.append(".. code-block:: json")
        lines.append("")

        example_json = json.dumps(schema.example, indent=2)
        for line in example_json.split("\n"):
            if line:
                lines.append(f"  {line}")
        lines.append("")

    return "\n".join(lines)


def generate_category_doc(category: str, schemas: Dict[str, JSONSchemaWrapper]) -> str:
    """
    Generate RST documentation for a category of controllers.

    Args:
        category: Category name (resources, storage, authentication, job_types)
        schemas: Dictionary of JSON schemas in this category

    Returns:
        RST formatted string documenting all controllers in the category
    """
    lines = []

    # Category header
    category_titles = {
        "resources": "Resource Controllers",
        "storage": "Storage Controllers",
        "authentication": "Authentication Controllers",
        "job_types": "Job Type Controllers",
    }
    title = category_titles.get(category, category.title())
    lines.append(title)
    lines.append("=" * len(title))
    lines.append("")

    # Category description
    category_descriptions = {
        "resources": "Resource controllers manage job execution on different compute platforms.",
        "storage": "Storage controllers manage workspace file storage backends.",
        "authentication": "Authentication controllers handle user authentication and authorization.",
        "job_types": "Job type controllers define different types of computational jobs.",
    }
    if category in category_descriptions:
        lines.append(category_descriptions[category])
        lines.append("")

    # Generate docs for each controller
    for controller_name in sorted(schemas.keys()):
        schema = schemas[controller_name]
        lines.append(generate_controller_doc(schema))
        lines.append("")

    return "\n".join(lines)


def generate_config_reference(output_dir: str):
    """
    Generate complete configuration reference documentation.

    Args:
        output_dir: Directory to write documentation files
    """
    logger.info("Generating configuration reference documentation from JSON schemas...")

    # Get schema loader
    schema_loader = get_schema_loader()
    all_schemas = schema_loader.get_all_schemas()

    # Generate overview/index
    index_lines = []
    index_lines.append("Configuration Reference")
    index_lines.append("=" * 25)
    index_lines.append("")
    index_lines.append("This documentation is automatically generated from JSON Schema files.")
    index_lines.append("All validation rules described here are enforced at startup time.")
    index_lines.append("")
    index_lines.append(
        "Schema files are located in ``src/user_workspaces_server/config_schemas/schemas/``"
    )
    index_lines.append("")
    index_lines.append(".. toctree::")
    index_lines.append("   :maxdepth: 2")
    index_lines.append("   :caption: Configuration:")
    index_lines.append("")
    index_lines.append("   config_resources")
    index_lines.append("   config_storage")
    index_lines.append("   config_authentication")
    index_lines.append("   config_job_types")
    index_lines.append("")

    # Write index
    with open(os.path.join(output_dir, "config_reference.rst"), "w") as f:
        f.write("\n".join(index_lines))

    # Generate category docs
    for category, schemas in all_schemas.items():
        if schemas:  # Only generate if there are schemas
            filename = f"config_{category}.rst"
            with open(os.path.join(output_dir, filename), "w") as f:
                f.write(generate_category_doc(category, schemas))

    logger.info(f"Configuration reference documentation written to {output_dir}")


def builder_inited(app: Sphinx):
    """
    Sphinx event handler called when builder is initialized.

    Generates configuration documentation before Sphinx processes it.
    """
    output_dir = app.srcdir
    try:
        generate_config_reference(output_dir)
    except Exception as e:
        logger.error(f"Failed to generate configuration documentation: {e}")
        raise


def setup(app: Sphinx) -> Dict[str, Any]:
    """
    Sphinx extension setup function.

    Args:
        app: Sphinx application instance

    Returns:
        Extension metadata
    """
    app.connect("builder-inited", builder_inited)

    return {
        "version": "1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
