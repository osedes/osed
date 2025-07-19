#!/usr/bin/env python3
"""
OSED Release Script

This script automates the release process for OSED packages.
See docs/RELEASE_CHECKLIST.md for the complete release checklist.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, check=True):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def get_version():
    """Get the current version from VERSION file."""
    with open("VERSION", "r", encoding="utf-8") as f:
        return f.read().strip()


def check_prerequisites():
    """Check that all prerequisites are met."""
    print("Checking prerequisites...")

    # Check if we're in a git repository
    if not Path(".git").exists():
        print("Error: Not in a git repository")
        sys.exit(1)

    # Check if we have uncommitted changes
    result = run_command("git status --porcelain", check=False)
    if result.stdout.strip():
        print("Warning: You have uncommitted changes")
        response = input("Continue anyway? (y/N): ")
        if response.lower() != "y":
            sys.exit(1)

    # Check if build tools are available
    try:
        run_command("python -m build --version")
    except FileNotFoundError:
        print("Error: build package not found. Install with: pip install build")
        sys.exit(1)

    try:
        run_command("python -m twine --version")
    except FileNotFoundError:
        print("Error: twine not found. Install with: pip install twine")
        sys.exit(1)


def run_tests():
    """Run all tests."""
    print("Running tests...")
    run_command("python -m pytest")


def build_package():
    """Build the package."""
    print("Building package...")
    run_command("rm -rf dist build src/*.egg-info")
    run_command("python -m build")


def check_package():
    """Check the built package."""
    print("Checking package...")
    run_command("python -m twine check dist/*")


def upload_to_testpypi():
    """Upload to Test PyPI."""
    print("Uploading to Test PyPI...")
    run_command("python -m twine upload --repository testpypi dist/*")


def upload_to_pypi():
    """Upload to PyPI."""
    print("Uploading to PyPI...")
    run_command("python -m twine upload dist/*")


def create_git_tag():
    """Create a git tag for the release."""
    version = get_version()
    print(f"Creating git tag v{version}...")
    run_command(f"git tag v{version}")
    run_command(f"git push origin v{version}")


def yank_version(version):
    """Yank a specific version from PyPI."""
    print(f"Yanking version {version} from PyPI...")
    print("WARNING: This will remove the version from PyPI!")
    response = input(f"Are you sure you want to yank osed {version}? (y/N): ")
    if response.lower() != "y":
        print("Yank cancelled.")
        return

    run_command(f"python -m twine delete osed {version}")
    print(f"Successfully yanked osed {version} from PyPI")


def main():
    """Main entry point for the release script."""
    parser = argparse.ArgumentParser(description="OSED Release Script")
    parser.add_argument(
        "--test", action="store_true", help="Upload to Test PyPI only"
    )
    parser.add_argument(
        "--no-tests", action="store_true", help="Skip running tests"
    )
    parser.add_argument(
        "--no-tag", action="store_true", help="Skip creating git tag"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and check only, don't upload",
    )
    parser.add_argument(
        "--yank", metavar="VERSION", help="Yank a specific version from PyPI"
    )

    args = parser.parse_args()

    # Handle yank command
    if args.yank:
        yank_version(args.yank)
        return

    version = get_version()
    print(f"Releasing OSED version {version}")

    # Check prerequisites
    check_prerequisites()

    # Run tests (unless skipped)
    if not args.no_tests:
        run_tests()

    # Build package
    build_package()

    # Check package
    check_package()

    if args.dry_run:
        print("Dry run completed. Package built and checked successfully.")
        return

    # Upload to Test PyPI
    if args.test:
        upload_to_testpypi()
        print("Uploaded to Test PyPI successfully!")
        return

    # Upload to PyPI
    upload_to_pypi()

    # Create git tag
    if not args.no_tag:
        create_git_tag()

    print(f"OSED {version} released successfully!")


if __name__ == "__main__":
    main()
