"""
Tests for OSED diff functionality.
"""

from pathlib import Path
from unittest.mock import patch
import pytest
import io

from src.python.osed_diff import (
    DiffResult,
    load_osed_document,
    is_schema_file,
    is_osed_document,
    extract_entities,
    extract_universals,
    extract_particulars,
    extract_schema_properties,
    extract_schema_definitions,
    compare_entity_structure,
    detect_breaking_changes,
    analyze_generated_code_impact,
    diff_osed_documents,
    diff_documents,
    diff_schemas,
    format_diff_result,
    colorize,
    wrap_text,
    supports_color,
)

from src.python.osed_cli import diff_command
from src.python import osed_logging


class TestDiffCoreFunctions:
    """Test core diff functionality."""

    def test_load_osed_document_valid(self):
        """Test loading a valid OSED document."""
        test_file = Path("sample/osed.v0.3.0.yaml")
        result = load_osed_document(test_file)
        assert isinstance(result, dict)
        assert "entities" in result
        assert "osed" in result

    def test_load_osed_document_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML file."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")

        with pytest.raises(RuntimeError, match="Failed to load OSED document"):
            load_osed_document(invalid_file)

    def test_load_osed_document_not_dict(self, tmp_path):
        """Test loading YAML that's not a dictionary."""
        invalid_file = tmp_path / "list.yaml"
        invalid_file.write_text("- item1\n- item2")

        with pytest.raises(RuntimeError, match="Failed to load OSED document"):
            load_osed_document(invalid_file)

    def test_is_schema_file(self):
        """Test schema file detection."""
        schema_doc = {"$schema": "http://json-schema.org/draft/2020-12/schema"}
        assert is_schema_file(schema_doc) is True

        doc_doc = {"entities": [], "osed": "0.3.0"}
        assert is_schema_file(doc_doc) is False

    def test_is_osed_document(self):
        """Test OSED document detection."""
        doc = {"entities": [], "osed": "0.3.0"}
        assert is_osed_document(doc) is True

        schema = {"$schema": "http://json-schema.org/draft/2020-12/schema"}
        assert is_osed_document(schema) is False

    def test_extract_entities(self):
        """Test entity extraction from OSED document."""
        doc = {
            "entities": ["user", "post", "comment"],
            "user": {"id": "systemId"},
            "post": {"id": "systemId"},
        }
        entities = extract_entities(doc)
        assert entities == {"user", "post", "comment"}

    def test_extract_universals(self):
        """Test universal extraction from OSED document."""
        doc = {
            "universals": [
                "name",
                "description",
                {"contact": ["email", "phone"]},
            ]
        }
        universals = extract_universals(doc)
        assert universals == {
            "name",
            "description",
            "contact",
            "email",
            "phone",
        }

    def test_extract_particulars(self):
        """Test particular extraction from OSED document."""
        doc = {
            "particulars": [
                "systemId",
                {"Employee": ["position", "department"]},
            ]
        }
        particulars = extract_particulars(doc)
        assert particulars == {"systemId", "Employee", "position", "department"}

    def test_extract_schema_properties(self):
        """Test schema property extraction."""
        doc = {
            "properties": {
                "osed": {"type": "string"},
                "entities": {"type": "array"},
            },
            "definitions": {
                "entityNamePattern": {
                    "properties": {"pattern": {"type": "string"}}
                }
            },
        }
        properties = extract_schema_properties(doc)
        assert properties == {"osed", "entities", "pattern"}

    def test_extract_schema_definitions(self):
        """Test schema definition extraction."""
        doc = {
            "definitions": {
                "entityNamePattern": {},
                "semanticNode": {},
                "valueDescription": {},
            }
        }
        definitions = extract_schema_definitions(doc)
        assert definitions == {
            "entityNamePattern",
            "semanticNode",
            "valueDescription",
        }

    def test_compare_entity_structure(self):
        """Test entity structure comparison."""
        entity1 = {"id": "systemId", "name": "string", "email": "email"}
        entity2 = {
            "id": "systemId",
            "name": "string",
            "email": "email",
            "avatar": "string",
        }

        changes = compare_entity_structure(entity1, entity2)
        # Sort both lists to handle set ordering
        assert sorted(changes["added_fields"]) == sorted(["avatar"])
        assert not changes["removed_fields"]
        assert not changes["modified_fields"]

    def test_compare_entity_structure_removed_fields(self):
        """Test entity structure comparison with removed fields."""
        entity1 = {
            "id": "systemId",
            "name": "string",
            "email": "email",
            "avatar": "string",
        }
        entity2 = {"id": "systemId", "name": "string"}

        changes = compare_entity_structure(entity1, entity2)
        assert not changes["added_fields"]
        # Sort both lists to handle set ordering
        assert sorted(changes["removed_fields"]) == sorted(["email", "avatar"])

    def test_compare_entity_structure_modified_fields(self):
        """Test entity structure comparison with modified fields."""
        entity1 = {"id": "systemId", "name": "string"}
        entity2 = {"id": "systemId", "name": "complex"}

        changes = compare_entity_structure(entity1, entity2)
        assert not changes["added_fields"]
        assert not changes["removed_fields"]
        assert changes["modified_fields"] == ["name"]

    def test_detect_breaking_changes(self):
        """Test breaking changes detection."""
        doc1 = {
            "entities": ["user", "post"],
            "user": {"id": "systemId", "name": "string"},
            "post": {"id": "systemId", "title": "string"},
        }
        doc2 = {"entities": ["user"], "user": {"id": "systemId"}}

        breaking_changes = detect_breaking_changes(doc1, doc2)
        assert "Removed entities: post" in breaking_changes
        assert "Removed fields in user: name" in breaking_changes

    def test_analyze_generated_code_impact(self):
        """Test generated code impact analysis."""
        doc1 = {"entities": ["user"], "user": {"id": "systemId"}}
        doc2 = {
            "entities": ["user", "post"],
            "user": {"id": "systemId", "name": "string"},
            "post": {"id": "systemId"},
        }

        impact = analyze_generated_code_impact(doc1, doc2)
        assert "New interfaces: post" in impact["typescript"]
        assert "New schemas: post" in impact["mongoose"]
        assert "Added fields to user: name" in impact["typescript"]


