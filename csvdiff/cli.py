"""Command-line interface for csvdiff-cli.

Provides the main entry point and argument parsing for the CSV diff tool.
"""

import sys
import argparse
from pathlib import Path

from .core import diff_csvs
from .formatter import format_result


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="csvdiff",
        description="Semantically diff two CSV files based on configurable key columns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  csvdiff old.csv new.csv --key id
  csvdiff old.csv new.csv --key id name --format json
  csvdiff old.csv new.csv --key id --format csv --output diff.csv
  csvdiff old.csv new.csv --key id --ignore updated_at --no-color
""",
    )

    parser.add_argument(
        "file_a",
        metavar="FILE_A",
        type=Path,
        help="original CSV file",
    )
    parser.add_argument(
        "file_b",
        metavar="FILE_B",
        type=Path,
        help="modified CSV file",
    )
    parser.add_argument(
        "--key",
        "-k",
        metavar="COLUMN",
        nargs="+",
        required=True,
        help="one or more column names to use as the row key",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "csv"],
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        type=Path,
        default=None,
        help="write output to FILE instead of stdout",
    )
    parser.add_argument(
        "--ignore",
        "-i",
        metavar="COLUMN",
        nargs="+",
        default=None,
        help="columns to ignore when comparing rows",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        default=False,
        help="disable colored output (text format only)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="suppress summary statistics",
    )

    return parser


def run(argv: list[str] | None = None) -> int:
    """Run the csvdiff CLI.

    Args:
        argv: Argument list; defaults to sys.argv if None.

    Returns:
        Exit code: 0 if no differences found, 1 if differences exist,
        2 on usage/file errors.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate input files exist
    for path, label in [(args.file_a, "FILE_A"), (args.file_b, "FILE_B")]:
        if not path.exists():
            parser.error(f"{label}: file not found: {path}")
        if not path.is_file():
            parser.error(f"{label}: not a regular file: {path}")

    try:
        result = diff_csvs(
            path_a=args.file_a,
            path_b=args.file_b,
            key_columns=args.key,
            ignore_columns=args.ignore or [],
        )
    except ValueError as exc:
        print(f"csvdiff: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"csvdiff: error reading file: {exc}", file=sys.stderr)
        return 2

    formatted = format_result(
        result,
        fmt=args.format,
        color=not args.no_color,
        show_summary=not args.quiet,
    )

    if args.output:
        try:
            args.output.write_text(formatted, encoding="utf-8")
        except OSError as exc:
            print(f"csvdiff: error writing output: {exc}", file=sys.stderr)
            return 2
    else:
        print(formatted, end="")

    # Exit 1 when differences were found (useful for CI pipelines)
    return 1 if result.has_differences() else 0


def main() -> None:
    """Entry point for the installed console script."""
    sys.exit(run())


if __name__ == "__main__":
    main()
