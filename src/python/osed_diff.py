"""
OSED Diff Module

Provides functionality to compare two OSED documents and show differences
in structure, semantics, and generated code impact.
"""

import os
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from .osed_utils import load_yaml
from .osed_logging import info, warning, error


# Color support for terminals
def supports_color():
    """Check if terminal supports color."""
    # Check if we're in a terminal and if colors are supported
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False

    # Check for common terminal types that support colors
    term = os.environ.get("TERM", "")
    return (
        term
        in [
            "xterm",
            "xterm-256color",
            "xterm-color",
            "linux",
            "cygwin",
            "rxvt",
            "screen",
        ]
        or "color" in term
    )


def colorize(text: str, color: str) -> str:
    """Add color to text if terminal supports it."""
    if not supports_color():
        return text

    # Use more compatible color codes
    colors = {
        "green": "\033[32m",  # Standard green instead of bright green
        "red": "\033[31m",  # Standard red instead of bright red
        "yellow": "\033[33m",  # Standard yellow instead of bright yellow
        "blue": "\033[34m",  # Standard blue instead of bright blue
        "magenta": "\033[35m",  # Standard magenta instead of bright magenta
        "cyan": "\033[36m",  # Standard cyan instead of bright cyan
        "bold": "\033[1m",
        "reset": "\033[0m",
    }

    return f"{colors.get(color, '')}{text}{colors['reset']}"


def wrap_text(text: str, width: int = 80) -> str:
    """Wrap text to specified width, preserving formatting."""
    return textwrap.fill(
        text, width=width, break_long_words=False, break_on_hyphens=False
    )


# pylint: disable=too-many-instance-attributes
@dataclass
class DiffResult:
    """Result of comparing two OSED documents."""

    added_entities: Set[str]
    removed_entities: Set[str]
    modified_entities: Dict[str, Dict]
    added_universals: Set[str]
    removed_universals: Set[str]
    added_particulars: Set[str]
    removed_particulars: Set[str]
    schema_version_changed: bool
    driver_changed: bool
    breaking_changes: List[str]
    impact_analysis: Dict[str, List[str]]


def load_osed_document(file_path: Path) -> Dict:
    """Load and validate an OSED document or schema."""
    try:
        content = load_yaml(file_path)
        if not isinstance(content, dict):
            error(
                f"OSED document must be a YAML object (file: {file_path})",
                context=f"file: {file_path}",
                suggestions=[
                    "Check that your YAML file is structured as a mapping/object at the top level."
                ],
            )
            raise ValueError("OSED document must be a YAML object")
        return content
    except Exception as e:
        error(
            f"Failed to load OSED document {file_path}: {e}",
            context=f"file: {file_path}",
            suggestions=["Check that the file exists and is valid YAML."],
        )
        raise RuntimeError(
            f"Failed to load OSED document {file_path}: {e}"
        ) from e


def is_schema_file(doc: Dict) -> bool:
    """Check if the loaded document is a schema file."""
    # Schema files have JSON Schema structure
    return "$schema" in doc or "$id" in doc or "definitions" in doc


def is_osed_document(doc: Dict) -> bool:
    """Check if the loaded document is an OSED document."""
    # OSED documents have entities, universals, particulars
    return "entities" in doc and "osed" in doc


def extract_entities(doc: Dict) -> Set[str]:
    """Extract entity names from OSED document."""
    entities = set()

    # Get declared entities from the entities list
    declared_entities = doc.get("entities", [])
    entities.update(declared_entities)

    return entities


def extract_universals(doc: Dict) -> Set[str]:
    """Extract universal names from OSED document."""
    universals = set()
    universal_list = doc.get("universals", [])

    for item in universal_list:
        if isinstance(item, str):
            universals.add(item)
        elif isinstance(item, dict):
            # Handle nested semanticNode structure
            for key, value in item.items():
                universals.add(key)
                if isinstance(value, list):
                    for sub_item in value:
                        if isinstance(sub_item, str):
                            universals.add(sub_item)

    return universals


