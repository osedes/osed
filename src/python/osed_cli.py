"""OSED CLI tooling module.

This module provides command-line interface functionality for the OSED (Open
Standard Entity Description) tool, including validation, linting, generation,
and diff operations on OSED documents.
"""

import argparse
from pathlib import Path
import os
import sys
import shutil

from .osed_diff import diff_osed_documents, format_diff_result
from .osed_lint import lint_file
from .osed_utils import (
    get_default_version,
    load_yaml,
    validate_version_consistency,
)
from .osed_validate import validate_file
from .osed_generate import generate_mongoose
from .osed_logging import info, warning, error
from .osed_logging_config import (
    setup_development_logging,
    setup_production_logging,
    setup_testing_logging,
)
from .osed_config import (
    acknowledge_path,
    ensure_config_dir_exists,
    unacknowledge_path,
)
from .osed_logging import OSEDLogger, set_logger
from .osed_logging import get_logger

# Visualization imports (optional - only imported when needed)
try:
    from .osed_visualize import (
        load_osed_yaml,
        generate_graph_easy,
        generate_dot,
        generate_svg_file,
        generate_png_file,
        generate_mermaid,
        generate_plantuml,
    )

    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False

DEFAULT_FILE = "osed.yaml"
DEFAULT_VERSION = "0.3.0"

COMPLETION_SCRIPT_PATH = os.path.join(
    os.path.dirname(__file__), '../../scripts/osed-completion.bash'
)
USER_COMPLETION_PATH = os.path.expanduser('~/.osed/osed-completion.bash')


def get_schema_path(version: str) -> Path:
    """Get the path to the schema file for a given version."""
    return Path(f"schema/osed.schema.v{version}.yaml")


def get_metadata_schema_path(version: str) -> Path:
    """Get the path to the metadata schema file for a given version."""
    return Path(f"schema/osed.driver.mongoose-mongodb.schema.v{version}.yaml")


def validate_command(
    path: Path,
    schema_version: str | None = None,
    driver: str | None = None,
    input_dir: Path | None = None,
    schema_file: Path | None = None,
    expected_schema_version: str | None = None,
) -> int:
    """Validate an OSED document against its schema."""
    base_path = input_dir or Path.cwd()
    if input_dir is None:
        info(f"Using default input directory: {base_path}")
    if str(path) == "osed.yaml":
        info("Using default OSED file: osed.yaml")
    try:  # pylint: disable=broad-exception-caught
        document = load_yaml(path)
        document_version = document.get("osed")
        if not document_version:
            error(f"Missing required 'osed' key in document {path}")
            return 1
    except Exception as e:  # pylint: disable=broad-exception-caught
        error(f"Could not read OSED document: {e}")
        return 1

    # Determine schema path
    if schema_file:
        schema_path = schema_file
        info(f"Using custom schema file: {schema_path}")
    else:
        if not schema_version:
            version = document_version
            info(f"Auto-detected schema version '{version}' from OSED document")
        else:
            version = schema_version
            if schema_version == get_default_version():
                info(f"Using default schema version: {schema_version}")
            else:
                info(f"Using specified schema version '{version}'")
            if document_version != version:
                warning(
                    f"OSED document specifies version '{document_version}' but validating against schema version '{version}'"
                )

        if driver:
            schema_path = (
                base_path
                / "schema"
                / f"osed.driver.{driver}.schema.v{version}.yaml"
            )
            info(f"Using driver schema: {driver}")
        else:
            schema_path = base_path / "schema" / f"osed.schema.v{version}.yaml"
            info("Using main OSED schema")

    if not schema_path.exists():
        error(f"Schema file not found: {schema_path}")
        return 2

    # Use default version if not specified
    if expected_schema_version is None:
        expected_schema_version = get_default_version()

    main_valid = validate_file(schema_path, path, expected_schema_version)
    if not main_valid:
        return 1
    get_logger().info("Validation passed")
    return 0


