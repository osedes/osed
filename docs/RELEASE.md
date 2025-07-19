# OSED Release Checklist

## Pre-Release Steps

### 1. Version Management
- [ ] Update `VERSION` file with new version number
- [ ] Ensure all schema files have correct `$id` and `version` fields
- [ ] Run `osed check-versions` to verify consistency
- [ ] Update `CHANGELOG.md` with release notes

### 2. Code Quality
- [ ] Run all tests: `python -m pytest`
- [ ] Run linting: `python -m osed lint sample/osed.v0.3.0.yaml`
- [ ] Run validation: `python -m osed validate sample/osed.v0.3.0.yaml`
- [ ] Ensure GitHub Actions pass

### 3. Documentation
- [ ] Update README.md if needed
- [ ] Verify all examples work correctly
- [ ] Check that all links are working

### 4. Packaging
- [ ] Clean previous builds: `rm -rf dist build src/*.egg-info`
- [ ] Build package: `python -m build`
- [ ] Check package: `python -m twine check dist/*`
- [ ] Test local installation: `pip install dist/osed-*.whl`
- [ ] Verify CLI works: `osed --help`

## Release Steps

### 1. Test PyPI (Optional but Recommended)
```bash
# Upload to test PyPI first
python -m twine upload --repository testpypi dist/*
```

### 2. Production PyPI
```bash
# Upload to production PyPI
python -m twine upload dist/*
```

### 3. GitHub Release
- [ ] Create GitHub release with version tag
- [ ] Upload built packages to GitHub release
- [ ] Add release notes

## Post-Release Steps

### 1. Verification
- [ ] Verify package is available on PyPI: `pip install osed`
- [ ] Test installation in clean environment
- [ ] Verify all CLI commands work

### 2. Documentation
- [ ] Update any documentation that references installation
- [ ] Update GitHub repository description if needed

### 3. Communication
- [ ] Announce release on relevant channels
- [ ] Update any external references

## Version Policy

### Semantic Versioning
- **MAJOR**: Breaking changes to schema or CLI
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

### Release Frequency
- **Patch releases**: As needed for bug fixes
- **Minor releases**: Every week for new features
- **Major releases**: When breaking changes are necessary

## Current Version: 0.3.0

### Next Release Planning
- Target: 0.4.0 (minor release)
- Planned features: Enhanced CLI, better developer experience
- Timeline: One week

## Emergency Procedures

### If Release Fails
1. Check PyPI status page
2. Verify package metadata
3. Rebuild and retry
4. Contact PyPI support if needed

### If Package Has Issues
1. Immediately yank the release: `python -m twine delete osed 0.3.0`
2. Fix the issue
3. Release patch version
4. Communicate the issue and fix

## Dependencies

### Required for Release
- `build>=1.0.0`
- `twine>=4.0.0`
- `wheel>=0.40.0`

### Development Dependencies
- `pytest>=7.3.0`
- `black>=23.0.0`
- `pylint>=2.17.0`
