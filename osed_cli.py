import argparse
from pathlib import Path

from osed_validate import validate_file, get_default_version
from osed_lint import lint_file

DEFAULT_FILE = "osed.yaml"
DEFAULT_VERSION = "0.1.0"

def get_schema_path(version: str) -> Path:
  return Path(f"schema/osed.schema.v{version}.yaml")

def validate_command(path: Path, schema_version: str | None = None) -> int:
  print(f"🔍 Validating {path}")
  version = schema_version or get_default_version()
  schema_path = get_schema_path(version)

  if not schema_path.exists():
    print(f"❌ Schema file not found: {schema_path}")
    return 2

  return 0 if validate_file(schema_path, path) else 1

def lint_command(path: Path) -> int:
  print(f"🧹 Linting {path}")
  return 0 if lint_file(path) else 1

def main():
  parser = argparse.ArgumentParser(
    prog="osed",
    description="OSED CLI tooling"
  )

  parser.add_argument(
    "--version", "-v",
    action="version",
    version=f"osed {get_default_version()}"
  )

  # Shared parent parser for --file
  file_parent = argparse.ArgumentParser(add_help=False)
  file_parent.add_argument(
    "--file", "-f",
    default=DEFAULT_FILE,
    help=f"Path to OSED document (default: {DEFAULT_FILE})"
  )

  subparsers = parser.add_subparsers(dest="command", required=True)

  # Validate subcommand
  validate_parser = subparsers.add_parser(
    "validate",
    parents=[file_parent],
    help="Validate an OSED document"
  )
  validate_parser.add_argument(
    "--schema",
    help="Schema version to validate against (e.g., 0.1.0). Default is latest."
  )

  # Lint subcommand
  lint_parser = subparsers.add_parser(
    "lint",
    parents=[file_parent],
    help="Lint an OSED document"
  )

  args = parser.parse_args()
  path = Path(args.file)

  if not path.exists():
    print(f"❌ File not found: {path}")
    exit(2)

  if args.command == "validate":
    exit(validate_command(path, args.schema))
  elif args.command == "lint":
    exit(lint_command(path))

if __name__ == "__main__":
  main()
