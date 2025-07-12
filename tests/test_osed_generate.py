"""
Tests for OSED generation functionality.
"""

import json
import tempfile
from pathlib import Path
import io
from unittest.mock import patch

import pytest

from src.python.osed_generate import (
    apply_driver_metadata,
    generate_mongoose,
    generate_mongoose_schema_content,
    generate_typescript_interface_content,
    is_driver_metadata,
    map_osed_to_mongoose_field,
    map_osed_to_typescript_type,
    process_driver_metadata,
)
from src.python.osed_logging import set_logger, OSEDLogger


def json_equals(field_def: str, expected_json: str) -> bool:
    """
    Check if a field definition string equals the expected JSON structure.
    Uses standard Python json library for reliable comparison.
    """
    try:
        # Parse both as JSON objects
        field_obj = json.loads(field_def)
        expected_obj = json.loads(expected_json)

        # Direct dictionary comparison
        return field_obj == expected_obj
    except json.JSONDecodeError:
        # If either is not valid JSON, fall back to string comparison
        return expected_json in field_def


def field_contains(field_def: str, expected_pairs: dict) -> bool:
    """
    Check if a field definition string contains the expected key-value pairs.
    Uses json.loads() for reliable parsing.
    """
    try:
        field_obj = json.loads(field_def)

        # Check if all expected key-value pairs are present
        for key, value in expected_pairs.items():
            if key not in field_obj or field_obj[key] != value:
                return False
        return True
    except json.JSONDecodeError:
        # If not valid JSON, fall back to string comparison
        for key, value in expected_pairs.items():
            if isinstance(value, str):
                if (
                    f'"{key}": "{value}"' not in field_def
                    and f"'{key}': '{value}'" not in field_def
                ):
                    return False
            elif isinstance(value, bool):
                if (
                    f'"{key}": {str(value).lower()}' not in field_def
                    and f"'{key}': {str(value).lower()}" not in field_def
                ):
                    return False
            else:
                if (
                    f'"{key}": {value}' not in field_def
                    and f"'{key}': {value}" not in field_def
                ):
                    return False
        return True


class TestDriverMetadataProcessing:
    """Test driver metadata processing functions."""

    def test_is_driver_metadata(self):
        """Test detection of driver metadata objects."""
        # Valid driver metadata
        assert is_driver_metadata({"type": "string"})
        assert is_driver_metadata({"type": "list", "items": "string"})
        assert is_driver_metadata({"type": "reference", "ref": "user"})

        # Not driver metadata
        assert not is_driver_metadata("string")
        assert not is_driver_metadata(["string"])
        assert not is_driver_metadata({"mongoose:type": "string"})
        assert not is_driver_metadata({"mongoose:items": "string"})

    def test_process_driver_metadata_primitive(self):
        """Test processing of primitive type metadata."""
        value = {"type": "string"}
        processed, _ = process_driver_metadata(value, set())

        assert processed == "string"
        assert _["type"] == "string"

    def test_process_driver_metadata_boolean(self):
        """Test processing of boolean type metadata."""
        value = {"type": "boolean", "default": True}
        processed, _ = process_driver_metadata(value, set())

        assert processed == "boolean"
        assert _["type"] == "boolean"
        assert _["default"] is True

    def test_process_driver_metadata_list(self):
        """Test processing of list type metadata."""
        value = {"type": "list", "items": "string"}
        processed, _ = process_driver_metadata(value, set())

        assert processed["type"] == "array"
        assert processed["items"] == "string"

    def test_process_driver_metadata_list_with_ref(self):
        """Test processing of list type metadata with entity reference."""
        value = {"type": "list", "items": "user", "ref": "user"}
        processed, _ = process_driver_metadata(value, {"user"})

        assert processed["type"] == "array"
        assert processed["items"]["type"] == "reference"
        assert processed["items"]["ref"] == "user"
        assert _["ref"] == "user"

    def test_process_driver_metadata_map(self):
        """Test processing of map type metadata."""
        value = {"type": "map", "value": "string"}
        processed, _ = process_driver_metadata(value, set())

        assert processed["type"] == "map"
        assert processed["value"] == "string"

    def test_process_driver_metadata_reference(self):
        """Test processing of reference type metadata."""
        value = {"type": "reference", "ref": "user", "required": True}
        processed, _ = process_driver_metadata(value, {"user"})

        assert processed["type"] == "reference"
        assert processed["ref"] == "user"
        assert _["required"] is True

    def test_process_driver_metadata_with_default(self):
        """Test processing of metadata with default values."""
        value = {"type": "date", "default": "now"}
        processed, _ = process_driver_metadata(value, set())

        assert processed == "date"
        assert _["default"] == "now"

    def test_process_driver_metadata_with_unique(self):
        """Test processing of metadata with unique constraint."""
        value = {"type": "string", "unique": True}
        processed, _ = process_driver_metadata(value, set())

        assert processed == "string"
        assert _["unique"] is True