class TestDiffDocuments:
    """Test document diff functionality."""

    def test_diff_documents_same(self):
        """Test diffing identical documents."""
        doc = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["name"],
            "particulars": ["systemId"],
            "user": {"id": "systemId"},
        }

        result = diff_documents(doc, doc)
        assert not result.added_entities
        assert not result.removed_entities
        assert not result.breaking_changes

    def test_diff_documents_different(self):
        """Test diffing different documents."""
        doc1 = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["name"],
            "particulars": ["systemId"],
            "user": {"id": "systemId"},
        }
        doc2 = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["name", "description"],
            "particulars": ["systemId"],
            "user": {"id": "systemId", "name": "string"},
            "post": {"id": "systemId"},
        }

        result = diff_documents(doc1, doc2)
        assert result.added_entities == {"post"}
        assert result.added_universals == {"description"}
        assert (
            "Added fields to user: name" in result.impact_analysis["typescript"]
        )

    def test_diff_documents_breaking_changes(self):
        """Test diffing documents with breaking changes."""
        doc1 = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "user": {"id": "systemId", "name": "string"},
            "post": {"id": "systemId"},
        }
        doc2 = {
            "osed": "0.3.0",
            "entities": ["user"],
            "user": {"id": "systemId"},
        }

        result = diff_documents(doc1, doc2)
        assert result.removed_entities == {"post"}
        assert result.removed_universals == set()
        assert "Removed entities: post" in result.breaking_changes


class TestDiffSchemas:
    """Test schema diff functionality."""

    def test_diff_schemas_same(self):
        """Test diffing identical schemas."""
        schema = {
            "version": "0.3.0",
            "properties": {
                "osed": {"type": "string"},
                "entities": {"type": "array"},
            },
            "definitions": {"entityNamePattern": {}},
        }

        result = diff_schemas(schema, schema)
        assert not result.added_entities
        assert not result.removed_entities
        assert not result.breaking_changes

    def test_diff_schemas_different(self):
        """Test diffing different schemas."""
        schema1 = {
            "version": "0.3.0",
            "properties": {"osed": {"type": "string"}},
            "definitions": {"entityNamePattern": {}},
        }
        schema2 = {
            "version": "0.3.0",
            "properties": {
                "osed": {"type": "string"},
                "entities": {"type": "array"},
            },
            "definitions": {"entityNamePattern": {}, "semanticNode": {}},
        }

        result = diff_schemas(schema1, schema2)
        assert result.added_entities == {"entities"}
        assert result.added_universals == {"semanticNode"}
        assert (
            "New required properties: entities"
            in result.impact_analysis["validation"]
        )

    def test_diff_schemas_breaking_changes(self):
        """Test diffing schemas with breaking changes."""
        schema1 = {
            "version": "0.3.0",
            "properties": {
                "osed": {"type": "string"},
                "entities": {"type": "array"},
            },
            "definitions": {"entityNamePattern": {}, "semanticNode": {}},
        }
        schema2 = {
            "version": "0.3.0",
            "properties": {"osed": {"type": "string"}},
            "definitions": {"entityNamePattern": {}},
        }

        result = diff_schemas(schema1, schema2)
        assert result.removed_entities == {"entities"}
        assert result.removed_universals == {"semanticNode"}
        assert "Removed properties: entities" in result.breaking_changes


