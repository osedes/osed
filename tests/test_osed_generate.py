import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest

from src.python.osed_generate import (
    generate_mongoose,
    process_driver_metadata,
    is_driver_metadata,
    map_osed_to_typescript_type,
    map_osed_to_mongoose_field,
    apply_driver_metadata,
    generate_typescript_interface_content,
    generate_mongoose_schema_content,
)


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
        processed, metadata = process_driver_metadata(value, set())

        assert processed == "string"
        assert metadata["type"] == "string"

    def test_process_driver_metadata_boolean(self):
        """Test processing of boolean type metadata."""
        value = {"type": "boolean", "default": True}
        processed, metadata = process_driver_metadata(value, set())

        assert processed == "boolean"
        assert metadata["type"] == "boolean"
        assert metadata["default"] is True

    def test_process_driver_metadata_list(self):
        """Test processing of list type metadata."""
        value = {"type": "list", "items": "string"}
        processed, metadata = process_driver_metadata(value, set())

        assert processed["type"] == "array"
        assert processed["items"] == "string"

    def test_process_driver_metadata_list_with_ref(self):
        """Test processing of list type metadata with entity reference."""
        value = {"type": "list", "items": "user", "ref": "user"}
        processed, metadata = process_driver_metadata(value, {"user"})

        assert processed["type"] == "array"
        assert processed["items"]["type"] == "reference"
        assert processed["items"]["ref"] == "user"
        assert metadata["ref"] == "user"

    def test_process_driver_metadata_map(self):
        """Test processing of map type metadata."""
        value = {"type": "map", "value": "string"}
        processed, metadata = process_driver_metadata(value, set())

        assert processed["type"] == "map"
        assert processed["value"] == "string"

    def test_process_driver_metadata_reference(self):
        """Test processing of reference type metadata."""
        value = {"type": "reference", "ref": "user", "required": True}
        processed, metadata = process_driver_metadata(value, {"user"})

        assert processed["type"] == "reference"
        assert processed["ref"] == "user"
        assert metadata["required"] is True

    def test_process_driver_metadata_with_default(self):
        """Test processing of metadata with default values."""
        value = {"type": "date", "default": "now"}
        processed, metadata = process_driver_metadata(value, set())

        assert processed == "date"
        assert metadata["default"] == "now"

    def test_process_driver_metadata_with_unique(self):
        """Test processing of metadata with unique constraint."""
        value = {"type": "string", "unique": True}
        processed, metadata = process_driver_metadata(value, set())

        assert processed == "string"
        assert metadata["unique"] is True


