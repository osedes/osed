"""
OSED Lint Module

Provides linting and validation for OSED documents, including checks for entity references, naming conventions, business rules, and driver-specific validation.
"""

from pathlib import Path
import re
import sys
from collections import defaultdict

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
    "String",
    "string",
    "Number",
    "number",
    "Date",
    "date",
    "Buffer",
    "buffer",
    "Boolean",
    "boolean",
    "Mixed",
    "mixed",
    "ObjectId",
    "objectid",
    "Array",
    "array",
    "List",
    "list",
    "Decimal128",
    "decimal128",
    "Map",
    "map",
    "Schema",
    "schema",
    "UUID",
    "uuid",
    "BigInt",
    "bigint",
    "Double",
    "double",
    "Int32",
    "int32",
    "Reference",
    "reference",
}

VALID_MONGOOSE_ITEM_TYPES = {
    "String",
    "string",
    "Number",
    "number",
    "Date",
    "date",
    "Buffer",
    "buffer",
    "Boolean",
    "boolean",
    "Mixed",
    "mixed",
    "ObjectId",
    "objectid",
    "Array",
    "array",
    "List",
    "list",
    "Decimal128",
    "decimal128",
    "Map",
    "map",
    "Schema",
    "schema",
    "UUID",
    "uuid",
    "BigInt",
    "bigint",
    "Double",
    "double",
    "Int32",
    "int32",
    "Reference",
    "reference",
}

MONGOOSE_DRIVERS = {"mongoose", "mongoose-mongo", "mongoose-mongodb"}

# Security-sensitive field patterns
SENSITIVE_FIELD_PATTERNS = {
    r"password",
    r"passwd",
    r"pwd",
    r"token",
    r"secret",
    r"key",
    r"auth",
    r"credential",
    r"private",
    r"ssn",
    r"social",
    r"tax",
    r"credit",
    r"card",
    r"account",
    r"phone",
    r"mobile",
    r"cell",
    r"address",
    r"location",
    r"gps",
    r"email",
    r"mail",
    r"contact",
}

# Performance anti-patterns
N_PLUS_ONE_PATTERNS = {
    "multiple_references": "Multiple references in single entity may cause N+1 queries",
    "nested_references": "Nested references can lead to performance issues",
    "circular_references": "Circular references may cause infinite loops",
}

# Naming convention patterns
NAMING_CONVENTIONS = {
    "camelCase": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "PascalCase": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    "snake_case": re.compile(r"^[a-z][a-z0-9_]*$"),
    "kebab-case": re.compile(r"^[a-z][a-z0-9-]*$"),
}

# Business rule validation patterns
BUSINESS_RULES = {
    "required_relationships": ["user", "order", "product"],
    "audit_fields": ["created_at", "updated_at", "created_by", "updated_by"],
    "status_fields": ["status", "state", "active", "enabled"],
}


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
    """Recursively extract all leaf string values from a nested structure."""
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
    """
    Lists entities declared in the document but not used.
    """
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
    print("\u2705 All used entities are declared.")
    return True


def list_unused_entities(document):
    """
    Lists entities declared in the document but not used.
    """
    declared = set(document.get("entities", []))
    used = extract_entity_references(document)
    unused = declared - used

    if unused:
        print("\u26a0\ufe0f  Declared but unused entities:")
        for entity in sorted(unused):
            print(f"  - {entity}")
        return False
    print("\u2705 All declared entities are used.")
    return True


def check_required_keys(document):
    """
    Checks if the required top-level keys ('osed', 'entities') are present.
    """
    missing = [key for key in ["osed", "entities"] if key not in document]
    if missing:
        print(f"\u274c Missing required top-level keys: {', '.join(missing)}")
        return False
    print("\u2705 All required keys are present.")
    return True


