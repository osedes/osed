"""
OSED Lint Module (New Version)

Provides linting and validation for OSED documents with severity-based results.
Includes checks for entity references, naming conventions, business rules, and driver-specific validation.
"""

from pathlib import Path
import re
import sys
from collections import defaultdict

from .osed_utils import (
    load_yaml,
    get_arg_parser,
    CONTROL_KEYS,
    VALID_MONGOOSE_TYPES,
    VALID_MONGOOSE_ITEM_TYPES,
)
from .osed_logging import Severity, get_logger, info, error
from .osed_results import LintResult
from .osed_config import is_path_acknowledged, make_path
from .osed_lint_mongoose import (
    check_mongoose_type_validation,
    check_mongoose_required_fields,
    check_mongoose_item_type_validation,
    check_mongoose_ref_validation,
)

VALID_ENTITY_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")

# Mongoose-specific constants for driver-aware validation
# TODO Check if this indeed true, valid Mongoose types start with uppercase
# VALID_MONGOOSE_TYPES = {
#     "String",
#     "string",
#     "Number",
#     "number",
#     "Date",
#     "date",
#     "Buffer",
#     "buffer",
#     "Boolean",
#     "boolean",
#     "Mixed",
#     "mixed",
#     "ObjectId",
#     "objectid",
#     "Array",
#     "array",
#     "List",
#     "list",
#     "Decimal128",
#     "decimal128",
#     "Map",
#     "map",
#     "Schema",
#     "schema",
#     "UUID",
#     "uuid",
#     "BigInt",
#     "bigint",
#     "Double",
#     "double",
#     "Int32",
#     "int32",
#     "Reference",
#     "reference",
# }

# TODO Check if this indeed true, valid Mongoose types start with uppercase
# VALID_MONGOOSE_ITEM_TYPES = VALID_MONGOOSE_TYPES

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

REQUIRED_KEYS = ["osed", "entities"]


def extract_entity_references(document):
    """
    Extracts all used entity references:
    - Collects all top-level keys (excluding control keys) as used entities
    - Collects all leaf node values (strings that are not property names) as used entities
    - Does NOT collect property names (non-top-level keys)
    """
    used = set()
    control_keys = set(CONTROL_KEYS)

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
            used.add(node)

    for k, v in document.items():
        if k not in control_keys:
            collect_leaf_values(v)

    return used


def extract_all_leaf_strings(node):
    """Extracts all leaf string values from a nested structure."""
    result = set()

    def recurse(n):
        if isinstance(n, str):
            result.add(n)
        elif isinstance(n, dict):
            for v in n.values():
                recurse(v)
        elif isinstance(n, list):
            for item in n:
                recurse(item)

    recurse(node)
    return result


def list_missing_entities(document, file_path=None):
    """
    Lists entities that are used but not declared in the 'entities' section, 'universals', or 'particulars',
    and are not built-in types.
    """
    declared = set(document.get("entities", []))

    # Add all leaf strings from universals and particulars
    declared.update(extract_all_leaf_strings(document.get("universals", [])))
    declared.update(extract_all_leaf_strings(document.get("particulars", [])))

    # Add all built-in types
    declared.update(VALID_MONGOOSE_TYPES)

    used = extract_entity_references(document)
    missing = used - declared

    if missing:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Missing entity declarations",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all used entities are declared in the 'entities' section."
            ],
        )
        for entity in sorted(missing):
            result.add_message(f"Entity '{entity}' is used but not declared")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All used entities are declared"],
        file_path=file_path,
    )


def list_unused_entities(document, file_path=None):
    """
    Lists entities that are declared but not used.
    """
    declared = set(document.get("entities", []))
    used = extract_entity_references(document)
    unused = declared - used

    if unused:
        result = LintResult(
            passed=True,  # Unused entities are warnings, not errors
            severity=Severity.WARNING,
            context="Unused entity declarations",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review unused entity declarations to ensure they are no longer needed."
            ],
        )
        for entity in sorted(unused):
            result.add_message(f"Entity '{entity}' is declared but not used")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All declared entities are used"],
        file_path=file_path,
    )


