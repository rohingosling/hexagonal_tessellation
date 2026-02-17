"""
HEX Grid Tessellator v3

A single-file Python CLI tool that generates publication-quality hexagonal grid
tessellation PNG images. Uses flat-top hexagons on an axial coordinate system
with supersampled anti-aliasing via Pillow.

Usage:
    python main.py --debug
    python main.py --width 1920 --height 1080 --circumradius 48 --antialias high --debug
    python main.py --import_settings settings.json
    python main.py --export_settings settings.json
"""

import argparse
import json
import math
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageColor, ImageDraw


# ---------------------------------------------------------------------------
# HexagonGeometry
# ---------------------------------------------------------------------------
class HexagonGeometry:
    """Vertex computation for flat-top regular hexagons.

    Encapsulates circumradius and provides vertex generation for hexagons
    centred at arbitrary pixel coordinates using the flat-top orientation.

    Attributes:
        circumradius: The circumradius (centre-to-vertex distance) in pixels.
    """

    def __init__(self, circumradius: float) -> None:
        """Initialise hexagon geometry with a given circumradius.

        Args:
            circumradius: The circumradius R of the hexagon in pixels.
        """
        self._circumradius: float = circumradius

    @property
    def circumradius(self) -> float:
        """Return the circumradius R."""
        return self._circumradius

    @property
    def inradius(self) -> float:
        """Return the inradius (apothem) r = R * sqrt(3)/2."""
        return self._circumradius * math.sqrt(3) / 2.0

    def vertices(self, cx: float, cy: float) -> List[Tuple[float, float]]:
        """Compute the 6 vertices of a flat-top hexagon centred at (cx, cy).

        Vertices start at the rightmost point (cx + R, cy) and proceed
        counter-clockwise at 60-degree intervals.

        Args:
            cx: X coordinate of the hexagon centre.
            cy: Y coordinate of the hexagon centre.

        Returns:
            A list of 6 (x, y) tuples representing the vertex positions.
        """
        R = self._circumradius
        return [
            (cx + R * math.cos(math.pi * k / 3.0),
             cy + R * math.sin(math.pi * k / 3.0))
            for k in range(6)
        ]


# ---------------------------------------------------------------------------
# AxialGrid
# ---------------------------------------------------------------------------
class AxialGrid:
    """Axial coordinate system for hexagonal grids.

    Provides coordinate-to-pixel conversion, ring traversal, concentric grid
    generation, and auto-fill layer computation for flat-top hexagonal grids.

    Attributes:
        spacing_radius: The effective spacing radius R_s used for layout.
    """

    # Canonical ring-traversal directions (axial deltas).
    _DIRECTIONS: List[Tuple[int, int]] = [
        (+1, -1), (+1, 0), (0, +1),
        (-1, +1), (-1, 0), (0, -1),
    ]

    def __init__(self, spacing_radius: float = 1.0) -> None:
        """Initialise the axial grid with a spacing radius.

        Args:
            spacing_radius: Effective spacing radius R_s = R + margin/2.
        """
        self._spacing_radius: float = spacing_radius

    def axial_to_pixel(self, q: int, r: int, w: int, h: int) -> Tuple[float, float]:
        """Convert axial coordinates (q, r) to pixel coordinates on canvas.

        Args:
            q: Axial q coordinate.
            r: Axial r coordinate.
            w: Canvas width in pixels.
            h: Canvas height in pixels.

        Returns:
            A (px, py) tuple of pixel coordinates.
        """
        R_s = self._spacing_radius
        px = R_s * 1.5 * q
        py = R_s * math.sqrt(3) * (r + q / 2.0)
        return (w / 2.0 + px, h / 2.0 + py)

    def ring(self, d: int) -> List[Tuple[int, int]]:
        """Generate all axial coordinates on ring at hex distance d.

        For d=0 returns only the origin (0, 0). For d>=1 returns 6d cells
        starting at (-d, 0) and walking along the 6 canonical directions.

        Args:
            d: The hex distance (ring number). Must be >= 0.

        Returns:
            A list of (q, r) tuples for all cells on this ring.
        """
        if d == 0:
            return [(0, 0)]
        cells: List[Tuple[int, int]] = []
        q, r = -d, 0
        for dq, dr in self._DIRECTIONS:
            for _ in range(d):
                cells.append((q, r))
                q += dq
                r += dr
        return cells

    def generate(self, layers: int) -> List[Tuple[int, int]]:
        """Generate all axial coordinates for a concentric grid of L layers.

        Layer 1 is the origin cell. Layer l >= 2 is ring at distance l-1.
        Total cells: 1 + 3*L*(L-1).

        Args:
            layers: Number of concentric layers (>= 1).

        Returns:
            A list of (q, r) tuples for all cells in the grid.
        """
        cells: List[Tuple[int, int]] = []
        for d in range(layers):
            cells.extend(self.ring(d))
        return cells

    def auto_fill_layers(self, w: int, h: int, spacing_radius: float) -> int:
        """Compute the minimum layers needed to cover a canvas of size w x h.

        Args:
            w: Canvas width in pixels.
            h: Canvas height in pixels.
            spacing_radius: The effective spacing radius R_s.

        Returns:
            The minimum number of layers (always >= 1).
        """
        R_s = spacing_radius
        L_h = math.ceil((w / 2.0) / (1.5 * R_s))
        L_v = math.ceil((h / 2.0) / (math.sqrt(3) * R_s))
        L = max(L_h, L_v) + 1
        return max(L, 1)


