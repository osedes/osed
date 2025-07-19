"""
OSED Results Module

Provides structured result classes for linting, validation, and generation operations.
Integrates with the severity-based logging system.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

from .osed_logging import Severity, LogMessage


@dataclass
class LintResult:
    """Structured result for linting operations."""

    passed: bool
    severity: Severity
    messages: List[str] = field(default_factory=list)
    context: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    file_path: Optional[Path] = None
    line_number: Optional[int] = None
    is_blocking: bool = True

    def __post_init__(self):
        """Set is_blocking based on severity after initialization."""
        self.is_blocking = self.severity in [Severity.ERROR]

    def add_message(self, message: str) -> None:
        """Add a message to the result."""
        self.messages.append(message)

    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the result."""
        self.suggestions.append(suggestion)

    def to_log_message(self) -> LogMessage:
        """Convert to a LogMessage for logging."""
        return LogMessage(
            severity=self.severity,
            message=(
                "; ".join(self.messages)
                if self.messages
                else "No specific messages"
            ),
            context=self.context,
            suggestions=self.suggestions,
            file_path=self.file_path,
            line_number=self.line_number,
        )


@dataclass
class ValidationResult:
    """Structured result for validation operations."""

    passed: bool
    severity: Severity
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    context: Optional[str] = None
    file_path: Optional[Path] = None

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.messages.append(f"ERROR: {error}")
        self.passed = False
        self.severity = Severity.ERROR

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        self.messages.append(f"WARNING: {warning}")
        if self.severity == Severity.INFO:
            self.severity = Severity.WARNING

    def add_info(self, info: str) -> None:
        """Add an info message."""
        self.info.append(info)
        self.messages.append(f"INFO: {info}")

    def to_log_message(self) -> LogMessage:
        """Convert to a LogMessage for logging."""
        return LogMessage(
            severity=self.severity,
            message=(
                "; ".join(self.messages)
                if self.messages
                else "Validation completed"
            ),
            context=self.context,
            file_path=self.file_path,
        )


@dataclass
class GenerationResult:
    """Structured result for code generation operations."""

    success: bool
    severity: Severity
    generated_files: List[Path] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    output_dir: Optional[Path] = None

    def add_generated_file(self, file_path: Path) -> None:
        """Add a generated file to the result."""
        self.generated_files.append(file_path)

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.messages.append(f"ERROR: {error}")
        self.success = False
        self.severity = Severity.ERROR

    def add_warning(self, warning: str) -> None:
        """Add a warning message."""
        self.warnings.append(warning)
        self.messages.append(f"WARNING: {warning}")
        if self.severity == Severity.INFO:
            self.severity = Severity.WARNING

    def add_message(self, message: str) -> None:
        """Add a general message."""
        self.messages.append(message)

    def to_log_message(self) -> LogMessage:
        """Convert to a LogMessage for logging."""
        return LogMessage(
            severity=self.severity,
            message=(
                "; ".join(self.messages)
                if self.messages
                else "Generation completed"
            ),
            context=(
                f"Generated {len(self.generated_files)} files"
                if self.generated_files
                else None
            ),
        )


@dataclass
class DiffResult:
    """Structured result for diff operations."""

    has_changes: bool
    severity: Severity
    added_entities: set = field(default_factory=set)
    removed_entities: set = field(default_factory=set)
    modified_entities: set = field(default_factory=set)
    breaking_changes: List[str] = field(default_factory=list)
    impact_analysis: Dict[str, List[str]] = field(default_factory=dict)
    messages: List[str] = field(default_factory=list)

    def add_breaking_change(self, change: str) -> None:
        """Add a breaking change."""
        self.breaking_changes.append(change)
        self.messages.append(f"BREAKING: {change}")
        self.severity = Severity.ERROR

    def add_change(self, change: str) -> None:
        """Add a non-breaking change."""
        self.messages.append(f"CHANGE: {change}")
        if self.severity == Severity.INFO:
            self.severity = Severity.WARNING

    def to_log_message(self) -> LogMessage:
        """Convert to a LogMessage for logging."""
        return LogMessage(
            severity=self.severity,
            message=(
                "; ".join(self.messages)
                if self.messages
                else "No changes detected"
            ),
            context=f"Added: {len(self.added_entities)}, Removed: {len(self.removed_entities)}, Modified: {len(self.modified_entities)}",
        )


class ResultCollector:
    """Collects and manages multiple results from different operations."""

    def __init__(self):
        """Initialize the result collector."""
        self.results: List[Any] = []
        self._severity_counts = {severity: 0 for severity in Severity}

    def add_result(self, result: Any) -> None:
        """Add a result to the collector."""
        self.results.append(result)
        if hasattr(result, "severity"):
            self._severity_counts[result.severity] += 1

    def get_overall_severity(self) -> Severity:
        """Get the overall severity based on all results."""
        if self._severity_counts[Severity.ERROR] > 0:
            return Severity.ERROR
        if self._severity_counts[Severity.WARNING] > 0:
            return Severity.WARNING
        if self._severity_counts[Severity.INFO] > 0:
            return Severity.INFO
        return Severity.DEBUG

    def get_exit_code(self) -> int:
        """Get appropriate exit code based on all results."""
        if self._severity_counts[Severity.ERROR] > 0:
            return 2
        if self._severity_counts[Severity.WARNING] > 0:
            return 1
        return 0

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all results."""
        return {
            "total_results": len(self.results),
            "severity_counts": self._severity_counts,
            "overall_severity": self.get_overall_severity().value,
            "exit_code": self.get_exit_code(),
            "has_errors": self._severity_counts[Severity.ERROR] > 0,
            "has_warnings": self._severity_counts[Severity.WARNING] > 0,
        }
