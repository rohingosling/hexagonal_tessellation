# Prompt — HEX Grid Tessellator

## Role

You are an expert Python software engineer. Write a single-file Python CLI program that generates publication-quality hexagonal grid tessellation images. The program must be implemented using **well-structured object-oriented architecture** and **formal software engineering principles** (encapsulation, separation of concerns, single responsibility, clear interfaces, comprehensive docstrings, and type annotations throughout).

---

## Program Overview

Build a command-line tool called **HEX Grid Tessellator** that:

1. Constructs concentric-layer hexagonal grids using the **axial coordinate system** (derived from cube coordinates).
2. Renders the grid into a PNG image using the **Pillow** library.
3. Supports **supersampled anti-aliasing** via oversampling and Lanczos downsampling.
4. Provides a full CLI parameter interface with **JSON-based settings import/export**.

The sole external dependency is **Pillow** (`Image`, `ImageColor`, `ImageDraw`). The standard library modules `argparse`, `json`, `math`, `os`, `re`, `sys`, and `typing` (`Dict`, `List`, `Optional`, `Tuple`) may also be used.

---

## Architectural Requirements

The program must use an **object-oriented design**. At minimum, define the following classes and helper function (or a comparable decomposition that achieves equivalent separation of concerns):

| Component | Responsibility |
|---|---|
| `HexagonGeometry` | Vertex computation for flat-top regular hexagons. Encapsulates circumradius and vertex generation. |
| `AxialGrid` | Axial coordinate system operations: coordinate-to-pixel conversion, ring generation, concentric grid generation, and auto-fill layer computation. |
| `ColorParser` | Parsing of color specifications from multiple string formats into RGB tuples. |
| `TessellationRenderer` | Orchestrates the rendering pipeline: canvas creation, two-pass concentric stroke drawing, viewport culling, and anti-alias downsampling. |
| `SettingsManager` | JSON import/export of parameter sets, with CLI-precedence logic. |
| `_changelog_version()` | Module-level helper that reads the highest `## [X.Y.Z]` heading from `CHANGELOG.md` (next to the script) and returns the version string. Falls back to a hardcoded default when the file is missing or contains no versioned headings (e.g., in a frozen `.exe`). |
| `Application` | Top-level entry point: CLI argument parsing, orchestration of settings loading, rendering, file output, banner display, and debug reporting. |

Each class must have clear **public interfaces**, **private implementation details**, and **comprehensive docstrings** with parameter/return documentation.

---

## Functional Requirements

### FR-1: Hexagon Geometry — Flat-Top Orientation

Compute the six vertices of a **flat-top** regular hexagon centred at $(c_x, c_y)$ with circumradius $R$:

$$v_k = \left( c_x + R \cos\!\left(\frac{\pi k}{3}\right),\; c_y + R \sin\!\left(\frac{\pi k}{3}\right) \right), \quad k \in \{0, 1, 2, 3, 4, 5\}$$

- Vertex $v_0$ is at the rightmost point $(c_x + R, \, c_y)$.
- Vertices proceed **counter-clockwise** at $60°$ intervals.
- The hexagon **width** (vertex-to-vertex) is $W = 2R$.
- The hexagon **height** (edge-to-edge) is $H = R\sqrt{3}$.
- The **inradius** (apothem) is $r = R \cdot \frac{\sqrt{3}}{2}$.

### FR-2: Axial Coordinate System

#### FR-2.1: Cube Coordinates

Address each hexagonal cell by a triple $(q, r, s) \in \mathbb{Z}^3$ constrained by $q + r + s = 0$. The **hex distance** from the origin is:

$$d = \max(|q|, |r|, |s|)$$

#### FR-2.2: Axial Projection

Since $s = -q - r$, retain only $(q, r)$. The centre cell is the origin $(0, 0)$.

#### FR-2.3: Axial-to-Pixel Conversion (Flat-Top)

Convert axial coordinates $(q, r)$ to pixel offsets $(p_x, p_y)$ from the grid origin:

$$p_x = R_s \cdot \frac{3}{2} \, q$$

$$p_y = R_s \cdot \sqrt{3} \left( r + \frac{q}{2} \right)$$

where $R_s$ is the **effective spacing radius** (see FR-3). Final image-space coordinates are:

$$x = \frac{w}{2} + p_x, \qquad y = \frac{h}{2} + p_y$$

### FR-3: Effective Spacing Radius and Margin

To introduce a uniform visual gap of $m$ pixels between adjacent hexagon edges, define:

$$R_s = R + \frac{m}{2}$$

- **Grid layout** uses $R_s$ for centre-to-centre spacing.
- **Drawing** uses the true circumradius $R$ for vertex positions.
- The visible edge-to-edge gap between drawn hexagons is thus $m$ pixels (along the perpendicular axis).

### FR-4: Concentric Ring Generation

#### FR-4.1: Layer Structure

- **Layer 1**: The origin cell $(0, 0)$ — 1 cell.
- **Layer $\ell \geq 2$**: A ring at hex distance $d = \ell - 1$ — $6d$ cells.
- **Total cells** for $L$ layers:

$$N(L) = 1 + 3L(L - 1)$$

#### FR-4.2: Ring Traversal Algorithm

To enumerate all cells on ring $d$:

1. Start at axial coordinate $(-d, \, 0)$.
2. Walk $d$ steps along each of the 6 canonical axial directions in sequence:

$$(\Delta q, \Delta r) \in \{ (+1, -1),\; (+1, 0),\; (0, +1),\; (-1, +1),\; (-1, 0),\; (0, -1) \}$$

3. This visits exactly $6d$ cells per ring. For $d = 0$, return only $(0, 0)$.

### FR-5: Auto-Fill Layer Computation

When the layer count is set to `0`, automatically compute the minimum number of layers $L$ to fully cover a canvas of dimensions $w \times h$:

$$L_h = \left\lceil \frac{w/2}{(3/2) \cdot R_s} \right\rceil, \qquad L_v = \left\lceil \frac{h/2}{\sqrt{3} \cdot R_s} \right\rceil$$

$$L = \max(L_h, \, L_v) + 1$$

The $+1$ buffer ensures edge hexagons are not clipped at the canvas boundary. Return $\max(L, 1)$.

### FR-6: Viewport Culling

When culling is enabled, discard any hexagon whose **outer extent** (including the stroke) overflows the image bounds. For each hexagon centre $(c_x, c_y)$:

1. Compute all 6 vertices at the **cull radius** $R_{\text{cull}} = R + \frac{t}{2}$, where $t$ is the line width.
2. If **any** vertex $(v_x, v_y)$ falls outside $[0, w] \times [0, h]$, discard the hexagon.

### FR-7: Two-Pass Concentric Stroke Rendering

Do **not** use Pillow's `polygon(outline=)` for strokes. Instead, simulate uniform outlines using two concentric filled hexagons:

**Pass 1 — Outer fill (stroke colour):** Draw a filled polygon at radius:

$$R_{\text{outer}} = R + \frac{t}{2}$$

**Pass 2 — Inner fill (fill colour):** Draw a filled polygon at radius:

$$R_{\text{inner}} = \max\!\left(R - \frac{t}{2},\; 0\right)$$

The visible stroke width is $R_{\text{outer}} - R_{\text{inner}} = t$.

**Rendering order:**

1. Draw **all** outer hexagons (Pass 1) across the entire grid.
2. Draw **all** inner hexagons (Pass 2) across the entire grid.

This eliminates miter-joint artefacts and straddle-overlap errors. When $t = 0$, skip Pass 1 and draw a single filled hexagon at $R$.

### FR-8: Supersampled Anti-Aliasing

Achieve anti-aliasing via oversampling:

1. Render at $k \times$ the target resolution.
2. Scale **all** pixel-space quantities (canvas dimensions, circumradius, spacing radius, line width) by $k$.
3. Downsample to target resolution using **Lanczos resampling** (`Image.LANCZOS`).

| Level | Key | Scale $k$ | Pixel Count |
|---|---|---|---|
| Off | `off` | 1 | $1\times$ |
| Low | `low` | 2 | $4\times$ |
| Medium | `medium` | 4 | $16\times$ |
| High | `high` | 8 | $64\times$ |

### FR-9: Color Parsing

Accept three color specification formats:

1. **CSS named colours** — e.g., `"red"`, `"cornflowerblue"`. Parsed via Pillow's `ImageColor.getrgb()`.
2. **Hex codes** — e.g., `"#FF0000"`, `"#abc"`. Also parsed via `ImageColor.getrgb()`.
3. **RGB comma-tuples** — e.g., `"255,128,0"`. Three comma-separated integers in $[0, 255]$. Parsed manually.

Return an `(R, G, B)` tuple of integers. Raise `ValueError` on invalid input with a descriptive message.

### FR-10: Settings Import/Export (JSON)

#### FR-10.1: Persisted Keys

The following parameter keys are persisted:

`width`, `height`, `circumradius`, `margin`, `line_width`, `layers`, `color_fill`, `color_line`, `color_background`, `antialias`, `file`, `cull`, `debug`

#### FR-10.2: Export

Serialize current parameters to a JSON file. Boolean flags (`cull`, `debug`) are stored as JSON booleans; all others in their natural CLI representation.

If the user-specified export filename lacks a `.json` extension, append one automatically.

#### FR-10.3: Import

Load a JSON file and apply its values as a **base layer**:

- JSON values **override** argparse defaults.
- CLI parameters **explicitly provided** by the user take **precedence** over JSON values.
- Missing keys in the JSON retain their default values.

If the user-specified import filename lacks a `.json` extension, append one automatically.

To detect which CLI parameters were explicitly provided, parse arguments twice: once normally, once with all defaults set to `argparse.SUPPRESS`. The second parse yields only explicitly-provided keys.

### FR-11: File Output

- Output format: **PNG**.
- If the user-specified filename lacks a `.png` extension, append one automatically.
- After saving, read back the file size from disk for reporting.

### FR-12: Banner Display

The program must **always** display an application banner on stdout, regardless of debug mode. The banner is a box-drawing character frame containing:

- **Program**: The application title (`HEX Grid Tessellator`).
- **Version**: Read dynamically from `CHANGELOG.md` via `_changelog_version()`, with a hardcoded fallback.
- **Build Date**: A stamped date string (updated at build time).
- **Author**: The author name.

The banner box uses Unicode box-drawing characters (`┌`, `─`, `┐`, `│`, `└`, `┘`) and has a configurable width controlled by a `BANNER_WIDTH` class attribute (default: `60`).

Immediately after the banner, always print a save confirmation line showing the output filename and human-readable file size (e.g., `Saved: tessellation.png (45.67 KB)`). If `--export_settings` was used, also print a save confirmation for the JSON file.

The banner must also be displayed above the usage text when `--help` is invoked. Implement this via a custom `ArgumentParser` subclass that overrides `print_help()` to prepend the banner, and overrides `error()` to print a blank line, then usage, then the error message.

### FR-13: Debug Output

When debug mode is enabled (`--debug`), print additional detail to stdout after the banner and save confirmation:

- A listing of all resolved parameters (image size, circumradius, margin, line width, layers, antialias level, cull flag).
- When layers were auto-computed, show the resolved count with a note like `(auto-computed from requested 0)`.
- Color values shown as both the original string and the resolved $(R, G, B)$ tuple (fill, line, background).
- Centre pixel coordinates.
- Polygon count drawn.
- Repeated save confirmation lines for the PNG and optional JSON export.

File sizes are formatted as human-readable strings: bytes (`B`), kilobytes (`KB` with 2 decimal places), or megabytes (`MB` with 2 decimal places).

### FR-14: Antialias Level Validation

Before rendering, validate that the `--antialias` value is one of the accepted levels (`off`, `low`, `medium`, `high`). If invalid, print a descriptive error message listing the valid options to `stderr` and exit with a non-zero code.

---

## CLI Interface

Define the following command-line arguments via `argparse`:

| Argument | Type | Default | Description |
|---|---|---|---|
| `--width` | `int` | `1024` | Image width in pixels. |
| `--height` | `int` | `768` | Image height in pixels. |
| `--circumradius` | `float` | `64` | Hexagon circumradius $R$ in pixels. |
| `--margin` | `float` | `16` | Gap between hexagon edges in pixels. |
| `--line_width` | `int` | `8` | Stroke width in pixels. `0` = no outline. |
| `--layers` | `int` | `0` | Concentric layers. `0` = auto-fill. |
| `--color_fill` | `str` | `grey` | Hexagon fill colour. |
| `--color_line` | `str` | `black` | Hexagon outline colour. |
| `--color_background` | `str` | `darkgrey` | Background colour. |
| `--antialias` | `str` | `high` | Anti-alias level: `off`, `low`, `medium`, `high`. |
| `--file` | `str` | `tessellation.png` | Output PNG filename. |
| `--cull` | flag | `false` | Enable viewport culling. |
| `--debug` | flag | `false` | Enable debug output. |
| `--export_settings` | `str` | `None` | Export parameters to a JSON file before rendering. |
| `--import_settings` | `str` | `None` | Import parameters from a JSON file. |

### Boolean Flag Parsing

The `--cull` and `--debug` flags use `nargs="?"` with `const=True` so they can be used in three ways:

