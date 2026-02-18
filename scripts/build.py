"""
Build script for HEX Grid Tessellator v3.

Compiles main.py to a standalone .exe via PyInstaller, then smoke-tests the
resulting executable to verify it runs and produces valid output.

Exit code 0 = build and smoke test passed, 1 = failed.
"""

import os
import re
import subprocess
import sys
import tempfile
from datetime import date

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(PROJECT_DIR, "main.py")
CHANGELOG = os.path.join(PROJECT_DIR, "CHANGELOG.md")
VENV_PYINSTALLER = os.path.join(PROJECT_DIR, "venv", "Scripts", "pyinstaller.exe")
EXE_PATH = os.path.join(PROJECT_DIR, "dist", "hextessellator.exe")
BANNER_WIDTH = 60

sys.stdout.reconfigure(encoding="utf-8")


def print_banner(text):
    """Print text inside an ASCII box-drawing banner."""
    width = max(BANNER_WIDTH, len(text) + 4)
    inner = width - 2
    print("\u250c" + "\u2500" * inner + "\u2510")
    print("\u2502 " + text.ljust(inner - 2) + " \u2502")
    print("\u2514" + "\u2500" * inner + "\u2518")


def _read_changelog_version():
    """Return the highest versioned heading from CHANGELOG.md, or None."""
    try:
        with open(CHANGELOG, "r", encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^##\s+\[(\d+\.\d+\.\d+)\]", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return None


def step_stamp_version():
    """Stamp the changelog version into main.py VERSION fallback. Returns (success: bool, summary: str)."""
    version = _read_changelog_version()
    if version is None:
        return False, "Could not read version from CHANGELOG.md"

    with open(MAIN_PY, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'(_changelog_version\(")[^"]*("\))'
    new_content, n = re.subn(pattern, rf'\g<1>{version}\2', content)

    if n == 0:
        return False, "Could not find _changelog_version() fallback pattern in main.py"

    if new_content != content:
        with open(MAIN_PY, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, f'Stamped VERSION fallback = "{version}"'
    else:
        return True, f'VERSION fallback already "{version}" - no change needed'


def step_stamp_build_date():
    """Stamp today's date into main.py BUILD_DATE. Returns (success: bool, summary: str)."""
    today = date.today().isoformat()

    with open(MAIN_PY, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'(BUILD_DATE:\s*str\s*=\s*")[^"]*(")'
    new_content, n = re.subn(pattern, rf"\g<1>{today}\2", content)

    if n == 0:
        return False, "Could not find BUILD_DATE pattern in main.py"

    if new_content != content:
        with open(MAIN_PY, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, f"Stamped BUILD_DATE = \"{today}\""
    else:
        return True, f"BUILD_DATE already \"{today}\" - no change needed"


def step_build_exe():
    """Build the .exe via PyInstaller. Returns (success: bool, summary: str)."""
    result = subprocess.run(
        [VENV_PYINSTALLER, "--onefile", "--name", "hextessellator", "main.py"],
        capture_output=True, text=True, cwd=PROJECT_DIR
    )
    if result.returncode == 0 and os.path.isfile(EXE_PATH):
        return True, f"Built {EXE_PATH}"
    else:
        stderr_tail = result.stderr.strip().splitlines()[-3:] if result.stderr else []
        return False, f"PyInstaller failed (exit {result.returncode}): {' '.join(stderr_tail)}"


def step_smoke_test_exe():
    """Run the .exe with --debug and verify it produces a PNG. Returns (success: bool, summary: str)."""
    if not os.path.isfile(EXE_PATH):
        return False, f"{EXE_PATH} not found"

    with tempfile.TemporaryDirectory() as tmpdir:
        output_png = os.path.join(tmpdir, "smoke_test.png")
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [EXE_PATH, "--file", output_png, "--debug"],
            capture_output=True, text=True, encoding="utf-8", cwd=tmpdir, env=env
        )
        if result.returncode != 0:
            return False, f".exe exited with code {result.returncode}"
        if not os.path.isfile(output_png):
            return False, ".exe ran but did not produce output PNG"
        size = os.path.getsize(output_png)
        if size == 0:
            return False, ".exe produced empty PNG file"
        return True, f".exe produced {size}-byte PNG"


def main():
    print_banner("HEX Grid Tessellator v3 - Build")
    print()

    # Step 1: Stamp version from changelog
    print("[1/4] Stamping version from CHANGELOG.md...")
    ok_version, msg = step_stamp_version()
    print(f"      {'PASS' if ok_version else 'FAIL'}: {msg}")
    print()

    # Step 2: Stamp build date
    print("[2/4] Stamping build date...")
    ok_stamp, msg = step_stamp_build_date()
    print(f"      {'PASS' if ok_stamp else 'FAIL'}: {msg}")
    print()

    # Step 3: Build
    print("[3/4] Building .exe...")
    ok_build, msg = step_build_exe()
    print(f"      {'PASS' if ok_build else 'FAIL'}: {msg}")
    print()

    # Step 4: Smoke test
    print("[4/4] Smoke-testing .exe...")
    if ok_build:
        ok_smoke, msg = step_smoke_test_exe()
        print(f"      {'PASS' if ok_smoke else 'FAIL'}: {msg}")
    else:
        ok_smoke = False
        msg = "Skipped - build failed"
        print(f"      SKIP: {msg}")
    print()

    # Summary
    all_passed = ok_version and ok_stamp and ok_build and ok_smoke
    if all_passed:
        print_banner("Build successful.")
    else:
        print_banner("Build FAILED.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
