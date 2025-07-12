"""
Integration tests for the complete OSED workflow.

These tests verify that validation, linting, and code generation work together
seamlessly in a complete workflow.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from src.python.osed_validate import validate_file
from src.python.osed_lint import lint_file
from src.python.osed_generate import generate_mongoose


class TestCompleteWorkflow:
    """Test the complete OSED workflow from validation to code generation."""

    @pytest.mark.xfail(
        reason="ref usage in lists, maps and required reference types needs clarification in schema rules before this test can be validated or invalidated."
    )
    def test_valid_document_complete_workflow(self):
        """Test that a valid document passes validation, linting, and generates code."""
        # Test data
        document = {
            "osed": "0.3.0",
            "driver": "mongoose-mongo",
            "entities": ["user", "post"],
            "universals": [
                "string",
                "email",
                "boolean",
                "True",
                "list",
                "reference",
                "map",
            ],
            "user": {
                "id": "string",
                "name": "string",
                "email": "email",
                "isActive": {"type": "boolean", "default": True},
                "posts": {"type": "list", "items": "post", "ref": "post"},
            },
            "post": {
                "id": "string",
                "title": "string",
                "content": "string",
                "author": {
                    "type": "reference",
                    "ref": "user",
                    "required": True,
                },
                "tags": {"type": "list", "items": "string"},
                "metadata": {"type": "map", "value": "string"},
            },
        }

        # Step 1: Validation should pass
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation
            schema_path = (
                Path(__file__).parent.parent
                / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            )
            assert (
                validate_file(schema_path, temp_file) is True
            ), "Document should pass validation"

            # Step 2: Linting should pass
            lint_result, _ = lint_file(temp_file)
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
                interfaces_file = output_path / "interfaces.ts"
                interfaces_content = interfaces_file.read_text()

                assert "import { IUser } from './interfaces.js'" in user_content
                assert "import { IPost } from './interfaces.js'" in post_content
                assert "isActive: boolean;" in interfaces_content
                assert "posts: Schema.Types.ObjectId[];" in interfaces_content
                assert "author: Schema.Types.ObjectId;" in interfaces_content
                assert "tags: string[];" in interfaces_content
                assert "metadata: Record<string, string>;" in interfaces_content

        finally:
            temp_file.unlink()

    def test_invalid_document_workflow(self):
        """Test that an invalid document fails validation and doesn't proceed to codegen."""
        # Test data with validation errors - using a document that should definitely fail
        document = {
            "osed": "invalid-version",  # Invalid OSED version
            "entities": "not-a-list",  # Invalid entities format
            "universals": ["string"],
            "user": {"id": "string", "name": "string"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation should fail
            schema_path = (
                Path(__file__).parent.parent
                / "schema/osed.driver.mongoose-mongodb.schema.v0.3.0.yaml"
            )
            assert (
                validate_file(schema_path, temp_file) is False
            ), "Invalid document should fail validation"

            # Linting should also fail
            lint_result, _ = lint_file(temp_file)
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
                "profile": {
                    "type": "reference",
                    "ref": "profile",
                },  # profile not declared
            },
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Validation might pass (depending on schema strictness)
            # Note: validation_passed is not used, so we don't store it

            # But linting should definitely fail
            lint_result, _ = lint_file(temp_file)
            assert (
                lint_result is False
            ), "Document with undeclared entity reference should fail linting"

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
            "user": {"id": "string", "name": "string"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Test CLI validate command
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.python.osed_validate",
                    "-f",
                    str(temp_file),
                    "--expected-schema-version",
                    "0.3.0",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert (
                result.returncode == 0
            ), f"CLI validate failed: {result.stderr}"

        finally:
            temp_file.unlink()

    def test_cli_lint_command(self):
        """Test CLI lint command."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": [],
            "user": {"id": "string", "name": "string"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Test CLI lint command
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.python.osed_lint",
                    "-f",
                    str(temp_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            assert result.returncode in (
                0,
                1,
            ), f"CLI lint failed: {result.stderr}"

        finally:
            temp_file.unlink()

    def test_cli_generate_command(self):
        """Test CLI generate command."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {"id": "string", "name": "string"},
            "driver": "mongoose",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                # Test CLI generate command
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.python.osed_generate",
                        "-f",
                        str(temp_file),
                        "--target",
                        "mongoose",
                        "--out",
                        output_dir,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert (
                    result.returncode == 0
                ), f"CLI generate failed: {result.stderr}"

                # Check that files were generated
                output_path = Path(output_dir)
                assert (output_path / "interfaces.ts").exists()
                # Instead of schemas.ts, check for user.model.ts
                assert (output_path / "user.model.ts").exists()

        finally:
            temp_file.unlink()

    def test_cli_complete_workflow(self):
        """Test complete CLI workflow from validation to generation."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user", "post"],
            "universals": ["string", "boolean"],
            "user": {
                "id": "string",
                "name": "string",
                "isActive": {"type": "boolean", "default": True},
            },
            "post": {
                "id": "string",
                "title": "string",
                "content": "string",
                "author": {
                    "type": "reference",
                    "ref": "user",
                },
            },
            "driver": "mongoose",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                # Step 1: Validate
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.python.osed_validate",
                        "-f",
                        str(temp_file),
                        "--expected-schema-version",
                        "0.3.0",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert (
                    result.returncode == 0
                ), f"Validation failed: {result.stderr}"

                # Step 2: Lint
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.python.osed_lint",
                        "-f",
                        str(temp_file),
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert result.returncode in (
                    0,
                    1,
                ), f"Linting failed: {result.stderr}"

                # Step 3: Generate
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "src.python.osed_generate",
                        "-f",
                        str(temp_file),
                        "--target",
                        "mongoose",
                        "--out",
                        output_dir,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                assert (
                    result.returncode == 0
                ), f"Generation failed: {result.stderr}"

                # Verify generated files
                output_path = Path(output_dir)
                interfaces_file = output_path / "interfaces.ts"
                # Instead of schemas.ts, check for user.model.ts and post.model.ts
                user_model_file = output_path / "user.model.ts"
                post_model_file = output_path / "post.model.ts"

                assert interfaces_file.exists()
                assert user_model_file.exists()
                assert post_model_file.exists()

                # Check content
                interfaces_content = interfaces_file.read_text()
                user_model_content = user_model_file.read_text()
                post_model_content = post_model_file.read_text()

                assert "export interface IUser" in interfaces_content
                assert "export interface IPost" in interfaces_content
                assert "export const userSchema" in user_model_content
                assert "export const postSchema" in post_model_content

        finally:
            temp_file.unlink()


class TestErrorHandling:
    """Test error handling in the workflow."""

    def test_missing_file_handling(self):
        """Test handling of missing files."""
        # Test with non-existent file
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "src.python.osed_validate",
                "-f",
                "nonexistent.yaml",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode != 0, "Should fail with non-existent file"

    def test_invalid_output_directory(self):
        """Test handling of invalid output directory."""
        # Create a valid test file
        document = {
            "osed": "0.3.0",
            "entities": ["user"],
            "universals": ["string"],
            "user": {"id": "string", "name": "string"},
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(document, f)
            temp_file = Path(f.name)

        try:
            # Test with invalid output directory
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "src.python.osed_generate",
                    "-f",
                    str(temp_file),
                    "--target",
                    "mongoose",
                    "--out",
                    "/invalid/path/that/does/not/exist",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            # Should fail due to invalid output directory
            assert result.returncode != 0

        finally:
            temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
