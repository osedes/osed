"""
Generates Mongoose TypeScript schema artifacts from an OSED document.
"""

import json
from pathlib import Path
import sys
from typing import Any, Dict, Tuple
import argparse
from .osed_utils import get_arg_parser, load_yaml

# Maps OSED universal types to Mongoose Schema constructor names.
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
    "String", "string", "Number", "number", "Date", "date", "Buffer", "buffer",
    "Boolean", "boolean", "Mixed", "mixed", "ObjectId", "objectid", "Array", "array",
    "List", "list", "Decimal128", "decimal128", "Map", "map", "Schema", "schema",
    "UUID", "uuid", "BigInt", "bigint", "Double", "double", "Int32", "int32"
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
  return f"{{\n" + "\n".join(formatted_lines) + f"\n{indent}}}{suffix}"


def is_driver_metadata(value: Any) -> bool:
  """Check if a value contains driver metadata keys (type, of, items, ref, etc.)."""
  if not isinstance(value, dict):
    return False
  # Check for driver-specific metadata keys
  driver_keys = {"type", "of", "items", "ref", "required", "unique", "index", "default", "enum"}
  # Don't treat already processed values as driver metadata
  if "type" in value and "value" in value:
    return False
  return any(key in value for key in driver_keys)


def process_driver_metadata(
  value: Any, declared_entities: set[str]
) -> Tuple[Any, Dict[str, Any]]:
  """
  Process driver metadata and extract the actual field definition.

  Returns:
    Tuple of (processed_value, metadata_dict)
  """
  if not isinstance(value, dict):
    return value, {}

  # Check if this is a driver metadata object
  if not is_driver_metadata(value):
    return value, {}

  metadata = {}
  processed_value = None

  # Extract type
  if "type" in value:
    field_type = value["type"]
    metadata["type"] = field_type

    # Handle different field types
    if field_type in ("Array", "array", "List", "list"):
      if "of" in value:
        items_type = value["of"]
        # Check if this should be treated as a reference (either items_type is an entity or there's a ref field)
        if items_type in declared_entities or "ref" in value:
          # Reference to another entity
          ref_entity = value.get("ref") or items_type
          processed_value = {
            "type": "array",
            "items": {"type": "reference", "ref": ref_entity}
          }
          if "ref" in value:
            metadata["ref"] = value["ref"]
        else:
          # Primitive type array
          processed_value = {
            "type": "array",
            "items": items_type
          }
      elif "items" in value:
        items_type = value["items"]
        if isinstance(items_type, str) and (items_type in declared_entities or "ref" in value):
          # Reference to another entity
          ref_entity = value.get("ref") or items_type
          processed_value = {
            "type": "array",
            "items": {"type": "reference", "ref": ref_entity}
          }
          if "ref" in value:
            metadata["ref"] = value["ref"]
        elif isinstance(items_type, dict):
          # Items is already a processed structure
          processed_value = {
            "type": "array",
            "items": items_type
          }
        else:
          # Primitive type array
          processed_value = {
            "type": "array",
            "items": items_type
          }
      else:
        raise ValueError(f"type '{field_type}' requires 'of' or 'items'")

    elif field_type in ("Map", "map"):
      if "of" in value:
        value_type = value["of"]
        # Check if this should be treated as a reference (either value_type is an entity or there's a ref field)
        if value_type in declared_entities or "ref" in value:
          ref_entity = value.get("ref") or value_type
          processed_value = {
            "type": "map",
            "value": {"type": "reference", "ref": ref_entity}
          }
        else:
          processed_value = {
            "type": "map",
            "value": value_type
          }
      else:
        print(f"DEBUG: value keys: {list(value.keys())}, value: {value}")
        raise ValueError("type 'map' requires 'of'")

    elif field_type in ("ObjectId", "objectid", "reference"):
      if "ref" in value:
        ref_entity = value["ref"]
        processed_value = {
          "type": "reference",
          "ref": ref_entity
        }
      else:
        raise ValueError("type 'reference' requires 'ref'")

    else:
      # Primitive type
      processed_value = field_type

  else:
    # No type, treat as primitive or entity reference
    if len(value) == 1 and list(value.keys())[0] in declared_entities:
      # Direct entity reference
      entity_name = list(value.keys())[0]
      processed_value = {
        "type": "reference",
        "ref": entity_name
      }
    else:
      # Fallback to original value
      processed_value = value

  # Extract other metadata
  for key, val in value.items():
    if key in ("type", "of", "items", "ref"):  # Skip these as they're already processed
      continue
    metadata[key] = val

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


