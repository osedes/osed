"""OSED configuration management module.

This module handles project and user-level configuration for the OSED tool,
including acknowledgement of linter warnings.
"""

from datetime import datetime, timezone
from pathlib import Path
import yaml

PROJECT_CONFIG_DIR = Path(".osed")
PROJECT_CONFIG_FILE = PROJECT_CONFIG_DIR / "config.yaml"
USER_CONFIG_DIR = Path.home() / ".osed"
USER_CONFIG_FILE = USER_CONFIG_DIR / "config.yaml"


def ensure_config_dir_exists():
    """Ensure that the config directories exist."""
    PROJECT_CONFIG_DIR.mkdir(exist_ok=True)
    USER_CONFIG_DIR.mkdir(exist_ok=True)


def load_config(path):
    """Load YAML config from the given path."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_config(path, config):
    """Save YAML config to the given path."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config, f)


def get_project_config():
    """Get the project config as a dict."""
    return load_config(PROJECT_CONFIG_FILE)


def get_user_config():
    """Get the user config as a dict."""
    return load_config(USER_CONFIG_FILE)


def save_project_config(config):
    """Save the project config."""
    save_config(PROJECT_CONFIG_FILE, config)


def save_user_config(config):
    """Save the user config."""
    save_config(USER_CONFIG_FILE, config)


def _ensure_config_keys(config, kind):
    """Ensure the config dict has the required keys for linting."""
    if "lint" not in config:
        config["lint"] = {}
    if kind not in config["lint"]:
        config["lint"][kind] = []


def get_acknowledged_paths(kind, user=False):
    """Get acknowledged paths for a given kind from user or project config."""
    config = get_user_config() if user else get_project_config()
    _ensure_config_keys(config, kind)
    return set(
        entry["path"]
        for entry in config["lint"][kind]
        if entry.get("addressed")
    )


def is_path_acknowledged(kind, path):
    """Check if a path is acknowledged in user or project config."""
    for config in (get_project_config(), get_user_config()):
        _ensure_config_keys(config, kind)
        for entry in config["lint"][kind]:
            if entry["path"] == path and entry.get("addressed"):
                return True
    return False


def acknowledge_path(kind, path, user, user_name, note=None):
    """Acknowledge a path in user or project config."""
    config = get_user_config() if user else get_project_config()
    _ensure_config_keys(config, kind)
    config["lint"][kind] = [
        e for e in config["lint"][kind] if e["path"] != path
    ]
    entry = {
        "path": path,
        "addressed": True,
        "acknowledged_by": user_name,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }
    if note:
        entry["note"] = note
    config["lint"][kind].append(entry)
    if user:
        save_user_config(config)
    else:
        save_project_config(config)


def unacknowledge_path(kind, path, user, user_name=None, note=None):
    """Remove acknowledgement for a path in user or project config."""
    config = get_user_config() if user else get_project_config()
    _ensure_config_keys(config, kind)
    before_count = len(config["lint"][kind])
    config["lint"][kind] = [
        e for e in config["lint"][kind] if e["path"] != path
    ]
    after_count = len(config["lint"][kind])
    # Optionally, could log or record the unacknowledgement somewhere
    if user:
        save_user_config(config)
        return before_count != after_count  # True if something was removed
    save_project_config(config)
    return before_count != after_count  # True if something was removed


def make_path(file_path, entity, field=None):
    """Generate a reference string for a field or entity in a file."""
    if field:
        return f"{file_path}#{entity}.{field}"
    return f"{file_path}#{entity}"


def parse_path(path):
    """Parse a reference string into (file_path, entity, field or None)."""
    if "#" not in path:
        raise ValueError("Invalid path reference: missing '#' separator")
    file_path, rest = path.split("#", 1)
    if "." in rest:
        entity, field = rest.split(".", 1)
        return file_path, entity, field
    return file_path, rest, None
