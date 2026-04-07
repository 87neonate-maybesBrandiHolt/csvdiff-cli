"""Tests for the core CSV diffing logic."""

import pytest
from csvdiff.core import (
    ChangeType,
    RowDiff,
    DiffResult,
    diff_csvs,
    load_csv,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_OLD = [
    {"id": "1", "name": "Alice", "age": "30"},
    {"id": "2", "name": "Bob",   "age": "25"},
    {"id": "3", "name": "Carol", "age": "40"},
]

SAMPLE_NEW = [
    {"id": "1", "name": "Alice",  "age": "31"},   # modified
    {"id": "3", "name": "Carol",  "age": "40"},   # unchanged
    {"id": "4", "name": "Dave",   "age": "22"},   # added
    # id=2 removed
]


# ---------------------------------------------------------------------------
# RowDiff / DiffResult unit tests
# ---------------------------------------------------------------------------

class TestRowDiff:
    def test_added(self):
        rd = RowDiff(change_type=ChangeType.ADDED, key={"id": "4"}, new_row={"id": "4", "name": "Dave", "age": "22"})
        assert rd.change_type == ChangeType.ADDED
        assert rd.old_row is None

    def test_removed(self):
        rd = RowDiff(change_type=ChangeType.REMOVED, key={"id": "2"}, old_row={"id": "2", "name": "Bob", "age": "25"})
        assert rd.change_type == ChangeType.REMOVED
        assert rd.new_row is None

    def test_modified_changed_fields(self):
        old = {"id": "1", "name": "Alice", "age": "30"}
        new = {"id": "1", "name": "Alice", "age": "31"}
        rd = RowDiff(change_type=ChangeType.MODIFIED, key={"id": "1"}, old_row=old, new_row=new)
        assert rd.changed_fields == {"age"}

    def test_unchanged_no_changed_fields(self):
        row = {"id": "3", "name": "Carol", "age": "40"}
        rd = RowDiff(change_type=ChangeType.UNCHANGED, key={"id": "3"}, old_row=row, new_row=row)
        assert rd.changed_fields == set()


class TestDiffResult:
    def _make_result(self):
        diffs = [
            RowDiff(ChangeType.ADDED,    {"id": "4"}, new_row={"id": "4", "name": "Dave",  "age": "22"}),
            RowDiff(ChangeType.REMOVED,  {"id": "2"}, old_row={"id": "2", "name": "Bob",   "age": "25"}),
            RowDiff(ChangeType.MODIFIED, {"id": "1"},
                    old_row={"id": "1", "name": "Alice", "age": "30"},
                    new_row={"id": "1", "name": "Alice", "age": "31"}),
            RowDiff(ChangeType.UNCHANGED, {"id": "3"},
                    old_row={"id": "3", "name": "Carol", "age": "40"},
                    new_row={"id": "3", "name": "Carol", "age": "40"}),
        ]
        return DiffResult(diffs=diffs, key_columns=["id"])

    def test_has_differences_true(self):
        result = self._make_result()
        assert result.has_differences() is True

    def test_counts(self):
        result = self._make_result()
        assert result.added_count == 1
        assert result.removed_count == 1
        assert result.modified_count == 1
        assert result.unchanged_count == 1

    def test_no_differences(self):
        row = {"id": "1", "name": "Alice", "age": "30"}
        diffs = [RowDiff(ChangeType.UNCHANGED, {"id": "1"}, old_row=row, new_row=row)]
        result = DiffResult(diffs=diffs, key_columns=["id"])
        assert result.has_differences() is False


# ---------------------------------------------------------------------------
# diff_csvs integration tests
# ---------------------------------------------------------------------------

class TestDiffCsvs:
    def test_detects_added(self):
        result = diff_csvs(SAMPLE_OLD, SAMPLE_NEW, key_columns=["id"])
        added = [d for d in result.diffs if d.change_type == ChangeType.ADDED]
        assert len(added) == 1
        assert added[0].key == {"id": "4"}

    def test_detects_removed(self):
        result = diff_csvs(SAMPLE_OLD, SAMPLE_NEW, key_columns=["id"])
        removed = [d for d in result.diffs if d.change_type == ChangeType.REMOVED]
        assert len(removed) == 1
        assert removed[0].key == {"id": "2"}

    def test_detects_modified(self):
        result = diff_csvs(SAMPLE_OLD, SAMPLE_NEW, key_columns=["id"])
        modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
        assert len(modified) == 1
        assert modified[0].key == {"id": "1"}
        assert modified[0].changed_fields == {"age"}

    def test_detects_unchanged(self):
        result = diff_csvs(SAMPLE_OLD, SAMPLE_NEW, key_columns=["id"])
        unchanged = [d for d in result.diffs if d.change_type == ChangeType.UNCHANGED]
        assert len(unchanged) == 1
        assert unchanged[0].key == {"id": "3"}

    def test_identical_files_no_differences(self):
        result = diff_csvs(SAMPLE_OLD, SAMPLE_OLD, key_columns=["id"])
        assert result.has_differences() is False

    def test_composite_key(self):
        old = [{"dept": "eng", "emp": "alice", "level": "3"}]
        new = [{"dept": "eng", "emp": "alice", "level": "4"}]
        result = diff_csvs(old, new, key_columns=["dept", "emp"])
        modified = [d for d in result.diffs if d.change_type == ChangeType.MODIFIED]
        assert len(modified) == 1
        assert modified[0].changed_fields == {"level"}

    def test_empty_old(self):
        result = diff_csvs([], SAMPLE_NEW, key_columns=["id"])
        assert result.added_count == len(SAMPLE_NEW)
        assert result.removed_count == 0

    def test_empty_new(self):
        result = diff_csvs(SAMPLE_OLD, [], key_columns=["id"])
        assert result.removed_count == len(SAMPLE_OLD)
        assert result.added_count == 0

    def test_missing_key_column_raises(self):
        with pytest.raises((KeyError, ValueError)):
            diff_csvs(SAMPLE_OLD, SAMPLE_NEW, key_columns=["nonexistent"])
