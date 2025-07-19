# Contributing to OSED

Thank you for your interest in contributing to OSED! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Guidelines](#development-guidelines)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)
- [Community Guidelines](#community-guidelines)

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.12+
- Git
- Basic understanding of YAML and Python

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/osedes/osed.git
   cd osed
   ```

2. **Create a dedicated Python virtual environment (recommended)**
   ```bash
   python -m venv osed
   source osed/bin/activate  # On Windows use: osed\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Run tests to verify setup**
   ```bash
   source osed/bin/activate   # __ (Ignore if activated earlier)
   pytest                     #  | On Windows use: osed\Scripts\activate
   osed lint sample/osed.v0.3.0.yaml
   ```

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, use Black for formatting
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Write docstrings for all functions and classes
- **Comments**: Add comments for complex logic

### Testing

- Write tests for new features
- Ensure all tests pass before submitting
- Add integration tests for CLI functionality
- Test both success and error scenarios
- Maintain test coverage

### Documentation

- Update README.md for user-facing changes
- Update DEVELOPMENT.md for developer-facing changes
- Add examples for new features
- Keep changelog updated

### Commit Messages

Use conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

Examples:
- `feat(cli): add --output-format option`
- `fix(lint): resolve naming convention issues`
- `docs(readme): update installation instructions`

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

## Pull Request Process

### Before Submitting

1. **Ensure your code follows guidelines**
   ```bash
   source osed/bin/activate   # (Ignore if activated earlier)
   osed lint sample/osed.v0.3.0.yaml
   pytest
   black --check .
   ```

2. **Update documentation**
   - Update relevant documentation files
   - Add examples if introducing new features
   - Update changelog if needed

3. **Test your changes**
   - Test with different OSED documents
   - Verify CLI functionality
   - Check generated output

### Submitting a Pull Request

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name # Or use `git flow`
   ```

2. **Make your changes**
   - Follow the development guidelines
   - Write tests for new functionality
   - Update documentation

3. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(scope): your change description"
   ```

4. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create a pull request**
   - Use the PR template // TODO Create PR Templates
   - Describe your changes clearly
   - **Link the pull request to an associated issue number (required)**
   - Request reviews from maintainers

### Pull Request Guidelines

- **Title**: Clear, descriptive title
- **Description**: Explain what and why, not how
- **Associated Issue**: All pull requests must reference an associated issue number (e.g., "Fixes #123" or "Closes #123")
- **Tests**: Include tests for new functionality
- **Documentation**: Update relevant docs
- **Breaking Changes**: Clearly mark and explain

### Review Process

- All PRs require at least one maintainer review
- Address review comments promptly
- Maintainers may request changes
- PRs are merged after approval and CI passes

## Issue Reporting

### Before Reporting

1. **Check existing issues** - Search for similar issues
2. **Check documentation** - Review README and docs
3. **Reproduce the issue** - Ensure it's reproducible

### Creating an Issue

Use the appropriate issue template and include: // TODO Issue template

- **Clear title** describing the problem
- **Detailed description** of the issue
- **Steps to reproduce** the problem
- **Expected vs actual behavior**
- **Environment information**:
  - OS and version
  - Python version
  - OSED version
- **Relevant files** (OSED documents, error logs)

### Issue Types

- **Bug Report**: Something isn't working
- **Feature Request**: Suggest a new feature
- **Documentation**: Suggest documentation improvements
- **Question**: Ask for help or clarification

## Community Guidelines

### Communication

- **Be respectful** and inclusive
- **Use clear language** and avoid jargon
- **Provide context** when asking questions
- **Help others** when you can

### Feedback

- **Be constructive** in reviews and comments
- **Focus on the code**, not the person
- **Suggest improvements** rather than just pointing out problems
- **Acknowledge good work** and contributions

### Learning

- **Ask questions** - No question is too basic
- **Share knowledge** - Help others learn
- **Be patient** - Everyone learns at their own pace
- **Celebrate progress** - Recognize improvements

## Getting Help

- **Documentation**: Check README.md and docs/
- **Issues**: Search existing issues
- **Discussions**: Use GitHub Discussions // TODO
- **Community**: Join our community channels // TODO

## Recognition

Contributors are recognized in:
- GitHub contributors list // TODO
- Release notes // TODO
- Project documentation
- Community acknowledgments // TODO

Thank you for contributing to OSED!
