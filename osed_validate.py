import sys
import yaml
import jsonschema
from pathlib import Path
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

DEFAULT_VERSION = "0.2.0"

def load_yaml(filepath):
  with open(filepath, "r", encoding="utf-8") as f:
    return yaml.safe_load(f)


def get_default_version() -> str:
  version_file = Path(__file__).parent / "VERSION"
  if version_file.exists():
    content = version_file.read_text().strip()
    if content:
      return content
  return DEFAULT_VERSION

def validate_file(schema_path: Path, document_path: Path) -> bool:
  if not schema_path.exists():
    print(f"❌ Schema file not found: {schema_path}")
    return False

  if not document_path.exists():
    print(f"❌ Data file not found: {document_path}")
    return False

  schema = yaml.safe_load(schema_path.read_text())
  data = yaml.safe_load(document_path.read_text())

  validator = Draft202012Validator(schema)
  errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

  if errors:
    print("❌ Validation failed:")
    for error in errors:
      location = "/".join(map(str, error.path)) or "<root>"
      print(f"  - [{location}] {error.message}")
    return False

  print("✅ Validation passed")
  return True

def main():
  if len(sys.argv) != 3:
    print(
      "Usage: python osed_validate.py <schema/osed.schema.yaml> <osed.yaml>"
      )
    sys.exit(1)

  schema_path = Path(sys.argv[1])
  document_path = Path(sys.argv[2])

  if not schema_path.exists() or not document_path.exists():
    print("❌ File not found. Please check the paths.")
    sys.exit(1)

  success = validate_file(schema_path, document_path)
  if not success:
    sys.exit(1)

if __name__ == "__main__":
    main()
