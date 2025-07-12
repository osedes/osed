"""
Tests for OSED CLI functionality.
"""

# Standard library imports
import json
import os
import subprocess
import sys
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Third-party imports
import pytest
import yaml

# Reconfigure logger to use patched streams
# from src.python.osed_logging import set_logger, OSEDLogger

# Import functions that don't require special mocking
from src.python.osed_utils import validate_version_consistency

# Mock the dependencies before importing
with patch("src.python.osed_cli.load_yaml"), patch(
    "src.python.osed_cli.validate_file"
), patch("src.python.osed_cli.get_default_version"):
    from src.python.osed_cli import validate_command


@pytest.fixture
def acknowledged_lint_config(tmp_path):
    """Simulate a project .osed config with acknowledgements for known warnings."""
    osed_dir = tmp_path / ".osed"
    osed_dir.mkdir()
    config_path = osed_dir / "config.yaml"
    # Compute the absolute path as the linter would see it
    abs_path = str((Path.cwd() / "tests/data/valid_osed.yaml").resolve())
    config = {
        "lint": {
            "missingDriver": [
                {
                    "path": f"{abs_path}#__document__",
                    "addressed": True,
                    "acknowledged_by": "test",
                    "acknowledged_at": "2024-07-18T00:00:00Z",
                    "note": "not required for basic sanity check",
                }
            ],
            "orphanedSemanticNodes": [
                {
                    "path": f"{abs_path}#__document__",
                    "addressed": True,
                    "acknowledged_by": "test",
                    "acknowledged_at": "2024-07-18T00:00:00Z",
                    "note": "not required for basic sanity check",
                }
            ],
            "sensitiveFields": [
                {
                    "path": f"{abs_path}#entityDescription.key",
                    "addressed": True,
                    "acknowledged_by": "test",
                    "acknowledged_at": "2024-07-18T00:00:00Z",
                    "note": "not sensitive in this context",
                }
            ],
            "auditFields": [
                {
                    "path": f"{abs_path}#documentDescription",
                    "addressed": True,
                    "acknowledged_by": "test",
                    "acknowledged_at": "2024-07-18T00:00:00Z",
                    "note": "not required for basic sanity check",
                }
            ],
            # Add other kinds as needed for other tests
        }
    }
    with open(config_path, "w", encoding='utf-8') as f:
        yaml.safe_dump(config, f)
    # Set environment variable to use this as project root
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield
    os.chdir(old_cwd)


