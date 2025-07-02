# setup.py
from setuptools import setup

setup(
    name="osed",
    version="0.2.0",
    py_modules=["osed_cli", "osed_validate", "osed_lint"],
    install_requires=[
        "PyYAML",
        "jsonschema"
    ],
    entry_points={
        "console_scripts": [
            "osed = osed_cli:main",
        ],
    },
)
