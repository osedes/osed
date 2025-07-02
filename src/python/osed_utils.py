from pathlib import Path
import argparse
import sys

import yaml


def load_yaml(filepath: Path):
  """Safely loads a YAML file."""
  with open(filepath, "r", encoding="utf-8") as f:
    return yaml.safe_load(f)


def get_arg_parser():
  """Returns an ArgumentParser with standard OSED CLI options."""
  parser = argparse.ArgumentParser(
      description="Process an OSED (Open Standard Entity Description) file."
  )
  parser.add_argument(
      "-f", "--file", required=True, help="Path to the OSED file to process."
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
      print("[WARNING] --schema-path provided; ignoring --schema-version and --driver.", file=sys.stderr)
    schema_path = Path(args.schema_path)
  else:
    driver = normalize_driver(args.driver) if args.driver else None
    version = args.schema_version or "0.3.0"
    if driver and args.schema_version:
      schema_path = base_path / f"osed.driver.{driver}.schema.v{version}.yaml"
    elif driver:
      schema_path = base_path / f"osed.driver.{driver}.schema.v0.3.0.yaml"
    elif args.schema_version:
      schema_path = base_path / f"osed.driver.mongoose-mongodb.schema.v{version}.yaml"
    else:
      schema_path = base_path / "osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"

  data_path = Path(args.file)

  if not schema_path.exists():
    print(f"❌ Schema file not found: '{schema_path}'")
    sys.exit(1)
  if not data_path.exists():
    print(f"❌ Data file not found: '{data_path}'")
    sys.exit(1)

  return schema_path, data_path


def get_default_version() -> str:
  """Get the default schema version from VERSION file or fallback."""
  DEFAULT_VERSION = "0.3.0"
  version_file = Path(__file__).parent / "VERSION"
  if version_file.exists():
    content = version_file.read_text().strip()
    if content:
      return content
  return DEFAULT_VERSION