class TestCLIVersionHandling:
    """Test CLI version handling and schema version fallback."""

    def test_auto_detection_from_document(self, tmp_path):
        """Test that schema version is auto-detected from OSED document when
        not provided."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):

            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": []}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:

                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(
                    test_file
                )  # No schema_version specified

                # Check that auto-detection message was printed (INFO → stdout)
                output = mock_stdout.getvalue().strip()
                assert (
                    "ℹ️ Auto-detected schema version '0.3.0' from OSED document"
                    in output
                )
                assert result == 0  # Should pass validation

    def test_missing_osed_key_error(self, tmp_path):
        """Test that error is shown when 'osed' key is missing from document."""
        # Create a test OSED document without 'osed' key
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load:

            # Mock load_yaml to return document without 'osed' key
            mock_load.return_value = {"entities": []}

            # Capture stdout to check error message
            with patch("sys.stdout", new=StringIO()), patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file)

                # Check that error was printed (ERROR → stderr)
                err_output = mock_stderr.getvalue().strip()
                assert (
                    "❌ Missing required 'osed' key in document".strip()
                    in err_output
                )
                assert result == 1  # Should return error code

    def test_auto_detection_with_explicit_version(self, tmp_path):
        """Test that explicit schema version takes precedence over auto-detection."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):

            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": []}

            # Capture stdout to check no auto-detection message when explicit version provided
            with patch("sys.stdout", new=StringIO()) as mock_stdout, patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_version="0.2.0")

                # Check that no auto-detection message was printed (INFO → stdout)
                output = mock_stdout.getvalue().strip()
                assert "ℹ️  Auto-detected schema version" not in output
                # But should show version mismatch warning (WARNING → stderr)
                err_output = mock_stderr.getvalue().strip()
                assert (
                    "⚠️ OSED document specifies version '0.3.0' but validating against schema version '0.2.0'"
                    in err_output
                )
                assert result == 0  # Should pass validation

    def test_version_mismatch_warning(self, tmp_path):
        """Test that version mismatch warning is shown when OSED document version differs from schema version."""
        # Create a test OSED document with different version
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.2.0"
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):

            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.2.0", "entities": []}

            # Capture stdout to check warning message
            with patch("sys.stdout", new=StringIO()), patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_version="0.3.0")

                # Check that warning was printed (WARNING → stderr)
                err_output = mock_stderr.getvalue().strip()
                assert (
                    "⚠️ OSED document specifies version '0.2.0' but validating against schema version '0.3.0'"
                    in err_output
                )
                assert result == 0  # Should still pass validation

    def test_no_warning_when_versions_match(self, tmp_path):
        """Test that no warning is shown when OSED document version matches schema version."""
        # Create a test OSED document with matching version
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):

            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": []}

            # Capture stdout to check no warning message
            with patch("sys.stdout", new=StringIO()), patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_version="0.3.0")

                # Check that no warning was printed (WARNING → stderr)
                err_output = mock_stderr.getvalue().strip()
                assert "⚠️  Warning:" not in err_output
                assert result == 0  # Should pass validation

    def test_fallback_to_version_file(self, tmp_path):
        """Test that get_default_version() falls back to VERSION file."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities: []
universals:
  - email
particulars:
  - systemId
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ), patch(
            "src.python.osed_cli.get_default_version", return_value="0.3.0"
        ):

            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": []}

            # Capture stdout to check no warning message
            with patch("sys.stdout", new=StringIO()), patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(
                    test_file
                )  # No schema_version specified

                # Check that no warning was printed (versions match)
                err_output = mock_stderr.getvalue().strip()
                assert "⚠️  Warning:" not in err_output
                assert result == 0  # Should pass validation

    def test_error_handling_for_invalid_yaml(self, tmp_path):
        """Test that errors are handled gracefully when YAML is invalid."""
        # Create an invalid YAML file
        test_file = tmp_path / "test.yaml"
        test_file.write_text("invalid: yaml: content: [")

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):

            # Mock load_yaml to raise an exception
            mock_load.side_effect = Exception("Invalid YAML")

            # Capture stdout to check error handling
            with patch("sys.stdout", new=StringIO()), patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                # Must import inside patch block so logger uses patched output streams
                from src.python.osed_logging import (  # pylint: disable=import-outside-toplevel
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_version="0.3.0")

                # Check that error was handled gracefully (ERROR → stderr)
                err_output = mock_stderr.getvalue().strip()
                assert "❌ Could not read OSED document:" in err_output
                assert result == 1  # Should return error code

    def test_schema_file_not_found(self, tmp_path):
        """Test error handling when schema file doesn't exist."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities:
  - user
universals:
  - string
user:
  id: string
  name: string
"""
        )

        # Test with non-existent schema version
        result = validate_command(test_file, schema_version="999.999.999")

        assert result == 2  # Should return 2 for schema file not found


class TestCLISchemaFileOption:
    """Test the new --schema-file option functionality."""

    def test_schema_file_option_uses_custom_schema(self, tmp_path):
        """Test that --schema-file option uses the specified schema file."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities:
  - user
universals:
  - string
user:
  id: string
  name: string
"""
        )

        # Create a custom schema file
        custom_schema = tmp_path / "custom_schema.yaml"
        custom_schema.write_text(
            """
$schema: "http://json-schema.org/draft-07/schema#"
version: "0.3.0"
type: object
properties:
  osed:
    type: string
  entities:
    type: array
  universals:
    type: array
  particulars:
    type: array
