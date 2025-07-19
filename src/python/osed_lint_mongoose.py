"""
Mongoose-specific lint checks for OSED documents.
"""

from .osed_logging import Severity
from .osed_results import LintResult
from .osed_utils import (
    CONTROL_KEYS,
    VALID_MONGOOSE_TYPES,
    VALID_MONGOOSE_ITEM_TYPES,
)


def check_mongoose_type_validation(document, file_path=None):
    """
    Validates that all type values are valid Mongoose types.
    """
    invalid_types = []

    def check_type_values(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "type" and isinstance(value, str):
                    if value not in VALID_MONGOOSE_TYPES:
                        invalid_types.append(
                            f"Invalid type '{value}' at {'.'.join(path)}"
                        )
                else:
                    check_type_values(value, path + [key])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_type_values(item, path + [str(i)])

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_type_values(entity_data, [entity_name])

    if invalid_types:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid Mongoose types",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all 'type' values in entity descriptions are valid Mongoose types."
            ],
        )
        for invalid_type in invalid_types:
            result.add_message(invalid_type)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All type values are valid Mongoose types"],
        file_path=file_path,
    )


def check_mongoose_required_fields(document, file_path=None):
    """
    Validates that required fields have proper metadata.
    """
    missing_metadata = []

    def check_required_metadata(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "required" and value is True:
                    # Check if parent has type information
                    parent_path = path[:-1] if path else []
                    if parent_path:
                        parent_node = document
                        for part in parent_path:
                            if (
                                isinstance(parent_node, dict)
                                and part in parent_node
                            ):
                                parent_node = parent_node[part]
                            else:
                                break
                        else:
                            if (
                                isinstance(parent_node, dict)
                                and "type" not in parent_node
                            ):
                                missing_metadata.append(
                                    f"Required field at {'.'.join(path)} missing type"
                                )
                else:
                    check_required_metadata(value, path + [key])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_required_metadata(item, path + [str(i)])

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_required_metadata(entity_data, [entity_name])

    if missing_metadata:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Missing required field metadata",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=["Ensure all required fields have a 'type' metadata."],
        )
        for missing in missing_metadata:
            result.add_message(missing)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All required fields are present"],
        file_path=file_path,
    )


def check_mongoose_item_type_validation(document, file_path=None):
    """
    Validates that list/map items have valid types.
    """
    invalid_items = []

    def check_item_types(node, path):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "items" and isinstance(value, dict):
                    if "type" in value:
                        item_type = value["type"]
                        if item_type not in VALID_MONGOOSE_ITEM_TYPES:
                            invalid_items.append(
                                f"Invalid item type '{item_type}' at {'.'.join(path)}"
                            )
                    elif "ref" in value:
                        # Reference validation is handled elsewhere
                        pass
                else:
                    check_item_types(value, path + [key])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_item_types(item, path + [str(i)])

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_item_types(entity_data, [entity_name])

    if invalid_items:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid item types",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all 'items' values in entity descriptions are valid Mongoose types."
            ],
        )
        for invalid_item in invalid_items:
            result.add_message(invalid_item)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All of/items values are valid"],
        file_path=file_path,
    )


def check_mongoose_ref_validation(document, file_path=None):
    """
    Validates that all references are to declared entities and that 'ref' is only used with valid types.
    """
    invalid_refs = []
    valid_ref_types = {"objectid", "reference"}

    def check_ref_values(node, path):
        if isinstance(node, dict):
            node_type = node.get("type")
            node_of = node.get("of")
            for key, value in node.items():
                if key == "ref" and isinstance(value, str):
                    # Check if the referenced entity exists
                    if value not in document:
                        invalid_refs.append(
                            f"Invalid reference '{value}' at {'.'.join(path)}"
                        )
                    # Check if the type is valid for ref
                    type_valid = False
                    if node_type:
                        if node_type.lower() in valid_ref_types:
                            type_valid = True
                        elif (
                            node_type.lower() == "array"
                            and node_of
                            and node_of.lower() in valid_ref_types
                        ):
                            type_valid = True
                    if not type_valid:
                        invalid_refs.append(
                            f"Invalid use of ref at {'.'.join(path)}: type '{node_type}' with ref is not allowed"
                        )
                else:
                    check_ref_values(value, path + [key])
        elif isinstance(node, list):
            for i, item in enumerate(node):
                check_ref_values(item, path + [str(i)])

    for entity_name, entity_data in document.items():
        if entity_name not in CONTROL_KEYS:
            check_ref_values(entity_data, [entity_name])

    if invalid_refs:
        result = LintResult(
            passed=False,
            severity=Severity.ERROR,
            context="Invalid references",
            file_path=file_path,
            line_number=None,  # TODO: Add line number support with advanced parser
            suggestions=[
                "Ensure all 'ref' values in entity descriptions refer to declared entities and are used with valid types (objectid, reference, or array of those)."
            ],
        )
        for invalid_ref in invalid_refs:
            result.add_message(invalid_ref)
        return result
    return LintResult(
        passed=True,
        severity=Severity.INFO,
        messages=["All references are valid"],
        file_path=file_path,
    )