def check_required_keys(document, file_path=None):
    """
    Checks if the required top-level keys ('osed', 'entities') are present.
    """
    missing = []
    for key in REQUIRED_KEYS:
        if key not in document:
            missing.append(key)
    if missing:
        result = LintResult(
            passed=False,
            severity=Severity.CRITICAL,  # Use CRITICAL for missing required keys
            context="Missing required keys",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=["Add all required keys to the document."],
        )
        for key in missing:
            result.add_message(f"Missing required key: {key}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All required keys are present"],
        file_path=file_path,
    )


def check_invalid_entity_names(document, file_path=None):
    """
    Checks if entity names in the 'entities' section follow the valid pattern.
    """
    invalid = []
    for name in document.get("entities", []):
        if not VALID_ENTITY_PATTERN.match(name):
            invalid.append(name)
    if invalid:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid entity names",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all entity names in the 'entities' section follow the pattern '^[A-Za-z][A-Za-z0-9._-]*$'."
            ],
        )
        for name in invalid:
            result.add_message(f"Invalid entity name: {name}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All entity names are valid"],
        file_path=file_path,
    )


def check_duplicate_entities(document, file_path=None):
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
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Duplicate entity names",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for duplicate entity names across 'entities', 'universals', and 'particulars'."
            ],
        )
        for name in sorted(duplicates):
            result.add_message(f"Duplicate entity name: {name}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=[
            "No duplicate entities across entities/universals/particulars"
        ],
        file_path=file_path,
    )


def check_reserved_entity_as_key(document, file_path=None):
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
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Reserved names reused as top-level keys",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for top-level keys that reuse reserved universal/particular names."
            ],
        )
        for key in sorted(misused):
            section, group_path = reserved_map[key]
            result.add_message(
                f"Key '{key}' reuses reserved name from {section}.{group_path}"
            )
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No reserved names reused as top-level keys"],
        file_path=file_path,
    )


def check_misplaced_entity_descriptions(document, file_path=None):
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
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Misplaced entity descriptions",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure entity descriptions are not placed as top-level keys."
            ],
        )
        for key, path in misplaced:
            result.add_message(f"Entity '{key}' misplaced at {'.'.join(path)}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No misplaced entity descriptions"],
        file_path=file_path,
    )


def check_collisions_with_control_keys(document, file_path=None):
    """
    Checks for collisions between entity names and reserved control keys.
    """
    declared = set(document.get("entities", []))

    for section in ["universals", "particulars"]:
        for node in document.get(section, []):
            declared.update(extract_all_leaf_strings(node))

    collisions = declared & CONTROL_KEYS
    if collisions:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Entity names colliding with control keys",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for entity names that conflict with reserved control keys."
            ],
        )
        for name in sorted(collisions):
            result.add_message(
                f"Entity name '{name}' conflicts with control key"
            )
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No entity names conflict with control keys"],
        file_path=file_path,
    )


def check_unknown_top_level_keys(document, file_path=None):
    """
    Checks for unknown top-level keys in the document.
    """
    known = set(CONTROL_KEYS)
    known.update(document.get("entities", []))
    unknown = [key for key in document if key not in known]
    if unknown:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Unknown top-level keys",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for top-level keys that are not 'osed', 'entities', 'universals', 'particulars', or entity names."
            ],
        )
        for key in sorted(unknown):
            result.add_message(f"Unknown top-level key: {key}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No unknown top-level keys"],
        file_path=file_path,
    )


def check_driver_validation(document, file_path=None):
    """
    Validates that the 'driver' field is set and is a valid value.
    """
    driver = document.get("driver")
    if not driver:
        result = LintResult(
            passed=True,  # No driver is OK, just a warning
            severity=Severity.WARNING,
            context="Missing driver specification",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Specify a valid driver if driver-specific validation is required."
            ],
        )
        result.add_message(
            "Document does not specify a 'driver', which is needed for code generation."
        )

        path_ref = make_path(file_path, "__document__")
        if is_path_acknowledged("missingDriver", path_ref):
            result.severity = Severity.INFO
            result.add_message(
                f"[Acknowledged: {path_ref} for 'missingDriver' downgraded to info]"
            )
        return result

    if driver not in MONGOOSE_DRIVERS:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid driver specification",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Specify a valid driver from the list: mongoose, mongoose-mongo, mongoose-mongodb."
            ],
        )
        result.add_message(
            f"Invalid driver '{driver}'. Valid drivers: {', '.join(sorted(MONGOOSE_DRIVERS))}"
        )
        return result
    else:
        return LintResult(
            passed=True,
            severity=Severity.INFO,
            context="Valid driver specified",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=["Driver '{driver}' is valid."],
        )


