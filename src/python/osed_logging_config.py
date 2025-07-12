"""
OSED Logging Configuration

Provides configuration utilities for the OSED logging system.
Allows easy setup of different logging configurations for different environments.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from .osed_logging import OSEDLogger


def setup_logging(
    name: str = "osed",
    level: str = "INFO",
    format_type: str = "human",
    use_colors: bool = True,
    log_file: Optional[Path] = None,
    config_file: Optional[Path] = None,
) -> OSEDLogger:
    """
    Set up logging with the specified configuration.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Output format (human, json, machine)
        use_colors: Whether to use colors in output
        log_file: Optional file to log to
        config_file: Optional configuration file path

    Returns:
        Configured logger instance
    """
    # Load configuration from file if provided
    if config_file and config_file.exists():
        config = load_logging_config(config_file)
        name = config.get("name", name)
        level = config.get("level", level)
        format_type = config.get("format", format_type)
        use_colors = config.get("use_colors", use_colors)
        log_file = (
            Path(config.get("log_file", log_file))
            if config.get("log_file")
            else log_file
        )

    # Convert level string to logging level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    logging_level = level_map.get(level.upper(), logging.INFO)

    # Create logger
    logger = OSEDLogger(
        name=name,
        level=logging_level,
        use_colors=use_colors,
        output_format=format_type,
    )

    # Add file handler if log_file is specified
    if log_file:
        logger.add_file_handler(log_file)

    return logger


def load_logging_config(config_file: Path) -> Dict[str, Any]:
    """
    Load logging configuration from a YAML file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary
    """
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_default_config() -> Dict[str, Any]:
    """
    Get default logging configuration.

    Returns:
        Default configuration dictionary
    """
    return {
        "name": "osed",
        "level": "INFO",
        "format": "human",
        "use_colors": True,
        "log_file": None,
    }


def create_config_file(
    config_path: Path, config: Optional[Dict[str, Any]] = None
) -> None:
    """
    Create a logging configuration file.

    Args:
        config_path: Path where to create the config file
        config: Configuration dictionary (uses default if None)
    """
    if config is None:
        config = get_default_config()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write configuration file
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, indent=2)


# Predefined configurations for different environments
DEVELOPMENT_CONFIG = {
    "name": "osed.dev",
    "level": "DEBUG",
    "format": "human",
    "use_colors": True,
    "log_file": "logs/osed_dev.log",
}

PRODUCTION_CONFIG = {
    "name": "osed.prod",
    "level": "WARNING",
    "format": "json",
    "use_colors": False,
    "log_file": "logs/osed_prod.log",
}

TESTING_CONFIG = {
    "name": "osed.test",
    "level": "INFO",
    "format": "machine",
    "use_colors": False,
    "log_file": None,
}


def setup_development_logging(format_type=None) -> OSEDLogger:
    """Set up logging for development environment."""
    return setup_logging(
        name=DEVELOPMENT_CONFIG["name"],
        level=DEVELOPMENT_CONFIG["level"],
        format_type=format_type or DEVELOPMENT_CONFIG["format"],
        use_colors=DEVELOPMENT_CONFIG["use_colors"],
        log_file=(
            Path(DEVELOPMENT_CONFIG["log_file"])
            if DEVELOPMENT_CONFIG["log_file"]
            else None
        ),
    )


def setup_production_logging(format_type=None) -> OSEDLogger:
    """Set up logging for production environment."""
    return setup_logging(
        name=PRODUCTION_CONFIG["name"],
        level=PRODUCTION_CONFIG["level"],
        format_type=format_type or PRODUCTION_CONFIG["format"],
        use_colors=PRODUCTION_CONFIG["use_colors"],
        log_file=(
            Path(PRODUCTION_CONFIG["log_file"])
            if PRODUCTION_CONFIG["log_file"]
            else None
        ),
    )


def setup_testing_logging(format_type=None) -> OSEDLogger:
    """Set up logging for testing environment."""
    return setup_logging(
        name=TESTING_CONFIG["name"],
        level=TESTING_CONFIG["level"],
        format_type=format_type or TESTING_CONFIG["format"],
        use_colors=TESTING_CONFIG["use_colors"],
        log_file=(
            Path(TESTING_CONFIG["log_file"])
            if TESTING_CONFIG["log_file"]
            else None
        ),
    )
