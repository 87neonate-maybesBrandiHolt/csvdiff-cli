"""Tests for the formatter module."""

import json
import pytest
from csvdiff.core import ChangeType, RowDiff, DiffResult
from csvdiff.formatter import format_text, format_json, format_csv


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_diff_result():
    """A DiffResult with one added, one removed, and one modified row."""
    added = RowDiff(
        change_type=ChangeType.ADDED,
        key={"id": "3"},
        old_row=None,
        new_row={"id": "3", "name": "Charlie", "score": "95"},
        changed_fields=[],
    )
    removed = RowDiff(
        change_type=ChangeType.REMOVED,
        key={"id": "2"},
        old_row={"id": "2", "name": "Bob", "score": "80"},
        new_row=None,
        changed_fields=[],
    )
    modified = RowDiff(
        change_type=ChangeType.MODIFIED,
        key={"id": "1"},
        old_row={"id": "1", "name": "Alice", "score": "70"},
        new_row={"id": "1", "name": "Alice", "score": "75"},
        changed_fields=["score"],
    )
    return DiffResult(diffs=[added, removed, modified])


@pytest.fixture
def empty_diff_result():
    """A DiffResult with no differences."""
    return DiffResult(diffs=[])


# ---------------------------------------------------------------------------
# format_text
# ---------------------------------------------------------------------------

class TestFormatText:
    def test_empty_diff_contains_no_differences(self, empty_diff_result):
        output = format_text(empty_diff_result)
        assert "no differences" in output.lower()

    def test_added_row_present(self, sample_diff_result):
        output = format_text(sample_diff_result)
        assert "ADDED" in output or "added" in output.lower()
        assert "Charlie" in output

    def test_removed_row_present(self, sample_diff_result):
        output = format_text(sample_diff_result)
        assert "REMOVED" in output or "removed" in output.lower()
        assert "Bob" in output

    def test_modified_row_present(self, sample_diff_result):
        output = format_text(sample_diff_result)
        assert "MODIFIED" in output or "modified" in output.lower()
        assert "score" in output

    def test_returns_string(self, sample_diff_result):
        assert isinstance(format_text(sample_diff_result), str)


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------

class TestFormatJson:
    def test_returns_valid_json(self, sample_diff_result):
        output = format_json(sample_diff_result)
        parsed = json.loads(output)  # must not raise
        assert parsed is not None

    def test_empty_diff_has_empty_list(self, empty_diff_result):
        output = format_json(empty_diff_result)
        parsed = json.loads(output)
        # Accept either a list or a dict with a 'diffs'/'changes' key
        if isinstance(parsed, list):
            assert len(parsed) == 0
        else:
            diffs = parsed.get("diffs") or parsed.get("changes") or []
            assert len(diffs) == 0

    def test_added_entry_in_json(self, sample_diff_result):
        output = format_json(sample_diff_result)
        assert "ADDED" in output or "added" in output

    def test_removed_entry_in_json(self, sample_diff_result):
        output = format_json(sample_diff_result)
        assert "REMOVED" in output or "removed" in output

    def test_modified_entry_in_json(self, sample_diff_result):
        output = format_json(sample_diff_result)
        assert "MODIFIED" in output or "modified" in output

    def test_key_present_in_json(self, sample_diff_result):
        output = format_json(sample_diff_result)
        parsed = json.loads(output)
        # Flatten to list of entries
        entries = parsed if isinstance(parsed, list) else (
            parsed.get("diffs") or parsed.get("changes") or []
        )
        assert any("1" in str(e) for e in entries)  # key id=1 is present


# ---------------------------------------------------------------------------
# format_csv
# ---------------------------------------------------------------------------

class TestFormatCsv:
    def test_returns_string(self, sample_diff_result):
        assert isinstance(format_csv(sample_diff_result), str)

    def test_has_header_row(self, sample_diff_result):
        output = format_csv(sample_diff_result)
        lines = [l for l in output.splitlines() if l.strip()]
        assert len(lines) >= 1
        # Header should contain a change-type column
        header = lines[0].lower()
        assert "change" in header or "type" in header

    def test_row_count_matches_diffs(self, sample_diff_result):
        output = format_csv(sample_diff_result)
        lines = [l for l in output.splitlines() if l.strip()]
        # 1 header + 3 data rows
        assert len(lines) == 4

    def test_empty_diff_only_header(self, empty_diff_result):
        output = format_csv(empty_diff_result)
        lines = [l for l in output.splitlines() if l.strip()]
        # Either empty string or just a header row
        assert len(lines) <= 1