def map_osed_to_typescript_type(
    value: Any, declared_entities: set[str], indent_level: int = 0
) -> str:
  """Recursively maps an OSED value to a TypeScript type definition string."""

  # Process driver metadata first
  if isinstance(value, dict) and is_driver_metadata(value):
    processed_value, metadata = process_driver_metadata(value, declared_entities)
    value = processed_value

  if isinstance(value, str):
    if value in declared_entities:
      pascal_case_ref = to_pascal_case(value)
      return f"Schema.Types.ObjectId | I{pascal_case_ref}"
    return TS_TYPE_MAP.get(value.lower(), "string")

  if isinstance(value, list) and all(isinstance(v, str) for v in value):
    return " | ".join(f"'{v}'" for v in value)

  if isinstance(value, dict):
    # Handle processed value descriptions
    if "type" in value:
      type_val = value["type"]
      if type_val in ("array", "list"):
        if "items" in value:
          item_type = map_osed_to_typescript_type(
              value["items"], declared_entities, indent_level
          )
          # Use Array<T> for complex/union types for better readability
          if "{" in item_type or "|" in item_type:
            return f"Array<{item_type}>"
          return f"{item_type}[]"
        else:
          return "any[]"
      elif type_val == "map":
        if "value" in value:
          value_type = map_osed_to_typescript_type(
              value["value"], declared_entities, indent_level
          )
          return f"Record<string, {value_type}>"
        else:
          return "Record<string, any>"
      elif type_val == "reference":
        if "ref" in value:
          ref_entity = value["ref"]
          if ref_entity in declared_entities:
            pascal_case_ref = to_pascal_case(ref_entity)
            return f"Schema.Types.ObjectId | I{pascal_case_ref}"
          else:
            return "any"
        else:
          return "any"

    # Handle nested objects (sub-schemas)
    closing_brace_indent = "  " * indent_level
    interface_content = generate_typescript_interface_content(
        value, declared_entities, indent_level + 1
    )
    return f"{{\n{interface_content}\n{closing_brace_indent}}}"

  # Fallback for unsupported structures
  return "any"


def map_osed_to_mongoose_field(
    value: Any, declared_entities: set[str], indent_level: int = 0
) -> str:
  """
  Recursively maps a single OSED value description to a Mongoose field
  definition string.
  """

  # Process driver metadata first
  metadata = {}
  if isinstance(value, dict) and is_driver_metadata(value):
    processed_value, metadata = process_driver_metadata(value, declared_entities)
    value = processed_value

  if isinstance(value, str):
    # Case 1: It's a reference to another entity
    if value in declared_entities:
      field_def = f"{{ type: mongoose.Schema.Types.ObjectId, ref: '{to_pascal_case(value)}' }}"
    # Case 2: It's a universal primitive type
    else:
      mongoose_type = TYPE_MAP.get(value.lower(), "String")
      field_def = f"{{ type: {mongoose_type} }}"

    # Apply metadata
    return apply_driver_metadata(field_def, metadata)

  if isinstance(value, list) and all(isinstance(v, str) for v in value):
    # Case 3: It's a flat list of strings (enum)
    enum_values = json.dumps(value)
    field_def = f"{{ type: String, enum: {enum_values} }}"
    return apply_driver_metadata(field_def, metadata)

  if isinstance(value, dict):
    # Handle processed value descriptions
    if "type" in value:
      type_val = value["type"]
      if type_val in ("array", "list"):
        if "items" in value:
          item_type_def = map_osed_to_mongoose_field(
              value["items"], declared_entities, indent_level
          )
          field_def = f"[{item_type_def}]"
        else:
          field_def = "[{ type: mongoose.Schema.Types.Mixed }]"
        return apply_driver_metadata(field_def, metadata)
      elif type_val == "map":
        if "value" in value:
          value_type_def = map_osed_to_mongoose_field(
              value["value"], declared_entities, indent_level
          )
          field_def = f"{{ type: Map, of: {value_type_def} }}"
        else:
          field_def = "{ type: Map, of: mongoose.Schema.Types.Mixed }"
        return apply_driver_metadata(field_def, metadata)
      elif type_val == "reference":
        if "ref" in value:
          ref_entity = value["ref"]
          if ref_entity in declared_entities:
            field_def = f"{{ type: mongoose.Schema.Types.ObjectId, ref: '{to_pascal_case(ref_entity)}' }}"
          else:
            field_def = "{ type: mongoose.Schema.Types.Mixed }"
        else:
          field_def = "{ type: mongoose.Schema.Types.Mixed }"
        return apply_driver_metadata(field_def, metadata)

    # Case 4: It's a nested object (sub-schema)
    closing_brace_indent = "  " * indent_level
    sub_schema_content = generate_mongoose_schema_content(
        value, declared_entities, indent_level + 1
    )
    field_def = f"{{\n{sub_schema_content}\n{closing_brace_indent}}}"
    return apply_driver_metadata(field_def, metadata)

  # Fallback for unsupported structures
  print(
      f"⚠️  Warning: Unsupported OSED structure '{value}'. Falling back to 'Mixed' type. "
      "This disables type validation and change tracking for this field.",
      file=sys.stderr,
  )
  field_def = "{ type: mongoose.Schema.Types.Mixed }"
  return apply_driver_metadata(field_def, metadata)


