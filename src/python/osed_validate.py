"""
OSED Validation Module

Provides validation functionality for OSED documents against JSON Schema,
including preprocessing of OSED-specific data structures and cross-file reference support.
"""

from pathlib import Path
import sys
import re
import yaml
from referencing import Registry, Resource
from jsonschema import Draft202012Validator

from .osed_utils import (
    get_arg_parser,
    resolve_schema_and_data_paths,
)
from .osed_logging import info, error, warning


def expand_list_description(value):
    """Expand list type descriptions to their item types."""
    if (
        isinstance(value, dict)
        and value.get("type") in ("list", "array")
        and "items" in value
    ):
        return value["items"]
    return value


def expand_map_description(value):
    """Expand map type descriptions to their value types."""
    if (
        isinstance(value, dict)
        and value.get("type") == "map"
        and "value" in value
    ):
        return value["value"]
    return value


def preprocess_osed_data(data):
    """Preprocess OSED data by expanding list and map descriptions."""
    if not isinstance(data, dict):
        return data
    processed = {}
    for k, v in data.items():
        if isinstance(v, dict):
            processed[k] = {
                sub_k: preprocess_osed_data(
                    expand_map_description(expand_list_description(sub_v))
                )
                for sub_k, sub_v in v.items()
            }
        elif isinstance(v, list):
            processed[k] = [
                preprocess_osed_data(
                    expand_map_description(expand_list_description(item))
                )
                for item in v
            ]
        else:
            processed[k] = expand_map_description(expand_list_description(v))
    return processed


def parse_semver(version_str):
    """Parse a semantic version string into (major, minor, patch)."""
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", str(version_str))
    if match:
        return tuple(map(int, match.groups()))
    return None, None, None


def load_schema_with_referencing(schema_path: Path):
    """
    Load a schema and build a referencing.Registry for cross-file $ref support.
    Returns the root schema and the registry.
    """
    schema_text = schema_path.read_text()
    schema = yaml.safe_load(schema_text)
    base_uri = schema_path.resolve().as_uri()
    resources = {base_uri: Resource.from_contents(schema)}
    loaded_paths = {str(schema_path.resolve())}

    def collect_refs(obj, current_path: Path):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "$ref" and isinstance(v, str):
                    if v.startswith("./") or v.startswith("../"):
                        ref_path = (
                            current_path.parent / v.split("#")[0]
                        ).resolve()
                        ref_uri = ref_path.as_uri()
                        if (
                            str(ref_path) not in loaded_paths
                            and ref_path.exists()
                        ):
                            ref_schema = yaml.safe_load(ref_path.read_text())
                            resources[ref_uri] = Resource.from_contents(
                                ref_schema
                            )
                            loaded_paths.add(str(ref_path))
                            collect_refs(ref_schema, ref_path)
                else:
                    collect_refs(v, current_path)
        elif isinstance(obj, list):
            for item in obj:
                collect_refs(item, current_path)

    collect_refs(schema, schema_path)
    registry = Registry(resources=resources)
    return schema, registry


def validate_file(
    schema_path: Path, data_path: Path, expected_version: str = "1.0.0"
) -> bool:
    """Validate a data file against a schema file."""
    # Step 1: Load schema
    try:  # pylint: disable=broad-exception-caught
        schema, registry = load_schema_with_referencing(schema_path)
    except Exception as e:  # pylint: disable=broad-exception-caught
        error(
            f"Failed to load schema file: {e}",
            context=f"schema: {schema_path}",
            suggestions=[
                "Check that the schema file exists and is valid YAML/JSON.",
                "Ensure all $ref dependencies are present and correct.",
            ],
        )
        return False
    # Step 2: Load data
    try:  # pylint: disable=broad-exception-caught
        data = yaml.safe_load(data_path.read_text())
    except Exception as e:  # pylint: disable=broad-exception-caught
        error(
            f"Failed to load or parse OSED document: {e}",
            context=f"data: {data_path}",
            suggestions=[
                "Check that the OSED document is valid YAML.",
                "Ensure the file exists and is readable.",
            ],
        )
        return False
    # Step 3: Version check (example: expect schema version 1.0.0)
    schema_version = schema.get("version")
    # TODO: Make expected_version and actual version configurable and improve version handling logic
    if schema_version:
        exp_major, exp_minor, exp_patch = parse_semver(expected_version)
        act_major, act_minor, act_patch = parse_semver(schema_version)
        if exp_major is not None and act_major is not None:
            if act_major != exp_major:
                error(
                    f"Schema major version mismatch: expected {expected_version}, found {schema_version}",
                    context=f"schema: {schema_path}",
                    suggestions=[
                        f"Update your schema to version {expected_version} or adjust the validator to accept version {schema_version}."
                    ],
                )
                return False
            if act_minor != exp_minor or act_patch != exp_patch:
                warning(
                    f"Schema minor/patch version mismatch: expected {expected_version}, found {schema_version}",
                    context=f"schema: {schema_path}",
                    suggestions=[
                        f"Update your schema to version {expected_version} or adjust the validator to accept version {schema_version}."
                    ],
                )
    # Step 4: Preprocess data
    try:
        data = preprocess_osed_data(data)
    except Exception as e:
        error(
            f"Failed to preprocess OSED data: {e}",
            context=f"data: {data_path}",
            suggestions=[
                "Check the structure of your OSED document for invalid types or values."
            ],
        )
        return False
    # Step 5: Validate against schema
    try:
        validator = Draft202012Validator(schema, registry=registry)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            error(
                "Validation failed: See details below.",
                context=f"schema: {schema_path}, data: {data_path}",
            )
            for validation_error in errors:
                location = "/".join(map(str, validation_error.path)) or "<root>"
                error(
                    f"  - [{location}] {validation_error.message}",
                    context=f"schema: {schema_path}, data: {data_path}",
                    suggestions=[
                        "Check the data structure and types against the schema.",
                        f"Field: {location}",
                        f"Error: {validation_error.message}",
                    ],
                )
            return False
    except (ValueError, TypeError) as e:
        error(
            f"Validation error: {e}",
            context=f"schema: {schema_path}, data: {data_path}",
            suggestions=[
                "Check that your OSED document matches the schema structure.",
                "Check for invalid types or values.",
            ],
        )
        return False
    info("Validation passed")
    return True


def main():
    """Main entry point for the validate command."""
    parser = get_arg_parser()
    parser.add_argument(
        "--expected-schema-version",
        default="1.0.0",
        help="Expected schema version for validation (default: 1.0.0). Use to match your schema file version.",
    )
    args = parser.parse_args()
    base_path = Path(__file__).parent / "schema"
    schema_path, data_path = resolve_schema_and_data_paths(args, base_path)

    info(f"Validating '{data_path.name}' against '{schema_path.name}'")
    success = validate_file(
        schema_path, data_path, expected_version=args.expected_schema_version
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