def check_semantic_node_structure(document, file_path=None):
    """
    Validates semantic node structures in universals and particulars.
    """
    invalid_nodes = []

    def check_semantic_node(node, path):
        if isinstance(node, dict):
            # Semantic nodes should have exactly one key
            if len(node) != 1:
                invalid_nodes.append(
                    f"Semantic node at {'.'.join(path)} has {len(node)} keys (should be 1)"
                )
            else:
                key, value = next(iter(node.items()))
                if not isinstance(value, list):
                    invalid_nodes.append(
                        f"Semantic node value at {'.'.join(path)} is not a list"
                    )
                elif len(value) == 0:
                    invalid_nodes.append(
                        f"Semantic node list at {'.'.join(path)} is empty"
                    )
                else:
                    # Check each item in the list
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            check_semantic_node(item, path + [f"{key}[{i}]"])
                        elif not isinstance(item, str):
                            invalid_nodes.append(
                                f"Semantic node item at {'.'.join(path)}[{i}] is not a string"
                            )

    # Check universals and particulars
    for section in ["universals", "particulars"]:
        for i, node in enumerate(document.get(section, [])):
            if isinstance(node, dict):
                check_semantic_node(node, [section, str(i)])

    if invalid_nodes:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid semantic node structures",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all semantic nodes have exactly one key and its value is a non-empty list of strings."
            ],
        )
        for invalid_node in invalid_nodes:
            result.add_message(invalid_node)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All semanticNode structures are valid"],
        file_path=file_path,
    )


def check_no_unnamed_lists(document, file_path=None):
    """
    Checks that there are no unnamed lists (lists without semantic node structure).
    Only flags lists that are direct values in a list (not values of a mapping).
    """
    unnamed_lists = []

    def find_unnamed_lists(node, path, parent_is_list=False):
        if isinstance(node, list):
            # Only flag if this list is inside another list (unnamed)
            if parent_is_list:
                for i, item in enumerate(node):
                    if isinstance(item, str):
                        unnamed_lists.append(
                            f"Unnamed list item '{item}' at {'.'.join(path)}[{i}]"
                        )
            # Recurse into children
            for i, item in enumerate(node):
                find_unnamed_lists(item, path + [str(i)], parent_is_list=True)
        elif isinstance(node, dict):
            for key, value in node.items():
                find_unnamed_lists(value, path + [key], parent_is_list=False)

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            find_unnamed_lists(entity_data, [entity_name], parent_is_list=False)

    if unnamed_lists:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Unnamed lists found",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=["Ensure all lists have a semantic node structure."],
        )
        for unnamed_list in unnamed_lists:
            result.add_message(unnamed_list)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No unnamed lists found"],
        file_path=file_path,
    )


def check_map_values_are_lists(document, file_path=None):
    """
    Checks that map values are properly structured as lists.
    """
    invalid_maps = []

    def check_map_values(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "value" and isinstance(value, dict):
                    # Map value should be a list of semantic nodes
                    if not isinstance(value, dict) or len(value) != 1:
                        invalid_maps.append(
                            f"Map value at {'.'.join(path)} is not properly structured"
                        )
                    else:
                        map_value = next(iter(value.values()))
                        if not isinstance(map_value, list):
                            invalid_maps.append(
                                f"Map value at {'.'.join(path)} is not a list"
                            )
                else:
                    check_map_values(value, path + [key])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_map_values(item, path + [str(i)])

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_map_values(entity_data, [entity_name])

    if invalid_maps:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid map values",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all 'value' fields in map structures are lists of semantic nodes."
            ],
        )
        for invalid_map in invalid_maps:
            result.add_message(invalid_map)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All map values are properly structured"],
        file_path=file_path,
    )