required: ["osed", "entities"]
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):
            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                # Reconfigure logger to use patched streams
                from src.python.osed_logging import (
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_file=custom_schema)

                # Check that custom schema file message was printed
                output = mock_stdout.getvalue().strip()
                assert f"ℹ️ Using custom schema file: {custom_schema}" in output
                assert result == 0  # Should pass validation

    def test_schema_file_overrides_schema_version(self, tmp_path):
        """Test that --schema-file overrides --schema-version option."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities:
  - user
universals:
  - string
user:
  id: string
  name: string
"""
        )

        # Create a custom schema file
        custom_schema = tmp_path / "custom_schema.yaml"
        custom_schema.write_text(
            """
$schema: "http://json-schema.org/draft-07/schema#"
version: "0.3.0"
type: object
properties:
  osed:
    type: string
  entities:
    type: array
required: ["osed", "entities"]
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):
            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                # Reconfigure logger to use patched streams
                from src.python.osed_logging import (
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(
                    test_file,
                    schema_version="0.2.0",  # This should be ignored
                    schema_file=custom_schema,
                )

                # Check that custom schema file message was printed (not auto-detection)
                output = mock_stdout.getvalue().strip()
                assert f"ℹ️ Using custom schema file: {custom_schema}" in output
                assert "ℹ️ Auto-detected schema version" not in output
                assert "ℹ️ Using specified schema version" not in output
                assert result == 0  # Should pass validation

    def test_schema_file_overrides_driver(self, tmp_path):
        """Test that --schema-file overrides --driver option."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities:
  - user
universals:
  - string
user:
  id: string
  name: string
"""
        )

        # Create a custom schema file
        custom_schema = tmp_path / "custom_schema.yaml"
        custom_schema.write_text(
            """
$schema: "http://json-schema.org/draft-07/schema#"
version: "0.3.0"
type: object
properties:
  osed:
    type: string
  entities:
    type: array
required: ["osed", "entities"]
"""
        )

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):
            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}

            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                # Reconfigure logger to use patched streams
                from src.python.osed_logging import (
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(
                    test_file,
                    driver="mongoose-mongodb",  # This should be ignored
                    schema_file=custom_schema,
                )

                # Check that custom schema file message was printed (not driver message)
                output = mock_stdout.getvalue().strip()
                assert f"ℹ️ Using custom schema file: {custom_schema}" in output
                assert "ℹ️ Using driver schema" not in output
                assert result == 0  # Should pass validation

    def test_schema_file_not_found_error(self, tmp_path):
        """Test error handling when custom schema file doesn't exist."""
        # Create a test OSED document
        test_file = tmp_path / "test.yaml"
        test_file.write_text(
            """
osed: "0.3.0"
entities:
  - user
universals:
  - string
user:
  id: string
  name: string
"""
        )

        # Create a non-existent schema file path
        non_existent_schema = tmp_path / "non_existent_schema.yaml"

        # Mock the dependencies
        with patch("src.python.osed_cli.load_yaml") as mock_load:
            # Mock load_yaml to return our test document
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}

            with patch("sys.stdout", new=StringIO()) as mock_stdout, patch(
                "sys.stderr", new=StringIO()
            ) as mock_stderr:
                # Reconfigure logger to use patched streams
                from src.python.osed_logging import (
                    set_logger,
                    OSEDLogger,
                )

                set_logger(OSEDLogger())
                result = validate_command(
                    test_file, schema_file=non_existent_schema
                )

                # Check that info message was printed to stdout
                stdout_output = mock_stdout.getvalue().strip()
                assert (
                    f"ℹ️ Using custom schema file: {non_existent_schema}"
                    in stdout_output
                )

                # Check that error was printed to stderr
                stderr_output = mock_stderr.getvalue().strip()
                assert (
                    f"❌ Schema file not found: {non_existent_schema}"
                    in stderr_output
                )
                assert result == 2  # Should return 2 for schema file not found

    def test_schema_file_help_text(self):
        """Test that --schema-file help text is descriptive."""
        # Mock the main function to avoid actual execution
        with patch("sys.argv", ["osed", "validate", "--help"]):
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                try:
                    # Import and run main with mocked dependencies
                    with patch("src.python.osed_cli.validate_command"), patch(
                        "src.python.osed_cli.lint_command"
                    ), patch("src.python.osed_cli.generate_command"):
                        from src.python.osed_cli import main

                        main()
                except SystemExit:
                    pass
                output = mock_stdout.getvalue().strip()
                assert "--schema-file" in output
                assert "overrides" in output
                assert "--schema-version" in output
                assert "--driver" in output


