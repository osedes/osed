from pathlib import Path

import pytest

from src.python.osed_lint import lint_file

DATA_DIR = Path(__file__).parent / "data"


@pytest.mark.parametrize("filename,expected", [
    ("valid_osed.yaml", True),
    ("missing_entity.yaml", False),
    ("duplicate_entities.yaml", False),
    ("invalid_entity_names.yaml", False),
    ("reserved_entity_key.yaml", False),
    ("unknown_top_level_keys.yaml", False),
    ("misplaced_entity_descriptions.yaml", False),
    ("control_key_collisions.yaml", False),
    # Ref validation test cases
    ("v0.3.0/valid_ref_usage.yaml", True),
    ("v0.3.0/invalid_ref_usage.yaml", False),
])
def test_linting_cases(filename, expected):
  path = DATA_DIR / filename
  assert lint_file(path) is expected
