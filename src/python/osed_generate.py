"""
Generates Mongoose TypeScript schema artifacts from an OSED document.
"""

from pathlib import Path
import sys
from typing import Any, Dict, Tuple
import json
import re

from .osed_utils import get_arg_parser, load_yaml
from .osed_logging import info, error, warning

# Maps OSED universal types to Mongoose Schema type strings.
TYPE_MAP: Dict[str, str] = {
    "string": "String",
    "integer": "Number",
    "number": "Number",
    "boolean": "Boolean",
    "date": "Date",
    # Universals that don't map directly to a primitive
    "email": "String",
    "password": "String",
    "url": "String",
}

# Maps OSED universal types to TypeScript primitive types.
TS_TYPE_MAP: Dict[str, str] = {
    "string": "string",
    "integer": "number",
    "number": "number",
    "boolean": "boolean",
    "date": "Date",
    "email": "string",
    "password": "string",
    "url": "string",
}

# Valid Mongoose types for the new driver-based approach
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
}


def to_camel_case(snake_str: str) -> str:
    """Converts a snake_case or kebab-case string to camelCase."""
    parts = snake_str.replace("-", "_").split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


def to_pascal_case(snake_str: str) -> str:
    """Converts a snake_case or kebab-case string to PascalCase."""
    camel_case = to_camel_case(snake_str)
    return camel_case[0].upper() + camel_case[1:]


def _format_block(lines: list[str], indent_level: int, suffix: str = "") -> str:
    """Formats a list of lines into an indented block with braces."""
    if not lines:
        return f"{{{suffix}}}"
    indent = "  " * indent_level
    inner_indent = "  " * (indent_level + 1)
    formatted_lines = [f"{inner_indent}{line}" for line in lines]
    return "{\n" + "\n".join(formatted_lines) + f"\n{indent}}}{suffix}"


def is_driver_metadata(value: Any) -> bool:
    """Check if a value contains driver metadata keys (type, of, items, ref, etc.)."""
    if not isinstance(value, dict):
        return False
    # Check for driver-specific metadata keys
    driver_keys = {
        "type",
        "of",
        "items",
        "ref",
        "required",
        "unique",
        "index",
        "default",
        "enum",
    }
    # Don't treat already processed values as driver metadata
    # But allow map types with "value" key
    if (
        "type" in value
        and "value" in value
        and value.get("type") not in ("Map", "map")
    ):
        return False
    return any(key in value for key in driver_keys)


def _process_array_metadata(value, declared_entities, metadata):
    if "of" in value:
        items_type = value["of"]
        if items_type in declared_entities or "ref" in value:
            ref_entity = value.get("ref") or items_type
            processed_value = {
                "type": "array",
                "items": {"type": "reference", "ref": ref_entity},
            }
            if "ref" in value:
                metadata["ref"] = value["ref"]
        else:
            processed_value = {"type": "array", "items": items_type}
    elif "items" in value:
        items_type = value["items"]
        if isinstance(items_type, str) and (
            items_type in declared_entities or "ref" in value
        ):
            ref_entity = value.get("ref") or items_type
            processed_value = {
                "type": "array",
                "items": {"type": "reference", "ref": ref_entity},
            }
            if "ref" in value:
                metadata["ref"] = value["ref"]
        elif isinstance(items_type, dict):
            processed_value = {"type": "array", "items": items_type}
        else:
            processed_value = {"type": "array", "items": items_type}
    else:
        raise ValueError(f"type '{value['type']}' requires 'of' or 'items'")
    return processed_value


def _process_map_metadata(value, declared_entities):
    value_type = value.get("of") or value.get("value")
    if not value_type:
        raise ValueError("type 'map' requires 'of' or 'value'")
    if value_type in declared_entities or "ref" in value:
        ref_entity = value.get("ref") or value_type
        return {
            "type": "map",
            "value": {"type": "reference", "ref": ref_entity},
        }
    return {"type": "map", "value": value_type}


