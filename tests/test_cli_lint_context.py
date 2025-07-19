"""
Test CLI lint contextual logging and exit codes.
"""

import sys
import subprocess
import json
from pathlib import Path
import itertools
import pytest

DATA_DIR = Path(__file__).parent / "data" / "v0.3.0"
CLI = [sys.executable, "-m", "src.python.osed_cli", "lint"]

TEST_CASES = [
    # clean_valid.yaml removed; see lint_config_demo for acknowledgement tests
    {
        "file": DATA_DIR / "valid_core.yaml",
        "expected_exit": 1,  # warnings only
    },
    {
        "file": DATA_DIR / "naming_conventions.yaml",
        "expected_exit": 2,  # errors
    },
    {
        "file": DATA_DIR / "invalid_mongoose.yaml",
        "expected_exit": 2,  # errors
    },
    {
        "file": DATA_DIR / "fatal_error.yaml",
        "expected_exit": 3,  # fatal/system error
    },
]

OUTPUT_FORMATS = ["json", "human"]


def run_cli_lint(file_path, output_format):
    """Run the CLI linter on the given file and return (exit_code, output_lines)."""
    proc = subprocess.run(
        CLI
        + ["run", "--file", str(file_path), "--output-format", output_format],
        capture_output=True,
        text=True,
        check=False,
    )
    output_lines = (
        proc.stdout.strip().splitlines() + proc.stderr.strip().splitlines()
    )
    return proc.returncode, output_lines


@pytest.mark.parametrize(
    "case,output_format", itertools.product(TEST_CASES, OUTPUT_FORMATS)
)
def test_cli_lint_context(case, output_format):
    """Test CLI linter exit codes and contextual info in both output formats."""
    exit_code, output_lines = run_cli_lint(case["file"], output_format)
    assert exit_code == case["expected_exit"], (
        f"Exit code for {case['file']} ({output_format}) was {exit_code}, "
        f"expected {case['expected_exit']}"
    )
    found_context = False
    found_severity = set()
    for line in output_lines:
        if output_format == "json":
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                raise  # Fail the test immediately if invalid JSON is encountered
            if "file_path" in msg and msg["file_path"]:
                found_context = True
            if "suggestions" in msg and isinstance(msg["suggestions"], list):
                found_context = True
            if "severity" in msg:
                found_severity.add(msg["severity"])
        else:
            if str(case["file"]) in line or "file:" in line:
                found_context = True
            for sev in ["info", "warning", "error", "fatal", "system error"]:
                if sev in line.lower():
                    found_severity.add(sev)
    assert found_context, (
        f"No contextual info found in output for {case['file']} "
        f"({output_format})"
    )
    if case["expected_exit"] == 3:
        assert any(
            sev in found_severity
            for sev in ["critical", "fatal", "system error"]
        ), (
            f"No fatal/system error severity found in output for "
            f"{case['file']} ({output_format})"
        )
