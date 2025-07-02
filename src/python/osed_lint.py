from pathlib import Path
import re
import sys

from .osed_utils import load_yaml, get_arg_parser, resolve_schema_and_data_paths

CONTROL_KEYS = {
    "osed",
    "entities",
    "universals",
    "particulars",
    "driver",
}
VALID_ENTITY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")

# Mongoose-specific constants for driver-aware validation
VALID_MONGOOSE_TYPES = {
    "String", "string", "Number", "number", "Date", "date", "Buffer", "buffer",
    "Boolean", "boolean", "Mixed", "mixed", "ObjectId", "objectid", "Array", "array",
    "List", "list", "Decimal128", "decimal128", "Map", "map", "Schema", "schema",
    "UUID", "uuid", "BigInt", "bigint", "Double", "double", "Int32", "int32"
}

VALID_MONGOOSE_ITEM_TYPES = {
    "String", "string", "Number", "number", "Date", "date", "Buffer", "buffer",
    "Boolean", "boolean", "Mixed", "mixed", "ObjectId", "objectid", "Array", "array",
    "List", "list", "Decimal128", "decimal128", "Map", "map", "Schema", "schema",
    "UUID", "uuid", "BigInt", "bigint", "Double", "double", "Int32", "int32"
}

MONGOOSE_DRIVERS = {"mongoose", "mongoose-mongo", "mongoose-mongodb"}


def extract_entity_references(document):
    """
    Extracts all used entity references:
    - Collects all top-level keys (excluding control keys) as used entities
    - Collects all leaf node values (strings that are not property names) as used entities
    - Does NOT collect property names (non-top-level keys)
    """
    used = set()
    control_keys = set(CONTROL_KEYS)
    property_names = set()

    # Collect all property names (keys in entity descriptions)
    def collect_property_names(node):
        if isinstance(node, dict):
            for k, v in node.items():
                property_names.add(k)
                collect_property_names(v)
        elif isinstance(node, list):
            for item in node:
                collect_property_names(item)
    for k, v in document.items():
        if k not in control_keys:
            collect_property_names(v)

    # Add top-level keys (excluding control keys) as used entities
    for k in document:
        if k not in control_keys:
            used.add(k)

    # Collect all leaf node values (strings that are not property names)
    def collect_leaf_values(node):
        if isinstance(node, dict):
            for v in node.values():
                collect_leaf_values(v)
        elif isinstance(node, list):
            for item in node:
                collect_leaf_values(item)
        elif isinstance(node, str):
            if node not in property_names:
                used.add(node)

    for k, v in document.items():
        if k not in control_keys:
            collect_leaf_values(v)

    return used


def extract_all_leaf_strings(node):
  leaves = set()

  def recurse(n):
    if isinstance(n, str):
      leaves.add(n)
    elif isinstance(n, list):
      for item in n:
        recurse(item)
    elif isinstance(n, dict):
      for v in n.values():
        recurse(v)

  recurse(node)
  return leaves


def list_missing_entities(document):
  declared = set(document.get("entities", []))

  for key in ["universals", "particulars"]:
    for node in document.get(key, []):
      declared.update(extract_all_leaf_strings(node))

  used = extract_entity_references(document)
  missing = used - declared

  if missing:
    print("\u26a0\ufe0f  Undeclared but used entities:")
    for entity in sorted(missing):
      print(f"  - {entity}")
    return False
  else:
    print("\u2705 All used entities are declared.")
    return True


def list_unused_entities(document):
  declared = set(document.get("entities", []))
  used = extract_entity_references(document)
  unused = declared - used

  if unused:
    print("\u26a0\ufe0f  Declared but unused entities:")
    for entity in sorted(unused):
      print(f"  - {entity}")
    return False
  else:
    print("\u2705 All declared entities are used.")
    return True


def check_required_keys(document):
  missing = [key for key in ["osed", "entities"] if key not in document]
  if missing:
    print(f"\u274c Missing required top-level keys: {', '.join(missing)}")
    return False
  print("\u2705 All required keys are present.")
  return True


def check_invalid_entity_names(document):
  invalid = [
      name for name in document.get("entities", [])
      if not VALID_ENTITY_PATTERN.match(name)
  ]
  if invalid:
    print("\u274c Invalid entity names:")
    for name in invalid:
      print(f"  - {name}")
    return False
  else:
    print("\u2705 All entity names are valid.")
    return True