# ---------------------------------------------------------------------------
# ColorParser
# ---------------------------------------------------------------------------
class ColorParser:
    """Parses color specifications from multiple string formats into RGB tuples.

    Supports CSS named colours, hex codes (#RGB, #RRGGBB), and RGB
    comma-separated tuples (e.g. '255,128,0').
    """

    def parse(self, color_str: str) -> Tuple[int, int, int]:
        """Parse a color string into an (R, G, B) tuple.

        Accepts CSS named colours, hex codes, and comma-separated RGB values.

        Args:
            color_str: The color specification string.

        Returns:
            An (R, G, B) tuple of integers in [0, 255].

        Raises:
            ValueError: If the color string cannot be parsed.
        """
        s = color_str.strip()

        # Try comma-separated RGB tuple first
        if "," in s:
            return self._parse_rgb_tuple(s)

        # Use Pillow's ImageColor for CSS names and hex codes
        try:
            rgb = ImageColor.getrgb(s)
            return (rgb[0], rgb[1], rgb[2])
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid color specification: '{color_str}'")

    def _parse_rgb_tuple(self, s: str) -> Tuple[int, int, int]:
        """Parse a comma-separated RGB string like '255,128,0'.

        Args:
            s: Comma-separated string with 3 integer components.

        Returns:
            An (R, G, B) tuple.

        Raises:
            ValueError: If parsing fails or values are out of range.
        """
        parts = [p.strip() for p in s.split(",")]
        if len(parts) != 3:
            raise ValueError(f"RGB tuple must have 3 components, got {len(parts)}: '{s}'")
        try:
            values = tuple(int(p) for p in parts)
        except ValueError:
            raise ValueError(f"RGB components must be integers: '{s}'")
        for v in values:
            if v < 0 or v > 255:
                raise ValueError(f"RGB values must be in [0, 255], got {v}: '{s}'")
        return (values[0], values[1], values[2])