def extract_particulars(doc: Dict) -> Set[str]:
    """Extract particular names from OSED document."""
    particulars = set()
    particular_list = doc.get("particulars", [])

    for item in particular_list:
        if isinstance(item, str):
            particulars.add(item)
        elif isinstance(item, dict):
            # Handle nested semanticNode structure
            for key, value in item.items():
                particulars.add(key)
                if isinstance(value, list):
                    for sub_item in value:
                        if isinstance(sub_item, str):
                            particulars.add(sub_item)

    return particulars


def extract_schema_properties(doc: Dict) -> Set[str]:
    """Extract property names from OSED schema."""
    properties = set()

    if "properties" in doc:
        properties.update(doc["properties"].keys())

    if "definitions" in doc:
        for definition in doc["definitions"].values():
            if isinstance(definition, dict) and "properties" in definition:
                properties.update(definition["properties"].keys())

    return properties


def extract_schema_definitions(doc: Dict) -> Set[str]:
    """Extract definition names from OSED schema."""
    definitions = set()

    if "definitions" in doc:
        definitions.update(doc["definitions"].keys())

    return definitions


def compare_entity_structure(entity1: Dict, entity2: Dict) -> Dict:
    """Compare the structure of a single entity between two documents."""
    changes = {
        "added_fields": [],
        "removed_fields": [],
        "modified_fields": [],
        "type_changes": [],
        "metadata_changes": [],
    }

    # Get all field names
    fields1 = set(entity1.keys())
    fields2 = set(entity2.keys())

    # Find added and removed fields
    changes["added_fields"] = list(fields2 - fields1)
    changes["removed_fields"] = list(fields1 - fields2)

    # Find modified fields
    common_fields = fields1 & fields2
    for field in common_fields:
        if entity1[field] != entity2[field]:
            changes["modified_fields"].append(field)

            # Check for type changes
            if isinstance(entity1[field], str) and isinstance(
                entity2[field], dict
            ):
                changes["type_changes"].append(f"{field}: simple → complex")
            elif isinstance(entity1[field], dict) and isinstance(
                entity2[field], str
            ):
                changes["type_changes"].append(f"{field}: complex → simple")

    return changes


def detect_breaking_changes(doc1: Dict, doc2: Dict) -> List[str]:
    """Detect breaking changes between two OSED documents."""
    breaking_changes = []

    # Check for removed entities
    entities1 = extract_entities(doc1)
    entities2 = extract_entities(doc2)
    removed_entities = entities1 - entities2
    if removed_entities:
        breaking_changes.append(
            f"Removed entities: {', '.join(removed_entities)}"
        )

    # Check for removed fields in common entities
    for entity_name in entities1 & entities2:
        entity1 = doc1.get(entity_name, {})
        entity2 = doc2.get(entity_name, {})

        if isinstance(entity1, dict) and isinstance(entity2, dict):
            removed_fields = set(entity1.keys()) - set(entity2.keys())
            if removed_fields:
                breaking_changes.append(
                    f"Removed fields in {entity_name}: {', '.join(removed_fields)}"
                )

    # Check for type changes that could break generated code
    for entity_name in entities1 & entities2:
        entity1 = doc1.get(entity_name, {})
        entity2 = doc2.get(entity_name, {})

        if isinstance(entity1, dict) and isinstance(entity2, dict):
            for field in set(entity1.keys()) & set(entity2.keys()):
                if isinstance(entity1[field], str) and isinstance(
                    entity2[field], dict
                ):
                    breaking_changes.append(
                        f"Field {entity_name}.{field} changed from simple to complex type"
                    )
                elif isinstance(entity1[field], dict) and isinstance(
                    entity2[field], str
                ):
                    breaking_changes.append(
                        f"Field {entity_name}.{field} changed from complex to simple type"
                    )

    return breaking_changes