def check_duplicate_entities(document):
  seen = set()
  duplicates = set()

  def check_and_add(name):
    if name in seen:
      duplicates.add(name)
    else:
      seen.add(name)

  def walk_group(group):
    if isinstance(group, str):
      check_and_add(group)
    elif isinstance(group, dict):
      for subgroup in group.values():
        walk_group(subgroup)
    elif isinstance(group, list):
      for item in group:
        walk_group(item)

  for name in document.get("entities", []):
    check_and_add(name)

  for section in ["universals", "particulars"]:
    for group in document.get(section, []):
      walk_group(group)

  if duplicates:
    print("\u274c Duplicate entity names across entities/universals/particulars:")
    for name in sorted(duplicates):
      print(f"  - {name}")
    return False
  else:
    print("\u2705 No duplicate entities across entities/universals/particulars.")
    return True


def check_reserved_entity_as_key(document):
  reserved_map = {}

  def walk_group(group, section, group_path):
    for item in group:
      if isinstance(item, str):
        reserved_map[item] = (section, group_path)
      elif isinstance(item, dict):
        for sub_group_name, sub_items in item.items():
          walk_group(sub_items, section, f"{group_path}.{sub_group_name}")

  for section in ["universals", "particulars"]:
    for group in document.get(section, []):
      if isinstance(group, dict):
        for group_name, items in group.items():
          walk_group(items, section, group_name)

  misused = [key for key in document if key in reserved_map]

  if misused:
    print("\u274c Top-level keys reuse reserved universal/particular names:")
    for key in sorted(misused):
      section, group_path = reserved_map[key]
      print(f"  - {key} (from {section}.{group_path})")
    return False
  else:
    print("\u2705 No reserved names reused as top-level keys.")
    return True


def check_misplaced_entity_descriptions(document):
  declared_entities = set(document.get("entities", []))
  misplaced = []

  def walk(node, path):
    if isinstance(node, dict):
      for k, v in node.items():
        if isinstance(v, str) and k in declared_entities:
          misplaced.append((k, path))
        walk(v, path + [k])
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        walk(item, path + [str(idx)])

  for section in ["universals", "particulars"]:
    for i, group in enumerate(document.get(section, [])):
      group_path = [section, str(i)]
      walk(group, group_path)

  if misplaced:
    print("\u274c Misplaced entity descriptions:")
    for key, path in misplaced:
      print(f"  - {key} (found at {'.'.join(path)})")
    return False
  else:
    print("\u2705 No misplaced entity descriptions.")
    return True


def check_collisions_with_control_keys(document):
  declared = set(document.get("entities", []))

  for section in ["universals", "particulars"]:
    for node in document.get(section, []):
      declared.update(extract_all_leaf_strings(node))

  collisions = declared & CONTROL_KEYS
  if collisions:
    print("\u26a0\ufe0f  Entity names colliding with reserved control keys:")
    for name in sorted(collisions):
      print(f"  - {name}")
    return False
  else:
    print("\u2705 No entity names conflict with reserved control keys.")
    return True


def check_unknown_top_level_keys(document):
  known = set(CONTROL_KEYS)
  known.update(document.get("entities", []))
  unknown = [key for key in document if key not in known]
  if unknown:
    print("\u274c Unknown top-level keys found:")
    for key in sorted(unknown):
      print(f"  - {key}")
    return False
  else:
    print("\u2705 No unknown top-level keys.")
    return True


def check_driver_validation(document):
  """Validate that driver is set and is a valid value."""
  driver = document.get("driver")
  if not driver:
    print("\u26a0\ufe0f  No driver specified. Driver-specific validation will be skipped.")
    return True

  if driver not in MONGOOSE_DRIVERS:
    print(f"\u274c Invalid driver '{driver}'. Valid drivers: {', '.join(sorted(MONGOOSE_DRIVERS))}")
    return False

  print(f"\u2705 Driver '{driver}' is valid.")
  return True