def check_invalid_entity_names(document):
    """
    Checks if entity names in the 'entities' section follow the valid pattern.
    """
    invalid = [
        name
        for name in document.get("entities", [])
        if not VALID_ENTITY_PATTERN.match(name)
    ]
    if invalid:
        print("\u274c Invalid entity names:")
        for name in invalid:
            print(f"  - {name}")
        return False
    print("\u2705 All entity names are valid.")
    return True


def check_duplicate_entities(document):
    """
    Checks for duplicate entity names across 'entities', 'universals', and 'particulars'.
    """
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
        print(
            "\u274c Duplicate entity names across entities/universals/particulars:"
        )
        for name in sorted(duplicates):
            print(f"  - {name}")
        return False
    print(
        "\u2705 No duplicate entities across entities/universals/particulars."
    )
    return True


def check_reserved_entity_as_key(document):
    """
    Checks if top-level keys reuse reserved universal/particular names.
    """
    reserved_map = {}

    def walk_group(group, section, group_path):
        if isinstance(group, list):
            for item in group:
                if isinstance(item, str):
                    reserved_map[item] = (section, group_path)
                elif isinstance(item, dict):
                    for sub_group_name, sub_items in item.items():
                        walk_group(
                            sub_items, section, f"{group_path}.{sub_group_name}"
                        )

    for section in ["universals", "particulars"]:
        for group in document.get(section, []):
            if isinstance(group, dict):
                for group_name, items in group.items():
                    walk_group(items, section, group_name)

    misused = [key for key in document if key in reserved_map]

    if misused:
        print(
            "\u274c Top-level keys reuse reserved universal/particular names:"
        )
        for key in sorted(misused):
            section, group_path = reserved_map[key]
            print(f"  - {key} (from {section}.{group_path})")
        return False
    print("\u2705 No reserved names reused as top-level keys.")
    return True


def check_misplaced_entity_descriptions(document):
    """
    Checks if entity descriptions are placed correctly (not as top-level keys).
    """
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
    print("\u2705 No misplaced entity descriptions.")
    return True


def check_collisions_with_control_keys(document):
    """
    Checks for collisions between entity names and reserved control keys.
    """
    declared = set(document.get("entities", []))

    for section in ["universals", "particulars"]:
        for node in document.get(section, []):
            declared.update(extract_all_leaf_strings(node))

    collisions = declared & CONTROL_KEYS
    if collisions:
        print(
            "\u26a0\ufe0f  Entity names colliding with reserved control keys:"
        )
        for name in sorted(collisions):
            print(f"  - {name}")
        return False
    print("\u2705 No entity names conflict with reserved control keys.")
    return True


def check_unknown_top_level_keys(document):
    """
    Checks for unknown top-level keys in the document.
    """
    known = set(CONTROL_KEYS)
    known.update(document.get("entities", []))
    unknown = [key for key in document if key not in known]
    if unknown:
        print("\u274c Unknown top-level keys found:")
        for key in sorted(unknown):
            print(f"  - {key}")
        return False
    print("\u2705 No unknown top-level keys.")
    return True


def check_driver_validation(document):
    """
    Validates that the 'driver' field is set and is a valid value.
    """
    driver = document.get("driver")
    if not driver:
        print(
            "\u26a0\ufe0f  No driver specified. Driver-specific validation will be skipped."
        )
        return True

    if driver not in MONGOOSE_DRIVERS:
        print(
            f"\u274c Invalid driver '{driver}'. Valid drivers: {', '.join(sorted(MONGOOSE_DRIVERS))}"
        )
        return False

    print(f"\u2705 Driver '{driver}' is valid.")
    return True


def check_mongoose_type_validation(document):
    """
    Validates that type values are valid Mongoose types when driver is mongoose.
    """
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
    print("\u2705 All type values are valid Mongoose types.")
    return True


