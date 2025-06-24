import yaml
import jsonschema
import sys
from pathlib import Path

def load_yaml(filepath):
  with open(filepath, 'r', encoding='utf-8') as f:
    return yaml.safe_load(f)

def validate(schema_path, document_path):
  schema = load_yaml(schema_path)
  document = load_yaml(document_path)

  try:
    jsonschema.validate(instance=document, schema=schema)
    print("✅ OSED document is valid.")
  except jsonschema.exceptions.ValidationError as e:
    print("❌ Validation failed:")
    print(f"Message: {e.message}")
    print(f"Path: {'/'.join(str(p) for p in e.absolute_path)}")
    print(f"Schema path: {'/'.join(str(p) for p in e.absolute_schema_path)}")
    sys.exit(1)

if __name__ == "__main__":
  if len(sys.argv) != 3:
    print(
      "Usage: python validate_osed.py <schema/osed.schema.yaml> <osed.yaml>"
      )
    sys.exit(1)

  schema_path = Path(sys.argv[1])
  document_path = Path(sys.argv[2])

  if not schema_path.exists() or not document_path.exists():
    print("❌ File not found. Please check the paths.")
    sys.exit(1)

  validate(schema_path, document_path)