def apply_driver_metadata(field_def: str, metadata: Dict[str, Any]) -> str:
  """Apply driver metadata to a field definition."""
  if not metadata:
    return field_def

  # Remove the outer braces to add metadata
  if field_def.startswith("{") and field_def.endswith("}"):
    inner_content = field_def[1:-1].strip()
  else:
    return field_def

  # Add metadata properties
  for key, value in metadata.items():
    if key in ("type", "ref"):  # Skip these as they're already in the field definition
      continue
    elif key == "required" and value is True:
      inner_content += ", required: true"
    elif key == "default":
      if isinstance(value, str) and value == "now":
        inner_content += ", default: Date.now"
      elif isinstance(value, bool):
        inner_content += f", default: {str(value).lower()}"
      else:
        # Use single quotes for consistency
        if isinstance(value, str):
          inner_content += f", default: '{value}'"
        else:
          inner_content += f", default: {json.dumps(value)}"
    elif key == "unique" and value is True:
      inner_content += ", unique: true"
    elif key == "index" and value is True:
      inner_content += ", index: true"
    elif key == "enum":
      enum_values = json.dumps(value)
      inner_content += f", enum: {enum_values}"

  return f"{{ {inner_content} }}"


def generate_typescript_interface_content(
    description: Dict[str, Any], declared_entities: set[str], indent_level: int
) -> str:
  """Generates the inner content for a TypeScript interface."""
  fields = []
  indent = "  " * indent_level
  for key, value in description.items():
    camel_key = to_camel_case(key)

    # Let map_osed_to_typescript_type handle all the processing
    ts_type = map_osed_to_typescript_type(
        value, declared_entities, indent_level
    )
    fields.append(f"{indent}{camel_key}: {ts_type};")
  return "\n".join(fields)


def generate_mongoose_schema_content(
    description: Dict[str, Any], declared_entities: set[str], indent_level: int
) -> str:
  """
  Generates the inner content (the fields) for a Mongoose schema from an
  OSED description object.
  """
  fields = []
  indent = "  " * indent_level
  for key, value in description.items():
    camel_key = to_camel_case(key)

    # Let map_osed_to_mongoose_field handle all the processing
    field_definition = map_osed_to_mongoose_field(
        value, declared_entities, indent_level
    )

    fields.append(f"{indent}{camel_key}: {field_definition}")
  return ",\n".join(fields)


def generate_index_calls(
    description: Dict[str, Any], declared_entities: set[str], camel_name: str
) -> list[str]:
  """
  Generates explicit index calls for fields that have index: true.
  Returns a list of index call strings.
  """
  index_calls = []

  for key, value in description.items():
    if isinstance(value, dict) and is_driver_metadata(value):
      processed_value, metadata = process_driver_metadata(value, declared_entities)

      # Check if this field has index: true
      if metadata.get("index") is True:
        camel_key = to_camel_case(key)
        index_options = {}

        # Add unique option if field is also unique
        if metadata.get("unique") is True:
          index_options["unique"] = True

        if index_options:
          options_str = ", " + json.dumps(index_options)
        else:
          options_str = ""

        index_calls.append(f"{camel_name}Schema.index({{ {camel_key}: 1 }}{options_str});")

  return index_calls


