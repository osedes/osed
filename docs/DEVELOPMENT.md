# Development Guide

This guide covers development practices, CI/CD, package management, and contribution guidelines for the OSED project.

## Project Structure

```
osed/
├── src/python/          # OSED CLI tools and libraries
├── schema/              # OSED schema definitions (all versions)
├── tests/               # Test suite and test data
├── docs/                # All documentation
├── scripts/             # Development and release scripts
├── examples/            # Example implementations
├── sample/              # Sample OSED documents
└── metadata/            # Environment configuration data
```

## Development Setup

### Prerequisites
```bash
# Install Python 3.12+
python --version

# Install development dependencies
pip install -r requirements-dev.txt

# Install OSED in development mode
pip install -e .
```

### Development Environment
```bash
# Clone the repository
git clone https://github.com/osedes/osed.git
cd osed

# Set up pre-commit hooks (optional)
pre-commit install

# Run tests
python -m pytest

# Run linting
python -m osed lint sample/osed.v0.3.0.yaml
```

## CI/CD Pipeline

### GitHub Actions Workflows

#### Main Workflow (`osed.yaml`)
- Runs on every push and pull request
- Tests on Python 3.12
- Runs linting, validation, and tests
- Checks code quality and formatting

#### Release Workflow (`release.yml`)
- Triggers on GitHub releases
- Builds and publishes to PyPI
- Uploads artifacts to GitHub releases

### Local Development Workflow

```bash
# 1. Make changes
# 2. Run tests
python -m pytest

# 3. Run linting
python -m osed lint sample/osed.v0.3.0.yaml

# 4. Validate changes
python -m osed validate sample/osed.v0.3.0.yaml

# 5. Commit and push
git add .
git commit -m "feat: your change description"
git push
```

## Code Quality

### Linting and Formatting
```bash
# Run pylint
pylint --indent-string='  ' --max-line-length=80 src/python/

# Format code with Black
black .

# Check formatting
black --check .

# Run prettier for other files
prettier --check "*.{json,md}" "schema/**/*.{yaml,yml}"
```

### Testing
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_cli_lint_context.py

# Run with coverage
python -m pytest --cov=src/python
```

## Package Management

### PyPI Package Management

This section covers managing OSED packages on PyPI using twine and yank.

#### Prerequisites

##### Install Required Tools
```bash
pip install build twine
```

##### Set Up PyPI Credentials
Create `~/.pypirc` file:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-your-production-token-here

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-your-test-token-here
```

#### Package Lifecycle

##### 1. Development Phase
```bash
# Build package locally
python -m build

# Check package validity
python -m twine check dist/*

# Test installation
pip install dist/osed-*.whl
```

##### 2. Testing Phase
```bash
# Upload to Test PyPI
python -m twine upload --repository testpypi dist/*

# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ osed
```

##### 3. Production Release
```bash
# Upload to production PyPI
python -m twine upload dist/*

# Verify installation
pip install osed
```

#### Emergency Procedures

##### Yanking a Release

If you need to remove a version from PyPI:

```bash
# Using our release script
python scripts/release.py --yank 0.3.0

# Or directly with twine
python -m twine delete osed 0.3.0
```

##### When to Yank

**Yank immediately if:**
- Security vulnerability discovered
- Package doesn't install correctly
- Critical functionality broken
- Wrong dependencies listed

**Consider yanking if:**
- Minor bugs that affect many users
- Incorrect metadata (description, classifiers)
- Breaking changes in patch release

##### Post-Yank Actions

1. **Fix the issue** in your codebase
2. **Release a new version** with the fix
3. **Communicate** the issue to users
4. **Update documentation** if needed

#### Common Scenarios

##### Scenario 1: Security Issue
```bash
# 1. Yank the vulnerable version
python scripts/release.py --yank 0.3.0

# 2. Fix the security issue
# ... fix code ...

# 3. Release patched version
python scripts/release.py
```

##### Scenario 2: Breaking Change in Patch
```bash
# 1. Yank the breaking version
python scripts/release.py --yank 0.3.0

# 2. Revert breaking changes
# ... fix code ...

# 3. Release correct patch
python scripts/release.py
```

##### Scenario 3: Wrong Dependencies
```bash
# 1. Yank the version
python scripts/release.py --yank 0.3.0

# 2. Fix requirements
# ... update requirements.txt ...

# 3. Release corrected version
python scripts/release.py
```

#### Best Practices

##### 1. Always Test First
```bash
# Test on Test PyPI before production
python scripts/release.py --test
```

##### 2. Validate Packages
```bash
# Always check before upload
python -m twine check dist/*
```

##### 3. Use Semantic Versioning
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

##### 4. Keep Release Notes
Document what changed in each release for transparency.

##### 5. Monitor Installations
Check PyPI download statistics to understand usage.

#### Troubleshooting

##### Upload Fails
```bash
# Check your credentials
cat ~/.pypirc

# Test connection
python -m twine check dist/*

# Try with verbose output
python -m twine upload -v dist/*
```

##### Yank Fails
```bash
# Check if version exists
pip index versions osed

# Verify you have permissions
# Check your PyPI account settings
```

##### Package Won't Install
```bash
# Check package contents
tar -tzf dist/osed-*.tar.gz

# Test in clean environment
python -m venv test_env
source test_env/bin/activate
pip install dist/osed-*.whl
```

#### Automation

##### GitHub Actions Release
Our workflow automatically releases when you create a GitHub release:

1. Create a release on GitHub
2. Workflow builds and uploads to PyPI
3. No manual intervention needed

##### Local Release Script
```bash
# Full release process
python scripts/release.py

# Test release only
python scripts/release.py --test

# Emergency yank
python scripts/release.py --yank 0.3.0
```

#### Monitoring

##### Check Package Status
```bash
# View package on PyPI
pip index versions osed

# Check download statistics
# Visit https://pypi.org/project/osed/
```

##### Monitor for Issues
- Watch GitHub issues
- Monitor PyPI download stats
- Check for security advisories

#### Security Considerations

##### API Tokens
- Use API tokens, not passwords
- Rotate tokens regularly
- Use different tokens for Test PyPI and production

##### Package Signing
Consider signing packages for additional security:
```bash
# Generate signing key
gpg --gen-key

# Sign package
python -m twine upload --sign dist/*
```

## Contributing

For contribution guidelines, development process, and community standards, see:

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Complete contribution guide
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** - Community standards and behavior expectations

## Resources

- [PyPI Documentation](https://packaging.python.org/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Python Packaging User Guide](https://packaging.python.org/guides/)