# ---------------------------------------------------------------------------
# TessellationRenderer
# ---------------------------------------------------------------------------
class TessellationRenderer:
    """Orchestrates the rendering pipeline for hexagonal tessellations.

    Handles canvas creation, two-pass concentric stroke drawing, viewport
    culling, and anti-alias downsampling.
    """

    # Anti-alias scale factors.
    _AA_SCALES: Dict[str, int] = {
        "off": 1,
        "low": 2,
        "medium": 4,
        "high": 8,
    }

    def render(
        self,
        width: int,
        height: int,
        circumradius: float,
        margin: float,
        line_width: int,
        layers: int,
        color_fill: Tuple[int, int, int],
        color_line: Tuple[int, int, int],
        color_background: Tuple[int, int, int],
        antialias: str,
        cull: bool,
    ) -> Tuple[Image.Image, int]:
        """Render a hexagonal tessellation image.

        Args:
            width: Target image width in pixels.
            height: Target image height in pixels.
            circumradius: Hexagon circumradius R in pixels.
            margin: Gap between hexagon edges in pixels.
            line_width: Stroke width in pixels (0 = no outline).
            layers: Number of concentric layers.
            color_fill: Fill colour as (R, G, B).
            color_line: Stroke colour as (R, G, B).
            color_background: Background colour as (R, G, B).
            antialias: Anti-alias level ('off', 'low', 'medium', 'high').
            cull: Whether to enable viewport culling.

        Returns:
            A tuple of (PIL Image at target resolution, polygon count drawn).
        """
        k = self._AA_SCALES.get(antialias, 1)

        # Scale geometry for supersampling
        sw = width * k
        sh = height * k
        sR = circumradius * k
        s_margin = margin * k
        s_lw = line_width * k

        R_s = sR + s_margin / 2.0

        # Auto-fill layers if needed
        grid = AxialGrid(spacing_radius=R_s)
        if layers == 0:
            layers = grid.auto_fill_layers(sw, sh, R_s)

        # Generate grid cells
        cells = grid.generate(layers)

        # Convert to pixel centres
        centres = [grid.axial_to_pixel(q, r, sw, sh) for q, r in cells]

        # Viewport culling
        if cull:
            R_cull = sR + s_lw / 2.0
            cull_geom = HexagonGeometry(circumradius=R_cull)
            filtered = []
            for cx, cy in centres:
                verts = cull_geom.vertices(cx, cy)
                inside = all(0 <= vx <= sw and 0 <= vy <= sh for vx, vy in verts)
                if inside:
                    filtered.append((cx, cy))
            centres = filtered

        # Create canvas
        img = Image.new("RGB", (sw, sh), color_background)
        draw = ImageDraw.Draw(img)

        polygon_count = 0

        # Two-pass rendering
        if s_lw > 0:
            # Pass 1: outer fill (stroke colour)
            R_outer = sR + s_lw / 2.0
            outer_geom = HexagonGeometry(circumradius=R_outer)
            for cx, cy in centres:
                verts = outer_geom.vertices(cx, cy)
                draw.polygon(verts, fill=color_line)
                polygon_count += 1

            # Pass 2: inner fill (fill colour)
            R_inner = max(sR - s_lw / 2.0, 0.0)
            if R_inner > 0:
                inner_geom = HexagonGeometry(circumradius=R_inner)
                for cx, cy in centres:
                    verts = inner_geom.vertices(cx, cy)
                    draw.polygon(verts, fill=color_fill)
                    polygon_count += 1
        else:
            # No outline: single fill pass at circumradius
            fill_geom = HexagonGeometry(circumradius=sR)
            for cx, cy in centres:
                verts = fill_geom.vertices(cx, cy)
                draw.polygon(verts, fill=color_fill)
                polygon_count += 1

        # Downsample if supersampled
        if k > 1:
            img = img.resize((width, height), Image.LANCZOS)

        return img, polygon_count