def generate_mongoose(document: Dict[str, Any], output_dir: Path) -> None:
  """
  Generates Mongoose TypeScript model and enum files from an OSED document.

  This function iterates through the entities declared in the document.
  - If an entity's description is a dictionary, it's treated as a schema
    and a `.model.ts` file is generated.
  - If an entity's description is a list of strings, it's treated as an
    enum and a `.enum.ts` file is generated.

  Args:
      document: The loaded OSED YAML document as a dictionary.
      output_dir: The directory where the generated files will be written.
  """
  if not output_dir.exists():
    print(f"📁 Creating output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

  declared_entities = set(document.get("entities", []))
  # Filter the document to only include descriptions for declared entities.
  entity_descriptions = {
      k: v for k, v in document.items() if k in declared_entities
  }

  for entity_name, description in entity_descriptions.items():
    pascal_name = to_pascal_case(entity_name)
    camel_name = to_camel_case(entity_name)

    file_content = ""
    output_filename = ""

    # Generate a Mongoose TypeScript Model for dictionary-based entities
    if isinstance(description, dict):
      # Find dependencies to generate import statements
      dependencies = get_entity_dependencies(
          description, declared_entities
      )
      import_statements = []
      for dep in sorted(list(dependencies)):
        dep_pascal = to_pascal_case(dep)
        dep_camel = to_camel_case(dep)
        import_statements.append(
            f"import {{ I{dep_pascal} }} from './{dep_camel}.model';"
        )
      import_block = "\n".join(import_statements)

      interface_name = f"I{pascal_name}"
      interface_content = generate_typescript_interface_content(
          description, declared_entities, indent_level=1
      )
      schema_content = generate_mongoose_schema_content(
          description, declared_entities, indent_level=1
      )
      index_calls = generate_index_calls(description, declared_entities, camel_name)

      template = f"""
import mongoose, {{ Document, Schema, model }} from "mongoose";
{import_block}

export interface {interface_name} extends Document {{
{interface_content}
}}

const {camel_name}Schema = new Schema<{interface_name}>(
  {{
{schema_content}
  }},
  {{ timestamps: true }}
);

{chr(10).join(index_calls)}

export const {pascal_name} = model<{interface_name}>("{pascal_name}", {camel_name}Schema);
"""
      file_content = template.strip() + "\n"
      output_filename = f"{camel_name}.model.ts"

    # Generate a TypeScript Enum for list-based entities
    elif isinstance(description, list) and all(
        isinstance(v, str) for v in description
    ):
      enum_name = f"{pascal_name}Enum"
      type_name = pascal_name
      enum_values = json.dumps(description, indent=2)
      template = f"""
export const {enum_name} = {enum_values} as const;

export type {type_name} = typeof {enum_name}[number];
"""
      file_content = template.strip() + "\n"
      output_filename = f"{camel_name}.enum.ts"

    if file_content and output_filename:
      output_path = output_dir / output_filename
      print(f"✅ Writing Mongoose TypeScript artifact to {output_path}")
      output_path.write_text(file_content, encoding="utf-8")


def main():
    parser = get_arg_parser()
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for generated code."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target driver for code generation (e.g., 'mongoose')."
    )
    args = parser.parse_args()

    # Load the OSED YAML file
    data_path = Path(args.file)
    if not data_path.exists():
        print(f"❌ Data file not found: '{data_path}'")
        sys.exit(1)
    document = load_yaml(data_path)

    # Output directory
    output_dir = Path(args.out)

    # Only support mongoose for now
    if args.target not in {"mongoose", "mongoose-mongo", "mongoose-mongodb"}:
        print(f"❌ Unsupported target: {args.target}")
        sys.exit(1)

    print(f"🚀 Generating mongoose TypeScript schema from {data_path} into {output_dir}")
    generate_mongoose(document, output_dir)

if __name__ == "__main__":
    main()