class TestDiffIntegration:
    """Test integrated diff functionality."""

    def test_diff_osed_documents_same_file(self):
        """Test diffing same file."""
        test_file = Path("sample/osed.v0.3.0.yaml")
        result = diff_osed_documents(test_file, test_file)
        assert not result.added_entities
        assert not result.removed_entities
        assert not result.breaking_changes

    def test_diff_osed_documents_different_files(self):
        """Test diffing different files."""
        file1 = Path("sample/osed.v0.2.0.yaml")
        file2 = Path("sample/osed.v0.3.0.yaml")
        result = diff_osed_documents(file1, file2)
        assert len(result.added_entities) > 0
        assert len(result.removed_entities) > 0
        assert len(result.breaking_changes) > 0

    def test_diff_osed_documents_schema_mismatch(self):
        """Test diffing document with schema file."""
        doc_file = Path("sample/osed.v0.3.0.yaml")
        schema_file = Path("schema/osed.schema.v0.3.0.yaml")

        with pytest.raises(
            ValueError, match="Cannot compare schema file with document file"
        ):
            diff_osed_documents(doc_file, schema_file)

    def test_diff_schemas(self):
        """Test diffing schema files."""
        schema1 = Path("schema/osed.schema.v0.2.0.yaml")
        schema2 = Path("schema/osed.schema.v0.3.0.yaml")
        result = diff_osed_documents(schema1, schema2)
        assert isinstance(result, DiffResult)


class TestFormatting:
    """Test output formatting functionality."""

    def test_colorize_with_color_support(self):
        """Test colorize function with color support."""
        with patch("src.python.osed_diff.supports_color", return_value=True):
            result = colorize("test", "red")
            assert "\033[31m" in result
            assert "\033[0m" in result

    def test_colorize_without_color_support(self):
        """Test colorize function without color support."""
        with patch("src.python.osed_diff.supports_color", return_value=False):
            result = colorize("test", "red")
            assert result == "test"

    def test_wrap_text(self):
        """Test text wrapping functionality."""
        long_text = "This is a very long text that should be wrapped to 80 characters or less for better readability in terminals."
        wrapped = wrap_text(long_text, width=40)
        lines = wrapped.split("\n")
        for line in lines:
            assert len(line) <= 40

    def test_format_diff_result_document(self):
        """Test formatting diff result for documents."""
        result = DiffResult(
            added_entities={"user"},
            removed_entities={"post"},
            modified_entities={},
            added_universals={"name"},
            removed_universals={"title"},
            added_particulars={"systemId"},
            removed_particulars={"id"},
            schema_version_changed=True,
            driver_changed=False,
            breaking_changes=["Removed entities: post"],
            impact_analysis={
                "typescript": ["New interfaces: user"],
                "mongoose": ["New schemas: user"],
            },
        )

        file1 = Path("test1.yaml")
        file2 = Path("test2.yaml")
        output = format_diff_result(result, file1, file2)

        assert "OSED Document Diff Analysis" in output
        assert "Added entities: user" in output
        assert "Removed entities: post" in output
        assert "Breaking Changes" in output

    def test_format_diff_result_schema(self):
        """Test formatting diff result for schemas."""
        result = DiffResult(
            added_entities={"entities"},
            removed_entities=set(),
            modified_entities={},
            added_universals={"metadataObject"},
            removed_universals=set(),
            added_particulars=set(),
            removed_particulars=set(),
            schema_version_changed=True,
            driver_changed=False,
            breaking_changes=[],
            impact_analysis={
                "validation": ["New required properties: entities"],
                "compatibility": ["New definitions: metadataObject"],
            },
        )

        file1 = Path("schema1.yaml")
        file2 = Path("schema2.yaml")
        output = format_diff_result(result, file1, file2)

        assert "OSED Schema Diff Analysis" in output
        assert "Added properties: entities" in output
        assert "Added definitions: metadataObject" in output


