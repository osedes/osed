# setup.py
from setuptools import setup

setup(
    name="osed",
    version="0.3.0",
    packages=["src.python"],
    install_requires=["PyYAML", "jsonschema"],
    entry_points={
        "console_scripts": [
            "osed = src.python.osed_cli:main",
        ],
    },
)
