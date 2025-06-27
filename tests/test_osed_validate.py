import pytest
from pathlib import Path
from osed_validate import validate_file

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