def check_mongoose_required_fields(document):
    """
    Validates that required fields are present based on type when driver is mongoose.
    """
    driver = document.get("driver")
    if driver not in MONGOOSE_DRIVERS:
        return True  # Skip if not a Mongoose driver

    missing_required = []

    def check_required_metadata(node, path):
        if isinstance(node, dict):
            # If 'ref' is present, require it to be non-empty
            if "ref" in node and not node["ref"]:
                missing_required.append(
                    ("ref", path, f"'ref' is required when present")
                )
            field_type = node.get("type")
            if field_type:
                # Check required fields based on type
                if field_type in ["Array", "array", "List", "list"]:
                    if "of" not in node and "items" not in node:
                        missing_required.append(
                            (
                                "of/items",
                                path,
                                f"required for type '{field_type}'",
                            )
                        )
                elif field_type in ["Map", "map"]:
                    if "of" not in node and "value" not in node:
                        missing_required.append(
                            (
                                "of/value",
                                path,
                                f"required for type '{field_type}'",
                            )
                        )
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
    print("\u2705 All required fields are present.")
    return True


def check_mongoose_item_type_validation(document):
    """
    Validates that of/items values are valid Mongoose types or declared entities when driver is mongoose.
    """
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
            print(
                f"ℹ️  Embedding entity '{value}' as a sub-document at {'.'.join(path)}."
            )
    if invalid_items or invalid_values:
        print("\u274c Invalid of/items values detected:")
        for value, path in invalid_items:
            print(
                f"  - of: '{value}' (at {'.'.join(path)}) | Valid: {', '.join(sorted(VALID_MONGOOSE_ITEM_TYPES))} or declared entity"
            )
        for value, path in invalid_values:
            print(
                f"  - items: '{value}' (at {'.'.join(path)}) | Valid: {', '.join(sorted(VALID_MONGOOSE_ITEM_TYPES))} or declared entity"
            )
        return False
    print("\u2705 All of/items values are valid.")
    return True


def check_mongoose_ref_validation(document):
    """
    Validates that ref values reference valid entities when driver is mongoose.
    """
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
                if field_type and field_type not in [
                    "ObjectId",
                    "objectid",
                    "Reference",
                    "reference",
                ]:
                    # Check if it's an array of objectid/reference
                    if field_type in ["Array", "array", "List", "list"]:
                        items_type = node.get("of") or node.get("items")
                        if (
                            items_type
                            not in [
                                "ObjectId",
                                "objectid",
                                "Reference",
                                "reference",
                            ]
                            and items_type not in declared_entities
                        ):
                            invalid_ref_types.append(
                                (field_type, items_type, path + ["ref"])
                            )
                    else:
                        invalid_ref_types.append(
                            (field_type, None, path + ["ref"])
                        )

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
            print(
                f"  - ref: '{value}' (at {'.'.join(path)}) | Must reference a declared entity: {', '.join(sorted(declared_entities))}"
            )
    if invalid_ref_types:
        print("\u274c Invalid ref usage detected:")
        for field_type, items_type, path in invalid_ref_types:
            if items_type:
                print(
                    f"  - ref used with type '{field_type}' of '{items_type}' (at {'.'.join(path)}) | ref can only be used with 'objectid'/'reference' type or arrays of 'objectid'/'reference'"
                )
            else:
                print(
                    f"  - ref used with type '{field_type}' (at {'.'.join(path)}) | ref can only be used with 'objectid'/'reference' type or arrays of 'objectid'/'reference'"
                )

    if invalid_refs or invalid_ref_types:
        return False
    print("\u2705 All ref values reference valid entities.")
    return True


