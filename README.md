# csvdiff-cli

A command-line tool for semantic diffing of CSV files with configurable key columns and output formats.

---

## Installation

```bash
pip install csvdiff-cli
```

Or install from source:

```bash
git clone https://github.com/yourname/csvdiff-cli.git && cd csvdiff-cli && pip install .
```

---

## Usage

```bash
csvdiff [OPTIONS] FILE_A FILE_B
```

**Options:**

| Flag | Description |
|------|-------------|
| `-k, --key COLUMN` | Column(s) to use as the row identifier (repeatable) |
| `-f, --format FORMAT` | Output format: `text` (default), `json`, or `csv` |
| `-o, --output FILE` | Write output to a file instead of stdout |
| `--ignore COLUMN` | Ignore a column when comparing (repeatable) |

**Example:**

```bash
# Diff two CSV files keyed on the "id" column, output as JSON
csvdiff -k id -f json old_data.csv new_data.csv
```

**Sample output (`text` format):**

```
~ MODIFIED  row id=42   price: 9.99 -> 12.49
+ ADDED      row id=99
- REMOVED    row id=17
```

---

## How It Works

`csvdiff-cli` performs a **semantic diff** rather than a line-by-line text diff. Rows are matched by the specified key column(s), so reordered rows are not reported as changes — only actual data modifications, additions, and deletions.

---

## Requirements

- Python 3.8+
- No external dependencies (uses standard library only)

---

## License

This project is licensed under the [MIT License](LICENSE).