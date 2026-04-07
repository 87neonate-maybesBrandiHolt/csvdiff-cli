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
    """Format diff result as a CSV file with a '_change_type' column prepended.

    Args:
        result: The diff result to format.
        show_unchanged: Whether to include unchanged rows in output.

    Returns:
        A CSV string with change type annotations.
    """
    output = io.StringIO()
    writer = None

    for diff in result.diffs:
        if diff.change_type == ChangeType.UNCHANGED and not show_unchanged:
            continue

        # Use new_row for added/modified/unchanged, old_row for removed
        row_data = diff.new_row if diff.new_row is not None else diff.old_row
        if row_data is None:
            continue

        annotated_row = {"_change_type": diff.change_type.value, **row_data}

        if writer is None:
            fieldnames = list(annotated_row.keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()

        writer.writerow(annotated_row)

    return output.getvalue()


FORMAT_HANDLERS = {
    "text": format_text,
    "json": format_json,
    "csv": format_csv,
}


def format_result(result: DiffResult, fmt: str = "text", show_unchanged: bool = False) -> str:
    """Dispatch to the appropriate formatter.

    Args:
        result: The diff result to format.
        fmt: Output format name ('text', 'json', or 'csv').
        show_unchanged: Whether to include unchanged rows in output.

    Returns:
        Formatted string output.

    Raises:
        ValueError: If the requested format is not supported.
    """
    handler = FORMAT_HANDLERS.get(fmt)
    if handler is None:
        supported = ", ".join(FORMAT_HANDLERS.keys())
        raise ValueError(f"Unsupported format {fmt!r}. Choose from: {supported}")
    return handler(result, show_unchanged=show_unchanged)