# ---------------------------------------------------------------------------
# SettingsManager
# ---------------------------------------------------------------------------
class SettingsManager:
    """JSON import/export of parameter sets with CLI-precedence logic.

    Handles serialisation of settings to JSON files and loading them back
    with proper precedence: JSON overrides defaults, explicit CLI args
    override JSON.
    """

    # Keys that are persisted to JSON.
    _PERSISTED_KEYS: List[str] = [
        "width", "height", "circumradius", "margin", "line_width",
        "layers", "color_fill", "color_line", "color_background",
        "antialias", "file", "cull", "debug",
    ]

    def export_settings(self, params: argparse.Namespace, path: str) -> None:
        """Export current parameters to a JSON file.

        Args:
            params: The resolved argparse Namespace.
            path: Output JSON file path.

        Raises:
            IOError: If the file cannot be written.
        """
        data: Dict = {}
        for key in self._PERSISTED_KEYS:
            val = getattr(params, key, None)
            data[key] = val
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def import_settings(self, path: str) -> Dict:
        """Import settings from a JSON file.

        Args:
            path: Path to the JSON settings file.

        Returns:
            A dictionary of loaded settings.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        with open(path, "r") as f:
            data = json.load(f)
        return data

    def merge_settings(
        self,
        defaults: argparse.Namespace,
        json_settings: Dict,
        explicit_keys: set,
    ) -> argparse.Namespace:
        """Merge JSON settings with CLI args, respecting precedence.

        JSON values override argparse defaults. Explicit CLI args override
        JSON values.

        Args:
            defaults: The argparse Namespace with default/CLI values.
            json_settings: Dictionary loaded from JSON.
            explicit_keys: Set of parameter names explicitly provided on CLI.

        Returns:
            A merged argparse Namespace.
        """
        for key in self._PERSISTED_KEYS:
            if key in json_settings and key not in explicit_keys:
                setattr(defaults, key, json_settings[key])
        return defaults


# ---------------------------------------------------------------------------
# Version helper
# ---------------------------------------------------------------------------
def _changelog_version(fallback: str = "0.0.0") -> str:
    """Read the highest version from CHANGELOG.md next to this script.

    Scans for ``## [X.Y.Z]`` headings (skipping ``[Unreleased]``) and returns
    the first match, which is the highest version.  Returns *fallback* when the
    file is missing or contains no versioned headings (e.g. frozen ``.exe``).
    """
    changelog = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CHANGELOG.md")
    try:
        with open(changelog, "r", encoding="utf-8") as fh:
            for line in fh:
                m = re.match(r"^##\s+\[(\d+\.\d+\.\d+)\]", line)
                if m:
                    return m.group(1)
    except OSError:
        pass
    return fallback


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class Application:
    """Top-level entry point for the HEX Grid Tessellator.

    Orchestrates CLI argument parsing, settings loading, rendering, file
    output, and debug reporting.
    """

    VERSION:      str = _changelog_version("3.1.0")
    BUILD_DATE:   str = "2026-02-09"
    TITLE:        str = "HEX Grid Tessellator"
    AUTHOR:       str = "Rohin Gosling + Claude Code"
    BANNER_WIDTH: int = 60    

    def run(self) -> None:
        """Execute the full application pipeline.

        Parses CLI arguments, loads/exports settings, renders the tessellation,
        saves the output PNG, and prints debug information if enabled.

        Returns:
            None
        """
        # Step 1: Parse CLI arguments and detect explicit keys
        args, explicit_keys = self._parse_args()

        # Step 2: Import settings if requested
        if args.import_settings:
            if not args.import_settings.lower().endswith(".json"):
                args.import_settings += ".json"
            try:
                manager = SettingsManager()
                json_data = manager.import_settings(args.import_settings)
                args = manager.merge_settings(args, json_data, explicit_keys)
            except FileNotFoundError:
                print(f"Error: Settings file not found: '{args.import_settings}'", file=sys.stderr)
                sys.exit(1)
            except json.JSONDecodeError as e:
                print(f"Error: Malformed JSON in settings file: {e}", file=sys.stderr)
                sys.exit(1)

        # Step 3: Export settings if requested
        if args.export_settings:
            export_path = args.export_settings
            if not export_path.lower().endswith(".json"):
                export_path += ".json"
            try:
                manager = SettingsManager()
                manager.export_settings(args, export_path)
            except IOError as e:
                print(f"Error: Cannot write settings file: {e}", file=sys.stderr)
                sys.exit(1)

        # Step 4: Parse colour strings
        parser = ColorParser()
        try:
            color_fill = parser.parse(args.color_fill)
            color_line = parser.parse(args.color_line)
            color_background = parser.parse(args.color_background)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Step 5: Auto-compute layers if layers == 0
        R_s = args.circumradius + args.margin / 2.0
        layers = args.layers
        auto_computed = False
        if layers == 0:
            grid = AxialGrid(spacing_radius=R_s)
            layers = grid.auto_fill_layers(args.width, args.height, R_s)
            auto_computed = True

        # Validate antialias level
        valid_aa = {"off", "low", "medium", "high"}
        if args.antialias not in valid_aa:
            print(f"Error: Invalid antialias level '{args.antialias}'. "
                  f"Must be one of: {', '.join(sorted(valid_aa))}", file=sys.stderr)
            sys.exit(1)

        # Step 6-12: Render
        renderer = TessellationRenderer()
        img, polygon_count = renderer.render(
            width=args.width,
            height=args.height,
            circumradius=args.circumradius,
            margin=args.margin,
            line_width=args.line_width,
            layers=layers,
            color_fill=color_fill,
            color_line=color_line,
            color_background=color_background,
            antialias=args.antialias,
            cull=args.cull,
        )

        # Step 13: Ensure .png extension and save
        out_file = args.file
        if not out_file.lower().endswith(".png"):
            out_file += ".png"
        img.save(out_file, "PNG")

        # Read file size
        file_size = os.path.getsize(out_file)

        # Banner (always shown)
        self._print_banner()

        # Save confirmation (always shown, right after banner)
        size_str = self._format_file_size(file_size)
        print(f"  Saved: {out_file} ({size_str})")
        if args.export_settings:
            export_path = args.export_settings
            if not export_path.lower().endswith(".json"):
                export_path += ".json"
            export_size_str = self._format_file_size(os.path.getsize(export_path))
            print(f"  Saved: {export_path} ({export_size_str})")

        # Step 14: Debug output
        if args.debug:
            self._print_debug(
                args=args,
                layers_resolved=layers,
                auto_computed=auto_computed,
                color_fill=color_fill,
                color_line=color_line,
                color_background=color_background,
                polygon_count=polygon_count,
                out_file=out_file,
                file_size=file_size,
            )
        print()

    def _parse_args(self) -> Tuple[argparse.Namespace, set]:
        """Parse CLI arguments and detect which were explicitly provided.

        Returns:
            A tuple of (parsed Namespace, set of explicitly-provided key names).
        """
        parser = self._build_parser()
        args = parser.parse_args()

        # Second parse with SUPPRESS defaults to detect explicit keys
        suppress_parser = self._build_parser(suppress_defaults=True)
        explicit_args = suppress_parser.parse_args()
        explicit_keys = set(vars(explicit_args).keys())

        return args, explicit_keys

    def _build_parser(self, suppress_defaults: bool = False) -> argparse.ArgumentParser:
        """Build the argparse ArgumentParser.

        Args:
            suppress_defaults: If True, set all defaults to SUPPRESS to
                detect explicitly-provided CLI args.

        Returns:
            A configured ArgumentParser.
        """
        S = argparse.SUPPRESS if suppress_defaults else None

        banner = self._banner_text()

        class _BannerParser(argparse.ArgumentParser):
            """ArgumentParser that prints the banner before help text."""

            def print_help(self, file=None):
                import sys as _sys
                if file is None:
                    file = _sys.stdout
                file.write(banner + "\n\n")
                super().print_help(file)

        parser = _BannerParser(
            description="HEX Grid Tessellator — generate hexagonal grid tessellation images.",
        )
        d = S  # shorthand

        parser.add_argument("--width", type=int, default=d if d else 1024,
                            help="Image width in pixels (default: 1024)")
        parser.add_argument("--height", type=int, default=d if d else 768,
                            help="Image height in pixels (default: 768)")
        parser.add_argument("--circumradius", type=float, default=d if d else 64.0,
                            help="Hexagon circumradius R in pixels (default: 64)")
        parser.add_argument("--margin", type=float, default=d if d else 16.0,
                            help="Gap between hexagon edges in pixels (default: 16)")
        parser.add_argument("--line_width", type=int, default=d if d else 8,
                            help="Stroke width in pixels, 0 = no outline (default: 8)")
        parser.add_argument("--layers", type=int, default=d if d else 0,
                            help="Concentric layers, 0 = auto-fill (default: 0)")
        parser.add_argument("--color_fill", type=str, default=d if d else "grey",
                            help="Hexagon fill colour (default: grey)")
        parser.add_argument("--color_line", type=str, default=d if d else "black",
                            help="Hexagon outline colour (default: black)")
        parser.add_argument("--color_background", type=str, default=d if d else "darkgrey",
                            help="Background colour (default: darkgrey)")
        parser.add_argument("--antialias", type=str, default=d if d else "high",
                            help="Anti-alias level: off, low, medium, high (default: high)")
        parser.add_argument("--file", type=str, default=d if d else "tessellation.png",
                            help="Output PNG filename (default: tessellation.png)")
        parser.add_argument("--cull", nargs="?", const=True, default=d if d else False,
                            type=self._parse_bool_flag,
                            help="Enable viewport culling")
        parser.add_argument("--debug", nargs="?", const=True, default=d if d else False,
                            type=self._parse_bool_flag,
                            help="Enable debug output")
        parser.add_argument("--export_settings", type=str, default=None,
                            help="Export parameters to a JSON file")
        parser.add_argument("--import_settings", type=str, default=None,
                            help="Import parameters from a JSON file")

        return parser

    def _parse_bool_flag(self, value: str) -> bool:
        """Parse a boolean flag value ('true'/'false' or bare flag).

        Args:
            value: String to interpret as boolean.

        Returns:
            Boolean interpretation of the value.
        """
        if isinstance(value, bool):
            return value
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise argparse.ArgumentTypeError(f"Boolean value expected, got '{value}'")

    def _banner_text(self) -> str:
        """Build the application banner as a string.

        Returns:
            The formatted banner string.
        """
        w = self.BANNER_WIDTH
        inner = w - 2  # space between │ and │
        lines = [
            "┌" + "─" * inner + "┐",
            f"│{'  Program:    ' + self.TITLE:<{inner}}│",
            f"│{'  Version:    ' + self.VERSION:<{inner}}│",
            f"│{'  Build Date: ' + self.BUILD_DATE:<{inner}}│",
            f"│{'  Author:     ' + self.AUTHOR:<{inner}}│",
            "└" + "─" * inner + "┘",
        ]
        return "\n".join(lines)

    def _print_banner(self) -> None:
        """Print the application banner to stdout."""
        print(self._banner_text())

    def _print_debug(
        self,
        args: argparse.Namespace,
        layers_resolved: int,
        auto_computed: bool,
        color_fill: Tuple[int, int, int],
        color_line: Tuple[int, int, int],
        color_background: Tuple[int, int, int],
        polygon_count: int,
        out_file: str,
        file_size: int,
    ) -> None:
        """Print debug information to stdout.

        Args:
            args: The resolved parameters.
            layers_resolved: The actual number of layers used.
            auto_computed: Whether layers were auto-computed.
            color_fill: Resolved fill colour.
            color_line: Resolved line colour.
            color_background: Resolved background colour.
            polygon_count: Number of polygons drawn.
            out_file: Output PNG file path.
            file_size: Output PNG file size in bytes.

        Returns:
            None
        """
        # Parameters
        print(f"\n  Image size:       {args.width} x {args.height}")
        print(f"  Circumradius:     {args.circumradius}")
        print(f"  Margin:           {args.margin}")
        print(f"  Line width:       {args.line_width}")
        layers_str = f"{layers_resolved}"
        if auto_computed:
            layers_str += f" (auto-computed from requested 0)"
        print(f"  Layers:           {layers_str}")
        print(f"  Anti-alias:       {args.antialias}")
        print(f"  Cull:             {args.cull}")
        print(f"  Fill colour:      {args.color_fill} -> {color_fill}")
        print(f"  Line colour:      {args.color_line} -> {color_line}")
        print(f"  Background:       {args.color_background} -> {color_background}")
        cx, cy = args.width // 2, args.height // 2
        print(f"  Centre pixel:     ({cx}, {cy})")
        print(f"  Polygons drawn:   {polygon_count}")

        # Saved files
        print(f"  Saved: {out_file} ({self._format_file_size(file_size)})")
        if args.export_settings:
            export_path = args.export_settings
            if not export_path.lower().endswith(".json"):
                export_path += ".json"
            export_size_str = self._format_file_size(os.path.getsize(export_path))
            print(f"  Saved: {export_path} ({export_size_str})")

    def _format_file_size(self, size_bytes: int) -> str:
        """Format a file size in human-readable form.

        Args:
            size_bytes: File size in bytes.

        Returns:
            Formatted string (e.g. '1.23 MB').
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Main entry point for the HEX Grid Tessellator."""
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    app = Application()
    app.run()


if __name__ == "__main__":
    main()