def _process_reference_metadata(value):
    if "ref" in value:
        ref_entity = value["ref"]
        return {"type": "reference", "ref": ref_entity}
    raise ValueError("type 'reference' requires 'ref'")


def _process_primitive_metadata(value):
    return value["type"]


def _process_no_type_metadata(value, declared_entities):
    if len(value) == 1 and list(value.keys())[0] in declared_entities:
        entity_name = list(value.keys())[0]
        return {"type": "reference", "ref": entity_name}
    return value


def _extract_metadata(value):
    metadata = {}
    for key, val in value.items():
        if key not in ("type", "of", "items", "ref"):
            metadata[key] = val
    return metadata


def process_driver_metadata(
    value: Any, declared_entities: set[str]
) -> Tuple[Any, Dict[str, Any]]:
    """
    Process driver metadata and extract the actual field definition.
    Returns: Tuple of (processed_value, metadata_dict)
    """
    if not isinstance(value, dict) or not is_driver_metadata(value):
        return value, {}
    metadata = {}
    processed_value = None
    if "type" in value:
        field_type = value["type"]
        metadata["type"] = field_type
        if field_type in ("Array", "array", "List", "list"):
            processed_value = _process_array_metadata(
                value, declared_entities, metadata
            )
        elif field_type in ("Map", "map"):
            processed_value = _process_map_metadata(value, declared_entities)
        elif field_type in ("ObjectId", "objectid", "reference"):
            processed_value = _process_reference_metadata(value)
        else:
            processed_value = _process_primitive_metadata(value)
    else:
        processed_value = _process_no_type_metadata(value, declared_entities)
    # Extract other metadata
    metadata.update(_extract_metadata(value))
    return processed_value, metadata


def get_entity_dependencies(
    value: Any, declared_entities: set[str]
) -> set[str]:
    """Recursively finds all references to other declared entities."""
    deps = set()

    # Process driver metadata first
    if isinstance(value, dict) and is_driver_metadata(value):
        processed_value, _ = process_driver_metadata(value, declared_entities)
        value = processed_value

    if isinstance(value, str):
        if value in declared_entities:
            deps.add(value)
    elif isinstance(value, list):
        for item in value:
            deps.update(get_entity_dependencies(item, declared_entities))
    elif isinstance(value, dict):
        for v in value.values():
            deps.update(get_entity_dependencies(v, declared_entities))
    return deps


def map_osed_to_typescript_type(value, declared_entities, indent_level=0):
    """Map OSED type to TypeScript type, handling primitives, lists, and maps."""
    # Handle primitive types
    if isinstance(value, str):
        if value == "string" or value == "email":
            return "string"
        if value == "number":
            return "number"
        if value == "boolean":
            return "boolean"
        if value == "date":
            return "Date"
        if value in declared_entities:
            return "Schema.Types.ObjectId"
        return "any"
    if isinstance(value, dict):
        t = value.get("type")
        if t == "reference" and value.get("ref") in declared_entities:
            return "Schema.Types.ObjectId"
        if t in ("array", "list"):
            items_type = map_osed_to_typescript_type(
                value["items"], declared_entities, indent_level
            )
            return f"{items_type}[]"
        if t == "map":
            value_type = map_osed_to_typescript_type(
                value["value"], declared_entities, indent_level
            )
            return f"Record<string, {value_type}>"
        if t == "boolean":
            return "boolean"
        if t == "string" or t == "email":
            return "string"
        if t == "number":
            return "number"
        if t == "date":
            return "Date"
    return "any"


def _typescript_type_for_str(value, declared_entities):
    """Return TypeScript type for a string value."""
    if value in declared_entities:
        return "Schema.Types.ObjectId"
    return TS_TYPE_MAP.get(value.lower(), "string")