def check_mongoose_type_validation(document):
  """Validate that type values are valid Mongoose types when driver is mongoose."""
  driver = document.get("driver")
  if driver not in MONGOOSE_DRIVERS:
    return True  # Skip if not a Mongoose driver

  invalid_types = []

  def check_type_values(node, path):
    if isinstance(node, dict):
      for key, value in node.items():
        if key == "type":
          if value not in VALID_MONGOOSE_TYPES:
            invalid_types.append((value, path))
        elif isinstance(value, (dict, list)):
          check_type_values(value, path + [key])
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        if isinstance(item, (dict, list)):
          check_type_values(item, path + [str(idx)])

  # Walk through all entities and their properties
  for entity_name, entity_data in document.items():
    if entity_name not in CONTROL_KEYS and isinstance(entity_data, dict):
      for prop, value in entity_data.items():
        if isinstance(value, dict):
          check_type_values(value, [entity_name, prop])
        elif isinstance(value, list) and len(value) == 1:
          # Handle array shorthand [type]
          item_type = value[0]
          if item_type not in VALID_MONGOOSE_TYPES:
            invalid_types.append((item_type, [entity_name, prop]))

  if invalid_types:
    print("\u274c Invalid type values found:")
    for invalid_type, path in invalid_types:
      print(f"  - '{invalid_type}' (at {'.'.join(path)})")
      print(f"    Valid types: {', '.join(sorted(VALID_MONGOOSE_TYPES))}")
    return False
  else:
    print("\u2705 All type values are valid Mongoose types.")
    return True


def check_mongoose_required_fields(document):
  """Validate that required fields are present based on type when driver is mongoose."""
  driver = document.get("driver")
  if driver not in MONGOOSE_DRIVERS:
    return True  # Skip if not a Mongoose driver

  missing_required = []

  def check_required_metadata(node, path):
    if isinstance(node, dict):
      # If 'ref' is present, require it to be non-empty
      if "ref" in node and not node["ref"]:
        missing_required.append(("ref", path, f"'ref' is required when present"))
      field_type = node.get("type")
      if field_type:
        # Check required fields based on type
        if field_type in ["Array", "array", "List", "list"]:
          if "of" not in node and "items" not in node:
            missing_required.append(("of/items", path, f"required for type '{field_type}'"))
        elif field_type in ["Map", "map"]:
          if "of" not in node:
            missing_required.append(("of", path, f"required for type '{field_type}'"))
      # Recurse into all values (properties) of the dict
      for key, value in node.items():
        if isinstance(value, (dict, list)):
          check_required_metadata(value, path + [key])
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        if isinstance(item, (dict, list)):
          check_required_metadata(item, path + [str(idx)])

  # Walk through all entities and their properties
  for entity_name, entity_data in document.items():
    if entity_name not in CONTROL_KEYS and isinstance(entity_data, dict):
      for prop, value in entity_data.items():
        if isinstance(value, dict):
          check_required_metadata(value, [entity_name, prop])

  if missing_required:
    print("\u274c Missing required fields:")
    for field, path, reason in missing_required:
      print(f"  - {field} (at {'.'.join(path)}) - {reason}")
    return False
  else:
    print("\u2705 All required fields are present.")
    return True


def check_mongoose_item_type_validation(document):
  """Validate that of/items values are valid Mongoose types or declared entities when driver is mongoose."""
  driver = document.get("driver")
  if driver not in MONGOOSE_DRIVERS:
    return True  # Skip if not a Mongoose driver

  invalid_items = []
  invalid_values = []
  info_embedded = []
  declared_entities = set(document.get("entities", []))

  def check_item_types(node, path):
    if isinstance(node, dict):
      for key in ["of", "items"]:
        if key in node:
          value = node[key]
          if value in declared_entities:
            info_embedded.append((value, path + [key]))
          elif value not in VALID_MONGOOSE_ITEM_TYPES:
            if key == "of":
              invalid_items.append((value, path + [key]))
            else:
              invalid_values.append((value, path + [key]))
      for key, val in node.items():
        if isinstance(val, (dict, list)):
          check_item_types(val, path + [key])
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        if isinstance(item, (dict, list)):
          check_item_types(item, path + [str(idx)])

  for entity_name, entity_data in document.items():
    if entity_name not in CONTROL_KEYS and isinstance(entity_data, dict):
      for prop, value in entity_data.items():
        if isinstance(value, dict):
          check_item_types(value, [entity_name, prop])

  if info_embedded:
    for value, path in info_embedded:
      print(f"ℹ️  Embedding entity '{value}' as a sub-document at {'.'.join(path)}.")
  if invalid_items or invalid_values:
    print("\u274c Invalid of/items values detected:")
    for value, path in invalid_items:
      print(f"  - of: '{value}' (at {'.'.join(path)}) | Valid: {', '.join(sorted(VALID_MONGOOSE_ITEM_TYPES))} or declared entity")
    for value, path in invalid_values:
      print(f"  - items: '{value}' (at {'.'.join(path)}) | Valid: {', '.join(sorted(VALID_MONGOOSE_ITEM_TYPES))} or declared entity")
    return False
  else:
    print("\u2705 All of/items values are valid.")
    return True


