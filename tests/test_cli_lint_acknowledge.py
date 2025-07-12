"""Tests for OSED CLI acknowledge and unacknowledge functionality.

This module tests the CLI commands for acknowledging and unacknowledging
linter warnings at both project and user (global) config levels.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import yaml
import pytest

test_dir = Path(__file__).parent / "lint_config_demo"
CLI = [sys.executable, "-m", "src.python.osed_cli", "lint"]


@pytest.fixture
def temp_home(monkeypatch):
    """Fixture to create a temporary HOME for user-level config isolation."""
    with tempfile.TemporaryDirectory() as tmp_home:
        monkeypatch.setenv("HOME", tmp_home)
        yield Path(tmp_home)


def run_cli(args, cwd=None, env=None):
    """Run the CLI with given arguments and return exit code, stdout, stderr."""
    if env is None:
        env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent)
    proc = subprocess.run(
        CLI + args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def read_yaml(path):
    """Read and parse a YAML file, returning empty dict if file doesn't exist."""
    if not path or not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        # Ensure lint key is a dict, not None
        if "lint" in data and data["lint"] is None:
            data["lint"] = {}
        return data


def test_acknowledge_project_level(tmp_path):
    """Test acknowledging a warning at project level."""
    # Copy demo to temp dir for isolation (ensure hidden files are copied)
    demo = tmp_path / "lint_config_demo"
    shutil.copytree(test_dir, demo, dirs_exist_ok=True)

    # Ensure .osed directory exists (in case it wasn't copied properly)
    osed_dir = demo / ".osed"
    osed_dir.mkdir(exist_ok=True)

    # Ensure config file exists (copy from original if needed)
    config = demo / ".osed" / "config.yaml"
    if not config.exists():
        original_config = test_dir / ".osed" / "config.yaml"
        if original_config.exists():
            shutil.copy2(original_config, config)
        else:
            # Create empty config if original doesn't exist
            config.write_text("lint:\n", encoding="utf-8")
    path = f"{demo}/clean_valid.yaml#Person.password"
    # Remove any existing acknowledgement
    data = read_yaml(config)
    if "lint" not in data or data["lint"] is None:
        data["lint"] = {}
    if "sensitiveFields" not in data["lint"]:
        data["lint"]["sensitiveFields"] = []
    with open(config, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    # Acknowledge
    code, _, _ = run_cli(
        [
            "acknowledge",
            "--kind",
            "sensitiveFields",
            "--path",
            path,
            "--user",
            "test-user",
        ],
        cwd=demo,
    )
    assert code == 0
    data = read_yaml(config)
    assert any(
        e["path"] == path and e["addressed"]
        for e in data["lint"]["sensitiveFields"]
    )


def test_unacknowledge_project_level(tmp_path):
    """Test unacknowledging a warning at project level."""
    demo = tmp_path / "lint_config_demo"
    shutil.copytree(test_dir, demo, dirs_exist_ok=True)

    # Ensure .osed directory exists (in case it wasn't copied properly)
    osed_dir = demo / ".osed"
    osed_dir.mkdir(exist_ok=True)

    # Ensure config file exists (copy from original if needed)
    config = demo / ".osed" / "config.yaml"
    if not config.exists():
        original_config = test_dir / ".osed" / "config.yaml"
        if original_config.exists():
            shutil.copy2(original_config, config)
        else:
            # Create empty config if original doesn't exist
            config.write_text("lint:\n", encoding="utf-8")
    path = f"{demo}/clean_valid.yaml#Person.password"
    # Add an acknowledgement
    data = read_yaml(config)
    if "lint" not in data or data["lint"] is None:
        data["lint"] = {}
    if "sensitiveFields" not in data["lint"]:
        data["lint"]["sensitiveFields"] = []
    data["lint"]["sensitiveFields"] = [
        {
            "path": path,
            "addressed": True,
            "acknowledged_by": "test-user",
            "acknowledged_at": "2024-07-15T00:00:00+00:00",
        }
    ]
    with open(config, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    # Unacknowledge
    code, _, _ = run_cli(
        [
            "unacknowledge",
            "--kind",
            "sensitiveFields",
            "--path",
            path,
            "--user",
            "test-user",
        ],
        cwd=demo,
    )
    assert code == 0
    data = read_yaml(config)
    assert not any(e["path"] == path for e in data["lint"]["sensitiveFields"])


def test_acknowledge_user_level(temp_home, tmp_path):
    """Test acknowledging a warning at user (global) level."""
    demo = tmp_path / "lint_config_demo"
    shutil.copytree(test_dir, demo, dirs_exist_ok=True)
    path = f"{demo}/clean_valid.yaml#Person.password"
    user_config_dir = temp_home / ".osed"
    user_config = user_config_dir / "config.yaml"
    user_config_dir.mkdir(parents=True, exist_ok=True)
    # Remove any existing user config
    if user_config.exists():
        user_config.unlink()
    # Acknowledge (user/global)
    code, _, _ = run_cli(
        [
            "acknowledge",
            "--kind",
            "sensitiveFields",
            "--path",
            path,
            "--user",
            "test-user",
            "--global",
        ],
        cwd=demo,
    )
    assert code == 0
    data = read_yaml(user_config)
    assert any(
        e["path"] == path and e["addressed"]
        for e in data["lint"]["sensitiveFields"]
    )


def test_unacknowledge_user_level(temp_home, tmp_path):
    """Test unacknowledging a warning at user (global) level."""
    demo = tmp_path / "lint_config_demo"
    shutil.copytree(test_dir, demo, dirs_exist_ok=True)
    path = f"{demo}/clean_valid.yaml#Person.password"
    user_config_dir = temp_home / ".osed"
    user_config = user_config_dir / "config.yaml"
    user_config_dir.mkdir(parents=True, exist_ok=True)
    # Add an acknowledgement to user config
    data = {
        "lint": {
            "sensitiveFields": [
                {
                    "path": path,
                    "addressed": True,
                    "acknowledged_by": "test-user",
                    "acknowledged_at": "2024-07-15T00:00:00+00:00",
                }
            ]
        }
    }
    with open(user_config, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    # Unacknowledge (user/global)
    code, _, _ = run_cli(
        [
            "unacknowledge",
            "--kind",
            "sensitiveFields",
            "--path",
            path,
            "--user",
            "test-user",
            "--global",
        ],
        cwd=demo,
    )
    assert code == 0
    data = read_yaml(user_config)
    assert not any(e["path"] == path for e in data["lint"]["sensitiveFields"])


def test_unacknowledge_nonexistent_entry(tmp_path):
    """Test unacknowledging a non-existent entry (should not error)."""
    demo = tmp_path / "lint_config_demo"
    shutil.copytree(test_dir, demo, dirs_exist_ok=True)

    # Ensure .osed directory exists (in case it wasn't copied properly)
    osed_dir = demo / ".osed"
    osed_dir.mkdir(exist_ok=True)

    # Ensure config file exists (copy from original if needed)
    config = demo / ".osed" / "config.yaml"
    if not config.exists():
        original_config = test_dir / ".osed" / "config.yaml"
        if original_config.exists():
            shutil.copy2(original_config, config)
        else:
            # Create empty config if original doesn't exist
            config.write_text("lint:\n", encoding="utf-8")
    path = f"{demo}/clean_valid.yaml#Person.password"
    # Ensure no acknowledgement exists
    data = read_yaml(config)
    if "lint" not in data or data["lint"] is None:
        data["lint"] = {}
    if "sensitiveFields" not in data["lint"]:
        data["lint"]["sensitiveFields"] = []
    with open(config, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f)
    # Unacknowledge
    code, _, _ = run_cli(
        [
            "unacknowledge",
            "--kind",
            "sensitiveFields",
            "--path",
            path,
            "--user",
            "test-user",
        ],
        cwd=demo,
    )
    assert code == 0
    # Should still be empty
    data = read_yaml(config)
    assert not any(e["path"] == path for e in data["lint"]["sensitiveFields"])