def analyze_generated_code_impact(
    doc1: Dict, doc2: Dict
) -> Dict[str, List[str]]:
    """Analyze how changes will impact generated code."""
    impact = {
        "typescript": [],
        "mongoose": [],
        "validation": [],
        "migration": [],
    }

    entities1 = extract_entities(doc1)
    entities2 = extract_entities(doc2)

    # New entities
    new_entities = entities2 - entities1
    if new_entities:
        impact["typescript"].append(
            f"New interfaces: {', '.join(new_entities)}"
        )
        impact["mongoose"].append(f"New schemas: {', '.join(new_entities)}")

    # Removed entities
    removed_entities = entities1 - entities2
    if removed_entities:
        impact["typescript"].append(
            f"Removed interfaces: {', '.join(removed_entities)}"
        )
        impact["mongoose"].append(
            f"Removed schemas: {', '.join(removed_entities)}"
        )
        impact["migration"].append(
            f"Remove references to: {', '.join(removed_entities)}"
        )

    # Modified entities
    for entity_name in entities1 & entities2:
        entity1 = doc1.get(entity_name, {})
        entity2 = doc2.get(entity_name, {})

        if isinstance(entity1, dict) and isinstance(entity2, dict):
            changes = compare_entity_structure(entity1, entity2)

            if changes["added_fields"]:
                impact["typescript"].append(
                    f"Added fields to {entity_name}: {', '.join(changes['added_fields'])}"
                )
                impact["mongoose"].append(
                    f"Added fields to {entity_name}: {', '.join(changes['added_fields'])}"
                )

            if changes["removed_fields"]:
                impact["typescript"].append(
                    f"Removed fields from {entity_name}: {', '.join(changes['removed_fields'])}"
                )
                impact["mongoose"].append(
                    f"Removed fields from {entity_name}: {', '.join(changes['removed_fields'])}"
                )
                impact["migration"].append(
                    f"Remove {entity_name}.{', '.join(changes['removed_fields'])} references"
                )

            if changes["type_changes"]:
                impact["typescript"].append(
                    f"Type changes in {entity_name}: {', '.join(changes['type_changes'])}"
                )
                impact["mongoose"].append(
                    f"Schema changes in {entity_name}: {', '.join(changes['type_changes'])}"
                )
                impact["migration"].append(
                    f"Update {entity_name} type definitions"
                )

    return impact


def _calculate_entity_diffs(doc1: Dict, doc2: Dict):
    entities1 = extract_entities(doc1)
    entities2 = extract_entities(doc2)
    return entities1, entities2, entities2 - entities1, entities1 - entities2


def _calculate_universal_diffs(doc1: Dict, doc2: Dict):
    universals1 = extract_universals(doc1)
    universals2 = extract_universals(doc2)
    return (
        universals1,
        universals2,
        universals2 - universals1,
        universals1 - universals2,
    )


def _calculate_particular_diffs(doc1: Dict, doc2: Dict):
    particulars1 = extract_particulars(doc1)
    particulars2 = extract_particulars(doc2)
    return (
        particulars1,
        particulars2,
        particulars2 - particulars1,
        particulars1 - particulars2,
    )


def _build_modified_entities(
    doc1: Dict, doc2: Dict, entities1: set, entities2: set
):
    modified_entities = {}
    for entity_name in entities1 & entities2:
        entity1 = doc1.get(entity_name, {})
        entity2 = doc2.get(entity_name, {})
        if isinstance(entity1, dict) and isinstance(entity2, dict):
            if entity1 != entity2:
                modified_entities[entity_name] = compare_entity_structure(
                    entity1, entity2
                )
    return modified_entities


def diff_documents(doc1: Dict, doc2: Dict) -> DiffResult:
    """Compare two OSED documents and return differences."""
    entities1, entities2, added_entities, removed_entities = (
        _calculate_entity_diffs(doc1, doc2)
    )
    _, _, added_universals, removed_universals = _calculate_universal_diffs(
        doc1, doc2
    )
    _, _, added_particulars, removed_particulars = _calculate_particular_diffs(
        doc1, doc2
    )

    schema_version_changed = doc1.get("osed") != doc2.get("osed")
    driver_changed = doc1.get("driver") != doc2.get("driver")
    modified_entities = _build_modified_entities(
        doc1, doc2, entities1, entities2
    )
    breaking_changes = detect_breaking_changes(doc1, doc2)
    impact_analysis = analyze_generated_code_impact(doc1, doc2)

    return DiffResult(
        added_entities=added_entities,
        removed_entities=removed_entities,
        modified_entities=modified_entities,
        added_universals=added_universals,
        removed_universals=removed_universals,
        added_particulars=added_particulars,
        removed_particulars=removed_particulars,
        schema_version_changed=schema_version_changed,
        driver_changed=driver_changed,
        breaking_changes=breaking_changes,
        impact_analysis=impact_analysis,
    )