def lint_command(path: Path, stdout=None, stderr=None) -> int:
    """Run the linter on the given file and output results."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    # Get the current logger to preserve output format
    current_logger = get_logger()

    # Create a new logger with the same output format but custom streams
    logger = OSEDLogger(
        output_format=current_logger.output_format,
        stdout_stream=stdout,
        stderr_stream=stderr,
    )
    set_logger(logger)

    _, results_by_severity = lint_file(path)
    for results in results_by_severity.values():
        for result in results:
            log_msg = result.to_log_message()
            logger.log(
                log_msg.severity,
                log_msg.message,
                context=log_msg.context,
                suggestions=log_msg.suggestions,
                file_path=log_msg.file_path,
                line_number=log_msg.line_number,
            )
    return logger.get_exit_code()


def generate_command(path: Path, target: str, output_dir: Path) -> int:
    """Generate downstream artifacts from an OSED document."""
    info(f"Generating {target} TypeScript schema from {path} into {output_dir}")
    info("-" * 40)
    is_valid = validate_command(path) == 0
    is_lint_clean = lint_command(path) == 0
    if not (is_valid and is_lint_clean):
        info("-" * 40)
        error("Generation aborted due to validation/linting errors.")
        return 1
    if target.lower() == "mongoose":
        document = load_yaml(path)
        generate_mongoose(document, output_dir)

        # Add structured output for JSON format
        logger = get_logger()
        if logger.output_format == "json":
            # Get the list of generated files
            generated_files = []
            entities = document.get("entities", [])
            for entity_name in entities:
                if entity_name in document:
                    model_file = output_dir / f"{entity_name}.model.ts"
                    if model_file.exists():
                        generated_files.append(str(model_file))

            interfaces_file = output_dir / "interfaces.ts"
            if interfaces_file.exists():
                generated_files.append(str(interfaces_file))

            # Log generation summary as structured data
            info(
                "Generation completed successfully",
                context=f"target: {target}, output_dir: {output_dir}",
                suggestions=generated_files,
            )

        return 0
    return 1


def check_versions_command() -> int:
    """Check version consistency across all tools and schema files."""
    info("Checking version consistency across tools and schema files...")
    info("-" * 50)
    is_consistent, issues = validate_version_consistency()
    if is_consistent:
        info("All versions are consistent!")
        return 0
    error("Version inconsistencies found:")
    for issue in issues:
        error(f"{issue}")
    return 1


def diff_command(file1: Path, file2: Path) -> int:
    """Compare two OSED documents and show differences."""
    try:
        result = diff_osed_documents(file1, file2)
        output = format_diff_result(result, file1, file2)
        info(output)
        if result.breaking_changes:
            warning("Breaking changes detected!")
            return 1
        return 0
    except (OSError, ValueError, RuntimeError) as e:
        error(f"Error comparing documents: {e}")
        return 2


def handle_check_versions():
    """Handle the check-versions CLI command."""
    return check_versions_command()


def handle_diff(args):
    """Handle the diff CLI command."""
    file1 = args.file1
    file2 = args.file2
    if not file1.exists():
        error(f"File not found: {file1}")
        sys.exit(2)
    if not file2.exists():
        error(f"File not found: {file2}")
        sys.exit(2)
    return diff_command(file1, file2)


def handle_lint(args):
    """Handle the lint CLI command, including acknowledge and unacknowledge
    subcommands."""
    lint_cmd = args.lint_command or "run"
    if lint_cmd == "acknowledge":
        acknowledge_path(
            args.kind,
            args.path,
            user=args.global_config,
            user_name=args.user,
            note=args.note,
        )
        info(
            f"Acknowledged {args.kind} at {args.path} by {args.user} "
            f"(global: {args.global_config})."
        )
        return 0
    if lint_cmd == "unacknowledge":
        removed = unacknowledge_path(
            args.kind,
            args.path,
            user=args.global_config,
            user_name=args.user,
            note=args.note,
        )
        if removed:
            info(
                f"Unacknowledged {args.kind} at {args.path} by {args.user} "
                f"(global: {args.global_config})."
            )
        else:
            info(
                f"No acknowledgement found for {args.kind} at {args.path} "
                f"(global: {args.global_config})."
            )
        return 0
    input_dir = Path(args.input_dir)
    path = (
        input_dir / args.file
        if not Path(args.file).is_absolute()
        else Path(args.file)
    )
    if not path.exists():
        error(f"File not found: {path}")
        sys.exit(2)
    lint_command(path)
    logger = get_logger()
    return logger.get_exit_code()


def handle_validate(args):
    """Handle the validate CLI command."""
    input_dir = Path(args.input_dir)
    path = (
        input_dir / args.file
        if not Path(args.file).is_absolute()
        else Path(args.file)
    )
    if not path.exists():
        error(f"File not found: {path}")
        sys.exit(2)
    return validate_command(
        path,
        args.schema_version,
        args.driver,
        input_dir,
        args.schema_file,
        args.expected_schema_version,
    )


def handle_generate(args):
    """Handle the generate CLI command."""
    input_dir = Path(args.input_dir)
    path = (
        input_dir / args.file
        if not Path(args.file).is_absolute()
        else Path(args.file)
    )
    if not path.exists():
        error(f"File not found: {path}")
        sys.exit(2)
    return generate_command(path, args.target, Path(args.out))


def handle_completion(args):
    """Handle the completion CLI command."""
    if args.completion_command == "show":
        with open(COMPLETION_SCRIPT_PATH, "r", encoding='utf-8') as f:
            print(f.read())
        return 0
    if args.completion_command == "install":
        os.makedirs(os.path.dirname(USER_COMPLETION_PATH), exist_ok=True)
        shutil.copyfile(COMPLETION_SCRIPT_PATH, USER_COMPLETION_PATH)
        print(f"Bash completion script installed to {USER_COMPLETION_PATH}")
        source_line = f"source {USER_COMPLETION_PATH}"
        bashrc = os.path.expanduser("~/.bashrc")
        with open(bashrc, "a+", encoding='utf-8') as f:
            f.seek(0)
            if source_line not in f.read():
                f.write(f"\n# Enable osed bash completion\n{source_line}\n")
                print(f"Appended source line to {bashrc}")
            else:
                print(f"Source line already present in {bashrc}")
        print("To enable completion now, run:")
        print(f"  source {USER_COMPLETION_PATH}")
        return 0
    print("Unknown completion command. Use 'show' or 'install'.")
    return 1


def handle_visualize(args):
    """Handle the visualize CLI command."""
    input_dir = Path(args.input_dir)
    path = (
        input_dir / args.file
        if not Path(args.file).is_absolute()
        else Path(args.file)
    )
    if not path.exists():
        error(f"File not found: {path}")
        sys.exit(2)

    # Check if visualization is available
    if not VISUALIZATION_AVAILABLE:
        error(
            "Visualization module not available. Install required dependencies."
        )
        return 1

    try:
        osed_doc = load_osed_yaml(path)

        if args.format == "graph-easy":
            output = generate_graph_easy(osed_doc)
        elif args.format == "dot":
            output = generate_dot(osed_doc)
        elif args.format == "png":
            if not args.output:
                error("Output file path is required for 'png' format.")
                return 1
            generate_png_file(osed_doc, args.output)
            info(f"Generated PNG file: {args.output}")
            return 0
        elif args.format == "svg":
            if not args.output:
                error("Output file path is required for 'svg' format.")
                return 1
            generate_svg_file(osed_doc, args.output)
            info(f"Generated SVG file: {args.output}")
            return 0
        elif args.format == "mermaid":
            output = generate_mermaid(osed_doc, show_types=args.show_types)
        elif args.format == "plantuml":
            output = generate_plantuml(osed_doc, show_types=args.show_types)
        else:
            error(f"Unsupported format '{args.format}'.")
            return 1

        if args.output:
            with open(args.output, "w", encoding='utf-8') as f:
                f.write(output)
            info(f"Generated {args.format} file: {args.output}")
        else:
            print(output)

        return 0

    except ImportError as e:
        error(f"Missing dependency: {e}")
        return 1
    except (OSError, ValueError, RuntimeError) as e:
        error(f"Visualization failed: {e}")
        return 1


def main():
    """Main entry point for the OSED CLI."""
    ensure_config_dir_exists()
    env = os.getenv("OSED_ENV", "development")

    parser = argparse.ArgumentParser(
        prog="osed", description="OSED CLI tooling"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Shared parent parser for --file and --output-format
    file_parent = argparse.ArgumentParser(add_help=False)
    file_parent.add_argument(
        "--file",
        "-f",
        default=DEFAULT_FILE,
        help=f"Path to OSED document (default: {DEFAULT_FILE})",
    )
    file_parent.add_argument(
        "--input-dir",
        default=str(Path.cwd()),
        help="Input directory to resolve schema and data files (default: current directory)",
    )
    file_parent.add_argument(
        "--output-format",
        choices=["human", "json"],
        default="human",
        help="Output format for logs and results (default: human)",
    )

    # Validate subcommand
    validate_parser = subparsers.add_parser(
        "validate", parents=[file_parent], help="Validate an OSED document"
    )
    validate_parser.add_argument(
        "--schema-version",
        default=get_default_version(),
        help="Schema version to validate against. If not provided, falls back to version from VERSION file.",
    )
    validate_parser.add_argument(
        "--schema-file",
        type=Path,
        help="Path to a specific schema file to validate against (overrides --schema-version and --driver)",
    )
    validate_parser.add_argument(
        "--driver",
        default=None,
        help="The name of the metadata driver to use (e.g., 'mongoose-mongodb'). If provided, validation is against this driver's schema.",
    )
    validate_parser.add_argument(
        "--expected-schema-version",
        default=get_default_version(),
        help=f"Expected schema version for validation (default: {get_default_version()}). Use to match your schema file version.",
    )

    # Lint subcommand with nested subparsers
    lint_parser = subparsers.add_parser(
        "lint",
        help="Lint an OSED document or manage lint warnings.",
        description=(
            "Lint an OSED document or manage lint warnings. Use one of the "
            "subcommands: run, acknowledge, unacknowledge."
        ),
    )
    lint_subparsers = lint_parser.add_subparsers(
        dest="lint_command", required=True
    )

    lint_subparsers.add_parser(
        "run", parents=[file_parent], help="Lint an OSED document"
    )

    # 'osed lint acknowledge' subcommand
    lint_ack_parser = lint_subparsers.add_parser(
        "acknowledge",
        help="Acknowledge a lint warning (downgrade to info)",
    )
    lint_ack_parser.add_argument(
        "--kind",
        required=True,
        help="Type of warning to acknowledge (e.g., sensitiveFields, "
        "auditFields)",
    )
    lint_ack_parser.add_argument(
        "--path",
        required=True,
        help="Reference to the field/entity to acknowledge "
        "(e.g., file.yaml#Entity.field)",
    )
    lint_ack_parser.add_argument(
        "--user",
        required=True,
        help="User name acknowledging the warning",
    )
    lint_ack_parser.add_argument(
        "--note",
        default=None,
        help="Optional note for the acknowledgement",
    )
    lint_ack_parser.add_argument(
        "--global",
        dest="global_config",
        action="store_true",
        help="Apply to user-level config (~/.osed/config.yaml) instead of "
        "project config (default)",
    )

    # 'osed lint unacknowledge' subcommand
    lint_unack_parser = lint_subparsers.add_parser(
        "unacknowledge",
        help="Remove acknowledgement for a lint warning (restore to warning)",
    )
    lint_unack_parser.add_argument(
        "--kind",
        required=True,
        help="Type of warning to unacknowledge (e.g., sensitiveFields, "
        "auditFields)",
    )
    lint_unack_parser.add_argument(
        "--path",
        required=True,
        help="Reference to the field/entity to unacknowledge "
        "(e.g., file.yaml#Entity.field)",
    )
    lint_unack_parser.add_argument(
        "--user",
        required=True,
        help="User name performing the unacknowledge",
    )
    lint_unack_parser.add_argument(
        "--note",
        default=None,
        help="Optional note for the unacknowledgement",
    )
    lint_unack_parser.add_argument(
        "--global",
        dest="global_config",
        action="store_true",
        help="Apply to user-level config (~/.osed/config.yaml) instead of "
        "project config (default)",
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

    # Check versions subcommand
    subparsers.add_parser(
        "check-versions",
        parents=[file_parent],
        help="Check version consistency across all tools and schema files",
    )

    # Diff subcommand
    diff_parser = subparsers.add_parser(
        "diff",
        parents=[file_parent],
        help="Compare two OSED documents and show differences",
    )
    diff_parser.add_argument(
        "file1",
        type=Path,
        help="First OSED document to compare",
    )
    diff_parser.add_argument(
        "file2",
        type=Path,
        help="Second OSED document to compare",
    )

    # Visualize subcommand
    visualize_parser = subparsers.add_parser(
        "visualize",
        parents=[file_parent],
        help="Generate visual diagrams from an OSED document",
    )
    visualize_parser.add_argument(
        "--format",
        type=str,
        default="graph-easy",
        choices=["graph-easy", "dot", "png", "svg", "mermaid", "plantuml"],
        help="Output format: 'graph-easy' (ASCII), 'dot' (Graphviz), 'png' (bitmap), 'svg' (scalable), 'mermaid' (ER diagram), 'plantuml' (UML class diagram)",
    )
    visualize_parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file path (if omitted, prints to terminal; required for 'png' and 'svg')",
    )
    visualize_parser.add_argument(
        "--show-types",
        action="store_true",
        default=False,
        help="Show field types in Mermaid ER diagram (default: false)",
    )

    # Add completion subcommand
    completion_parser = subparsers.add_parser(
        "completion",
        help="Show or install bash completion script",
    )
    completion_subparsers = completion_parser.add_subparsers(
        dest="completion_command", required=True
    )
    completion_subparsers.add_parser(
        "show", help="Show the bash completion script"
    )
    completion_subparsers.add_parser(
        "install", help="Install the bash completion script to ~/.osed/"
    )

    args = parser.parse_args()
    exit_code = 0
    try:
        # Set up logger with selected output format from args
        if env == "production":
            logger = setup_production_logging(
                format_type=getattr(args, "output_format", "human")
            )
        elif env == "testing":
            logger = setup_testing_logging(
                format_type=getattr(args, "output_format", "human")
            )
        else:
            logger = setup_development_logging(
                format_type=getattr(args, "output_format", "human")
            )
        set_logger(logger)

        if args.command == "check-versions":
            exit_code = handle_check_versions()
        elif args.command == "diff":
            exit_code = handle_diff(args)
        elif args.command == "lint":
            exit_code = handle_lint(args)
        elif args.command == "validate":
            exit_code = handle_validate(args)
        elif args.command == "generate":
            exit_code = handle_generate(args)
        elif args.command == "visualize":
            exit_code = handle_visualize(args)
        elif args.command == "completion":
            exit_code = handle_completion(args)
        sys.exit(exit_code)
    except (OSError, ValueError, RuntimeError) as e:
        error(f"Fatal error: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()
