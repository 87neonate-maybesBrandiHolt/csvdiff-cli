"""Output formatters for CSV diff results.

Supports multiple output formats: text (human-readable), JSON, and CSV.
"""

import json
import csv
import io
from typing import List

from .core import DiffResult, RowDiff, ChangeType


def format_text(result: DiffResult, show_unchanged: bool = False) -> str:
    """Format diff result as human-readable text.

    Args:
        result: The diff result to format.
        show_unchanged: Whether to include unchanged rows in output.

    Returns:
        A formatted string representation of the diff.
    """
    lines = []

    summary = result.summary()
    lines.append("=== CSV Diff Summary ===")
    lines.append(f"  Added rows:    {summary['added']}")
    lines.append(f"  Removed rows:  {summary['removed']}")
    lines.append(f"  Modified rows: {summary['modified']}")
    if show_unchanged:
        lines.append(f"  Unchanged rows:{summary['unchanged']}")
    lines.append("")

    if not result.has_differences():
        lines.append("No differences found.")
        return "\n".join(lines)

    for diff in result.diffs:
        if diff.change_type == ChangeType.ADDED:
            lines.append(f"[+] Key: {diff.key}")
            lines.append(f"    New: {diff.new_row}")
        elif diff.change_type == ChangeType.REMOVED:
            lines.append(f"[-] Key: {diff.key}")
            lines.append(f"    Old: {diff.old_row}")
        elif diff.change_type == ChangeType.MODIFIED:
            lines.append(f"[~] Key: {diff.key}")
            for col, (old_val, new_val) in (diff.changed_fields or {}).items():
                lines.append(f"    {col}: {old_val!r} -> {new_val!r}")
        elif diff.change_type == ChangeType.UNCHANGED and show_unchanged:
            lines.append(f"[=] Key: {diff.key}")
        lines.append("")

    return "\n".join(lines)


def format_json(result: DiffResult, show_unchanged: bool = False) -> str:
    """Format diff result as JSON.

    Args:
        result: The diff result to format.
        show_unchanged: Whether to include unchanged rows in output.

    Returns:
        A JSON string representation of the diff.
    """
    output = {
        "summary": result.summary(),
        "diffs": [],
    }

    for diff in result.diffs:
        if diff.change_type == ChangeType.UNCHANGED and not show_unchanged:
            continue

        entry = {
            "change_type": diff.change_type.value,
            "key": diff.key,
        }

        if diff.old_row is not None:
            entry["old_row"] = diff.old_row
        if diff.new_row is not None:
            entry["new_row"] = diff.new_row
        if diff.changed_fields:
            entry["changed_fields"] = {
                col: {"old": old_val, "new": new_val}
                for col, (old_val, new_val) in diff.changed_fields.items()
            }

        output["diffs"].append(entry)

    return json.dumps(output, indent=2, default=str)


def format_csv(result: DiffResult, show_unchanged: bool = False) -> str:
    """Format diff result as CSV.

    Each row in the output includes a '_change_type' column indicating whether
    the row was added, removed, modified, or unchanged. Modified rows appear
    twice: once with the old values and once with the new values, distinguished
    by '_change_type' values of 'modified_old' and 'modified_new' respectively.

    Args:
        result: The diff result to format.
        show_unchanged: Whether to include unchanged rows in output.

    Returns:
        A CSV string representation of the diff.
    """
    output = io.StringIO()

    # Collect all field names from diffs to build a consistent header
    fieldnames_seen: list = ["_change_type"]
    for diff in result.diffs:
        row = diff.new_row or diff.old_row or {}
        for key in row:
            if key not in fieldnames_seen:
                fieldnames_seen.append(key)

    writer = csv.DictWriter(output, fieldnames=fieldnames_seen, extrasaction="ignore")
    writer.writeheader()

    for diff in result.diffs:
        if diff.change_type == ChangeType.UNCHANGED and not show_unchanged:
            continue

        if diff.change_type == ChangeType.ADDED:
            writer.writerow({"_change_type": "added", **(diff.new_row or {})})
        elif diff.change_type == ChangeType.REMOVED:
            writer.writerow({"_change_type": "removed", **(diff.old_row or {})})
        elif diff.change_type == ChangeType.MODIFIED:
            writer.writerow({"_change_type": "modified_old", **(diff.old_row or {})})
            writer.writerow({"_change_type": "modified_new", **(diff.new_row or {})})
        elif diff.change_type == ChangeType.UNCHANGED:
            writer.writerow({"_change_type": "unchanged", **(diff.new_row or {})})

    return output.getvalue()