def diff_schemas(doc1: Dict, doc2: Dict) -> DiffResult:
    """Compare two OSED schemas and return differences."""
    # Extract schema-specific elements
    properties1 = extract_schema_properties(doc1)
    properties2 = extract_schema_properties(doc2)
    definitions1 = extract_schema_definitions(doc1)
    definitions2 = extract_schema_definitions(doc2)

    # For schemas, we treat properties as entities and definitions as universals
    added_entities = properties2 - properties1
    removed_entities = properties1 - properties2
    added_universals = definitions2 - definitions1
    removed_universals = definitions1 - definitions2

    # Schemas don't have particulars
    added_particulars = set()
    removed_particulars = set()

    # Check for schema version changes
    schema_version_changed = doc1.get("$id") != doc2.get("$id")

    # Schemas don't have drivers
    driver_changed = False

    # Analyze modified properties
    modified_entities = {}
    for prop_name in properties1 & properties2:
        prop1 = doc1.get("properties", {}).get(prop_name, {})
        prop2 = doc2.get("properties", {}).get(prop_name, {})
        if prop1 != prop2:
            modified_entities[prop_name] = {
                "added_fields": [],
                "removed_fields": [],
                "modified_fields": [prop_name],
                "type_changes": [],
                "metadata_changes": [],
            }

    # Detect breaking changes for schemas
    breaking_changes = []
    if removed_entities:
        breaking_changes.append(
            f"Removed properties: {', '.join(removed_entities)}"
        )

    # Analyze impact on generated code
    impact_analysis = {
        "typescript": [],
        "mongoose": [],
        "validation": [],
        "compatibility": [],
        "migration": [],
    }

    if added_entities:
        impact_analysis["typescript"].append(
            f"New properties: {', '.join(added_entities)}"
        )
        impact_analysis["validation"].append(
            f"New required properties: {', '.join(added_entities)}"
        )
    if removed_entities:
        impact_analysis["typescript"].append(
            f"Removed properties: {', '.join(removed_entities)}"
        )
    if added_universals:
        impact_analysis["compatibility"].append(
            f"New definitions: {', '.join(added_universals)}"
        )
    if removed_universals:
        impact_analysis["compatibility"].append(
            f"Removed definitions: {', '.join(removed_universals)}"
        )

    return DiffResult(
        added_entities=added_entities,
        removed_entities=removed_entities,
        modified_entities=modified_entities,
        added_universals=added_universals,
        removed_universals=removed_universals,
        added_particulars=added_particulars,
        removed_particulars=removed_particulars,
        schema_version_changed=schema_version_changed,
        driver_changed=driver_changed,
        breaking_changes=breaking_changes,
        impact_analysis=impact_analysis,
    )


def diff_osed_documents(file1: Path, file2: Path) -> DiffResult:
    """Compare two OSED documents or schemas and return structured differences."""
    doc1 = load_osed_document(file1)
    doc2 = load_osed_document(file2)

    is_schema1 = is_schema_file(doc1)
    is_schema2 = is_schema_file(doc2)

    if is_schema1 != is_schema2:
        error(
            "Cannot compare schema file with document file",
            context=f"file1: {file1}, file2: {file2}",
            suggestions=[
                "Provide two schema files or two document files, not one of each."
            ],
        )
        raise ValueError("Cannot compare schema file with document file")

    if is_schema1:
        return diff_schemas(doc1, doc2)
    return diff_documents(doc1, doc2)


