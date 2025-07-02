import argparse
from pathlib import Path
import sys
from .osed_utils import get_arg_parser, resolve_schema_and_data_paths, get_default_version
import yaml
from referencing import Registry, Resource
from jsonschema import Draft202012Validator

def expand_list_description(value):
  if (
      isinstance(value, dict)
      and value.get("type") in ("list", "array")
      and "items" in value
  ):
    return value["items"]
  return value

def expand_map_description(value):
  if (
      isinstance(value, dict)
      and value.get("type") == "map"
      and "value" in value
  ):
    return value["value"]
  return value

def preprocess_osed_data(data):
  if not isinstance(data, dict):
    return data
  processed = {}
  for k, v in data.items():
    if isinstance(v, dict):
      processed[k] = {
          sub_k: preprocess_osed_data(
              expand_map_description(expand_list_description(sub_v))
          )
          for sub_k, sub_v in v.items()
      }
    elif isinstance(v, list):
      processed[k] = [
          preprocess_osed_data(
              expand_map_description(expand_list_description(item))
          )
          for item in v
      ]
    else:
      processed[k] = expand_map_description(expand_list_description(v))
  return processed

def load_schema_with_referencing(schema_path: Path):
  """
  Load a schema and build a referencing.Registry for cross-file $ref support.
  Returns the root schema and the registry.
  """
  schema_text = schema_path.read_text()
  schema = yaml.safe_load(schema_text)
  base_uri = schema_path.resolve().as_uri()
  resources = {base_uri: Resource.from_contents(schema)}
  loaded_paths = {str(schema_path.resolve())}

  def collect_refs(obj, current_path: Path):
    if isinstance(obj, dict):
      for k, v in obj.items():
        if k == "$ref" and isinstance(v, str):
          if v.startswith("./") or v.startswith("../"):
            ref_path = (
                current_path.parent / v.split("#")[0]
            ).resolve()
            ref_uri = ref_path.as_uri()
            if (
                str(ref_path) not in loaded_paths
                and ref_path.exists()
            ):
              ref_schema = yaml.safe_load(ref_path.read_text())
              resources[ref_uri] = Resource.from_contents(
                  ref_schema
              )
              loaded_paths.add(str(ref_path))
              collect_refs(ref_schema, ref_path)
        else:
          collect_refs(v, current_path)
    elif isinstance(obj, list):
      for item in obj:
        collect_refs(item, current_path)
  collect_refs(schema, schema_path)
  registry = Registry(resources=resources)
  return schema, registry

def validate_file(schema_path: Path, data_path: Path) -> bool:
  try:
    schema, registry = load_schema_with_referencing(schema_path)
    data = yaml.safe_load(data_path.read_text())
  except Exception as e:
    print(f"❌ Error loading files: {e}")
    return False
  data = preprocess_osed_data(data)
  try:
    validator = Draft202012Validator(schema, registry=registry)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
      print("❌ Validation failed:")
      for error in errors:
        location = "/".join(map(str, error.path)) or "<root>"
        print(f"  - [{location}] {error.message}")
      return False
    print("✅ Validation passed")
    return True
  except Exception as e:
    print(f"❌ Validation error: {e}")
    return False

def main():
    parser = get_arg_parser()
    args = parser.parse_args()
    base_path = Path(__file__).parent / "schema"
    schema_path, data_path = resolve_schema_and_data_paths(args, base_path)

    print(f"🔍 Validating '{data_path.name}' against '{schema_path.name}'")
    success = validate_file(schema_path, data_path)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
  main()
