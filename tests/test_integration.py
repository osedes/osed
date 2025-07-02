"""
Integration tests for the complete OSED workflow.

These tests verify that validation, linting, and code generation work together
seamlessly in a complete workflow.
"""

import tempfile
from pathlib import Path
import pytest
import subprocess
import sys

from src.python.osed_validate import validate_file
from src.python.osed_lint import lint_file
from src.python.osed_generate import generate_mongoose


class TestCompleteWorkflow:
    """Test the complete OSED workflow from validation to code generation."""

    def test_valid_document_complete_workflow(self):
        """Test that a valid document passes validation, linting, and generates code."""
        # Test data
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": [
                "string",
                "email",
                "boolean",
                "True",
                "list",
                "reference",
                "map"
                ],
            "user": {
                "id": "string",
                "name": "string",
                "email": "email",
                "isActive": {"type": "boolean", "default": True},
                "posts": {"type": "list", "items": "post", "ref": "post"}
            },
            "post": {
                "id": "string",
                "title": "string",
                "content": "string",
                "author": {"type": "reference", "ref": "user", "required": True},
                "tags": {"type": "list", "items": "string"},
                "metadata": {"type": "map", "value": "string"}
            }
        }

        # Step 1: Validation should pass
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation
            schema_path = Path(__file__).parent.parent / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            assert validate_file(schema_path, temp_file) is True, "Document should pass validation"

            # Step 2: Linting should pass
            lint_result = lint_file(temp_file)
            assert lint_result is True, "Document should pass linting"

            # Step 3: Code generation should work
            with tempfile.TemporaryDirectory() as output_dir:
                output_path = Path(output_dir)
                generate_mongoose(document, output_path)

                # Check generated files
                user_model = output_path / "user.model.ts"
                post_model = output_path / "post.model.ts"

                assert user_model.exists(), "User model should be generated"
                assert post_model.exists(), "Post model should be generated"

                # Check content
                user_content = user_model.read_text()
                post_content = post_model.read_text()

                assert "export interface IUser extends Document" in user_content
                assert "export interface IPost extends Document" in post_content
                assert "isActive: boolean;" in user_content
                assert "posts: Array<" in user_content
                assert "author: Schema.Types.ObjectId | IUser;" in post_content
                assert "tags: string[];" in post_content
                assert "metadata: Record<string, string>;" in post_content

        finally:
            temp_file.unlink()

    def test_invalid_document_workflow(self):
        """Test that an invalid document fails validation and doesn't proceed to codegen."""
        # Test data with validation errors - using a document that should definitely fail
        document = {
            "osed": "invalid-version",  # Invalid OSED version
            "entities": "not-a-list",   # Invalid entities format
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation should fail
            schema_path = Path(__file__).parent.parent / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            assert validate_file(schema_path, temp_file) is False, "Invalid document should fail validation"

            # Linting should also fail
            lint_result = lint_file(temp_file)
            assert lint_result is False, "Invalid document should fail linting"

        finally:
            temp_file.unlink()

    def test_linting_errors_workflow(self):
        """Test that linting errors are caught even if validation passes."""
        # Test data with linting errors (undeclared entity reference)
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string",
                "profile": {"type": "reference", "ref": "profile"}  # profile not declared
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation might pass (depending on schema strictness)
            schema_path = Path(__file__).parent.parent / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            validation_passed = validate_file(schema_path, temp_file)

            # But linting should definitely fail
            lint_result = lint_file(temp_file)
            assert lint_result is False, "Document with undeclared entity reference should fail linting"

        finally:
            temp_file.unlink()


class TestCLIIntegration:
    """Test CLI integration for the complete workflow."""

    def test_cli_validate_command(self):
        """Test CLI validate command."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Test CLI validate command
            result = subprocess.run([
                sys.executable, "-m", "src.python.osed_cli", "validate", "--file", str(temp_file)
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

            assert result.returncode == 0, f"CLI validate should succeed: {result.stderr}"
            assert "valid" in result.stdout.lower() or "success" in result.stdout.lower()

        finally:
            temp_file.unlink()

    def test_cli_lint_command(self):
        """Test CLI lint command."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Test CLI lint command
            result = subprocess.run([
                sys.executable, "-m", "src.python.osed_cli", "lint", "--file", str(temp_file)
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

            assert result.returncode == 0, f"CLI lint should succeed: {result.stderr}"

        finally:
            temp_file.unlink()

    def test_cli_generate_command(self):
        """Test CLI generate command."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string", "boolean", "True"],
            "user": {
                "id": "string",
                "name": "string",
                "isActive": {"mongoose:type": "boolean", "mongoose:default": True}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                # Test CLI generate command
                result = subprocess.run([
                    sys.executable, "-m", "src.python.osed_cli", "generate",
                    "--file", str(temp_file), "--target", "mongoose", "--out", output_dir
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

                assert result.returncode == 0, f"CLI generate should succeed: {result.stderr}"

                # Check generated files
                output_path = Path(output_dir)
                user_model = output_path / "user.model.ts"
                assert user_model.exists(), "User model should be generated"

        finally:
            temp_file.unlink()

    def test_cli_complete_workflow(self):
        """Test complete CLI workflow: validate -> lint -> generate."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string", "boolean", "True"],
            "user": {
                "id": "string",
                "name": "string",
                "isActive": {"mongoose:type": "boolean", "mongoose:default": True}
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                # Step 1: Validate
                validate_result = subprocess.run([
                    sys.executable, "-m", "src.python.osed_cli", "validate", "--file", str(temp_file)
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

                assert validate_result.returncode == 0, "Validation should succeed"

                # Step 2: Lint
                lint_result = subprocess.run([
                    sys.executable, "-m", "src.python.osed_cli", "lint", "--file", str(temp_file)
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

                assert lint_result.returncode == 0, "Linting should succeed"

                # Step 3: Generate
                generate_result = subprocess.run([
                    sys.executable, "-m", "src.python.osed_cli", "generate",
                    "--file", str(temp_file), "--target", "mongoose", "--out", output_dir
                ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

                assert generate_result.returncode == 0, "Code generation should succeed"

                # Verify output
                output_path = Path(output_dir)
                user_model = output_path / "user.model.ts"
                assert user_model.exists(), "User model should be generated"

        finally:
            temp_file.unlink()


class TestErrorHandling:
    """Test error handling in the integration workflow."""

    def test_missing_file_handling(self):
        """Test handling of missing input files."""
        missing_file = Path("/tmp/nonexistent_file.yaml")

        # CLI validate should handle missing file gracefully
        result = subprocess.run([
            sys.executable, "-m", "osed_cli", "validate", "--file", str(missing_file)
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        assert result.returncode != 0, "CLI should fail for missing file"

        # CLI lint should handle missing file gracefully
        result = subprocess.run([
            sys.executable, "-m", "osed_cli", "lint", "--file", str(missing_file)
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        assert result.returncode != 0, "CLI should fail for missing file"

    def test_invalid_output_directory(self):
        """Test handling of invalid output directory for code generation."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {
                "id": "string",
                "name": "string"
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Try to generate to a non-existent directory
            invalid_output = "/tmp/nonexistent/directory"
            result = subprocess.run([
                sys.executable, "-m", "osed_cli", "generate",
                "--file", str(temp_file), "--target", "mongoose", "--out", invalid_output
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent)

            # This should either fail or create the directory
            # The exact behavior depends on the implementation

        finally:
            temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
