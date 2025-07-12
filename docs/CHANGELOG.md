# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Enhanced packaging infrastructure for PyPI distribution
- Comprehensive release automation with GitHub Actions
- Improved developer experience with better CLI tools
- Complete documentation structure in `docs/` directory

### Changed
- Moved all documentation to `docs/` directory for better organization
- Simplified installation process (removed Docker complexity)
- Optimized package size by excluding unnecessary files from production builds

### Fixed
- GitHub Actions workflow now properly installs development dependencies
- Package validation and build process improvements
- MANIFEST.in configuration for minimal production packages

## [0.3.0] - 2024-01-15

### Added
- Driver-based schema approach with `osed.driver.*` naming convention
- Mongoose-MongoDB support with comprehensive validation and code generation
- Enhanced semanticNode diagnostics for malformed structures
- CLI tools for validation, linting, and code generation
- Comprehensive test suite with 58/58 tests passing
- Major refactor from meta-entity structure to concrete, real-world entities (e.g., user, post, comment, userProfile, etc.)
- Enhanced support for Mongoose metadata, including type, required, unique, default, reference, and array/map handling
- Simplified and clarified the OSED YAML structure for easier authoring and downstream code generation
- Improved validation and linting via CLI (`osed validate`, `osed lint`) with stricter schema enforcement and comprehensive entity reference extraction
- Updated all examples and documentation to use sample/osed.v0.3.0.yaml
- Example server and tests now support any MongoDB instance, not just Docker
- Enhanced linting logic that properly distinguishes between top-level keys, leaf node values, and property names for accurate entity reference validation

### Changed
- Migrated to `src/python/` structure for better organization
- Updated all imports and references for new package structure
- Enhanced linting with deeper semantic checks
- Deprecated or removed unused/obsolete meta-entities (e.g., specialValueDescription)
- Improved documentation and consistency across CLI, examples, and schema

### Fixed
- Resolved duplicate index warnings in mongoose-mongo-server example
- Fixed valueDescription string support in schema validation
- Enhanced code generation to avoid duplicate indexes

## [0.2.0] - 2024-01-01

### Added
- Initial OSED schema definition
- Basic validation and linting capabilities
- Core entity and relationship modeling
- Defined reusable `entityNamePattern` via `$ref` to ensure consistency in naming rules
- Added SemVer regex validation for the `osed` field to enforce proper versioning format
- Introduced `$id` and `version` metadata in the schema to support external tooling and hosting
- Improved `valueDescription` structure to support only well-defined types (no booleans, nulls, or raw scalars)
- Removed support for `type: list/map` constructs from the core schema (now handled via downstream metadata)
- Added `osed_lint.py` tool for semantic validation, checking:
  - Reserved word misuse
  - Undeclared/unused/duplicate entity names
  - Invalid characters in entity names
  - Misplaced entity descriptions

### Changed
- Improved schema structure and validation rules

## [0.1.0] - 2023-12-01

### Added
- Initial project setup
- Basic YAML schema definition
- Core OSED concept and documentation
- Required fields: `osed`, `entities`
- Optional fields: `universals`, `particulars`
- Recursive `semanticNode` structure for noun grouping
- Entity descriptions supporting nested maps or flat string lists
- Naming convention enforced for all property names and entities