class TestTypeMapping:
    """Test TypeScript and Mongoose type mapping functions."""

    def test_map_osed_to_typescript_type_primitive(self):
        """Test mapping of primitive types to TypeScript."""
        declared_entities = set()

        assert map_osed_to_typescript_type("string", declared_entities) == "string"
        assert map_osed_to_typescript_type("number", declared_entities) == "number"
        assert map_osed_to_typescript_type("boolean", declared_entities) == "boolean"
        assert map_osed_to_typescript_type("date", declared_entities) == "Date"

    def test_map_osed_to_typescript_type_entity_reference(self):
        """Test mapping of entity references to TypeScript."""
        declared_entities = {"user", "post"}

        result = map_osed_to_typescript_type("user", declared_entities)
        assert "Schema.Types.ObjectId" in result
        assert "IUser" in result

    def test_map_osed_to_typescript_type_list(self):
        """Test mapping of list types to TypeScript."""
        declared_entities = {"user"}

        # List of primitives
        list_value = {"type": "array", "items": "string"}
        result = map_osed_to_typescript_type(list_value, declared_entities)
        assert result == "string[]"

        # List of entities
        list_value = {"type": "array", "items": {"type": "reference", "ref": "user"}}
        result = map_osed_to_typescript_type(list_value, declared_entities)
        assert "Array<" in result
        assert "IUser" in result

    def test_map_osed_to_mongoose_field_primitive(self):
        """Test mapping of primitive types to Mongoose fields."""
        declared_entities = set()

        result = map_osed_to_mongoose_field("string", declared_entities)
        assert "{ type: String }" in result

        result = map_osed_to_mongoose_field("boolean", declared_entities)
        assert "{ type: Boolean }" in result

    def test_map_osed_to_mongoose_field_with_metadata(self):
        """Test mapping with metadata application."""
        declared_entities = set()

        # Test required field
        value = {"type": "string", "required": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert "{ type: String, required: true }" in result

        # Test default value
        value = {"type": "boolean", "default": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert "{ type: Boolean, default: true }" in result

        # Test unique field
        value = {"type": "string", "unique": True}
        result = map_osed_to_mongoose_field(value, declared_entities)
        assert "{ type: String, unique: true }" in result


class TestMetadataApplication:
    """Test metadata application to field definitions."""

    def test_apply_driver_metadata_required(self):
        """Test applying required metadata."""
        field_def = "{ type: String }"
        metadata = {"required": True}

        result = apply_driver_metadata(field_def, metadata)
        assert "{ type: String, required: true }" in result

    def test_apply_driver_metadata_default(self):
        """Test applying default metadata."""
        field_def = "{ type: Boolean }"
        metadata = {"default": True}

        result = apply_driver_metadata(field_def, metadata)
        assert "{ type: Boolean, default: true }" in result

    def test_apply_driver_metadata_default_now(self):
        """Test applying default 'now' for dates."""
        field_def = "{ type: Date }"
        metadata = {"default": "now"}

        result = apply_driver_metadata(field_def, metadata)
        assert "{ type: Date, default: Date.now }" in result

    def test_apply_driver_metadata_unique(self):
        """Test applying unique metadata."""
        field_def = "{ type: String }"
        metadata = {"unique": True}

        result = apply_driver_metadata(field_def, metadata)
        assert "{ type: String, unique: true }" in result

    def test_apply_driver_metadata_multiple(self):
        """Test applying multiple metadata properties."""
        field_def = "{ type: String }"
        metadata = {"required": True, "unique": True, "default": "test"}

        result = apply_driver_metadata(field_def, metadata)
        assert "{ type: String, required: true, unique: true, default: 'test' }" in result


class TestInterfaceAndSchemaGeneration:
    """Test interface and schema content generation."""

    def test_generate_typescript_interface_content(self):
        """Test TypeScript interface content generation."""
        description = {
            "name": "string",
            "email": "email",
            "age": "number",
            "isActive": {"type": "boolean", "default": True}
        }
        declared_entities = set()

        result = generate_typescript_interface_content(description, declared_entities, 1)

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
            "profile": {"type": "reference", "ref": "user", "required": True}
        }
        declared_entities = {"user"}

        result = generate_mongoose_schema_content(description, declared_entities, 1)

        assert "{ type: String }" in result
        assert "{ type: Boolean, default: true }" in result
        assert "{ type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true }" in result


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
                "isActive": {"type": "boolean", "default": True}
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            # Check that files were generated
            user_model_file = output_dir / "user.model.ts"
            assert user_model_file.exists()

            # Check file content
            content = user_model_file.read_text()
            assert "export interface IUser extends Document" in content
            assert "export const User = model<IUser>" in content
            assert "isActive: boolean;" in content
            assert "{ type: Boolean, default: true }" in content

    def test_generate_mongoose_with_references(self):
        """Test generating Mongoose files with entity references."""
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string"
            },
            "post": {
                "id": "string",
                "title": "string",
                "author": {"type": "reference", "ref": "user", "required": True}
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            # Check that both files were generated
            user_model_file = output_dir / "user.model.ts"
            post_model_file = output_dir / "post.model.ts"

            assert user_model_file.exists()
            assert post_model_file.exists()

            # Check that post model imports user model
            post_content = post_model_file.read_text()
            assert "import { IUser } from './user.model';" in post_content
            assert "author: Schema.Types.ObjectId | IUser;" in post_content

    def test_generate_mongoose_with_arrays(self):
        """Test generating Mongoose files with array types."""
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "tags": {"type": "list", "items": "string"},
                "posts": {"type": "list", "items": "post", "ref": "post"}
            },
            "post": {
                "id": "string",
                "title": "string"
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            user_model_file = output_dir / "user.model.ts"
            content = user_model_file.read_text()

            assert "tags: string[];" in content
            assert "posts: Array<" in content
            assert "[{ type: String }]" in content
            assert "[{ type: mongoose.Schema.Types.ObjectId, ref: 'Post' }]" in content

    def test_generate_mongoose_with_maps(self):
        """Test generating Mongoose files with map types."""
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "metadata": {"type": "map", "value": "string"}
            }
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            generate_mongoose(document, output_dir)

            user_model_file = output_dir / "user.model.ts"
            content = user_model_file.read_text()

            assert "metadata: Record<string, string>;" in content
            assert "{ type: Map, of: { type: String } }" in content


if __name__ == "__main__":
    pytest.main([__file__])
