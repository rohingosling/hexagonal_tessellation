# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HEX Grid Tessellator v3 — a single-file Python CLI tool that generates publication-quality hexagonal grid tessellation PNG images. Uses flat-top hexagons on an axial coordinate system with supersampled anti-aliasing via Pillow.

## Status

Fully implemented. All 71 tests in `test_main.py` pass (including 4 executable smoke tests). Standalone `.exe` builds successfully via PyInstaller. Full requirements are in `prompts/prompt-requirements-hex-grid-tessellator.md`.

## Dependencies

- **Pillow** (only external dependency)
- **PyInstaller** (build dependency for `.exe` compilation)
- Standard library: `argparse`, `json`, `math`, `os`, `sys`

## Setup

```bash
venv_create.bat
venv_install_requirements.bat
```

All dependencies (Pillow, PyInstaller) are listed in `venv_requirements.txt`. The standard `venv_*.bat` scripts manage the virtual environment lifecycle (create, activate, deactivate, delete, install/save requirements).

## Running

```bash
python main.py --debug
python main.py --width 1920 --height 1080 --circumradius 48 --antialias high --debug
python main.py --import_settings settings.json
python main.py --export_settings settings.json
```

## Testing

```bash
python -m pytest test_main.py -v                           # full suite
python -m pytest test_main.py -v -k TestHexagonGeometry    # single test class
python -m pytest test_main.py -v -k test_vertex_count      # single test
python test_main.py                                        # without pytest
```

Run the full suite during development. Tests cover: class architecture/docstrings/type annotations, hexagon geometry math, axial grid and ring generation, color parsing, settings JSON round-trip, CLI defaults and error handling, image output validation (dimensions, colors, anti-aliasing), viewport culling, and two-pass stroke rendering.

## Building the Executable

```bash
pyinstaller --onefile main.py
```

The standalone `.exe` is output to `dist/hextessellator.exe` and runs without a Python installation.

## Rules

### Always
- Run `venv/Scripts/python.exe scripts/housekeeping.py` after any change to `main.py` or `test_main.py` — it runs tests, updates the test count in this file, rebuilds the `.exe`, smoke-tests it, updates the changelog table, and validates `run.bat`
- Use the venv Python (`venv/Scripts/python.exe`) for all commands — never bare `python` or `pip`
- Keep all code in a single file (`main.py`)
- Update `CHANGELOG.md` with every change — record the date, what was added/changed/fixed/removed, and why

### Never
- Never install packages to the global/system Python
- Never skip the executable build step after code changes
- Never split `main.py` into multiple source files
- Never use `polygon(outline=)` for stroke rendering — use the two-pass fill approach
- Never commit a broken `.exe` — if tests pass against `main.py` but fail against the exe, the exe must be rebuilt and retested

## Definition of Done

When implementing or modifying this project, ALL of the following must be completed before the task is considered finished. Do not skip any step.

1. **Virtual environment**: Create the venv (`python -m venv venv`) and install all dependencies using `venv/Scripts/pip.exe install -r venv_requirements.txt`. NEVER install packages to the global Python.
2. **Implementation**: All code in a single file (`main.py`). All six required classes present with docstrings and type annotations.
3. **Run housekeeping**: Run `venv/Scripts/python.exe scripts/housekeeping.py` and verify all checks pass. This script automatically: runs the full test suite, updates the CLAUDE.md test count, builds the `.exe`, smoke-tests the `.exe`, updates the changelog table, and validates `run.bat`.
4. **CHANGELOG.md updated**: Add an entry under `[Unreleased]` (or a new version heading) documenting what was added, changed, fixed, or removed. Follow [Keep a Changelog](https://keepachangelog.com/) format.

## Architecture

Single-file OOP design with six classes:

- **HexagonGeometry** — Vertex computation for flat-top regular hexagons (circumradius, inradius, vertex generation)
- **AxialGrid** — Axial coordinate system: coordinate-to-pixel conversion, ring traversal, concentric grid generation, auto-fill layer computation
- **ColorParser** — Parses CSS named colors, hex codes (`#FF0000`), and RGB comma-tuples (`255,128,0`) into `(R,G,B)` tuples via `ImageColor.getrgb()`
- **TessellationRenderer** — Rendering pipeline: canvas creation, two-pass concentric stroke drawing (outer fill then inner fill across entire grid), viewport culling, anti-alias downsampling
- **SettingsManager** — JSON import/export with CLI-precedence logic (JSON overrides defaults, explicit CLI args override JSON)
- **Application** — Entry point: CLI parsing, orchestration of settings, rendering, file output, debug reporting

## Key Design Details

- **Spacing radius**: `R_s = R + margin/2` separates grid layout spacing from drawing radius
- **Two-pass stroke rendering**: All outer hexagons drawn first (Pass 1), then all inner hexagons (Pass 2) — avoids miter-joint artifacts. Does NOT use Pillow's `polygon(outline=)`
- **Viewport culling**: Discards hexagons whose outer extent (including stroke) exceeds canvas bounds, using cull radius `R + line_width/2`
- **Anti-aliasing**: Renders at k× resolution (off=1×, low=2×, medium=4×, high=8×), then Lanczos downsamples
- **CLI precedence detection**: Parses args twice (once normally, once with `SUPPRESS` defaults) to distinguish explicit CLI args from defaults when merging with JSON settings
- **Auto-fill layers**: When `--layers 0`, computes minimum layers to cover canvas with +1 buffer

## Prompts Directory

The `prompts/` directory contains scratch markdown files used for prompt engineering and task descriptions. These are working notes — do not read or modify them unless explicitly asked.

## Ring Traversal

Rings enumerate from axial `(-d, 0)` walking `d` steps along each of 6 directions: `(+1,-1), (+1,0), (0,+1), (-1,+1), (-1,0), (0,-1)`. Total cells for L layers: `1 + 3L(L-1)`.

## TODO

- [x] **Publish to GitHub as a standalone repo** — Published to https://github.com/rohingosling/hexagonal_tessellation on 2026-02-18. Added MIT LICENSE, configured `.gitignore`, and pushed initial commit.

- [ ] **Set up GitHub Releases for distributing `hextessellator.exe`** — After the repo is published, the `.exe` should be distributed as a release asset rather than committed in `dist/`. Steps:
  1. Install GitHub CLI: download from https://cli.github.com, then run `gh auth login`
  2. Create a git tag: `git tag v3.1.0`
  3. Push the tag: `git push origin v3.1.0`
  4. Create the release with the binary attached: `gh release create v3.1.0 dist/hextessellator.exe --title "HEX Grid Tessellator v3.1.0" --notes "Release notes here"`
  5. Update `README.md` download link to point to the GitHub Releases page instead of `dist/`
  6. Add `dist/` to `.gitignore` and remove it from version control