def _typescript_type_for_list(value, declared_entities, indent_level):
    """Return TypeScript type for a list value."""
    if len(value) == 1:
        item_type = map_osed_to_typescript_type(
            value[0], declared_entities, indent_level
        )
        return f"{item_type}[]"
    item_types = [
        map_osed_to_typescript_type(item, declared_entities, indent_level)
        for item in value
    ]
    return f"({' | '.join(item_types)})[]"


def _typescript_type_for_dict(value, declared_entities, indent_level):
    """Return TypeScript type for a dict value."""
    if "type" in value:
        if value["type"] == "reference":
            return "Schema.Types.ObjectId"
        if value["type"] == "array":
            items_type = map_osed_to_typescript_type(
                value["items"], declared_entities, indent_level
            )
            return f"{items_type}[]"
        if value["type"] == "map":
            value_type = map_osed_to_typescript_type(
                value["value"], declared_entities, indent_level
            )
            return f"Record<string, {value_type}>"
        if value["type"] == "boolean":
            return "boolean"
        return "any"
    return "any"


def _typescript_type_for_other():
    """Return TypeScript type for other/unknown types."""
    return "any"


def map_osed_to_mongoose_field(value, declared_entities, indent_level=0):
    """
    Maps OSED values to Mongoose schema field definitions.
    Handles complex types like arrays, maps, and references.
    Always outputs classic Mongoose JS object literal.
    """
    if isinstance(value, str):
        return _mongoose_field_for_dict(value, declared_entities, indent_level)
    elif isinstance(value, list):
        return _mongoose_field_for_list(value, declared_entities, indent_level)
    elif isinstance(value, dict):
        return _mongoose_field_for_dict(value, declared_entities, indent_level)
    else:
        return _mongoose_field_for_other()


def _mongoose_field_for_str(value, declared_entities):
    if value in declared_entities:
        return "Schema.Types.ObjectId"
    mongoose_type = TYPE_MAP.get(value.lower(), "String")
    return f'{{"type": "{mongoose_type}"}}'


def _mongoose_field_for_list(value, declared_entities, indent_level):
    # Always render as an array of classic Mongoose type objects
    if len(value) == 1:
        item_type = _mongoose_field_for_dict(
            value[0], declared_entities, indent_level
        )
        return f"[{item_type}]"
    item_types = [
        _mongoose_field_for_dict(item, declared_entities, indent_level)
        for item in value
    ]
    return f"[{', '.join(item_types)}]"


def _mongoose_field_for_dict(value, declared_entities, indent_level):
    # Handle primitive types
    if isinstance(value, str):
        if value == "string" or value == "email":
            return "{ type: String }"
        if value == "number":
            return "{ type: Number }"
        if value == "boolean":
            return "{ type: Boolean }"
        if value == "date":
            return "{ type: Date }"
        if value in declared_entities:
            return "{ type: Schema.Types.ObjectId }"
        return "{ type: String }"
    if isinstance(value, dict):
        t = value.get("type")
        # Fix: always map 'reference' type to Schema.Types.ObjectId
        if t == "reference" and "ref" in value:
            ref_entity = value["ref"]
            # Capitalize entity name for ref
            ref_cap = ref_entity[0].upper() + ref_entity[1:]
            return f"{{ type: Schema.Types.ObjectId, ref: '{ref_cap}' }}"
        if t in ("array", "list"):
            items_schema = _mongoose_field_for_dict(
                value["items"], declared_entities, indent_level
            )
            return f"[{items_schema}]"
        if t == "map":
            value_schema = _mongoose_field_for_dict(
                value["value"], declared_entities, indent_level
            )
            return f"{{ type: Map, of: {value_schema} }}"
        if t == "boolean":
            return "{ type: Boolean }"
        if t == "string" or t == "email":
            return "{ type: String }"
        if t == "number":
            return "{ type: Number }"
        if t == "date":
            return "{ type: Date }"
    return "{ type: String }"


def _mongoose_field_for_other():
    return "Mixed"