class TestTypeMapping:
    """Test TypeScript and Mongoose type mapping functions."""

    def test_map_osed_to_typescript_type_primitive(self):
        """Test mapping of primitive types to TypeScript."""
        declared_entities = set()

        assert (
            map_osed_to_typescript_type("string", declared_entities) == "string"
        )
        assert (
            map_osed_to_typescript_type("number", declared_entities) == "number"
        )
        assert (
            map_osed_to_typescript_type("boolean", declared_entities)
            == "boolean"
        )
        assert map_osed_to_typescript_type("date", declared_entities) == "Date"

    def test_map_osed_to_typescript_type_entity_reference(self):
        """Test mapping of entity references to TypeScript."""
        declared_entities = {"user", "post"}

        result = map_osed_to_typescript_type("user", declared_entities)
        assert "Schema.Types.ObjectId" in result
        # Note: IUser is now in separate interfaces file, not in the type mapping

    def test_map_osed_to_typescript_type_list(self):
        """Test mapping of list types to TypeScript."""
        declared_entities = {"user"}

        # List of primitives
        list_value = {"type": "array", "items": "string"}
        result = map_osed_to_typescript_type(list_value, declared_entities)
        assert result == "string[]"

        # List of entities
        list_value = {
            "type": "array",
            "items": {"type": "reference", "ref": "user"},
        }
        result = map_osed_to_typescript_type(list_value, declared_entities)
        assert "Schema.Types.ObjectId[]" in result
        # Note: IUser is now in separate interfaces file, not in the type mapping

    def test_map_osed_to_mongoose_field_primitive(self):
        """Test mapping of primitive types to Mongoose fields."""
        declared_entities = set()

        result = map_osed_to_mongoose_field("string", declared_entities)
        assert result == "{ type: String }"

        result = map_osed_to_mongoose_field("boolean", declared_entities)
        assert result == "{ type: Boolean }"

    def test_map_osed_to_mongoose_field_with_metadata(self):
        """Test mapping with metadata application."""
        declared_entities = set()

        # Test required field - map_osed_to_mongoose_field should only return the base type
        value = {"type": "string", "required": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert result == "{ type: String }"

        # Test default value
        value = {"type": "boolean", "default": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert result == "{ type: Boolean }"

        # Test unique field
        value = {"type": "string", "unique": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert result == "{ type: String }"


class TestMetadataApplication:
    """Test metadata application to field definitions."""

    def test_apply_driver_metadata_required(self):
        """Test applying required metadata."""
        field_def = "{ type: String }"
        metadata = {"required": True}
        result = apply_driver_metadata(field_def, metadata)
        assert result == "{ type: String, required: true }"

    def test_apply_driver_metadata_default(self):
        """Test applying default metadata."""
        field_def = "{ type: Boolean }"
        metadata = {"default": True}
        result = apply_driver_metadata(field_def, metadata)
        assert result == "{ type: Boolean, default: true }"

    def test_apply_driver_metadata_default_now(self):
        """Test applying default 'now' for dates."""
        field_def = "{ type: Date }"
        metadata = {"default": "now"}
        result = apply_driver_metadata(field_def, metadata)
        assert result == "{ type: Date, default: 'now' }"

    def test_apply_driver_metadata_unique(self):
        """Test applying unique metadata."""
        field_def = "{ type: String }"
        metadata = {"unique": True}
        result = apply_driver_metadata(field_def, metadata)
        assert result == "{ type: String, unique: true }"

    def test_apply_driver_metadata_multiple(self):
        """Test applying multiple metadata properties."""
        field_def = "{ type: String }"
        metadata = {"required": True, "unique": True, "default": "test"}
        result = apply_driver_metadata(field_def, metadata)
        assert (
            result
            == "{ type: String, required: true, unique: true, default: 'test' }"
        )


class TestInterfaceAndSchemaGeneration:
    """Test interface and schema content generation."""

    def test_generate_typescript_interface_content(self):
        """Test TypeScript interface content generation."""
        description = {
            "name": "string",
            "email": "email",
            "age": "number",
            "isActive": {"type": "boolean", "default": True},
        }
        declared_entities = set()

        result = generate_typescript_interface_content(
            description, declared_entities, 1
        )

        assert "name: string;" in result
        assert "email: string;" in result
        assert "age: number;" in result
        assert "isActive: boolean;" in result

    def test_generate_mongoose_schema_content(self):
        """Test Mongoose schema content generation."""
        description = {
            "name": "string",
            "email": "email",
            "isActive": {"type": "boolean", "default": True},
            "profile": {"type": "reference", "ref": "user", "required": True},
        }
        declared_entities = {"user"}

        result = generate_mongoose_schema_content(
            description, declared_entities, 1
        )

        assert "type: String" in result
        assert "type: Boolean, default: true" in result
        assert "Schema.Types.ObjectId" in result


class TestCodegenIntegration:
    """Test full codegen integration."""

    def test_generate_mongoose_simple_entity(self):
        """Test generating Mongoose files for a simple entity."""
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string", "email"],
            "user": {
                "id": "string",
                "name": "string",
                "email": "email",
                "isActive": {"type": "boolean", "default": True},
            },
            "driver": "mongoose",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            # Check that files were generated
            user_model_file = output_dir / "user.model.ts"
            interfaces_file = output_dir / "interfaces.ts"
            assert user_model_file.exists()
            assert interfaces_file.exists()

            # Check file content
            content = user_model_file.read_text()
            interfaces_content = interfaces_file.read_text()
            assert "import { IUser } from './interfaces.js'" in content
            assert "export const User = model<IUser>" in content
            assert "isActive: boolean;" in interfaces_content
            assert "{ type: Boolean, default: true }" in content

    def test_generate_mongoose_with_references(self):
        """Test generating Mongoose files with entity references."""
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["string"],
            "user": {"id": "string", "name": "string"},
            "post": {
                "id": "string",
                "title": "string",
                "author": {
                    "type": "reference",
                    "ref": "user",
                    "required": True,
                },
            },
            "driver": "mongoose",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            # Check that files were generated
            user_model_file = output_dir / "user.model.ts"
            post_model_file = output_dir / "post.model.ts"
            interfaces_file = output_dir / "interfaces.ts"

            assert user_model_file.exists()
            assert post_model_file.exists()
            assert interfaces_file.exists()

            # Check that models import from interfaces file
            post_content = post_model_file.read_text()
            interfaces_content = interfaces_file.read_text()
            assert "import { IPost } from './interfaces.js'" in post_content
            assert "author: Schema.Types.ObjectId;" in interfaces_content

    def test_generate_mongoose_with_arrays(self):
        """Test generating Mongoose files with array types."""
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "tags": {"type": "list", "items": "string"},
                "posts": {"type": "list", "items": "post", "ref": "post"},
            },
            "post": {"id": "string", "title": "string"},
            "driver": "mongoose",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            user_model_file = output_dir / "user.model.ts"
            interfaces_file = output_dir / "interfaces.ts"
            content = user_model_file.read_text()
            interfaces_content = interfaces_file.read_text()

            assert "tags: string[];" in interfaces_content
            assert "posts: Schema.Types.ObjectId[];" in interfaces_content
            assert "[{ type: String }]" in content
            assert "[{ type: Schema.Types.ObjectId, ref: 'Post' }]" in content

    def test_generate_mongoose_with_maps(self):
        """Test generating Mongoose files with map types."""
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "metadata": {"type": "map", "value": "string"},
            },
            "driver": "mongoose",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            user_model_file = output_dir / "user.model.ts"
            interfaces_file = output_dir / "interfaces.ts"
            content = user_model_file.read_text()
            interfaces_content = interfaces_file.read_text()

            assert "metadata: Record<string, string>;" in interfaces_content
            assert "{ type: Map, of: {'type': 'String'} }" in content


class TestGenerateLogging:
    """Test severity-based logging output in osed_generate.py."""

    def test_logging_for_missing_optional_field(self, tmp_path):
        # Entity missing 'description' field should trigger a warning
        doc = {
            "entities": ["user"],
            "user": {"id": "systemId"},
            "driver": "mongoose",
        }
        output_dir = tmp_path / "output"
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            generate_mongoose(doc, output_dir)
            warn_output = fake_stderr.getvalue()
            assert "missing an optional 'description' field" in warn_output
            assert (
                "Add a 'description' field to improve documentation"
                in warn_output
            )

    def test_logging_for_performance_warning(self, tmp_path):
        # Large number of entities should trigger a performance warning
        doc = {
            "entities": [f"entity{i}" for i in range(51)],
            "driver": "mongoose",
        }
        for i in range(51):
            doc[f"entity{i}"] = {"id": "systemId"}
        output_dir = tmp_path / "output"
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            generate_mongoose(doc, output_dir)
            warn_output = fake_stderr.getvalue()
            assert "Large number of entities detected" in warn_output
            assert (
                "Consider splitting your schema or optimizing your entity definitions"
                in warn_output
            )

    @pytest.mark.xfail(
        reason="generate_mongoose does not currently log errors for invalid entities; should be improved in future."
    )
    def test_logging_for_generation_error(self, tmp_path):
        # Trigger a generation error by passing an invalid document
        doc = {"entities": ["user"], "user": ["not", "a", "dict"]}
        output_dir = tmp_path / "output"
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            try:
                generate_mongoose(doc, output_dir)
            except Exception:
                pass  # We only care about logging
            err_output = fake_stderr.getvalue()
            assert (
                "Generation failed" in err_output
                or "error" in err_output.lower()
            )


if __name__ == "__main__":
    pytest.main([__file__])
