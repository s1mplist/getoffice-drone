"""JSON serialization utilities for handling common non-serializable types."""

import json
from datetime import date, datetime
from typing import Any
from uuid import UUID


def json_default_handler(obj: Any) -> str:
    """Handle common non-serializable types for JSON encoding.

    Args:
        obj: Object to serialize

    Returns:
        String representation of the object
    """
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    return str(obj)


def to_json_string(obj: dict, indent: int = 2) -> str:
    """Convert dictionary to JSON string with proper handling of complex types.

    Args:
        obj: Dictionary to convert to JSON
        indent: Indentation level for pretty printing

    Returns:
        JSON string representation
    """
    try:
        return json.dumps(obj, ensure_ascii=False, indent=indent, default=json_default_handler)
    except Exception:
        # Fallback to simple string representation
        return str(obj)