def detect_cyclic_references(document, file_path=None):
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
        result = LintResult(
            passed=True,  # Cyclic references are warnings, not errors
            severity=Severity.WARNING,
            context="Cyclic references detected",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for cyclic references in entity relationships."
            ],
        )
        for cycle in cycles:
            result.add_message(f"Cyclic reference: {cycle}")
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No cyclic references detected"],
        file_path=file_path,
    )


def check_nesting_depth(document, file_path=None):
    """
    Warns for overly nested descriptions.
    """
    issues = []

    def check_depth(node, path, depth=0):
        if depth > 3:
            issues.append(
                f"Overly nested structure at {'.'.join(path)} (depth: {depth})"
            )

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
        result = LintResult(
            passed=True,  # Nesting depth is a warning, not an error
            severity=Severity.WARNING,
            context="Overly nested structures",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for overly nested structures in entity descriptions."
            ],
        )
        for issue in issues:
            result.add_message(issue)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All structures have reasonable nesting depth"],
        file_path=file_path,
    )


def detect_orphaned_semantic_nodes(document, file_path=None):
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
        result = LintResult(
            passed=True,  # Orphaned nodes are warnings, not errors
            severity=Severity.WARNING,
            context="Orphaned semantic nodes",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for universals/particulars that are no longer used in entities."
            ],
        )
        for node in sorted(orphaned):
            result.add_message(f"Orphaned semantic node: {node}")
        # Add acknowledgment support (camelCase)
        path_ref = make_path(file_path, "__document__")
        if is_path_acknowledged("orphanedSemanticNodes", path_ref):
            result.severity = Severity.INFO
            result.add_message(
                f"[Acknowledged: {path_ref} for 'orphanedSemanticNodes' downgraded to info]"
            )
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All semantic nodes are used"],
        file_path=file_path,
    )


def detect_n_plus_one_patterns(document, file_path=None):
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
        result = LintResult(
            passed=True,  # Performance issues are warnings, not errors
            severity=Severity.WARNING,
            context="Performance concerns",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for potential N+1 query patterns in entity descriptions."
            ],
        )
        for issue in issues:
            result.add_message(issue)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No obvious performance issues detected"],
        file_path=file_path,
    )


def check_sensitive_fields(document, file_path=None):
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
        result = LintResult(
            passed=True,  # Sensitive fields are warnings, not errors
            severity=Severity.WARNING,
            context="Potentially sensitive fields detected",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for potentially sensitive field names in entity descriptions."
            ],
        )
        for field in sensitive_fields:
            result.add_message(field)
            # Parse entity and field from the field string
            # Example: Sensitive field 'password' at Person.password
            m = re.match(r"Sensitive field '(.+)' at ([^.]+)\.(.+)", field)
            if m:
                field_name, entity, field_key = m.groups()
                path_ref = make_path(file_path, entity, field_key)
                if is_path_acknowledged("sensitiveFields", path_ref):
                    result.severity = Severity.INFO
                    result.add_message(
                        f"[Acknowledged: {path_ref} downgraded from warning to info]"
                    )
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["No sensitive fields detected"],
        file_path=file_path,
    )


def enforce_naming_conventions(document, file_path=None):
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
        result = LintResult(
            passed=False,  # Naming conventions are errors
            severity=Severity.ERROR,
            context="Naming convention issues",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for inconsistent naming conventions across entity descriptions."
            ],
        )
        for issue in naming_issues:
            result.add_message(issue)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All names follow conventions"],
        file_path=file_path,
    )


def validate_business_rules(document, file_path=None):
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
        result = LintResult(
            passed=True,  # Business rules are warnings, not errors
            severity=Severity.WARNING,
            context="Business rule violations",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Review for violations of business rules in entity descriptions."
            ],
        )
        for issue in business_issues:
            result.add_message(issue)
            # Patch: downgrade audit field warning if acknowledged
            m = re.match(
                r"Entity '([A-Za-z0-9_]+)' should have audit fields", issue
            )
            if m:
                entity = m.group(1)
                path_ref = make_path(file_path, entity)
                if is_path_acknowledged("auditFields", path_ref):
                    result.severity = Severity.INFO
                    result.add_message(
                        f"[Acknowledged: {path_ref} downgraded from warning to info]"
                    )
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All business rules satisfied"],
        file_path=file_path,
    )


