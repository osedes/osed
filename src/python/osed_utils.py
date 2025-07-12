"""
OSED Utilities Module

Provides common utility functions for OSED tooling, including YAML loading,
argument parsing, path resolution, and version consistency validation.
"""

import argparse
import sys
import tomllib
from pathlib import Path

import yaml
from .osed_logging import warning, error

CONTROL_KEYS = {
    "osed",
    "entities",
    "universals",
    "particulars",
    "driver",
}

VALID_MONGOOSE_TYPES = {
    "String",
    "string",
    "Number",
    "number",
    "Date",
    "date",
    "Buffer",
    "buffer",
    "Boolean",
    "boolean",
    "Mixed",
    "mixed",
    "ObjectId",
    "objectid",
    "Array",
    "array",
    "List",
    "list",
    "Decimal128",
    "decimal128",
    "Map",
    "map",
    "Schema",
    "schema",
    "UUID",
    "uuid",
    "BigInt",
    "bigint",
    "Double",
    "double",
    "Int32",
    "int32",
    "Reference",
    "reference",
}

VALID_MONGOOSE_ITEM_TYPES = VALID_MONGOOSE_TYPES


def load_yaml(filepath: Path):
    """Load and parse a YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_arg_parser():
    """Get the argument parser for OSED CLI commands."""
    parser = argparse.ArgumentParser(
        prog="osed",
        description="OSED (Open Standard Entity Description) CLI tool",
    )
    parser.add_argument(
        "--file",
        "-f",
        dest="file",
        default="osed.yaml",
        help="Path to the OSED document file (default: osed.yaml)",
    )
    parser.add_argument(
        "--schema-version",
        dest="schema_version",
        default=None,
        help="The schema version to use. Defaults to 0.3.0.",
    )
    parser.add_argument(
        "--driver",
        dest="driver",
        default=None,
        help="The name of the metadata driver to use (e.g., 'mongoose-mongo'). If provided, processing is against this driver schema.",
    )
    parser.add_argument(
        "--schema-path",
        dest="schema_path",
        default=None,
        help="Path to an explicit schema file to use for validation. Takes precedence over --schema-version/--driver.",
    )
    return parser


def _check_version_file(base_path: Path) -> tuple[str, list[str]]:
    """Check VERSION file and return source version and any issues."""
    issues = []
    version_file = base_path / "VERSION"

    if not version_file.exists():
        issues.append("VERSION file not found")
        return "", issues

    source_version = version_file.read_text().strip()
    if not source_version:
        issues.append("VERSION file is empty")
        return "", issues

    return source_version, issues


def _check_schema_files(base_path: Path, source_version: str) -> list[str]:
    """Check schema files for version consistency."""
    issues = []
    schema_dir = base_path / "schema"

    if not schema_dir.exists():
        return issues

    for schema_file in schema_dir.glob("*.yaml"):
        try:
            schema_content = load_yaml(schema_file)

            # Check if schema has version field
            schema_version = schema_content.get("version")
            if not schema_version:
                issues.append(
                    f"Schema file {schema_file.name} missing version field"
                )
                continue

            if schema_version != source_version:
                issues.append(
                    f"Schema file {schema_file.name} version {schema_version} != source version {source_version}"
                )

            # Check if schema has $id field
            schema_id = schema_content.get("$id")
            if not schema_id:
                issues.append(
                    f"Schema file {schema_file.name} missing $id field"
                )
                continue

            # Check if $id contains correct version
            if source_version not in schema_id:
                issues.append(
                    f"Schema file {schema_file.name} $id does not contain version {source_version}"
                )

        except (yaml.YAMLError, OSError) as e:
            issues.append(f"Error reading schema file {schema_file.name}: {e}")

    return issues


def _check_pyproject_toml(base_path: Path, source_version: str) -> list[str]:
    """Check pyproject.toml for version consistency."""
    issues = []
    pyproject_toml = base_path / "pyproject.toml"

    if not pyproject_toml.exists():
        return issues

    try:
        with open(pyproject_toml, "rb") as f:
            pyproject_data = tomllib.load(f)

        # Check if dynamic version is configured
        project_data = pyproject_data.get("project", {})
        dynamic_versions = project_data.get("dynamic", [])

        if "version" in dynamic_versions:
            # Version is dynamic, check if it's configured to read from VERSION file
            tool_data = pyproject_data.get("tool", {})
            setuptools_data = tool_data.get("setuptools", {})
            dynamic_data = setuptools_data.get("dynamic", {})
            version_config = dynamic_data.get("version", {})

            if version_config.get("file") != "VERSION":
                issues.append(
                    "pyproject.toml version configuration not reading from VERSION file"
                )
        else:
            # Version is static, check if it matches
            static_version = project_data.get("version")
            if static_version and static_version != source_version:
                issues.append(
                    f"pyproject.toml version {static_version} != source version {source_version}"
                )
            elif not static_version:
                issues.append("pyproject.toml missing version field")

    except (OSError, ValueError) as e:
        issues.append(f"Error reading pyproject.toml: {e}")

    return issues


def _check_cli_version(source_version: str) -> list[str]:
    """Check CLI version for consistency."""
    issues = []
    cli_version = get_default_version()

    if cli_version != source_version:
        issues.append(
            f"CLI default version {cli_version} != source version {source_version}"
        )

    return issues


def resolve_schema_and_data_paths(args, base_path: Path):
    """Resolves schema and data file paths given parsed args and base path.

    Returns:
      tuple: (schema_path, data_path) as Path objects

    Raises:
      SystemExit: If schema or data file does not exist
    """

    # Normalize all mongoose driver variants to 'mongoose-mongodb'
    def normalize_driver(driver):
        if driver in {"mongoose", "mongoose-mongo", "mongoose-mongodb"}:
            return "mongoose-mongodb"
        return driver

    if args.schema_path:
        if args.schema_version or args.driver:
            warning(
                "--schema-path provided; ignoring --schema-version and --driver."
            )
        schema_path = Path(args.schema_path)
    else:
        driver = normalize_driver(args.driver) if args.driver else None
        version = args.schema_version or "0.3.0"
        schema_dir = Path("schema")
        if driver and args.schema_version:
            schema_path = (
                schema_dir / f"osed.driver.{driver}.schema.v{version}.yaml"
            )
        elif driver:
            schema_path = (
                schema_dir / f"osed.driver.{driver}.schema.v0.3.0.yaml"
            )
        elif args.schema_version:
            schema_path = (
                schema_dir
                / f"osed.driver.mongoose-mongodb.schema.v{version}.yaml"
            )
        else:
            schema_path = (
                schema_dir / "osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            )

    data_path = Path(args.file)

    if not schema_path.exists():
        error(f"Schema file not found: '{schema_path}'")
        sys.exit(1)
    if not data_path.exists():
        error(f"Data file not found: '{data_path}'")
        sys.exit(1)

    return schema_path, data_path


def get_default_version() -> str:
    """Get the default schema version from VERSION file or fallback."""
    default_version = "0.3.0"

    # Try to read from repo root VERSION file
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        content = version_file.read_text().strip()
        if content:
            return content

    # Fallback to default version
    return default_version


def validate_version_consistency() -> tuple[bool, list[str]]:
    """
    Validate version consistency across all tools and schema files.

    Returns:
        tuple: (is_consistent, list_of_issues)
    """
    base_path = Path.cwd()

    # Check VERSION file first
    source_version, issues = _check_version_file(base_path)
    if not source_version:
        return False, issues

    # Check schema files
    issues.extend(_check_schema_files(base_path, source_version))

    # Check pyproject.toml
    issues.extend(_check_pyproject_toml(base_path, source_version))

    # Check CLI version
    issues.extend(_check_cli_version(source_version))

    return len(issues) == 0, issues
