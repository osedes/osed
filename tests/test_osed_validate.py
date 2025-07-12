"""
Tests for OSED validation functionality.
"""

import io
from unittest.mock import patch
from pathlib import Path
import pytest

from src.python.osed_validate import validate_file
from src.python.osed_logging import set_logger, OSEDLogger

DATA_DIR = Path(__file__).parent / "data"
SCHEMA_PATH = DATA_DIR / "osed.schema.yaml"


@pytest.mark.parametrize(
    "filename",
    [
        "invalid_missing_entities.yaml",
        "invalid_wrong_osed_type.yaml",
        "invalid_entity_name_format.yaml",
        "invalid_entities_not_list.yaml",
        "invalid_extra_top_level_key.yaml",
        "invalid_universals_structure.yaml",
        "invalid_empty_document.yaml",
        "invalid_semver.yaml",
    ],
)
def test_invalid_osed_documents(filename):
    """Test that invalid OSED documents fail validation."""
    invalid_path = DATA_DIR / filename
    assert validate_file(SCHEMA_PATH, invalid_path) is False


def test_valid_osed_document():
    """Test that valid OSED documents pass validation."""
    valid_file = DATA_DIR / "valid_osed.yaml"
    assert validate_file(SCHEMA_PATH, valid_file) is True


def test_valid_core_v0_3_0():
    """Test validation of core v0.3.0 schema."""
    data_file = Path(__file__).parent / "data/v0.3.0/valid_core.yaml"
    schema_file = (
        Path(__file__).parent.parent / "schema/osed.schema.v0.3.0.yaml"
    )
    assert (
        validate_file(schema_file, data_file, expected_version="0.3.0") is True
    )


def test_valid_mongoose_v0_3_0():
    """Test validation of mongoose driver v0.3.0 schema."""
    data_file = Path(__file__).parent / "data/v0.3.0/valid_mongoose.yaml"
    schema_file = (
        Path(__file__).parent.parent
        / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
    )
    assert (
        validate_file(schema_file, data_file, expected_version="0.3.0") is True
    )


def test_invalid_mongoose_driver_v0_3_0():
    """Test that invalid mongoose driver metadata fails validation."""
    data_file = Path(__file__).parent / "data/v0.3.0/invalid_mongoose.yaml"
    schema_file = (
        Path(__file__).parent.parent
        / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
    )
    # This should fail because it uses invalid driver-based format:
    # - using 'mongoose:' prefix in driver-based approach
    # - using invalid type that's not in the enum
    # - mixing 'of' and 'items' with different values
    # - using 'unique' with non-boolean value
    assert validate_file(schema_file, data_file) is False


class TestValidateLogging:
    """Test severity-based logging output in osed_validate.py."""

    def test_logging_for_invalid_yaml(self, tmp_path):
        """Test logging for invalid YAML in OSED document."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            "$schema: 'http://json-schema.org/draft-07/schema#'\ntype: object\nversion: 1.0.0\n"
        )
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, invalid_file)
            log_output = fake_stderr.getvalue()
            assert result is False
            assert "Failed to load or parse OSED document" in log_output
            assert (
                "Check the data structure and types against the schema."
                not in log_output
            )  # Only file loading error expected

    def test_logging_for_version_mismatch(self, tmp_path):
        """Test logging for version mismatch between schema and data."""
        # Schema version is 1.0.0, data version is 2.0.0 (major mismatch)
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            "$schema: 'http://json-schema.org/draft-07/schema#'\nversion: 2.0.0\ntype: object\n"
        )
        data_file = tmp_path / "data.yaml"
        data_file.write_text("version: 1.0.0\nentities: []\n")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            err_output = fake_stderr.getvalue()
            assert (
                result is True or result is False
            )  # We only care about logging here
            assert "Schema major version mismatch" in err_output
            assert "Update your schema to version" in err_output


class TestValidateFeedback:
    """Test enhanced validation feedback and error handling."""

    def test_schema_file_load_failure(self, tmp_path):
        """Test error when schema file cannot be loaded (invalid YAML)."""
        schema_file = tmp_path / "bad_schema.yaml"
        schema_file.write_text("not: [valid: yaml:]")
        data_file = tmp_path / "data.yaml"
        data_file.write_text("osed: '1.0.0'\nentities: []\n")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            err_output = fake_stderr.getvalue()
            assert result is False
            assert "Failed to load schema file" in err_output
            assert (
                "Check that the schema file exists and is valid YAML/JSON."
                in err_output
            )

    def test_osed_yaml_parse_failure(self, tmp_path):
        """Test error when OSED document cannot be parsed (invalid YAML)."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            "$schema: 'http://json-schema.org/draft-07/schema#'\ntype: object\nversion: 1.0.0\n"
        )
        data_file = tmp_path / "bad_data.yaml"
        data_file.write_text("not: [valid: yaml:")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            err_output = fake_stderr.getvalue()
            assert result is False
            assert "Failed to load or parse OSED document" in err_output
            assert "Check that the OSED document is valid YAML." in err_output

    def test_preprocess_failure(self, tmp_path):
        """Test error when preprocessing fails (simulate with patch)."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            "$schema: 'http://json-schema.org/draft-07/schema#'\ntype: object\nversion: 1.0.0\n"
        )
        data_file = tmp_path / "data.yaml"
        data_file.write_text("osed: '1.0.0'\nentities: []\n")
        with patch(
            "src.python.osed_validate.preprocess_osed_data",
            side_effect=Exception("bad preprocess"),
        ), patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            err_output = fake_stderr.getvalue()
            assert result is False
            assert "Failed to preprocess OSED data" in err_output
            assert (
                "Check the structure of your OSED document for invalid types or values."
                in err_output
            )

    def test_schema_validation_failure(self, tmp_path):
        """Test error when schema validation fails (invalid data)."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
$schema: 'http://json-schema.org/draft-07/schema#'
type: object
version: 1.0.0
properties:
  osed:
    type: string
  entities:
    type: array
required: [osed, entities]
"""
        )
        data_file = tmp_path / "data.yaml"
        data_file.write_text("osed: 123\nentities: 'notalist'\n")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            err_output = fake_stderr.getvalue()
            assert result is False
            assert "Validation failed: See details below." in err_output
            assert (
                "Field: osed" in err_output or "Field: entities" in err_output
            )
            assert "Error:" in err_output

    def test_single_validation_passed_message(self, tmp_path):
        """Test that only one 'Validation passed' message is shown on success."""
        schema_file = tmp_path / "schema.yaml"
        schema_file.write_text(
            """
$schema: 'http://json-schema.org/draft-07/schema#'
type: object
version: 1.0.0
properties:
  osed:
    type: string
  entities:
    type: array
required: [osed, entities]
"""
        )
        data_file = tmp_path / "data.yaml"
        data_file.write_text("osed: '1.0.0'\nentities: []\n")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            result = validate_file(schema_file, data_file)
            out = fake_stdout.getvalue()
            assert result is True
            # Only one 'Validation passed' message
            assert out.count("Validation passed") == 1