def lint_file(path: Path) -> tuple[bool, dict]:
    """
    Lint an OSED document and return structured results.

    Returns:
        Tuple of (passed, results_by_severity)
    """
    try:
        document = load_yaml(path)
        logger = get_logger()
        file_path = str(path)

        # Define all linting checks (now accept file_path)
        checks = [
            lambda doc: check_required_keys(doc, file_path=file_path),
            lambda doc: check_invalid_entity_names(doc, file_path=file_path),
            lambda doc: check_duplicate_entities(doc, file_path=file_path),
            lambda doc: list_missing_entities(doc, file_path=file_path),
            lambda doc: list_unused_entities(doc, file_path=file_path),
            lambda doc: check_reserved_entity_as_key(doc, file_path=file_path),
            lambda doc: check_misplaced_entity_descriptions(
                doc, file_path=file_path
            ),
            lambda doc: check_collisions_with_control_keys(
                doc, file_path=file_path
            ),
            lambda doc: check_unknown_top_level_keys(doc, file_path=file_path),
            lambda doc: check_driver_validation(doc, file_path=file_path),
            lambda doc: check_semantic_node_structure(doc, file_path=file_path),
            lambda doc: check_no_unnamed_lists(doc, file_path=file_path),
            lambda doc: check_map_values_are_lists(doc, file_path=file_path),
            lambda doc: detect_cyclic_references(doc, file_path=file_path),
            lambda doc: check_nesting_depth(doc, file_path=file_path),
            lambda doc: detect_orphaned_semantic_nodes(
                doc, file_path=file_path
            ),
            lambda doc: detect_n_plus_one_patterns(doc, file_path=file_path),
            lambda doc: check_sensitive_fields(doc, file_path=file_path),
            lambda doc: enforce_naming_conventions(doc, file_path=file_path),
            lambda doc: validate_business_rules(doc, file_path=file_path),
            lambda doc: check_mongoose_type_validation(
                doc, file_path=file_path
            ),
            lambda doc: check_mongoose_required_fields(
                doc, file_path=file_path
            ),
            lambda doc: check_mongoose_item_type_validation(
                doc, file_path=file_path
            ),
            lambda doc: check_mongoose_ref_validation(doc, file_path=file_path),
        ]

        # Run all checks and collect results
        results = []
        for check in checks:
            result = check(document)
            results.append(result)

            # Log the result with contextual info if available
            log_msg = result.to_log_message()
            logger.log(
                log_msg.severity,
                log_msg.message,
                context=log_msg.context,
                suggestions=log_msg.suggestions,
                file_path=log_msg.file_path,
                line_number=log_msg.line_number,
            )

        # Determine overall pass/fail (only errors are blocking)
        passed = all(
            result.passed or result.severity != Severity.ERROR
            for result in results
        )

        # Group results by severity
        results_by_severity = {
            Severity.INFO: [r for r in results if r.severity == Severity.INFO],
            Severity.WARNING: [
                r for r in results if r.severity == Severity.WARNING
            ],
            Severity.ERROR: [
                r for r in results if r.severity == Severity.ERROR
            ],
        }

        return passed, results_by_severity
    except Exception as e:
        logger = get_logger()
        logger.log(
            Severity.CRITICAL,
            f"Fatal error: {e}",
            context="Fatal/system error",
            suggestions=["Check the input file for critical issues."],
            file_path=str(path),
        )
        # Return a failed result with the fatal error as a LintResult
        fatal_result = LintResult(
            passed=False,
            severity=Severity.CRITICAL,
            messages=[f"Fatal error: {e}"],
            file_path=str(path),
            context="Fatal/system error",
            suggestions=["Check the input file for critical issues."],
        )
        return False, {Severity.CRITICAL: [fatal_result]}


def main():
    """Main entry point for linting."""
    parser = get_arg_parser()
    args = parser.parse_args()

    # Get the data file path
    data_path = Path(args.file) if args.file else Path("osed.yaml")

    if not data_path.exists():
        error(f"File not found: {data_path}")
        sys.exit(2)

    info(f"Linting '{data_path.name}'")
    passed, results_by_severity = lint_file(data_path)

    # Get exit code based on severity
    logger = get_logger()
    exit_code = logger.get_exit_code()

    if exit_code != 0:
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