def check_semantic_node_structure(document):
    """
    Validates semanticNode structure rules: maps have exactly one key with list values.
    """
    errors = []

    def check_semantic_node(node, path):
        if isinstance(node, dict):
            # Check if map has exactly one key
            if len(node) != 1:
                errors.append(
                    f"Map at {'.'.join(path)} has {len(node)} keys, must have exactly one"
                )
            else:
                key, value = next(iter(node.items()))
                # Check if value is a list
                if not isinstance(value, list):
                    errors.append(
                        f"Map value at {'.'.join(path)}.{key} is {type(value).__name__} '{value}', should be list of semanticNodes"
                    )
                elif len(value) == 0:
                    errors.append(
                        f"Map value at {'.'.join(path)}.{key} is empty list, must have at least one item"
                    )
                else:
                    # Recurse into list items
                    for i, item in enumerate(value):
                        if isinstance(item, (dict, list)):
                            check_semantic_node(item, path + [key, str(i)])
        elif isinstance(node, list):
            # Check for unnamed lists (should not be at top level of universals/particulars)
            if (
                path
                and len(path) >= 2
                and path[-2] in ["universals", "particulars"]
            ):
                errors.append(
                    f"Unnamed list at {'.'.join(path)} is not allowed in semanticNode structure"
                )
            else:
                # Recurse into list items
                for i, item in enumerate(node):
                    if isinstance(item, (dict, list)):
                        check_semantic_node(item, path + [str(i)])

    # Check universals and particulars
    for section in ["universals", "particulars"]:
        for i, node in enumerate(document.get(section, [])):
            check_semantic_node(node, [section, str(i)])

    if errors:
        print("\u274c SemanticNode structure violations:")
        for error in errors:
            print(f"  - {error}")
        return False
    print("\u2705 All semanticNode structures are valid.")
    return True


def check_no_unnamed_lists(document):
    """
    Validates that no unnamed lists exist in universals/particulars.
    """
    unnamed_lists = []

    def find_unnamed_lists(node, path):
        if isinstance(node, list):
            # Check if this is an unnamed list in universals/particulars
            if (
                path
                and len(path) >= 2
                and path[-2] in ["universals", "particulars"]
            ):
                unnamed_lists.append(".".join(path))
            # Recurse into list items
            for i, item in enumerate(node):
                if isinstance(item, (dict, list)):
                    find_unnamed_lists(item, path + [str(i)])
        elif isinstance(node, dict):
            # Recurse into dict values
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    find_unnamed_lists(value, path + [key])

    # Check universals and particulars
    for section in ["universals", "particulars"]:
        for i, node in enumerate(document.get(section, [])):
            find_unnamed_lists(node, [section, str(i)])

    if unnamed_lists:
        print(
            "\u274c Unnamed lists found (not allowed in semanticNode structure):"
        )
        for path in unnamed_lists:
            print(f"  - {path}")
        return False
    print("\u2705 No unnamed lists found.")
    return True


