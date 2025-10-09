"""
Utility functions for Apple Mail MCP.
"""

import re
from typing import Any


def escape_applescript_string(s: str) -> str:
    """
    Escape string for safe AppleScript insertion.

    Args:
        s: String to escape

    Returns:
        Escaped string safe for AppleScript

    Examples:
        >>> escape_applescript_string('Hello "World"')
        'Hello \\\\"World\\\\"'
        >>> escape_applescript_string('Path\\to\\file')
        'Path\\\\to\\\\file'
    """
    return s.replace("\\", "\\\\").replace('"', '\\"')


def parse_applescript_list(result: str) -> list[str]:
    """
    Parse AppleScript list result into Python list.

    AppleScript returns lists as comma-separated values.

    Args:
        result: AppleScript output

    Returns:
        List of strings
    """
    if not result or result == "":
        return []

    # Handle empty list
    if result.strip() in ["{}", ""]:
        return []

    # Remove braces if present
    result = result.strip()
    if result.startswith("{") and result.endswith("}"):
        result = result[1:-1]

    # Split by comma and clean up
    items = [item.strip() for item in result.split(",") if item.strip()]
    return items


def format_applescript_list(items: list[str]) -> str:
    """
    Format Python list for AppleScript.

    Args:
        items: List of strings

    Returns:
        AppleScript list format

    Examples:
        >>> format_applescript_list(['a', 'b', 'c'])
        '{"a", "b", "c"}'
    """
    escaped_items = [f'"{escape_applescript_string(item)}"' for item in items]
    return "{" + ", ".join(escaped_items) + "}"


def parse_date_filter(date_str: str) -> str:
    """
    Convert human-readable date to AppleScript date expression.

    Args:
        date_str: Date string like "7 days ago", "2024-01-01", "last week"

    Returns:
        AppleScript date expression
    """
    # Handle relative dates
    pattern = r"(\d+)\s+(day|week|month|year)s?\s+ago"
    match = re.match(pattern, date_str.lower())

    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        return f"(current date) - ({amount} * {unit}s)"

    # Handle "last X"
    if date_str.lower().startswith("last "):
        unit = date_str[5:].strip().rstrip("s") + "s"
        return f"(current date) - (1 * {unit})"

    # Handle ISO dates (YYYY-MM-DD)
    if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
        return f'date "{date_str}"'

    # Default: return as is
    return f'date "{date_str}"'


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_input(value: Any) -> str:
    """
    Sanitize user input for safety.

    Args:
        value: User input value

    Returns:
        Sanitized string
    """
    if value is None:
        return ""

    # Convert to string
    s = str(value)

    # Remove null bytes
    s = s.replace("\x00", "")

    # Limit length
    max_length = 10000
    if len(s) > max_length:
        s = s[:max_length]

    return s