class TestCLIVersionConsistency:
    """Test version consistency checking functionality."""

    def test_version_consistency_check(self):
        """Test that version consistency check works correctly."""
        # Change to the project root directory for the test
        project_root = Path(__file__).parent.parent
        original_cwd = Path.cwd()

        try:
            # Change to project root where VERSION file exists
            os.chdir(project_root)

            is_consistent, issues = validate_version_consistency()

            # The version consistency check should find legitimate version differences
            # between older schema files and the current VERSION file
            # This is expected behavior, so we should not assert consistency
            # Instead, we should verify that the check runs without errors
            assert isinstance(is_consistent, bool), "Should return boolean"
            assert isinstance(issues, list), "Should return list of issues"

            # Verify that the issues found are legitimate
            expected_issues = [
                "Schema file osed.schema.v0.1.0.yaml version 0.1.0 != source version 0.3.0",
                "Schema file osed.schema.v0.1.0.yaml $id does not contain version 0.3.0",
                "Schema file osed.schema.v0.2.0.yaml version 0.2.0 != source version 0.3.0",
                "Schema file osed.schema.v0.2.0.yaml $id does not contain version 0.3.0",
            ]

            for expected_issue in expected_issues:
                assert any(
                    expected_issue in issue for issue in issues
                ), f"Expected issue not found: {expected_issue}"

        finally:
            # Restore original directory
            os.chdir(original_cwd)

    def test_cli_check_versions_command(self):
        """Test CLI check-versions command."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.python.osed_cli",
                "check-versions",
            ],
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent.parent,
        )

        # The CLI should return error code 1 when inconsistencies are found
        assert (
            result.returncode == 1
        ), f"Version check should find inconsistencies: {result.stdout}"
        assert "Version inconsistencies found:" in result.stderr
        assert (
            "Schema file osed.schema.v0.1.0.yaml version 0.1.0 != source version 0.3.0"
            in result.stderr
        )


class TestCLIArgumentParsing:
    """Test CLI argument parsing for schema version flag."""

    def test_schema_version_flag_help(self):
        """Test that --schema-version help text is descriptive."""
        # Mock the main function to avoid actual execution
        with patch("sys.argv", ["osed", "validate", "--help"]):
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                try:
                    # Import and run main with mocked dependencies
                    with patch("src.python.osed_cli.validate_command"), patch(
                        "src.python.osed_cli.lint_command"
                    ), patch("src.python.osed_cli.generate_command"):
                        from src.python.osed_cli import main

                        main()
                except SystemExit:
                    pass
                output = mock_stdout.getvalue().strip()
                assert "--schema-version" in output
                assert "VERSION file" in output


class TestCLIJsonOutput:
    """Test CLI --output-format json output."""

    def test_validate_json_output(
        self, tmp_path
    ):  # pylint: disable=unused-argument
        """Test validate command outputs valid NDJSON."""
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.python.osed_cli",
                "validate",
                "--file",
                "tests/data/valid_osed.yaml",
                "--schema-version",
                "0.2.0",
                "--expected-schema-version",
                "0.2.0",
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            output_jsons = [json.loads(line) for line in lines]
        except json.JSONDecodeError:
            assert False, f"Output is not valid NDJSON: {result.stdout}"
        assert len(output_jsons) > 0
        assert any(
            obj.get("severity") == "info"
            and "Validation passed" in obj.get("message", "")
            for obj in output_jsons
        )
        assert all(isinstance(obj, dict) for obj in output_jsons)

    def test_lint_json_output(
        self, acknowledged_lint_config, tmp_path
    ):  # pylint: disable=unused-argument
        """Test lint command outputs valid NDJSON with warnings acknowledged."""
        project_root = os.path.dirname(os.path.dirname(__file__))
        test_file_path = os.path.join(
            project_root, "tests/data/valid_osed.yaml"
        )
        result = subprocess.run(
            [
                "osed",
                "lint",
                "run",
                "--file",
                test_file_path,
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=tmp_path,
        )
        try:
            lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            output_jsons = [json.loads(line) for line in lines]
        except json.JSONDecodeError:
            assert False, f"Lint output is not valid NDJSON: {result.stdout}"
        assert len(output_jsons) > 0
        assert all(isinstance(obj, dict) for obj in output_jsons)

    @pytest.mark.xfail(
        reason="Support for JSON/NDJSON output for generate command needs to be decided."
    )
    def test_generate_json_output(
        self, tmp_path
    ):  # pylint: disable=unused-argument
        """Test generate command outputs valid NDJSON.
        NOTE: We use an inline sample doc here instead of 'valid_osed.yaml' to ensure the required 'driver' key is present and avoid modifying static test data.
        """
        # Inline sample OSED doc with driver - more complete to pass linting
        sample_doc = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string",
                "profile": {"ref": "profile"},  # Add a relationship
                "audit": {"created_at": "string", "updated_at": "string"},
            },
            "driver": "mongoose",
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(sample_doc, f)
            temp_file = f.name
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.python.osed_cli",
                "generate",
                "--file",
                temp_file,
                "--target",
                "mongoose",
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            output_jsons = [json.loads(line) for line in lines]
        except json.JSONDecodeError:
            assert (
                False
            ), f"Generate output is not valid NDJSON: {result.stdout}"
        assert len(output_jsons) > 0
        assert all(isinstance(obj, dict) for obj in output_jsons)

    def test_diff_json_output(
        self, tmp_path
    ):  # pylint: disable=unused-argument
        """Test diff command outputs valid NDJSON."""
        file1 = "tests/data/valid_osed.yaml"
        file2 = "tests/data/valid_osed.yaml"
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.python.osed_cli",
                "diff",
                file1,
                file2,
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        try:
            lines = [
                line
                for line in result.stdout.strip().split("\n")
                if line.strip()
            ]
            output_jsons = [json.loads(line) for line in lines]
        except json.JSONDecodeError:
            assert False, f"Diff output is not valid NDJSON: {result.stdout}"
        assert len(output_jsons) > 0
        assert all(isinstance(obj, dict) for obj in output_jsons)


class TestCLIInformativeLogging:
    """Test informative logging for defaults in validate_command."""

    def test_default_file_logging(
        self, tmp_path
    ):  # pylint: disable=unused-argument
        """Test that using the default file logs the correct message."""
        test_file = Path("osed.yaml")
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                from src.python.osed_logging import set_logger, OSEDLogger

                set_logger(OSEDLogger())
                result = validate_command(test_file)
                output = mock_stdout.getvalue().strip()
                assert "Using default OSED file: osed.yaml" in output
                assert result == 0

    def test_default_schema_version_logging(self, tmp_path):
        """Test that using the default schema version logs the correct message."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("osed: '0.3.0'\nentities: [user]\n")
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ), patch(
            "src.python.osed_cli.get_default_version", return_value="0.3.0"
        ):
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                from src.python.osed_logging import set_logger, OSEDLogger

                set_logger(OSEDLogger())
                result = validate_command(test_file, schema_version="0.3.0")
                output = mock_stdout.getvalue().strip()
                assert "Using default schema version: 0.3.0" in output
                assert result == 0

    def test_default_input_dir_logging(self, tmp_path):
        """Test that using the default input directory logs the correct message."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("osed: '0.3.0'\nentities: [user]\n")
        with patch("src.python.osed_cli.load_yaml") as mock_load, patch(
            "src.python.osed_cli.validate_file", return_value=True
        ):
            mock_load.return_value = {"osed": "0.3.0", "entities": ["user"]}
            with patch("sys.stdout", new=StringIO()) as mock_stdout:
                from src.python.osed_logging import set_logger, OSEDLogger

                set_logger(OSEDLogger())
                result = validate_command(test_file, input_dir=None)
                output = mock_stdout.getvalue().strip()
                assert "Using default input directory:" in output
                assert result == 0