def _js_literal(val):
    """Recursively convert a Python dict to a JS object literal string for Mongoose schemas."""
    if isinstance(val, dict):
        items = []
        for k, v in val.items():
            items.append(f"{k}: {_js_literal(v)}")
        return f"{{{', '.join(items)}}}"
    elif isinstance(val, list):
        return f"[{', '.join(_js_literal(x) for x in val)}]"
    elif isinstance(val, str):
        # For known JS types, don't quote
        if val in [
            "String",
            "Number",
            "Boolean",
            "Date",
            "Buffer",
            "ObjectId",
            "Mixed",
            "Map",
            "Schema.Types.ObjectId",
        ]:
            return val
        return f"'{val}'"
    elif isinstance(val, bool):
        return "true" if val else "false"
    elif val is None:
        return "null"
    else:
        return str(val)


def apply_driver_metadata(field_def: str, metadata: Dict[str, Any]) -> str:
    """
    Apply driver metadata (required, unique, index, default, enum) to a field definition.
    Output as a Mongoose JS object literal (never JSON).
    """

    # Convert the field_def string to a dict for merging
    def js_obj_to_dict(js_obj):
        js_obj = js_obj.replace(
            "Schema.Types.ObjectId", '"Schema.Types.ObjectId"'
        )
        js_obj = (
            js_obj.replace("String", '"String"')
            .replace("Number", '"Number"')
            .replace("Boolean", '"Boolean"')
            .replace("Date", '"Date"')
            .replace("Map", '"Map"')
        )
        js_obj = re.sub(r"([a-zA-Z0-9_]+):", r'"\1":', js_obj)
        js_obj = js_obj.replace("'", '"')
        return json.loads(js_obj)

    base_dict = js_obj_to_dict(field_def)
    base_dict.update(metadata)

    # Convert back to JS object literal
    def dict_to_js_obj(d):
        items = []
        canonical_types = {
            "String",
            "Boolean",
            "Number",
            "Date",
            "Schema.Types.ObjectId",
            "Map",
        }
        for k, v in d.items():
            if isinstance(v, dict):
                items.append(f"{k}: {dict_to_js_obj(v)}")
            elif isinstance(v, list):
                items.append(
                    f"{k}: [{', '.join(dict_to_js_obj(x) if isinstance(x, dict) else (x if (isinstance(x, str) and x in canonical_types) else repr(x) if isinstance(x, str) else str(x)) for x in v)}]"
                )
            elif isinstance(v, str) and v in canonical_types:
                items.append(f"{k}: {v}")
            elif isinstance(v, str) and v.startswith("Schema.Types."):
                items.append(f"{k}: {v}")
            elif isinstance(v, str):
                items.append(f"{k}: '{v}'")
            elif isinstance(v, bool):
                items.append(f"{k}: {'true' if v else 'false'}")
            else:
                items.append(f"{k}: {v}")
        return "{ " + ", ".join(items) + " }"

    return dict_to_js_obj(base_dict)


def generate_typescript_interface_content(
    description: Dict[str, Any], declared_entities: set[str], indent_level: int
) -> str:
    """Generate TypeScript interface content from entity description."""
    lines = []
    for field_name, field_value in description.items():
        if field_name in ("_id", "id"):  # Skip ID fields
            continue
        ts_type = map_osed_to_typescript_type(
            field_value, declared_entities, indent_level
        )
        lines.append(f"{field_name}: {ts_type};")
    return "\n".join(lines)