class TestCLIIntegration:
    """Test CLI integration."""

    def test_diff_command_success(self):
        """Test successful diff command execution."""
        file1 = Path("sample/osed.v0.3.0.yaml")
        file2 = Path("sample/osed.v0.3.0.yaml")

        result = diff_command(file1, file2)
        assert result == 0

    def test_diff_command_error(self):
        """Test diff command with error."""
        file1 = Path("nonexistent1.yaml")
        file2 = Path("nonexistent2.yaml")

        result = diff_command(file1, file2)
        assert result == 2

    def test_supports_color_environment_check(self):
        """Test color support detection with different environments."""
        # Mock isatty to return True for terminal simulation
        with patch("os.sys.stdout.isatty", return_value=True):
            # Test with TERM environment variable
            with patch.dict("os.environ", {"TERM": "xterm-256color"}):
                assert supports_color() is True

            # Test with no TERM environment variable
            with patch.dict("os.environ", {}, clear=True):
                assert supports_color() is False

        # Test with isatty returning False (non-terminal)
        with patch("os.sys.stdout.isatty", return_value=False):
            with patch.dict("os.environ", {"TERM": "xterm-256color"}):
                assert supports_color() is False

    def test_compare_entity_structure_type_changes(self):
        """Test entity structure comparison with type changes."""
        entity1 = {"field": "simple"}
        entity2 = {"field": {"type": "complex"}}

        changes = compare_entity_structure(entity1, entity2)
        assert "field: simple → complex" in changes["type_changes"]

    def test_compare_entity_structure_complex_to_simple(self):
        """Test entity structure comparison with complex to simple type change."""
        entity1 = {"field": {"type": "complex"}}
        entity2 = {"field": "simple"}

        changes = compare_entity_structure(entity1, entity2)
        assert "field: complex → simple" in changes["type_changes"]

    def test_analyze_generated_code_impact_removed_entities(self):
        """Test impact analysis with removed entities."""
        doc1 = {
            "entities": ["user", "post"],
            "user": {"id": "systemId"},
            "post": {"id": "systemId"},
        }
        doc2 = {"entities": ["user"], "user": {"id": "systemId"}}

        impact = analyze_generated_code_impact(doc1, doc2)
        assert "Removed interfaces: post" in impact["typescript"]
        assert "Removed schemas: post" in impact["mongoose"]
        assert "Remove references to: post" in impact["migration"]

    def test_analyze_generated_code_impact_modified_entities(self):
        """Test impact analysis with modified entities."""
        doc1 = {"entities": ["user"], "user": {"id": "systemId"}}
        doc2 = {
            "entities": ["user"],
            "user": {"id": "systemId", "name": "string"},
        }

        impact = analyze_generated_code_impact(doc1, doc2)
        assert "Added fields to user: name" in impact["typescript"]
        assert "Added fields to user: name" in impact["mongoose"]

    def test_format_diff_result_with_modified_entities(self):
        """Test formatting with modified entities."""
        result = DiffResult(
            added_entities=set(),
            removed_entities=set(),
            modified_entities={
                "user": {
                    "added_fields": ["name"],
                    "removed_fields": ["email"],
                    "modified_fields": ["id"],
                    "type_changes": ["id: simple → complex"],
                }
            },
            added_universals=set(),
            removed_universals=set(),
            added_particulars=set(),
            removed_particulars=set(),
            schema_version_changed=False,
            driver_changed=False,
            breaking_changes=[],
            impact_analysis={},
        )

        file1 = Path("test1.yaml")
        file2 = Path("test2.yaml")
        output = format_diff_result(result, file1, file2)

        assert "Modified entities: user" in output
        assert "user:" in output
        assert "Added: name" in output
        assert "Removed: email" in output
        assert "Modified: id" in output
        assert "Type changes: id: simple → complex" in output


class TestDiffLogging:
    """Test severity-based logging output in osed_diff.py."""

    def test_logging_for_invalid_file(self, tmp_path):
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            from src.python.osed_logging import set_logger, OSEDLogger

            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            with pytest.raises(RuntimeError):
                load_osed_document(invalid_file)
            log_output = fake_stderr.getvalue()
            assert "Failed to load OSED document" in log_output
            assert "Check that the file exists and is valid YAML." in log_output

    def test_logging_for_schema_version_and_breaking_changes(self):
        # Create a DiffResult with schema_version_changed and breaking_changes
        result = DiffResult(
            added_entities={"user"},
            removed_entities={"post"},
            modified_entities={},
            added_universals=set(),
            removed_universals=set(),
            added_particulars=set(),
            removed_particulars=set(),
            schema_version_changed=True,
            driver_changed=False,
            breaking_changes=["Removed entities: post"],
            impact_analysis={},
        )
        file1 = Path("test1.yaml")
        file2 = Path("test2.yaml")
        with patch("sys.stdout", new=io.StringIO()) as fake_stdout, patch(
            "sys.stderr", new=io.StringIO()
        ) as fake_stderr:
            from src.python.osed_logging import set_logger, OSEDLogger

            set_logger(
                OSEDLogger(stdout_stream=fake_stdout, stderr_stream=fake_stderr)
            )
            output = format_diff_result(result, file1, file2)
            # Info log should go to stdout
            info_output = fake_stdout.getvalue()
            assert "OSED Document Diff Analysis" in info_output
            # Warning and error logs should go to stderr
            err_output = fake_stderr.getvalue()
            assert "Schema version changed" in err_output
            assert "Breaking changes detected in diff result." in err_output
            assert (
                "Review the breaking changes and update your code or data accordingly."
                in err_output
            )
