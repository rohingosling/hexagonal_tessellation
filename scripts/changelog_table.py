"""
Changelog table generator for HEX Grid Tessellator v3.

Parses CHANGELOG.md entries and generates/updates a summary table at the end
of the file using standard markdown table syntax.  Manual edits to the Name
and Size columns are preserved across regenerations.

Usage:
    python changelog_table.py          # update table in CHANGELOG.md
    python changelog_table.py --dry    # preview without writing
"""

import os
import re
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHANGELOG = os.path.join(PROJECT_DIR, "CHANGELOG.md")

# Markers delimiting the auto-generated table
TABLE_START = "<!-- changelog-table-start -->"
TABLE_END = "<!-- changelog-table-end -->"

# Maximum column content widths for truncation
W_NAME = 30
W_DESC = 80

# Fibonacci T-shirt sizing heuristic (by description character count)
_SIZE_THRESHOLDS = [(60, "XS"), (100, "S"), (160, "M"), (250, "L"), (400, "XL")]


def _estimate_size(description: str) -> str:
    """Map description length to a Fibonacci T-shirt size."""
    n = len(description)
    for limit, label in _SIZE_THRESHOLDS:
        if n < limit:
            return label
    return "XXL"


def _generate_name(description: str, max_len: int = W_NAME) -> str:
    """Derive a short name from the first clause of a description."""
    name = description.replace("`", "")
    # Split on colon, em-dash, or parenthesis to get the leading phrase
    name = re.split(r"[:(—]", name)[0].strip()
    # Remove leading verbs that duplicate the Operation column
    for prefix in (
        "Add ", "Added ", "Fix ", "Fixed ", "Update ", "Updated ",
        "Moved ", "Migrated ", "Simplified ", "Extracted ", "Rebuilt ",
        "This ",
    ):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    # Collapse "Test test_foo" → "test_foo"
    if name.startswith("Test "):
        name = name[5:]
    if len(name) > max_len:
        name = name[: max_len - 1].rsplit(" ", 1)[0] + "…"
    return name


def _match_key(description: str) -> str:
    """Normalise the first 50 chars of a description for row matching."""
    return description.replace("`", "").strip()[:50].lower()


# ------------------------------------------------------------------
# Parsing
# ------------------------------------------------------------------

def parse_changelog(text: str) -> list:
    """Extract (date, operation, description) entries from changelog markdown."""
    if TABLE_START in text:
        text = text[: text.index(TABLE_START)]

    entries = []
    current_date = ""
    current_op = ""

    for line in text.splitlines():
        # Version heading: ## [X.Y.Z] - YYYY-MM-DD  or  ## [Unreleased]
        m = re.match(r"^##\s+\[([^\]]+)\](?:\s*[-–—]\s*(.+))?", line)
        if m:
            ver = m.group(1)
            date_str = (m.group(2) or "").strip()
            if ver.lower() == "unreleased":
                current_date = "Unreleased"
            else:
                # Extract YYYY-MM-DD if present, else keep raw text
                dm = re.search(r"\d{4}-\d{2}-\d{2}", date_str)
                current_date = dm.group(0) if dm else date_str
            current_op = ""
            continue

        # Operation heading: ### Added, ### Changed, etc.
        m = re.match(r"^###\s+(\w+)", line)
        if m:
            current_op = m.group(1)
            continue

        # Top-level bullet (skip indented sub-bullets)
        m = re.match(r"^- (.+)", line)
        if m and current_op:
            entries.append({
                "date": current_date,
                "operation": current_op,
                "description": m.group(1).strip(),
                "name": None,
                "size": None,
            })

    return entries


def parse_existing_table(text: str) -> dict:
    """Read existing table rows; return {match_key: {size, name}}."""
    if TABLE_START not in text or TABLE_END not in text:
        return {}

    section = text[text.index(TABLE_START): text.index(TABLE_END)]
    rows = {}

    for line in section.splitlines():
        # Match markdown table rows: | col | col | ... |
        if not line.startswith("|"):
            continue
        # Skip separator rows like |---|---|
        if re.match(r"^\|[-:\s|]+\|$", line):
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) != 5:
            continue
        date, op, size, name, desc = parts
        if date == "Date":  # header
            continue
        key = _match_key(desc)
        rows[key] = {"size": size, "name": name}

    return rows


# ------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------

def _truncate(text: str, width: int) -> str:
    """Truncate text with ellipsis if it exceeds *width*."""
    text = text.replace("`", "")
    # Escape pipe characters so they don't break the markdown table
    text = text.replace("|", "\\|")
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def build_table(entries: list, existing: dict) -> str:
    """Format *entries* into a markdown table string."""
    lines = [
        "| Date | Operation | Size | Name | Description |",
        "|------|-----------|------|------|-------------|",
    ]

    for e in entries:
        key = _match_key(e["description"])

        # Preserve manually-edited Name/Size from a previous table
        if key in existing:
            name = existing[key]["name"]
            size = existing[key]["size"]
        else:
            name = _generate_name(e["description"])
            size = _estimate_size(e["description"])

        date = _truncate(e["date"], 10)
        op = _truncate(e["operation"], 9)
        name = _truncate(name, W_NAME)
        desc = _truncate(e["description"], W_DESC)

        lines.append(f"| {date} | {op} | {size} | {name} | {desc} |")

    return "\n".join(lines)


# ------------------------------------------------------------------
# Public step (importable by housekeeping.py)
# ------------------------------------------------------------------

def step_update_changelog_table():
    """Regenerate the summary table in CHANGELOG.md.

    Returns:
        (success: bool, summary: str)
    """
    try:
        with open(CHANGELOG, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        return False, f"Cannot read CHANGELOG.md: {exc}"

    entries = parse_changelog(content)
    if not entries:
        return False, "No changelog entries found"

    existing = parse_existing_table(content)
    table = build_table(entries, existing)
    section = f"\n{TABLE_START}\n{table}\n{TABLE_END}\n"

    if TABLE_START in content and TABLE_END in content:
        before = content[: content.index(TABLE_START)]
        after = content[content.index(TABLE_END) + len(TABLE_END):]
        new_content = before.rstrip("\n") + "\n" + section + after.lstrip("\n")
    else:
        new_content = content.rstrip("\n") + "\n\n## Change Log\n" + section

    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True, f"Updated table with {len(entries)} entries"


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    if "--dry" in sys.argv:
        with open(CHANGELOG, "r", encoding="utf-8") as f:
            content = f.read()
        entries = parse_changelog(content)
        existing = parse_existing_table(content)
        print(build_table(entries, existing))
        print(f"\n({len(entries)} entries)")
        return 0

    ok, msg = step_update_changelog_table()
    print(f"{'DONE' if ok else 'FAIL'}: {msg}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
