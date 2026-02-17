---
description: Update all project documentation to reflect the current state of the codebase.
---

Update all project documentation to reflect the current state of the codebase.

## Steps

1. **Run housekeeping** using `venv/Scripts/python.exe scripts/housekeeping.py`. This runs the test suite, updates the CLAUDE.md test count, rebuilds the `.exe`, smoke-tests the `.exe`, updates the changelog table, and validates `run.bat`. All checks must pass.
2. **Update CHANGELOG.md** with any changes made during this session that are not yet recorded. Add entries under `[Unreleased]` using the appropriate category (Added, Changed, Fixed, Removed). Include today's date if creating a new version heading.
3. **Report** a summary of what was updated.
