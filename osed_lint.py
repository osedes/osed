import sys
import yaml
import re
from pathlib import Path

CONTROL_KEYS = {
  "osed",
  "entities",
  "universals",
  "particulars",
}
VALID_ENTITY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")

def load_yaml(filepath):
  with open(filepath, "r", encoding="utf-8") as f:
    return yaml.safe_load(f)

def extract_entity_references(document):
  used = set()

  def recurse(value):
    if isinstance(value, dict):
      for k, v in value.items():
        if isinstance(v, (str, list, dict)):
          recurse(v)
        if isinstance(k, str):
          used.add(k)
    elif isinstance(value, list):
      for item in value:
        recurse(item)
    elif isinstance(value, str):
      used.add(value)

  relevant_items = {
    k: v for k, v in document.items() if k not in CONTROL_KEYS
  }
  for k, v in relevant_items.items():
    recurse(v)
    if isinstance(k, str):
      used.add(k)

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

  return all_passed

def main():
  if len(sys.argv) != 2:
    print("Usage: python lint_osed.py <osed.yaml>")
    return

  path = Path(sys.argv[1])
  if not path.exists():
    print(f"\u274c '{path}' not found.")
    return

  lint_file(path)

if __name__ == "__main__":
  main()
