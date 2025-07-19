"""
Tests for OSED linting functionality.
"""

from pathlib import Path

import pytest

from src.python.osed_lint import lint_file
import io
from unittest.mock import patch
from src.python.osed_logging import set_logger, OSEDLogger

DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("valid_osed.yaml", True),
        ("missing_entity.yaml", True),
        ("duplicate_entities.yaml", False),
        ("invalid_entity_names.yaml", False),
        ("reserved_entity_key.yaml", False),
        ("unknown_top_level_keys.yaml", False),
        ("misplaced_entity_descriptions.yaml", False),
        ("control_key_collisions.yaml", False),
        # Ref validation test cases
        ("v0.3.0/valid_ref_usage.yaml", True),
        ("v0.3.0/invalid_ref_usage.yaml", False),
        # SemanticNode validation test cases
        (
            "v0.3.0/semantic_node_validation_test.yaml",
            False,
        ),  # Should fail - contains invalid semanticNode structures
        (
            "v0.3.0/valid_semantic_node_structure.yaml",
            True,
        ),  # Should pass - contains valid semanticNode structures
        # New enhanced linting test cases
        (
            "v0.3.0/cyclic_references.yaml",
            False,
        ),  # Should fail - contains cyclic references
        (
            "v0.3.0/sensitive_fields.yaml",
            False,
        ),  # Should fail - contains sensitive fields
        (
            "v0.3.0/naming_conventions.yaml",
            False,
        ),  # Should fail - inconsistent naming
    ],
)
def test_linting_cases(filename, expected):
    """Test various linting scenarios."""
    path = DATA_DIR / filename
    assert lint_file(path)[0] is expected


class TestLintLogging:
    """Test severity-based logging output in osed_lint.py."""

    def test_logging_for_duplicate_entities(self, tmp_path):
        # Duplicate entities should trigger an error
        lint_file_content = """
entities:
  - user
  - user
user:
  id: systemId
"""
        lint_file_path = tmp_path / "duplicate_entities.yaml"
        lint_file_path.write_text(lint_file_content)
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            from src.python.osed_lint import lint_file as lint_file_local

            result, _ = lint_file_local(lint_file_path)
            err_output = fake_stderr.getvalue()
            assert result is False
            assert (
                "Duplicate entities" in err_output
                or "duplicate" in err_output.lower()
            )

    def test_logging_for_cyclic_references(self, tmp_path):
        # Cyclic references should trigger a warning
        lint_file_content = """
entities:
  - a
  - b
a:
  ref: b
b:
  ref: a
"""
        lint_file_path = tmp_path / "cyclic_references.yaml"
        lint_file_path.write_text(lint_file_content)
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            from src.python.osed_lint import lint_file as lint_file_local

            result, _ = lint_file_local(lint_file_path)
            warn_output = fake_stderr.getvalue()
            assert (
                result is False or result is True
            )  # We only care about logging
            assert (
                "cyclic reference" in warn_output.lower()
                or "cycle" in warn_output.lower()
            )
