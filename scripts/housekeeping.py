"""
Housekeeping script for HEX Grid Tessellator v3.

Automates the mechanical Definition-of-Done checks:
  1. Stamp version from CHANGELOG.md into main.py fallback
  2. Stamp build date into main.py
  3. Build standalone .exe via PyInstaller
  4. Smoke-test the .exe (exit code + PNG output)
  5. Run pytest and parse pass/fail count
  6. Update CLAUDE.md Status section with current test count
  7. Update CHANGELOG.md summary table
  8. Validate run.bat uses venv or dist exe (not bare python)

Exit code 0 = all checks passed, 1 = one or more failed.
"""

import os
import re
import subprocess
import sys

from build import step_stamp_version, step_stamp_build_date, step_build_exe, step_smoke_test_exe
from changelog_table import step_update_changelog_table

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
CLAUDE_MD = os.path.join(PROJECT_DIR, "CLAUDE.md")
RUN_BAT = os.path.join(PROJECT_DIR, "run.bat")
BANNER_WIDTH = 60

sys.stdout.reconfigure(encoding="utf-8")


def print_banner(text):
    """Print text inside an ASCII box-drawing banner."""
    width = max(BANNER_WIDTH, len(text) + 4)
    inner = width - 2
    print("\u250c" + "\u2500" * inner + "\u2510")
    print("\u2502 " + text.ljust(inner - 2) + " \u2502")
    print("\u2514" + "\u2500" * inner + "\u2518")


def step_run_tests():
    """Run pytest, return (passed: bool, total_count: int, summary: str)."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run(
        [VENV_PYTHON, "-m", "pytest", "test_main.py", "-v"],
        capture_output=True, text=True, encoding="utf-8", cwd=PROJECT_DIR, env=env
    )
    # Parse summary line like "71 passed" or "70 passed, 1 failed"
    match = re.search(r"(\d+) passed", result.stdout)
    total = int(match.group(1)) if match else 0
    failed_match = re.search(r"(\d+) failed", result.stdout)
    failed = int(failed_match.group(1)) if failed_match else 0

    if result.returncode == 0 and total > 0:
        return True, total, f"{total} passed, 0 failed"
    else:
        return False, total, f"{total} passed, {failed} failed (exit code {result.returncode})"


def step_update_claude_md(test_count):
    """Update the test count in CLAUDE.md Status section. Returns (changed: bool, summary: str)."""
    with open(CLAUDE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(All )\d+( tests in `test_main\.py` pass)"
    replacement = rf"\g<1>{test_count}\2"
    new_content, n = re.subn(pattern, replacement, content)

    if n == 0:
        return False, "Could not find test count pattern in CLAUDE.md Status section"

    if new_content != content:
        with open(CLAUDE_MD, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, f"Updated test count to {test_count}"
    else:
        return True, f"Test count already {test_count} - no change needed"


def step_validate_run_bat():
    """Check that run.bat does not use bare 'python'. Returns (valid: bool, summary: str)."""
    if not os.path.isfile(RUN_BAT):
        return False, f"{RUN_BAT} not found"

    with open(RUN_BAT, "r", encoding="utf-8") as f:
        content = f.read()

    # Acceptable: contains venv path or dist\hextessellator.exe
    uses_venv = "venv\\Scripts\\python.exe" in content or "venv/Scripts/python.exe" in content
    uses_exe = "dist\\hextessellator.exe" in content or "dist/hextessellator.exe" in content

    if uses_venv or uses_exe:
        return True, "run.bat uses venv/exe path"

    # Check for bare python (not preceded by venv path)
    if re.search(r"(?<!Scripts\\)(?<!Scripts/)python\b", content, re.IGNORECASE):
        return False, "run.bat uses bare 'python' - must use venv\\Scripts\\python.exe"

    return True, "run.bat does not invoke python directly"


def main():
    print_banner("HEX Grid Tessellator v3 - Housekeeping")
    print()

    results = []

    # Step 1: Stamp version from changelog
    print("[1/8] Stamping version from CHANGELOG.md...")
    ok_ver, msg = step_stamp_version()
    results.append(("Stamp version", ok_ver, msg))
    print(f"      {'PASS' if ok_ver else 'FAIL'}: {msg}")
    print()

    # Step 2: Stamp build date
    print("[2/8] Stamping build date...")
    ok_date, msg = step_stamp_build_date()
    results.append(("Stamp build date", ok_date, msg))
    print(f"      {'PASS' if ok_date else 'FAIL'}: {msg}")
    print()

    # Step 3: Build .exe (before tests so exe tests run against fresh build)
    print("[3/8] Building .exe...")
    ok_build, msg = step_build_exe()
    results.append(("Build .exe", ok_build, msg))
    print(f"      {'PASS' if ok_build else 'FAIL'}: {msg}")
    print()

    # Step 4: Smoke-test .exe
    print("[4/8] Smoke-testing .exe...")
    if ok_build:
        ok_smoke, msg = step_smoke_test_exe()
        results.append(("Smoke-test .exe", ok_smoke, msg))
        print(f"      {'PASS' if ok_smoke else 'FAIL'}: {msg}")
    else:
        results.append(("Smoke-test .exe", False, "Skipped - build failed"))
        print("      SKIP: Build failed")
    print()

    # Step 5: Run tests (after build so exe tests use the fresh .exe)
    print("[5/8] Running tests...")
    ok, count, msg = step_run_tests()
    results.append(("Run tests", ok, msg))
    print(f"      {'PASS' if ok else 'FAIL'}: {msg}")
    print()

    # Step 6: Update CLAUDE.md
    print("[6/8] Updating CLAUDE.md test count...")
    if ok:
        changed, msg = step_update_claude_md(count)
        results.append(("Update CLAUDE.md", changed, msg))
        print(f"      {'PASS' if changed else 'FAIL'}: {msg}")
    else:
        results.append(("Update CLAUDE.md", False, "Skipped - tests failed"))
        print("      SKIP: Tests failed, not updating test count")
    print()

    # Step 7: Update changelog table
    print("[7/8] Updating CHANGELOG.md table...")
    ok_tbl, msg = step_update_changelog_table()
    results.append(("Update changelog table", ok_tbl, msg))
    print(f"      {'PASS' if ok_tbl else 'FAIL'}: {msg}")
    print()

    # Step 8: Validate run.bat
    print("[8/8] Validating run.bat...")
    ok_bat, msg = step_validate_run_bat()
    results.append(("Validate run.bat", ok_bat, msg))
    print(f"      {'PASS' if ok_bat else 'FAIL'}: {msg}")
    print()

    # Summary
    all_passed = all(r[1] for r in results)
    print_banner("Summary")
    for name, ok, msg in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {msg}")
    print()
    if all_passed:
        print_banner("All checks passed.")
    else:
        print_banner("One or more checks FAILED.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
