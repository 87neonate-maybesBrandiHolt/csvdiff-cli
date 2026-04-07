"""Core diffing logic for csvdiff-cli.

This module provides the primary functionality for comparing two CSV files
semanticaly, using configurable key columns to identify matching rows and
detecting additions, deletions, and modifications.
"""

import csv
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ChangeType(Enum):
    ADDED = "added"
    DELETED = "deleted"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class RowDiff:
    """Represents a single row-level difference between two CSV files."""

    change_type: ChangeType
    key: Tuple
    old_row: Optional[Dict[str, str]] = None
    new_row: Optional[Dict[str, str]] = None
    changed_fields: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.change_type == ChangeType.MODIFIED and self.old_row and self.new_row:
            self.changed_fields = [
                col
                for col in self.new_row
                if col in self.old_row and self.old_row[col] != self.new_row[col]
            ]


@dataclass
class DiffResult:
    """Aggregated result of comparing two CSV files."""

    added: List[RowDiff] = field(default_factory=list)
    deleted: List[RowDiff] = field(default_factory=list)
    modified: List[RowDiff] = field(default_factory=list)
    unchanged: List[RowDiff] = field(default_factory=list)

    @property
    def has_differences(self) -> bool:
        return bool(self.added or self.deleted or self.modified)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.deleted) + len(self.modified)

    def all_diffs(self) -> List[RowDiff]:
        """Return all diffs sorted by change type for consistent output."""
        return self.deleted + self.added + self.modified


def _read_csv(filepath: str, encoding: str = "utf-8") -> Tuple[List[str], List[Dict[str, str]]]:
    """Read a CSV file and return its headers and rows as a list of dicts."""
    with open(filepath, newline="", encoding=encoding) as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            return [], []
        headers = list(reader.fieldnames)
        rows = [dict(row) for row in reader]
    return headers, rows


def _build_index(
    rows: List[Dict[str, str]], key_columns: List[str]
) -> Dict[Tuple, Dict[str, str]]:
    """Index rows by their composite key for fast lookup.

    Raises:
        ValueError: If a duplicate key is encountered.
    """
    index: Dict[Tuple, Dict[str, str]] = {}
    for row in rows:
        try:
            key = tuple(row[col] for col in key_columns)
        except KeyError as exc:
            raise ValueError(f"Key column {exc} not found in CSV headers.") from exc
        if key in index:
            raise ValueError(
                f"Duplicate key {key} found. Ensure key columns uniquely identify each row."
            )
        index[key] = row
    return index


def diff_csv(
    old_path: str,
    new_path: str,
    key_columns: List[str],
    encoding: str = "utf-8",
    ignore_columns: Optional[List[str]] = None,
) -> DiffResult:
    """Compare two CSV files and return a structured DiffResult.

    Args:
        old_path: Path to the original (baseline) CSV file.
        new_path: Path to the new (modified) CSV file.
        key_columns: Column name(s) that uniquely identify each row.
        encoding: File encoding to use when reading both files.
        ignore_columns: Optional list of columns to exclude from comparison.

    Returns:
        A DiffResult containing categorised row differences.
    """
    ignore = set(ignore_columns or [])

    old_headers, old_rows = _read_csv(old_path, encoding)
    new_headers, new_rows = _read_csv(new_path, encoding)

    if not old_headers and not new_headers:
        return DiffResult()

    old_index = _build_index(old_rows, key_columns)
    new_index = _build_index(new_rows, key_columns)

    result = DiffResult()

    # Detect deletions and modifications
    for key, old_row in old_index.items():
        if key not in new_index:
            result.deleted.append(
                RowDiff(change_type=ChangeType.DELETED, key=key, old_row=old_row)
            )
        else:
            new_row = new_index[key]
            # Compare only columns present in both and not ignored
            comparable_cols = [
                c for c in old_row if c not in ignore and c in new_row
            ]
            if any(old_row[c] != new_row[c] for c in comparable_cols):
                result.modified.append(
                    RowDiff(
                        change_type=ChangeType.MODIFIED,
                        key=key,
                        old_row=old_row,
                        new_row=new_row,
                    )
                )
            else:
                result.unchanged.append(
                    RowDiff(change_type=ChangeType.UNCHANGED, key=key, old_row=old_row, new_row=new_row)
                )

    # Detect additions
    for key, new_row in new_index.items():
        if key not in old_index:
            result.added.append(
                RowDiff(change_type=ChangeType.ADDED, key=key, new_row=new_row)
            )

    return result