def check_map_values_are_lists(document):
    """
    Checks that map values are lists (semanticNode requirement).
    """
    issues = []

    def check_map_values(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}.{key}" if path else key
                if key == "value" and isinstance(value, dict):
                    # Map values should be lists, not objects
                    issues.append(
                        f"Map value at {current_path} should be a list, not an object"
                    )
                check_map_values(value, current_path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_map_values(item, f"{path}[{i}]")

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_map_values(entity_data, entity_name)

    if issues:
        print("\u26a0\ufe0f  Map value issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    print("\u2705 All map values are properly structured.")
    return True


def detect_cyclic_references(document):
    """
    Detects cyclic references (e.g., A → B → A) in entity relationships.
    """
    # Build adjacency list of entity references
    graph = defaultdict(set)
    control_keys = set(CONTROL_KEYS)

    def extract_references(node, source_entity):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "ref" and isinstance(value, str):
                    graph[source_entity].add(value)
                elif key == "items" and isinstance(value, dict):
                    extract_references(value, source_entity)
                elif key == "value" and isinstance(value, dict):
                    extract_references(value, source_entity)
                else:
                    extract_references(value, source_entity)
        elif isinstance(node, list):
            for item in node:
                extract_references(item, source_entity)

    # Extract references from each entity
    for entity_name, entity_data in document.items():
        if entity_name not in control_keys:
            extract_references(entity_data, entity_name)

    # Detect cycles using DFS
    def has_cycle(start, visited, rec_stack):
        visited.add(start)
        rec_stack.add(start)

        for neighbor in graph[start]:
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(start)
        return False

    cycles = []
    visited = set()

    # Create a copy of graph keys to avoid modification during iteration
    graph_entities = list(graph.keys())
    for entity in graph_entities:
        if entity not in visited:
            rec_stack = set()
            if has_cycle(entity, visited, rec_stack):
                # Find the actual cycle
                def find_cycle_path(start, path):
                    if start in path:
                        cycle_start = path.index(start)
                        return path[cycle_start:] + [start]
                    path.append(start)
                    for neighbor in graph[start]:
                        result = find_cycle_path(neighbor, path)
                        if result:
                            return result
                    path.pop()
                    return None

                cycle = find_cycle_path(entity, [])
                if cycle:
                    cycles.append(" → ".join(cycle))

    if cycles:
        print("\u26a0\ufe0f  Cyclic references detected:")
        for cycle in cycles:
            print(f"  - {cycle}")
        # Return True for warnings, False for errors
        return True  # Changed to warning
    print("\u2705 No cyclic references detected.")
    return True


def check_nesting_depth(document, max_depth=3):
    """
    Warns for overly nested descriptions.
    """
    issues = []

    def check_depth(node, path, depth=0):
        if depth > max_depth:
            issues.append(f"Overly nested structure at {path} (depth: {depth})")

        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}.{key}" if path else key
                check_depth(value, current_path, depth + 1)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_depth(item, f"{path}[{i}]", depth + 1)

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_depth(entity_data, entity_name)

    if issues:
        print("\u26a0\ufe0f  Overly nested structures:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    print("\u2705 All structures have reasonable nesting depth.")
    return True


def detect_orphaned_semantic_nodes(document):
    """
    Detects universals/particulars not used in entities.
    """
    # Extract all semantic nodes
    semantic_nodes = set()

    for section in ["universals", "particulars"]:
        for node in document.get(section, []):
            if isinstance(node, str):
                semantic_nodes.add(node)
            elif isinstance(node, dict):
                semantic_nodes.update(extract_all_leaf_strings(node))

    # Extract all used entities and references
    used_entities = extract_entity_references(document)

    # Find orphaned semantic nodes
    orphaned = semantic_nodes - used_entities

    if orphaned:
        print("\u26a0\ufe0f  Orphaned semantic nodes:")
        for node in sorted(orphaned):
            print(f"  - {node}")
        return True  # Changed to warning
    print("\u2705 All semantic nodes are used.")
    return True


def detect_n_plus_one_patterns(document):
    """
    Detects potential N+1 query patterns.
    """
    issues = []

    def analyze_entity_references(entity_name, entity_data):
        ref_count = 0
        nested_refs = 0

        def count_references(node, depth=0):
            nonlocal ref_count, nested_refs

            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "ref" and isinstance(value, str):
                        ref_count += 1
                        if depth > 0:
                            nested_refs += 1
                    else:
                        count_references(value, depth + 1)
            elif isinstance(node, list):
                for item in node:
                    count_references(item, depth + 1)

        count_references(entity_data)

        if ref_count > 3:
            issues.append(
                f"Entity '{entity_name}' has {ref_count} references (potential N+1)"
            )
        if nested_refs > 0:
            issues.append(
                f"Entity '{entity_name}' has {nested_refs} nested references"
            )

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            analyze_entity_references(entity_name, entity_data)

    if issues:
        print("\u26a0\ufe0f  Performance concerns:")
        for issue in issues:
            print(f"  - {issue}")
        return True  # Changed to warning
    print("\u2705 No obvious performance issues detected.")
    return True


def check_sensitive_fields(document):
    """
    Detects potentially sensitive field names.
    """
    sensitive_fields = []

    def check_field_names(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                current_path = f"{path}.{key}" if path else key

                # Check if field name matches sensitive patterns
                for pattern in SENSITIVE_FIELD_PATTERNS:
                    if re.search(pattern, key, re.IGNORECASE):
                        sensitive_fields.append(
                            f"Sensitive field '{key}' at {current_path}"
                        )

                check_field_names(value, current_path)
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_field_names(item, f"{path}[{i}]")

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_field_names(entity_data, entity_name)

    if sensitive_fields:
        print("\u26a0\ufe0f  Potentially sensitive fields detected:")
        for field in sensitive_fields:
            print(f"  - {field}")
        return True  # Changed to warning
    print("\u2705 No sensitive fields detected.")
    return True


def enforce_naming_conventions(document):
    """
    Enforces consistent naming conventions across teams.
    """
    naming_issues = []
    entity_names = []

    # Collect all entity names
    for entity_name in document:
        if entity_name not in CONTROL_KEYS:
            entity_names.append(entity_name)

    # Check entity naming consistency
    if entity_names:
        # Determine most common naming convention
        convention_counts = defaultdict(int)
        for name in entity_names:
            for convention_name, pattern in NAMING_CONVENTIONS.items():
                if pattern.match(name):
                    convention_counts[convention_name] += 1
                    break

        if convention_counts:
            dominant_convention = max(
                convention_counts, key=convention_counts.get
            )

            # Check for inconsistencies
            for name in entity_names:
                matches_convention = False
                for convention_name, pattern in NAMING_CONVENTIONS.items():
                    if pattern.match(name):
                        if convention_name == dominant_convention:
                            matches_convention = True
                        break

                if not matches_convention:
                    naming_issues.append(
                        f"Entity '{name}' doesn't follow dominant convention '{dominant_convention}'"
                    )

    if naming_issues:
        print("\u26a0\ufe0f  Naming convention issues:")
        for issue in naming_issues:
            print(f"  - {issue}")
        return False
    print("\u2705 All names follow conventions.")
    return True


def validate_business_rules(document):
    """
    Validates business rules (e.g., required relationships, audit fields).
    """
    business_issues = []

    def check_entity_rules(entity_name, entity_data):
        # Check for required relationships
        if entity_name.lower() in ["user", "order", "product"]:
            has_relationships = False

            def check_for_refs(node):
                nonlocal has_relationships
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key == "ref" and isinstance(value, str):
                            has_relationships = True
                        else:
                            check_for_refs(value)
                elif isinstance(node, list):
                    for item in node:
                        check_for_refs(item)

            check_for_refs(entity_data)
            if not has_relationships:
                business_issues.append(
                    f"Entity '{entity_name}' should have relationships"
                )

        # Check for audit fields
        audit_fields_found = set()

        def check_audit_fields(node):
            if isinstance(node, dict):
                for key in node.keys():
                    if key in BUSINESS_RULES["audit_fields"]:
                        audit_fields_found.add(key)
                for value in node.values():
                    check_audit_fields(value)
            elif isinstance(node, list):
                for item in node:
                    check_audit_fields(item)

        check_audit_fields(entity_data)
        if not audit_fields_found:
            business_issues.append(
                f"Entity '{entity_name}' should have audit fields (created_at, updated_at, etc.)"
            )

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_entity_rules(entity_name, entity_data)

    if business_issues:
        print("\u26a0\ufe0f  Business rule violations:")
        for issue in business_issues:
            print(f"  - {issue}")
        return False
    print("\u2705 All business rules satisfied.")
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
    all_passed &= check_semantic_node_structure(document)
    all_passed &= check_no_unnamed_lists(document)
    all_passed &= check_map_values_are_lists(document)
    all_passed &= detect_cyclic_references(document)
    all_passed &= check_nesting_depth(document)
    all_passed &= detect_orphaned_semantic_nodes(document)
    all_passed &= detect_n_plus_one_patterns(document)
    all_passed &= check_sensitive_fields(document)
    all_passed &= enforce_naming_conventions(document)
    all_passed &= validate_business_rules(document)

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