def generate_mongoose_schema_content(
    description: Dict[str, Any], declared_entities: set[str], indent_level: int
) -> str:
    """Generate Mongoose schema content from entity description."""
    lines = []
    for field_name, field_value in description.items():
        if field_name in ("_id", "id"):  # Skip ID fields
            continue
        # Process driver metadata
        processed_value, metadata = process_driver_metadata(
            field_value, declared_entities
        )
        # Always get the classic Mongoose type object
        mongoose_type = _mongoose_field_for_dict(
            processed_value, declared_entities, indent_level
        )

        # Merge metadata into the classic Mongoose object (if it's a dict)
        # Convert the mongoose_type string to a dict for merging
        # e.g., '{ type: String }' -> {"type": "String"}
        def js_obj_to_dict(js_obj):
            # crude conversion for simple cases
            js_obj = js_obj.replace(
                "Schema.Types.ObjectId", '"Schema.Types.ObjectId"'
            )
            js_obj = (
                js_obj.replace("String", '"String"')
                .replace("Number", '"Number"')
                .replace("Boolean", '"Boolean"')
                .replace("Date", '"Date"')
                .replace("Map", '"Map"')
            )
            js_obj = re.sub(r"([a-zA-Z0-9_]+):", r'"\1":', js_obj)
            js_obj = js_obj.replace("'", '"')
            return json.loads(js_obj)

        base_dict = js_obj_to_dict(mongoose_type)
        # Only merge metadata for primitives and references, not arrays/maps
        if (
            isinstance(base_dict, dict)
            and base_dict.get("type") not in ["Map"]
            and not isinstance(base_dict.get("type"), list)
        ):
            # Remove 'type' from metadata if it's 'reference' and processed_value is a reference
            if (
                metadata.get("type") == "reference"
                and isinstance(processed_value, dict)
                and processed_value.get("type") == "reference"
            ):
                metadata = {k: v for k, v in metadata.items() if k != "type"}
            base_dict.update(metadata)

        # Convert back to JS object literal
        def dict_to_js_obj(d):
            items = []
            canonical_types = {
                "String",
                "Boolean",
                "Number",
                "Date",
                "Schema.Types.ObjectId",
                "Map",
            }
            for k, v in d.items():
                # Fix: treat 'boolean' (lowercase) as canonical 'Boolean'
                if isinstance(v, str) and v.lower() == "boolean":
                    items.append(f"{k}: Boolean")
                elif isinstance(v, str) and v in canonical_types:
                    items.append(f"{k}: {v}")
                elif isinstance(v, str) and v.startswith("Schema.Types."):
                    items.append(f"{k}: {v}")
                elif isinstance(v, str):
                    items.append(f"{k}: '{v}'")
                elif isinstance(v, bool):
                    items.append(f"{k}: {'true' if v else 'false'}")
                else:
                    items.append(f"{k}: {v}")
            return "{ " + ", ".join(items) + " }"

        field_def = (
            dict_to_js_obj(base_dict)
            if isinstance(base_dict, dict)
            else mongoose_type
        )
        lines.append(f"{field_name}: {field_def},")
    return "\n".join(lines)


def generate_index_calls(
    description: Dict[str, Any], declared_entities: set[str], camel_name: str
) -> list[str]:
    """Generate Mongoose index calls for fields with index metadata."""
    index_calls = []
    for field_name, field_value in description.items():
        if field_name in ("_id", "id"):  # Skip ID fields
            continue
        # Process driver metadata
        _, metadata = process_driver_metadata(field_value, declared_entities)
        if metadata.get("index"):
            index_calls.append(
                f"{camel_name}Schema.index({{ {field_name}: 1 }});"
            )
    return index_calls