1. **Bare flag**: `--cull` → `True`
2. **With explicit value**: `--cull true`, `--cull false`
3. **Omitted**: defaults to `False`

The accepted truthy values are `true`, `1`, `yes` (case-insensitive). The accepted falsy values are `false`, `0`, `no` (case-insensitive). Any other value raises an `ArgumentTypeError`.

---

## Non-Functional Requirements

- **Single-file**: The entire program resides in one Python file (`main.py`).
- **Type annotations**: All function signatures and class methods must include type hints, using `typing` imports (`Dict`, `List`, `Optional`, `Tuple`).
- **Docstrings**: All classes and public methods must include docstrings with parameter and return documentation.
- **Error handling**: Graceful handling of invalid colour strings, invalid antialias levels, missing/malformed JSON files, and filesystem errors. Print descriptive error messages to `stderr` and exit with a non-zero code.
- **No unused dependencies**: Only Pillow and the Python standard library.
- **UTF-8 stdout**: The `main()` entry point must reconfigure `sys.stdout` to UTF-8 encoding (with `errors="replace"`) before running the application, to ensure Unicode box-drawing characters render correctly on Windows consoles that default to cp1252.
- **Virtual environment**: The project must use a Python virtual environment for dependency isolation. Provide standardized batch scripts (`venv_create.bat`, `venv_activate.bat`, `venv_deactivate.bat`, `venv_delete.bat`, `venv_install_requirements.bat`, `venv_save_requirements.bat`) and a `venv_requirements.txt` listing all dependencies (Pillow, PyInstaller).
- **Executable build**: The program must be compiled to a standalone `.exe` using **PyInstaller** (`pyinstaller --onefile main.py`). The resulting executable (`dist/hextessellator.exe`) must run without requiring a Python installation on the target machine.
- **Validation**: The implementation must pass all 71 automated tests in `test_main.py` (including 4 executable smoke tests). Run `python -m pytest test_main.py -v` to validate. The test suite covers: architecture (required classes, docstrings, type annotations, single-file assertion), hexagon geometry (vertex count, positions, distances, angles, width, height), axial grid and ring generation (origin mapping, ring traversal, cell counts, hex distances, auto-fill), color parsing (CSS names, hex codes, RGB tuples, error cases, return types), settings import/export (JSON validity, required keys, boolean serialisation, `.json` auto-append, import/override, missing file handling), CLI defaults and flags (output filename, `.png` auto-append, debug flag, invalid antialias), image output (PNG validity, dimensions, background colour, fill colour, anti-alias levels, file size), viewport culling, effective spacing radius, two-pass stroke rendering (outline visibility, no-outline when `line_width=0`), error handling (invalid colour, malformed JSON, stderr output), settings round-trip, and standalone executable smoke tests (PNG output, `.json` auto-append, debug flag).

---

## Execution Pipeline

The `main()` function must reconfigure stdout to UTF-8, then instantiate `Application` and call `run()`. The `Application.run()` method executes the following steps in order:

1. Parse CLI arguments and detect explicitly-provided keys.
2. If `--import_settings` is specified, auto-append `.json` if missing, load JSON, and apply as the base layer (CLI-explicit values take precedence). Exit with non-zero code on `FileNotFoundError` or `JSONDecodeError`.
3. If `--export_settings` is specified, auto-append `.json` if missing, and write current parameters to JSON. Exit with non-zero code on `IOError`.
4. Parse all colour strings into RGB tuples. Exit with non-zero code on `ValueError`.
5. Auto-compute layers if `layers == 0`.
6. Validate the antialias level. Exit with non-zero code if invalid.
7. Render the tessellation (steps 7a–7f are internal to `TessellationRenderer.render()`):
   - 7a. Scale all geometry by the anti-alias multiplier $k$.
   - 7b. Compute $R_s$ and auto-fill layers if needed.
   - 7c. Generate all axial cell coordinates and convert to pixel centres.
   - 7d. Apply viewport culling (if enabled).
   - 7e. Create the oversampled canvas, filled with the background colour.
   - 7f. Execute the two-pass concentric stroke rendering.
   - 7g. Downsample to target resolution via Lanczos (if $k > 1$).
8. Ensure `.png` extension on the output filename, then save the image.
9. **Always** print the banner (program title, version, build date, author in a box-drawing frame).
10. **Always** print save confirmation(s) (output PNG, and JSON export if applicable).
11. If debug mode is enabled, print the detailed parameter summary and statistics.
12. Print a trailing blank line.
