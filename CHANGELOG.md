# Changelog

All notable changes to the HEX Grid Tessellator v3 are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `README.md` for GitHub with mathematical foundations writeup covering hexagon geometry, axial coordinates, ring traversal, two-pass rendering, viewport culling, and supersampled anti-aliasing
- Semantic Versioning section in `README.md` with reference to [semver.org](https://semver.org/)
- `images/` directory with 4 example output PNGs showcased in README (default, dense grid, viewport culling, high contrast)
- Examples section in `README.md` with rendered previews and the CLI commands that produced them
- TODO section in `CLAUDE.md` with checklist for GitHub repo setup and GitHub Releases publishing

### Changed
- Restructured `README.md` to lead with `main.exe` usage for end users; moved Python/venv setup into a dedicated Development section
- Examples section in `README.md` switched from vertical stack to 2x2 table layout with images in table cells to reduce scrolling

## [3.1.0] - 2026-02-08

### Added
- Dynamic version sourcing: banner `VERSION` is now read from the highest versioned heading in `CHANGELOG.md` at runtime, with a hardcoded fallback for frozen `.exe` builds
- `_changelog_version()` helper function in `main.py` that parses `CHANGELOG.md` for the latest `## [X.Y.Z]` heading
- `step_stamp_version()` in `build.py` that stamps the changelog version into the `main.py` fallback before each build
- Version and build-date stamping steps in `housekeeping.py` (now 8 steps, up from 5)
- `changelog_table.py` script that parses `CHANGELOG.md` entries and generates/updates a summary table in markdown format; preserves manual Name/Size edits across regenerations
- Change Log summary table appended to `CHANGELOG.md` with Date, Operation, Size, Name, and Description columns
- `scripts/` directory for tooling scripts (`build.py`, `housekeeping.py`, `changelog_table.py`), separating automation from application source

### Changed
- `Application.VERSION` class attribute now calls `_changelog_version()` instead of being a static string
- `build.py` expanded from 3 steps to 4 (added version stamping from changelog)
- `housekeeping.py` expanded from 5 steps to 8 (added version stamp, build-date stamp, changelog table generation)
- `test_single_file` exclusion list simplified to just `test_main.py` — tooling scripts no longer in project root
- Moved `build.py`, `housekeeping.py`, `changelog_table.py` from project root into `scripts/` directory
- Updated all path references in CLAUDE.md, SKILL.md files, and script internals (`SCRIPT_DIR` → `PROJECT_DIR`)
- Change Log table switched from ASCII box-drawing characters to standard markdown table syntax for native rendering

- `housekeeping.py` script that automates mechanical Definition-of-Done checks: builds `.exe`, smoke-tests `.exe`, runs pytest, updates CLAUDE.md test count, validates `run.bat`
- `build.py` script for standalone exe builds (compile + smoke-test)
- `/build` skill to invoke `build.py` for manual code changes
- `.markdownlint.json` config disabling MD032, MD013, MD025, MD041
- `BUILD_DATE` class attribute on `Application`, displayed in the banner
- Automatic build-date stamping in `build.py` — writes today's date into `main.py`'s `BUILD_DATE` before each build
- `BANNER_WIDTH` class attribute (default 60) controlling the banner box width
- Banner displayed in `--help` output above the usage line, via custom `ArgumentParser` subclass
- `prompts/` directory for scratch markdown prompt files, with `.gitkeep`
- Prompts Directory section in `CLAUDE.md` documenting the `prompts/` directory

### Changed
- Banner and save confirmation are now always displayed, not just in `--debug` mode
- Detailed parameters and statistics remain `--debug`-only
- Extracted `_print_banner()` and `_banner_text()` methods from `_print_debug()` for reuse
- `--export_settings` now prints a save confirmation with file path and size
- Save confirmations now appear right after the banner (always visible) and repeated at the end of debug output
- `_print_debug()` now includes "Saved:" lines for the PNG and optional JSON export
- Banner uses full ASCII box-drawing characters (`┌─┐│└─┘`) instead of horizontal rules
- `--import_settings` now auto-appends `.json` extension when omitted, matching `--export_settings` behaviour
- Moved `prompt-requirements-hex-grid-tessellator.md` from project root into `prompts/`
- Updated CLAUDE.md requirements file path reference to `prompts/`

### Fixed
- `test_single_file` now excludes `housekeeping.py` and `build.py` from the single-source-file assertion
- Fixed `UnicodeEncodeError` on cp1252 consoles and in frozen `.exe` by reconfiguring stdout to UTF-8 at startup (preserves Unicode box-drawing characters)
- `housekeeping.py` builds `.exe` before running tests so exe smoke tests run against the fresh build
- Added `encoding="utf-8"` to all `subprocess.run` calls in `test_main.py`, `build.py`, and `housekeeping.py` to handle box-drawing characters on Windows cp1252 consoles

### Changed
- Migrated `/update-docs` custom slash command from `.claude/commands/update-docs.md` to `.claude/skills/update-docs/SKILL.md` (modern recommended format per Anthropic)
- Simplified CLAUDE.md Definition of Done from 8 manual steps to 4 (`housekeeping.py` handles the mechanical steps)
- Updated `/update-docs` skill to invoke `housekeeping.py` instead of manual pytest/CLAUDE.md update steps
- `housekeeping.py` imports build/smoke-test logic from `build.py` (no duplication)

## [3.0.1] - 2026-02-08

### Added
- Auto-append `.json` extension when `--export_settings` filename lacks it
- Test `test_export_auto_appends_json_extension` validating the `.json` auto-append logic against `main.py`
- `TestExecutable` test class with 4 smoke tests that run directly against `dist/main.exe`:
  - `test_exe_produces_png` — verifies exe generates a valid PNG
  - `test_exe_export_auto_appends_json_extension` — verifies `.json` extension auto-append in exe
  - `test_exe_export_preserves_json_extension` — verifies `.json` is not doubled
  - `test_exe_debug_flag` — verifies `--debug` produces output
- Rules section (Always/Never) in `CLAUDE.md`
- This `CHANGELOG.md` file

### Fixed
- Rebuilt `.exe` which was compiled from older code and did not include the `.json` auto-append logic

## [3.0.0] - Initial release

### Added
- Single-file CLI tool (`main.py`) generating hexagonal grid tessellation PNGs
- Six-class OOP architecture: HexagonGeometry, AxialGrid, ColorParser, TessellationRenderer, SettingsManager, Application
- Flat-top hexagons on axial coordinate system
- Supersampled anti-aliasing (off/low/medium/high) via Pillow with Lanczos downsampling
- Two-pass concentric stroke rendering to avoid miter-joint artifacts
- Viewport culling for performance
- JSON settings import/export with CLI-precedence merging
- Auto-fill layer computation when `--layers 0`
- CSS named colors, hex codes, and RGB comma-tuple color parsing
- Standalone `.exe` build via PyInstaller
- 66 automated tests covering geometry, grid, color, settings, CLI, image output, culling, and rendering
- Full requirements specification in `prompt-requirements-hex-grid-tessellator.md`

## Change Log

<!-- changelog-table-start -->
| Date | Operation | Size | Name | Description |
|------|-----------|------|------|-------------|
| Unreleased | Added | L | README.md for GitHub with… | README.md for GitHub with mathematical foundations writeup covering hexagon geo… |
| Unreleased | Added | S | Semantic Versioning section… | Semantic Versioning section in README.md with reference to [semver.org](https:/… |
| Unreleased | Added | M | images/ directory with 4… | images/ directory with 4 example output PNGs showcased in README (default, dens… |
| Unreleased | Added | S | Examples section in… | Examples section in README.md with rendered previews and the CLI commands that … |
| Unreleased | Added | S | TODO section in CLAUDE.md… | TODO section in CLAUDE.md with checklist for GitHub repo setup and GitHub Relea… |
| Unreleased | Changed | M | Restructured README.md to… | Restructured README.md to lead with main.exe usage for end users; moved Python/… |
| Unreleased | Changed | M | Examples section in… | Examples section in README.md switched from vertical stack to 2x2 table layout … |
| 2026-02-08 | Added | L | Dynamic version sourcing | Dynamic version sourcing: banner VERSION is now read from the highest versioned… |
| 2026-02-08 | Added | M | _changelog_version | _changelog_version() helper function in main.py that parses CHANGELOG.md for th… |
| 2026-02-08 | Added | M | step_stamp_version | step_stamp_version() in build.py that stamps the changelog version into the mai… |
| 2026-02-08 | Added | S | Version and build-date… | Version and build-date stamping steps in housekeeping.py (now 8 steps, up from … |
| 2026-02-08 | Added | L | changelog_table.py script… | changelog_table.py script that parses CHANGELOG.md entries and generates/update… |
| 2026-02-08 | Added | M | Change Log summary table… | Change Log summary table appended to CHANGELOG.md with Date, Operation, Size, N… |
| 2026-02-08 | Added | M | scripts/ directory for… | scripts/ directory for tooling scripts (build.py, housekeeping.py, changelog_ta… |
| 2026-02-08 | Changed | M | Application.VERSION class… | Application.VERSION class attribute now calls _changelog_version() instead of b… |
| 2026-02-08 | Changed | S | build.py expanded from 3… | build.py expanded from 3 steps to 4 (added version stamping from changelog) |
| 2026-02-08 | Changed | M | housekeeping.py expanded… | housekeeping.py expanded from 5 steps to 8 (added version stamp, build-date sta… |
| 2026-02-08 | Changed | M | test_single_file exclusion… | test_single_file exclusion list simplified to just test_main.py — tooling scrip… |
| 2026-02-08 | Changed | M | build.py, housekeeping.py,… | Moved build.py, housekeeping.py, changelog_table.py from project root into scri… |
| 2026-02-08 | Changed | M | all path references in… | Updated all path references in CLAUDE.md, SKILL.md files, and script internals … |
| 2026-02-08 | Changed | M | Change Log table switched… | Change Log table switched from ASCII box-drawing characters to standard markdow… |
| 2026-02-08 | Changed | L | housekeeping.py script that… | housekeeping.py script that automates mechanical Definition-of-Done checks: bui… |
| 2026-02-08 | Changed | S | build.py script for… | build.py script for standalone exe builds (compile + smoke-test) |
| 2026-02-08 | Changed | XS | /build skill to invoke… | /build skill to invoke build.py for manual code changes |
| 2026-02-08 | Changed | S | .markdownlint.json config… | .markdownlint.json config disabling MD032, MD013, MD025, MD041 |
| 2026-02-08 | Changed | S | BUILD_DATE class attribute… | BUILD_DATE class attribute on Application, displayed in the banner |
| 2026-02-08 | Changed | M | Automatic build-date… | Automatic build-date stamping in build.py — writes today's date into main.py's … |
| 2026-02-08 | Changed | S | BANNER_WIDTH class attribute | BANNER_WIDTH class attribute (default 60) controlling the banner box width |
| 2026-02-08 | Changed | S | Banner displayed in --help… | Banner displayed in --help output above the usage line, via custom ArgumentPars… |
| 2026-02-08 | Changed | S | prompts/ directory for… | prompts/ directory for scratch markdown prompt files, with .gitkeep |
| 2026-02-08 | Changed | S | Prompts Directory section in… | Prompts Directory section in CLAUDE.md documenting the prompts/ directory |
| 2026-02-08 | Changed | S | Banner and save confirmation… | Banner and save confirmation are now always displayed, not just in --debug mode |
| 2026-02-08 | Changed | XS | Detailed parameters and… | Detailed parameters and statistics remain --debug-only |
| 2026-02-08 | Changed | S | _print_banner | Extracted _print_banner() and _banner_text() methods from _print_debug() for re… |
| 2026-02-08 | Changed | S | --export_settings now prints… | --export_settings now prints a save confirmation with file path and size |
| 2026-02-08 | Changed | M | Save confirmations now… | Save confirmations now appear right after the banner (always visible) and repea… |
| 2026-02-08 | Changed | S | _print_debug | _print_debug() now includes "Saved:" lines for the PNG and optional JSON export |
| 2026-02-08 | Changed | S | Banner uses full ASCII… | Banner uses full ASCII box-drawing characters (┌─┐│└─┘) instead of horizontal r… |
| 2026-02-08 | Changed | M | --import_settings now… | --import_settings now auto-appends .json extension when omitted, matching --exp… |
| 2026-02-08 | Changed | S | prompt-requirements-hex-grid-… | Moved prompt-requirements-hex-grid-tessellator.md from project root into prompt… |
| 2026-02-08 | Changed | S | CLAUDE.md requirements file… | Updated CLAUDE.md requirements file path reference to prompts/ |
| 2026-02-08 | Fixed | M | test_single_file now… | test_single_file now excludes housekeeping.py and build.py from the single-sour… |
| 2026-02-08 | Fixed | M | UnicodeEncodeError on cp1252… | Fixed UnicodeEncodeError on cp1252 consoles and in frozen .exe by reconfiguring… |
| 2026-02-08 | Fixed | S | housekeeping.py builds .exe… | housekeeping.py builds .exe before running tests so exe smoke tests run against… |
| 2026-02-08 | Fixed | L | encoding="utf-8" to all… | Added encoding="utf-8" to all subprocess.run calls in test_main.py, build.py, a… |
| 2026-02-08 | Changed | L | /update-docs custom slash… | Migrated /update-docs custom slash command from .claude/commands/update-docs.md… |
| 2026-02-08 | Changed | M | CLAUDE.md Definition of Done… | Simplified CLAUDE.md Definition of Done from 8 manual steps to 4 (housekeeping.… |
| 2026-02-08 | Changed | M | /update-docs skill to invoke… | Updated /update-docs skill to invoke housekeeping.py instead of manual pytest/C… |
| 2026-02-08 | Changed | S | housekeeping.py imports… | housekeeping.py imports build/smoke-test logic from build.py (no duplication) |
| 2026-02-08 | Added | S | Auto-append .json extension… | Auto-append .json extension when --export_settings filename lacks it |
| 2026-02-08 | Added | M | test_export_auto_appends_json… | Test test_export_auto_appends_json_extension validating the .json auto-append l… |
| 2026-02-08 | Added | S | TestExecutable test class… | TestExecutable test class with 4 smoke tests that run directly against dist/mai… |
| 2026-02-08 | Added | XS | Rules section | Rules section (Always/Never) in CLAUDE.md |
| 2026-02-08 | Added | XS | CHANGELOG.md file | This CHANGELOG.md file |
| 2026-02-08 | Fixed | S | .exe which was compiled from… | Rebuilt .exe which was compiled from older code and did not include the .json a… |
| Initial r… | Added | S | Single-file CLI tool | Single-file CLI tool (main.py) generating hexagonal grid tessellation PNGs |
| Initial r… | Added | M | Six-class OOP architecture | Six-class OOP architecture: HexagonGeometry, AxialGrid, ColorParser, Tessellati… |
| Initial r… | Added | XS | Flat-top hexagons on axial… | Flat-top hexagons on axial coordinate system |
| Initial r… | Added | S | Supersampled anti-aliasing | Supersampled anti-aliasing (off/low/medium/high) via Pillow with Lanczos downsa… |
| Initial r… | Added | S | Two-pass concentric stroke… | Two-pass concentric stroke rendering to avoid miter-joint artifacts |
| Initial r… | Added | XS | Viewport culling for… | Viewport culling for performance |
| Initial r… | Added | XS | JSON settings import/export… | JSON settings import/export with CLI-precedence merging |
| Initial r… | Added | XS | Auto-fill layer computation… | Auto-fill layer computation when --layers 0 |
| Initial r… | Added | S | CSS named colors, hex codes,… | CSS named colors, hex codes, and RGB comma-tuple color parsing |
| Initial r… | Added | XS | Standalone .exe build via… | Standalone .exe build via PyInstaller |
| Initial r… | Added | M | 66 automated tests covering… | 66 automated tests covering geometry, grid, color, settings, CLI, image output,… |
| Initial r… | Added | S | Full requirements… | Full requirements specification in prompt-requirements-hex-grid-tessellator.md |
<!-- changelog-table-end -->
