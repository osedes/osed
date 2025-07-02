from pathlib import Path

import pytest

from src.python.osed_validate import validate_file

DATA_DIR = Path(__file__).parent / "data"
SCHEMA_PATH = DATA_DIR / "osed.schema.yaml"


@pytest.mark.parametrize("filename", [
    "invalid_missing_entities.yaml",
    "invalid_wrong_osed_type.yaml",
    "invalid_entity_name_format.yaml",
    "invalid_entities_not_list.yaml",
    "invalid_extra_top_level_key.yaml",
    "invalid_universals_structure.yaml",
    "invalid_empty_document.yaml",
    "invalid_semver.yaml",
])
def test_invalid_osed_documents(filename):
  invalid_path = DATA_DIR / filename
  assert validate_file(SCHEMA_PATH, invalid_path) is False


def test_valid_osed_document():
  valid_file = DATA_DIR / "valid_osed.yaml"
  assert validate_file(SCHEMA_PATH, valid_file) is True


def test_valid_core_v0_3_0():
  data_file = Path(__file__).parent / "data/v0.3.0/valid_core.yaml"
  schema_file = Path(__file__).parent.parent / "schema/osed.schema.v0.3.0.yaml"
  assert validate_file(schema_file, data_file) is True


def test_valid_mongoose_v0_3_0():
  data_file = Path(__file__).parent / "data/v0.3.0/valid_mongoose.yaml"
  schema_file = Path(__file__).parent.parent / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
  assert validate_file(schema_file, data_file) is True


@pytest.mark.xfail(reason="Known limitation: validation doesn't properly fail for legacy 'items' usage")
def test_invalid_mongoose_v0_3_0():
  """Test that invalid mongoose metadata fails validation."""
  data_file = Path(__file__).parent / "data/v0.3.0/invalid_mongoose.yaml"
  schema_file = Path(__file__).parent.parent / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
  # This should fail because it uses 'items' instead of 'mongoose:items'
  assert validate_file(schema_file, data_file) is False
