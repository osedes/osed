"""
OSED Logging Module

Provides a centralized severity-based logging system for the OSED project.
Uses Python's standard logging module with custom formatters for icons and colors.
"""

import sys
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from datetime import datetime


class Severity(Enum):
    """Severity levels for logging messages."""

    DEBUG = "debug"  # 🔍 Development/troubleshooting info
    INFO = "info"  # ℹ️  General information
    WARNING = "warning"  # ⚠️  Non-blocking issues
    ERROR = "error"  # ❌ Blocking issues
    CRITICAL = "critical"  # 💀 System/fatal errors
    FATAL = "critical"  # 💀 Alias for backward compatibility


@dataclass
class LogMessage:
    """Structured log message with severity and context."""

    severity: Severity
    message: str
    context: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    file_path: Optional[Path] = None
    line_number: Optional[int] = None


class OSEDFormatter(logging.Formatter):
    """Custom formatter for OSED with colors and icons."""

    # Color codes for different terminals
    COLORS = {
        logging.DEBUG: "\033[36m",  # Cyan
        logging.INFO: "\033[32m",  # Green
        logging.WARNING: "\033[33m",  # Yellow
        logging.ERROR: "\033[31m",  # Red
        logging.CRITICAL: "\033[35m",  # Magenta
        "RESET": "\033[0m",  # Reset
    }

    # Icons for different severity levels
    ICONS = {
        logging.DEBUG: "🔍",
        logging.INFO: "ℹ️",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "💥",
    }

    def __init__(self, use_colors: bool = True, show_context: bool = True):
        """Initialize the formatter."""
        super().__init__()
        self.use_colors = use_colors and self._supports_colors()
        self.show_context = show_context

    def _supports_colors(self) -> bool:
        """Check if the current terminal supports colors."""
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def format(self, record):
        """Format a log record with colors and icons."""
        icon = self.ICONS.get(record.levelno, "ℹ️")
        color = self.COLORS.get(record.levelno, "") if self.use_colors else ""
        reset = self.COLORS["RESET"] if self.use_colors else ""

        # Build the formatted message
        formatted = f"{color}{icon} {record.getMessage()}{reset}"

        # Add context if available and enabled
        context = getattr(record, "context", None)
        if self.show_context and context:
            formatted += f"\n  Context: {context}"

        # Add file location if available
        file_path = getattr(record, "file_path", None)
        line_number = getattr(record, "line_number", None)
        if file_path:
            location = f"{file_path}"
            if line_number:
                location += f":{line_number}"
            formatted += f"\n  Location: {location}"

        # Add suggestions if available
        suggestions = getattr(record, "suggestions", None)
        if suggestions:
            formatted += "\n  Suggestions:"
            for suggestion in suggestions:
                formatted += f"\n    • {suggestion}"

        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for machine-readable output."""

    def format(self, record):
        """Format record as JSON."""
        json_msg = {
            "severity": record.levelname.lower(),
            "message": record.getMessage(),
            "timestamp": datetime.now().isoformat(),
        }

        # Add custom attributes
        for attr in ["context", "file_path", "line_number", "suggestions"]:
            if hasattr(record, attr):
                value = getattr(record, attr)
                if value:
                    json_msg[attr] = value

        return json.dumps(json_msg)


class MachineFormatter(logging.Formatter):
    """Machine-readable formatter."""

    def format(self, record):
        """Format record for machine processing."""
        parts = [record.levelname.upper(), record.getMessage()]

        # Add custom attributes
        for attr in ["context", "file_path", "line_number"]:
            if hasattr(record, attr):
                value = getattr(record, attr)
                if value:
                    parts.append(f"{attr}={value}")

        return "|".join(parts)


class OSEDLogger:
    """Centralized logger for OSED project using standard logging."""

    def __init__(
        self,
        name: str = "osed",
        level: int = logging.INFO,
        use_colors: bool = True,
        output_format: str = "human",
        stdout_stream=None,
        stderr_stream=None,
    ):
        """
        Initialize the logger.

        Args:
            name: Logger name
            level: Logging level (from logging module)
            use_colors: Whether to use color-coded output
            output_format: Output format ("human", "json", "machine")
            stdout_stream: Stream for stdout logs (default: sys.stdout)
            stderr_stream: Stream for stderr logs (default: sys.stderr)
        """

        self.name = name
        self.output_format = output_format
        self.messages: List[LogMessage] = []
        self._severity_counts = {severity: 0 for severity in Severity}

        # Create logger using standard logging
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Use provided streams or default to sys.stdout/sys.stderr
        stdout_stream = stdout_stream or sys.stdout
        stderr_stream = stderr_stream or sys.stderr

        # Add console handlers for stdout (INFO and below) and stderr (WARNING and above)
        stdout_handler = logging.StreamHandler(stdout_stream)
        stdout_handler.setLevel(logging.DEBUG)
        stdout_handler.addFilter(
            lambda record: record.levelno < logging.WARNING
        )

        stderr_handler = logging.StreamHandler(stderr_stream)
        stderr_handler.setLevel(logging.WARNING)
        stderr_handler.addFilter(
            lambda record: record.levelno >= logging.WARNING
        )

        if output_format == "human":
            formatter = OSEDFormatter(use_colors=use_colors)
        elif output_format == "json":
            formatter = JSONFormatter()
        elif output_format == "machine":
            formatter = MachineFormatter()
        else:
            formatter = OSEDFormatter(use_colors=use_colors)

        stdout_handler.setFormatter(formatter)
        stderr_handler.setFormatter(formatter)
        self.logger.addHandler(stdout_handler)
        self.logger.addHandler(stderr_handler)

    def _get_severity_value(self, severity: Severity) -> int:
        """Get numeric value for severity comparison."""
        severity_values = {
            Severity.DEBUG: 0,
            Severity.INFO: 1,
            Severity.WARNING: 2,
            Severity.ERROR: 3,
        }
        return severity_values[severity]

    def _severity_to_logging_level(self, severity: Severity) -> int:
        """Convert our severity enum to logging level."""
        severity_map = {
            Severity.DEBUG: logging.DEBUG,
            Severity.INFO: logging.INFO,
            Severity.WARNING: logging.WARNING,
            Severity.ERROR: logging.ERROR,
            Severity.CRITICAL: logging.CRITICAL,
        }
        return severity_map[severity]

    def log(self, severity: Severity, message: str, **kwargs) -> None:
        """
        Log a message with the specified severity.

        Args:
            severity: Severity level of the message
            message: The message to log
            **kwargs: Additional context (context, suggestions, file_path, line_number)
        """
        # Create log message
        log_msg = LogMessage(
            severity=severity,
            message=message,
            context=kwargs.get("context"),
            suggestions=kwargs.get("suggestions", []),
            file_path=kwargs.get("file_path"),
            line_number=kwargs.get("line_number"),
        )

        # Store message
        self.messages.append(log_msg)
        self._severity_counts[severity] += 1

        # Log using standard logging
        level = self._severity_to_logging_level(severity)

        # Create a custom log record with additional attributes
        record = self.logger.makeRecord(
            name=self.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=None,
        )

        # Add custom attributes to the record
        for key, value in kwargs.items():
            setattr(record, key, value)

        # Log the record
        self.logger.handle(record)

    def debug(self, message: str, **kwargs) -> None:
        """Log a debug message."""
        self.log(Severity.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log an info message."""
        self.log(Severity.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log a warning message."""
        self.log(Severity.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log an error message."""
        self.log(Severity.ERROR, message, **kwargs)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all logged messages."""
        return {
            "total_messages": len(self.messages),
            "severity_counts": self._severity_counts,
            "has_errors": self._severity_counts[Severity.ERROR] > 0,
            "has_warnings": self._severity_counts[Severity.WARNING] > 0,
            "all_messages": [
                {
                    "severity": msg.severity.value,
                    "message": msg.message,
                    "context": msg.context,
                    "file_path": str(msg.file_path) if msg.file_path else None,
                    "line_number": msg.line_number,
                }
                for msg in self.messages
            ],
        }

    def get_exit_code(self) -> int:
        """
        Get appropriate exit code based on logged messages.

        Returns:
            0: Success (no errors, no warnings)
            1: Warnings only (no errors)
            2: Errors (blocking issues)
            3: Fatal/system errors
        """
        if self._severity_counts.get(Severity.CRITICAL, 0) > 0:
            return 3
        if self._severity_counts[Severity.ERROR] > 0:
            return 2
        if self._severity_counts[Severity.WARNING] > 0:
            return 1
        return 0

    def clear(self) -> None:
        """Clear all logged messages."""
        self.messages.clear()
        self._severity_counts = {severity: 0 for severity in Severity}

    def add_file_handler(self, log_file: Path) -> None:
        """Add a file handler to the logger."""
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create file handler
        file_handler = logging.FileHandler(log_file, encoding="utf-8")

        # Use a simple formatter for file output
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(file_handler)


# Global logger instance
LOGGER = None


def get_logger() -> OSEDLogger:
    """Get the global logger instance."""
    global LOGGER
    if LOGGER is None:
        LOGGER = OSEDLogger()
    return LOGGER


def set_logger(logger: OSEDLogger) -> None:
    """Set the global logger instance."""
    global LOGGER
    LOGGER = logger


def log(severity: Severity, message: str, **kwargs) -> None:
    """Log a message using the global logger."""
    get_logger().log(severity, message, **kwargs)


def debug(message: str, **kwargs) -> None:
    """Log a debug message using the global logger."""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs) -> None:
    """Log an info message using the global logger."""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs) -> None:
    """Log a warning message using the global logger."""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs) -> None:
    """Log an error message using the global logger."""
    get_logger().error(message, **kwargs)