def format_diff_result(result: DiffResult, file1: Path, file2: Path) -> str:
    """Format the diff result for display."""
    output = []
    # Determine if this is a schema diff or document diff
    is_schema = (
        file1.name.endswith(".schema.yaml")
        or file2.name.endswith(".schema.yaml")
        or file1.name.startswith("schema")
        or file2.name.startswith("schema")
    )
    if is_schema:
        info(
            "OSED Schema Diff Analysis",
            context=f"file1: {file1}, file2: {file2}",
        )
        output.append("OSED Schema Diff Analysis")
    else:
        info(
            "OSED Document Diff Analysis",
            context=f"file1: {file1}, file2: {file2}",
        )
        output.append("OSED Document Diff Analysis")
    output.append("=" * 60)

    # Summary
    total_changes = (
        len(result.added_entities)
        + len(result.removed_entities)
        + len(result.modified_entities)
        + len(result.added_universals)
        + len(result.removed_universals)
        + len(result.added_particulars)
        + len(result.removed_particulars)
    )

    if total_changes == 0:
        info("No changes detected", context=f"file1: {file1}, file2: {file2}")
        output.append("✅ No changes detected")
        return "\n".join(output)

    # Entities
    if result.added_entities:
        output.append(
            f"Added properties: {', '.join(result.added_entities)}"
            if is_schema
            else f"Added entities: {', '.join(result.added_entities)}"
        )
    if result.removed_entities:
        output.append(
            f"Removed properties: {', '.join(result.removed_entities)}"
            if is_schema
            else f"Removed entities: {', '.join(result.removed_entities)}"
        )
    if result.modified_entities:
        output.append(
            f"Modified properties: {', '.join(result.modified_entities.keys())}"
            if is_schema
            else f"Modified entities: {', '.join(result.modified_entities.keys())}"
        )
        # Add detailed output for each modified entity/property
        for name, changes in result.modified_entities.items():
            output.append(f"{name}:")
            if changes.get("added_fields"):
                output.append(
                    f"  + Added: {', '.join(changes['added_fields'])}"
                )
            if changes.get("removed_fields"):
                output.append(
                    f"  - Removed: {', '.join(changes['removed_fields'])}"
                )
            if changes.get("modified_fields"):
                output.append(
                    f"  * Modified: {', '.join(changes['modified_fields'])}"
                )
            if changes.get("type_changes"):
                output.append(
                    f"  ~ Type changes: {', '.join(changes['type_changes'])}"
                )
            if changes.get("metadata_changes"):
                output.append(
                    f"  ~ Metadata changes: {', '.join(changes['metadata_changes'])}"
                )

    # Universals
    if result.added_universals:
        output.append(
            f"Added definitions: {', '.join(result.added_universals)}"
            if is_schema
            else f"Added universals: {', '.join(result.added_universals)}"
        )
    if result.removed_universals:
        output.append(
            f"Removed definitions: {', '.join(result.removed_universals)}"
            if is_schema
            else f"Removed universals: {', '.join(result.removed_universals)}"
        )

    # Particulars
    if result.added_particulars:
        output.append(
            f"Added particulars: {', '.join(result.added_particulars)}"
        )
    if result.removed_particulars:
        output.append(
            f"Removed particulars: {', '.join(result.removed_particulars)}"
        )

    # Schema version changes
    if result.schema_version_changed:
        warning(
            "Schema version changed",
            context=f"file1: {file1}, file2: {file2}",
            suggestions=[
                "Review schema changes for compatibility and migration impact."
            ],
        )
        output.append("Schema version changed")

    # Driver changes
    if result.driver_changed:
        warning(
            "Driver changed",
            context=f"file1: {file1}, file2: {file2}",
            suggestions=[
                "Check driver compatibility and update your application if needed."
            ],
        )
        output.append("Driver changed")

    # Breaking changes
    if result.breaking_changes:
        error(
            "Breaking changes detected in diff result.",
            context=f"file1: {file1}, file2: {file2}",
            suggestions=[
                "Review the breaking changes and update your code or data accordingly."
            ],
        )
        output.append("\nBreaking Changes:")
        for change in result.breaking_changes:
            output.append(f"  • {change}")

    # Impact analysis
    if result.impact_analysis:
        output.append("\nImpact Analysis:")
        for category, impacts in result.impact_analysis.items():
            if impacts:
                output.append(f"  {category.title()}:")
                for impact in impacts:
                    output.append(f"    • {impact}")

    return "\n".join(output)
