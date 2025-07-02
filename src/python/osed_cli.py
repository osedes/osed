import argparse
from pathlib import Path
import os
from .osed_lint import lint_file
from .osed_utils import load_yaml, get_default_version
from .osed_validate import validate_file

DEFAULT_FILE = "osed.yaml"
DEFAULT_VERSION = "0.3.0"


def get_schema_path(version: str) -> Path:
  return Path(f"schema/osed.schema.v{version}.yaml")


def get_metadata_schema_path(version: str) -> Path:
  return Path(f"schema/osed.driver.mongoose-mongodb.schema.v{version}.yaml")


def validate_command(
        path: Path,
        schema_version: str = None,
        driver: str = None,
        input_dir: Path = None) -> int:
  version = schema_version or get_default_version()
  base_path = input_dir or Path.cwd()
  if driver:
    schema_path = (
        base_path
        / "schema"
        / f"osed.driver.{driver}.schema.v{version}.yaml"
    )
  else:
    schema_path = (
        base_path
        / "schema"
        / f"osed.schema.v{version}.yaml"
    )
  if not schema_path.exists():
    print(f"❌ Schema file not found: {schema_path}")
    return 2
  main_valid = validate_file(schema_path, path)
  if not main_valid:
    return 1
  return 0


def lint_command(path: Path, input_dir: Path = None) -> int:
  # Optionally use input_dir for future linting logic
  print(f"🧹 Linting {path}")
  return 0 if lint_file(path) else 1


def generate_command(path: Path, target: str, output_dir: Path) -> int:
  print(
      f"🚀 Generating {target} TypeScript schema from {path} into {output_dir}"
  )
  print("-" * 40)

  # Generation should only proceed if the file is valid and lint-free.
  # The command functions print their own detailed output.
  is_valid = validate_command(path) == 0
  is_lint_clean = lint_command(path) == 0

  if not (is_valid and is_lint_clean):
    print("-" * 40)
    print("❌ Generation aborted due to validation/linting errors.")
    return 1

  if target.lower() == "mongoose":
    from .osed_generate import generate_mongoose

    document = load_yaml(path)
    generate_mongoose(document, output_dir)
    return 0

  return 1  # Should not be reached with `choices` in argparse


def main():
  parser = argparse.ArgumentParser(
      prog="osed", description="OSED CLI tooling"
  )

  parser.add_argument(
      "--version",
      "-v",
      action="version",
      version=f"osed {get_default_version()}",
  )

  # Shared parent parser for --file
  file_parent = argparse.ArgumentParser(add_help=False)
  file_parent.add_argument(
      "--file",
      "-f",
      default=DEFAULT_FILE,
      help=f"Path to OSED document (default: {DEFAULT_FILE})",
  )
  file_parent.add_argument(
      "--input-dir",
      default=os.getcwd(),
      help="Input directory to resolve schema and data files (default: current directory)",
  )

  subparsers = parser.add_subparsers(dest="command", required=True)

  # Validate subcommand
  validate_parser = subparsers.add_parser(
      "validate", parents=[file_parent], help="Validate an OSED document"
  )
  validate_parser.add_argument(
      "--schema-version",
      default=get_default_version(),
      help="Schema version to validate against. Defaults to latest.",
  )
  validate_parser.add_argument(
      "--driver",
      default=None,
      help="The name of the metadata driver to use (e.g., 'mongoose-mongodb'). If provided, validation is against this driver's schema.",
  )

  # Lint subcommand
  lint_parser = subparsers.add_parser(
      "lint", parents=[file_parent], help="Lint an OSED document"
  )

  # Generate subcommand
  generate_parser = subparsers.add_parser(
      "generate",
      parents=[file_parent],
      help="Generate downstream artifacts from an OSED document",
  )
  generate_parser.add_argument(
      "--target",
      required=True,
      choices=["mongoose"],
      help="The target framework to generate for (e.g., mongoose)",
  )
  generate_parser.add_argument(
      "--out",
      default=".",
      help="Output directory for generated files (default: current directory)",
  )

  args = parser.parse_args()
  input_dir = Path(args.input_dir)
  path = input_dir / \
      args.file if not Path(args.file).is_absolute() else Path(args.file)

  if not path.exists():
    print(f"❌ File not found: {path}")
    exit(2)

  if args.command == "validate":
    exit(validate_command(path, args.schema_version, args.driver, input_dir))
  elif args.command == "lint":
    exit(lint_command(path, input_dir))
  elif args.command == "generate":
    exit(generate_command(path, args.target, Path(args.out)))


if __name__ == "__main__":
  main()