def generate_mongoose(document: Dict[str, Any], output_dir: Path) -> None:
    """
    Generate Mongoose TypeScript schema files from an OSED document.
    Creates individual model files for each entity and a consolidated interfaces file.
    """
    # Check for required 'driver' key
    driver = document.get("driver")
    if not driver:
        error(
            "Missing required 'driver' key in OSED document. Code generation aborted.",
            context=f"output_dir: {output_dir}",
            suggestions=[
                "Add a supported 'driver' key to your OSED document (e.g., 'mongoose')."
            ],
        )
        sys.exit(2)

    # Extract entities
    entities = document.get("entities", [])

    # Performance note: warn if too many entities
    if len(entities) > 50:
        warning(
            f"Large number of entities detected: {len(entities)}. Generation may be slow.",
            context=f"output_dir: {output_dir}",
            suggestions=[
                "Consider splitting your schema or optimizing your entity definitions."
            ],
        )

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate TypeScript interfaces
    interface_content = []
    interface_content.append("import { Schema } from 'mongoose';")
    interface_content.append("")

    # Generate interfaces for each entity
    for entity_name in entities:
        if entity_name in document:
            description = document[entity_name]
            if isinstance(description, dict):
                pascal_name = to_pascal_case(entity_name)
                interface_name = f"I{pascal_name}"

                # Warn if optional fields are missing (example: 'description')
                if "description" not in description:
                    warning(
                        f"Entity '{entity_name}' is missing an optional 'description' field.",
                        context=f"entity: {entity_name}",
                        suggestions=[
                            "Add a 'description' field to improve documentation and maintainability."
                        ],
                    )

                # Generate interface
                interface_content.append(
                    f"export interface {interface_name} {{"
                )
                interface_content.append("  _id?: Schema.Types.ObjectId;")
                interface_content.append(
                    generate_typescript_interface_content(
                        description, set(entities), 1
                    )
                )
                interface_content.append("}")
                interface_content.append("")

    # Write interfaces file
    interfaces_file = output_dir / "interfaces.ts"
    with open(interfaces_file, "w", encoding="utf-8") as f:
        f.write("\n".join(interface_content))

    # Generate individual model files for each entity
    for entity_name in entities:
        if entity_name in document:
            description = document[entity_name]
            if isinstance(description, dict):
                camel_name = to_camel_case(entity_name)
                pascal_name = to_pascal_case(entity_name)
                interface_name = f"I{pascal_name}"

                # Generate model file content
                model_content = []
                model_content.append(
                    "import { Schema, model } from 'mongoose';"
                )
                model_content.append(
                    f"import {{ {interface_name} }} from './interfaces.js';"
                )
                model_content.append("")

                # Generate schema
                model_content.append(
                    f"export const {camel_name}Schema = new Schema<{interface_name}>({{"
                )
                model_content.append(
                    generate_mongoose_schema_content(
                        description, set(entities), 1
                    )
                )
                model_content.append("});")
                model_content.append("")

                # Generate index calls
                index_calls = generate_index_calls(
                    description, set(entities), camel_name
                )
                for index_call in index_calls:
                    model_content.append(index_call)
                model_content.append("")

                # Generate model
                model_content.append(
                    f"export const {pascal_name} = model<{interface_name}>('{pascal_name}', {camel_name}Schema);"
                )
                model_content.append("")

                # Write individual model file
                model_file = output_dir / f"{entity_name}.model.ts"
                with open(model_file, "w", encoding="utf-8") as f:
                    f.write("\n".join(model_content))

    info(f"Generated Mongoose schemas in {output_dir}")
    info(f"  \ud83d\udcc4 Interfaces: {interfaces_file}")
    for entity_name in entities:
        if entity_name in document:
            model_file = output_dir / f"{entity_name}.model.ts"
            info(f"  \ud83d\udcc4 Model: {model_file}")


def main():
    """Main entry point for the generate command."""
    parser = get_arg_parser()
    parser.add_argument(
        "--target",
        required=True,
        choices=["mongoose"],
        help="The target framework to generate for",
    )
    parser.add_argument(
        "--out",
        default=".",
        help="Output directory for generated files",
    )

    args = parser.parse_args()

    # Load the OSED document
    document = load_yaml(args.file)

    # Generate based on target
    if args.target.lower() == "mongoose":
        try:
            generate_mongoose(document, Path(args.out))
        except Exception as e:
            error(
                f"Generation failed: {e}",
                context=f"target: {args.target}, out: {args.out}",
                suggestions=[
                    "Check your OSED document for errors.",
                    "Ensure the output directory is writable.",
                ],
            )
            sys.exit(1)
    else:
        error(
            f"Unknown target: {args.target}", context=f"target: {args.target}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