def check_mongoose_ref_validation(document):
  """Validate that ref values reference valid entities when driver is mongoose."""
  driver = document.get("driver")
  if driver not in MONGOOSE_DRIVERS:
    return True  # Skip if not a Mongoose driver

  invalid_refs = []
  info_reference = []
  invalid_ref_types = []
  declared_entities = set(document.get("entities", []))

  def check_ref_values(node, path):
    if isinstance(node, dict):
      if "ref" in node:
        value = node["ref"]
        field_type = node.get("type")

        # Check if ref is used with valid type
        if field_type and field_type not in ["ObjectId", "objectid"]:
          # Check if it's an array of objectid
          if field_type in ["Array", "array", "List", "list"]:
            items_type = node.get("of") or node.get("items")
            if items_type not in ["ObjectId", "objectid"]:
              invalid_ref_types.append((field_type, items_type, path + ["ref"]))
          else:
            invalid_ref_types.append((field_type, None, path + ["ref"]))

        # Validate ref value
        if value not in declared_entities:
          invalid_refs.append((value, path + ["ref"]))
        else:
          info_reference.append((value, path + ["ref"]))
      for key, val in node.items():
        if isinstance(val, (dict, list)):
          check_ref_values(val, path + [key])
    elif isinstance(node, list):
      for idx, item in enumerate(node):
        if isinstance(item, (dict, list)):
          check_ref_values(item, path + [str(idx)])

  for entity_name, entity_data in document.items():
    if entity_name not in CONTROL_KEYS and isinstance(entity_data, dict):
      for prop, value in entity_data.items():
        if isinstance(value, dict):
          check_ref_values(value, [entity_name, prop])

  if info_reference:
    for value, path in info_reference:
      print(f"ℹ️  Referencing entity '{value}' at {'.'.join(path)}.")
  if invalid_refs:
    print("\u274c Invalid ref values detected:")
    for value, path in invalid_refs:
      print(f"  - ref: '{value}' (at {'.'.join(path)}) | Must reference a declared entity: {', '.join(sorted(declared_entities))}")
  if invalid_ref_types:
    print("\u274c Invalid ref usage detected:")
    for field_type, items_type, path in invalid_ref_types:
      if items_type:
        print(f"  - ref used with type '{field_type}' of '{items_type}' (at {'.'.join(path)}) | ref can only be used with 'objectid' type or arrays of 'objectid'")
      else:
        print(f"  - ref used with type '{field_type}' (at {'.'.join(path)}) | ref can only be used with 'objectid' type or arrays of 'objectid'")

  if invalid_refs or invalid_ref_types:
    return False
  else:
    print("\u2705 All ref values reference valid entities.")
    return True


def lint_file(path: Path) -> bool:
  document = load_yaml(path)

  all_passed = True

  all_passed &= check_required_keys(document)
  all_passed &= check_invalid_entity_names(document)
  all_passed &= check_duplicate_entities(document)
  all_passed &= list_missing_entities(document)
  all_passed &= list_unused_entities(document)
  all_passed &= check_reserved_entity_as_key(document)
  all_passed &= check_misplaced_entity_descriptions(document)
  all_passed &= check_collisions_with_control_keys(document)
  all_passed &= check_unknown_top_level_keys(document)
  all_passed &= check_driver_validation(document)
  all_passed &= check_mongoose_type_validation(document)
  all_passed &= check_mongoose_required_fields(document)
  all_passed &= check_mongoose_item_type_validation(document)
  all_passed &= check_mongoose_ref_validation(document)

  return all_passed


def main():
  parser = get_arg_parser()
  args = parser.parse_args()

  # Determine the schema path
  base_path = Path(__file__).parent / "schema"
  schema_path, data_path = resolve_schema_and_data_paths(args, base_path)

  print(f"🔍 Linting '{data_path.name}'")
  success = lint_file(data_path)
  if not success:
    sys.exit(1)


if __name__ == "__main__":
  main()
