"""
Automated test suite for HEX Grid Tessellator.

Run:  python -m pytest test_main.py -v
Or:   python test_main.py
"""

import importlib
import inspect
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Import the main module. Adjust if the filename differs.
# ---------------------------------------------------------------------------
MAIN_MODULE_NAME = "main"
MAIN_FILE = os.path.join(os.path.dirname(__file__), f"{MAIN_MODULE_NAME}.py")


def _import_main():
    """Dynamically import main.py so tests fail clearly if it doesn't exist."""
    spec = importlib.util.spec_from_file_location(MAIN_MODULE_NAME, MAIN_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Helper: run main.py as a subprocess (for CLI / integration tests)
# ---------------------------------------------------------------------------
def _run_cli(*args, expect_fail=False):
    """Run main.py with the given CLI args and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, MAIN_FILE, *args],
        capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    if not expect_fail and result.returncode != 0:
        raise AssertionError(
            f"CLI exited with code {result.returncode}\n"
            f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}"
        )
    return result.returncode, result.stdout, result.stderr


# ===================================================================
# 1. ARCHITECTURAL / STRUCTURAL TESTS
# ===================================================================
class TestArchitecture(unittest.TestCase):
    """Verify required classes, type annotations, and docstrings exist."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()

    def test_required_classes_exist(self):
        """FR-arch: All six required classes must be defined."""
        required = [
            "HexagonGeometry", "AxialGrid", "ColorParser",
            "TessellationRenderer", "SettingsManager", "Application",
        ]
        for name in required:
            self.assertTrue(
                hasattr(self.mod, name) and inspect.isclass(getattr(self.mod, name)),
                f"Missing required class: {name}"
            )

    def test_classes_have_docstrings(self):
        """NFR: Every required class must have block comment documentation."""
        required = [
            "HexagonGeometry", "AxialGrid", "ColorParser",
            "TessellationRenderer", "SettingsManager", "Application",
        ]
        source = inspect.getsource(self.mod).replace('\r\n', '\n')
        for name in required:
            self.assertIn(
                f"# {name}\n#\n# Description:",
                source,
                f"Class {name} is missing block comment documentation"
            )

    def test_public_methods_have_docstrings(self):
        """NFR: Public methods on required classes must have block comment documentation."""
        required = [
            "HexagonGeometry", "AxialGrid", "ColorParser",
            "TessellationRenderer", "SettingsManager", "Application",
        ]
        source = inspect.getsource(self.mod).replace('\r\n', '\n')
        for class_name in required:
            cls = getattr(self.mod, class_name)
            for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not method_name.startswith("_"):
                    self.assertIn(
                        f"# Function: {method_name}",
                        source,
                        f"{class_name}.{method_name}() is missing block comment documentation"
                    )

    def test_public_methods_have_type_annotations(self):
        """NFR: Public methods must have type annotations."""
        required = [
            "HexagonGeometry", "AxialGrid", "ColorParser",
            "TessellationRenderer", "SettingsManager", "Application",
        ]
        for class_name in required:
            cls = getattr(self.mod, class_name)
            for method_name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not method_name.startswith("_"):
                    hints = method.__annotations__
                    self.assertTrue(
                        len(hints) > 0,
                        f"{class_name}.{method_name}() has no type annotations"
                    )

    def test_single_file(self):
        """NFR: The entire program must reside in one Python file."""
        excluded = {"test_main.py"}
        py_files = [
            f for f in os.listdir(os.path.dirname(MAIN_FILE))
            if f.endswith(".py") and f not in excluded and not f.startswith("__")
        ]
        self.assertEqual(len(py_files), 1, f"Expected 1 source .py file, found: {py_files}")


# ===================================================================
# 2. HEXAGON GEOMETRY TESTS (FR-1)
# ===================================================================
class TestHexagonGeometry(unittest.TestCase):
    """FR-1: Flat-top hexagon vertex computation."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()
        cls.HexGeom = cls.mod.HexagonGeometry

    def test_vertex_count(self):
        """A hexagon must have exactly 6 vertices."""
        geom = self.HexGeom(circumradius=100)
        verts = geom.vertices(0, 0) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(0, 0)
        self.assertEqual(len(verts), 6)

    def test_vertex_0_is_rightmost(self):
        """v0 must be at (cx + R, cy) — the rightmost point."""
        R = 50.0
        cx, cy = 200.0, 300.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(cx, cy) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(cx, cy)
        v0x, v0y = verts[0]
        self.assertAlmostEqual(v0x, cx + R, places=5)
        self.assertAlmostEqual(v0y, cy, places=5)

    def test_all_vertices_at_circumradius(self):
        """Every vertex must be exactly R from the centre."""
        R = 64.0
        cx, cy = 100.0, 100.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(cx, cy) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(cx, cy)
        for i, (vx, vy) in enumerate(verts):
            dist = math.hypot(vx - cx, vy - cy)
            self.assertAlmostEqual(dist, R, places=5, msg=f"Vertex {i} distance wrong")

    def test_vertices_counter_clockwise(self):
        """Vertices must proceed counter-clockwise (increasing angle)."""
        R = 64.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(0, 0) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(0, 0)
        angles = [math.atan2(vy, vx) for vx, vy in verts]
        # Unwrap angles to be monotonically increasing
        for i in range(1, len(angles)):
            while angles[i] < angles[i - 1]:
                angles[i] += 2 * math.pi
        for i in range(1, len(angles)):
            self.assertGreater(angles[i], angles[i - 1], f"Vertex {i} is not CCW from vertex {i-1}")

    def test_vertex_spacing_60_degrees(self):
        """Adjacent vertices must be 60 degrees apart."""
        R = 64.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(0, 0) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(0, 0)
        angles = [math.atan2(vy, vx) for vx, vy in verts]
        for i in range(len(angles)):
            diff = angles[(i + 1) % 6] - angles[i]
            # Normalize to [0, 2pi)
            diff = diff % (2 * math.pi)
            self.assertAlmostEqual(diff, math.pi / 3, places=5,
                                   msg=f"Angle gap between vertex {i} and {(i+1)%6} is not 60 degrees")

    def test_width_is_2R(self):
        """Hexagon width (vertex-to-vertex) must be 2R."""
        R = 40.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(0, 0) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(0, 0)
        xs = [v[0] for v in verts]
        width = max(xs) - min(xs)
        self.assertAlmostEqual(width, 2 * R, places=5)

    def test_height_is_R_sqrt3(self):
        """Hexagon height (edge-to-edge) must be R * sqrt(3)."""
        R = 40.0
        geom = self.HexGeom(circumradius=R)
        verts = geom.vertices(0, 0) if callable(getattr(geom, "vertices", None)) else geom.get_vertices(0, 0)
        ys = [v[1] for v in verts]
        height = max(ys) - min(ys)
        self.assertAlmostEqual(height, R * math.sqrt(3), places=5)


# ===================================================================
# 3. AXIAL GRID TESTS (FR-2, FR-3, FR-4, FR-5)
# ===================================================================
class TestAxialGrid(unittest.TestCase):
    """FR-2 through FR-5: Coordinate system, ring generation, auto-fill."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()
        cls.Grid = cls.mod.AxialGrid

    def _get_ring(self, grid, d):
        """Get ring cells — try common method names."""
        for name in ("ring", "get_ring", "generate_ring", "ring_cells"):
            fn = getattr(grid, name, None)
            if callable(fn):
                return list(fn(d))
        raise AttributeError("Cannot find ring generation method on AxialGrid")

    def _get_grid_cells(self, grid, layers):
        """Get all grid cells — try common method names."""
        for name in ("generate", "get_cells", "generate_grid", "grid_cells", "all_cells"):
            fn = getattr(grid, name, None)
            if callable(fn):
                return list(fn(layers))
        raise AttributeError("Cannot find grid generation method on AxialGrid")

    # -- FR-2.3: Axial-to-pixel conversion --

    def test_origin_maps_to_centre(self):
        """FR-2.3: Axial (0,0) must map to canvas centre (w/2, h/2)."""
        R_s = 72.0  # spacing radius
        w, h = 1024, 768
        grid = self.Grid(spacing_radius=R_s) if "spacing_radius" in inspect.signature(self.Grid.__init__).parameters else self.Grid(R_s)
        # Try common method names for axial-to-pixel
        for name in ("axial_to_pixel", "to_pixel", "convert"):
            fn = getattr(grid, name, None)
            if callable(fn):
                px, py = fn(0, 0, w, h)
                self.assertAlmostEqual(px, w / 2, places=3)
                self.assertAlmostEqual(py, h / 2, places=3)
                return
        self.fail("Cannot find axial-to-pixel method on AxialGrid")

    # -- FR-4: Ring generation --

    def test_ring_0_is_origin(self):
        """FR-4: Ring d=0 must return only (0,0)."""
        grid = self.Grid.__new__(self.Grid)
        # Call __init__ if needed
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        cells = self._get_ring(grid, 0)
        self.assertEqual(cells, [(0, 0)])

    def test_ring_1_has_6_cells(self):
        """FR-4: Ring d=1 must have exactly 6 cells."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        cells = self._get_ring(grid, 1)
        self.assertEqual(len(cells), 6)

    def test_ring_1_starts_at_minus1_0(self):
        """FR-4.2: Ring d=1 must start at (-1, 0)."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        cells = self._get_ring(grid, 1)
        self.assertEqual(cells[0], (-1, 0))

    def test_ring_d_has_6d_cells(self):
        """FR-4: Ring d must have exactly 6d cells for d >= 1."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        for d in range(1, 6):
            cells = self._get_ring(grid, d)
            self.assertEqual(len(cells), 6 * d, f"Ring {d} cell count wrong")

    def test_ring_cells_no_duplicates(self):
        """FR-4: Ring cells must have no duplicates."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        for d in range(0, 5):
            cells = self._get_ring(grid, d)
            self.assertEqual(len(cells), len(set(cells)), f"Ring {d} has duplicate cells")

    def test_ring_cells_at_correct_hex_distance(self):
        """FR-2.1/FR-4: Every cell in ring d must have hex distance d."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        for d in range(0, 5):
            cells = self._get_ring(grid, d)
            for q, r in cells:
                s = -q - r
                hex_dist = max(abs(q), abs(r), abs(s))
                self.assertEqual(hex_dist, d, f"Cell ({q},{r}) has hex distance {hex_dist}, expected {d}")

    # -- FR-4.1: Total cell count --

    def test_total_cells_formula(self):
        """FR-4.1: Total cells for L layers must be 1 + 3L(L-1)."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        for L in range(1, 8):
            cells = self._get_grid_cells(grid, L)
            expected = 1 + 3 * L * (L - 1)
            self.assertEqual(len(cells), expected, f"L={L}: expected {expected}, got {len(cells)}")

    def test_grid_cells_no_duplicates(self):
        """All grid cells across all layers must be unique."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        cells = self._get_grid_cells(grid, 5)
        self.assertEqual(len(cells), len(set(cells)))

    # -- FR-5: Auto-fill --

    def test_auto_fill_minimum_1(self):
        """FR-5: Auto-fill must return at least 1 layer."""
        grid = self.Grid.__new__(self.Grid)
        try:
            grid.__init__()
        except TypeError:
            grid.__init__(1.0)
        for name in ("auto_fill_layers", "compute_layers", "auto_layers", "calculate_layers"):
            fn = getattr(grid, name, None)
            if callable(fn):
                L = fn(10, 10, 100.0)  # tiny canvas, huge radius
                self.assertGreaterEqual(L, 1)
                return
        self.fail("Cannot find auto-fill method on AxialGrid")


# ===================================================================
# 4. COLOR PARSER TESTS (FR-9)
# ===================================================================
class TestColorParser(unittest.TestCase):
    """FR-9: Color parsing from CSS names, hex codes, RGB tuples."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()
        cls.Parser = cls.mod.ColorParser

    def _parse(self, color_str):
        """Call the parser — try common patterns."""
        parser = self.Parser()
        for name in ("parse", "parse_color", "get_rgb", "to_rgb"):
            fn = getattr(parser, name, None)
            if callable(fn):
                return fn(color_str)
        # Try as a static/class method
        for name in ("parse", "parse_color", "get_rgb", "to_rgb"):
            fn = getattr(self.Parser, name, None)
            if callable(fn):
                return fn(color_str)
        raise AttributeError("Cannot find parse method on ColorParser")

    def test_css_named_color_red(self):
        """FR-9.1: 'red' must parse to (255, 0, 0)."""
        self.assertEqual(self._parse("red"), (255, 0, 0))

    def test_css_named_color_cornflowerblue(self):
        """FR-9.1: 'cornflowerblue' must parse correctly."""
        self.assertEqual(self._parse("cornflowerblue"), (100, 149, 237))

    def test_hex_code_full(self):
        """FR-9.2: '#FF0000' must parse to (255, 0, 0)."""
        self.assertEqual(self._parse("#FF0000"), (255, 0, 0))

    def test_hex_code_short(self):
        """FR-9.2: '#abc' must parse to (170, 187, 204)."""
        self.assertEqual(self._parse("#abc"), (170, 187, 204))

    def test_hex_code_lowercase(self):
        """FR-9.2: '#ff8800' must parse correctly."""
        self.assertEqual(self._parse("#ff8800"), (255, 136, 0))

    def test_rgb_comma_tuple(self):
        """FR-9.3: '255,128,0' must parse to (255, 128, 0)."""
        self.assertEqual(self._parse("255,128,0"), (255, 128, 0))

    def test_rgb_comma_tuple_with_spaces(self):
        """FR-9.3: '0, 0, 0' should parse to (0, 0, 0)."""
        self.assertEqual(self._parse("0, 0, 0"), (0, 0, 0))

    def test_rgb_all_zeros(self):
        """FR-9.3: '0,0,0' must parse to (0, 0, 0)."""
        self.assertEqual(self._parse("0,0,0"), (0, 0, 0))

    def test_rgb_all_max(self):
        """FR-9.3: '255,255,255' must parse to (255, 255, 255)."""
        self.assertEqual(self._parse("255,255,255"), (255, 255, 255))

    def test_invalid_color_raises(self):
        """FR-9: Invalid color string must raise ValueError."""
        with self.assertRaises(ValueError):
            self._parse("not_a_real_color_xyz")

    def test_rgb_out_of_range_raises(self):
        """FR-9.3: RGB values outside [0,255] must raise ValueError."""
        with self.assertRaises(ValueError):
            self._parse("256,0,0")

    def test_rgb_negative_raises(self):
        """FR-9.3: Negative RGB values must raise ValueError."""
        with self.assertRaises(ValueError):
            self._parse("-1,0,0")

    def test_return_type_is_tuple(self):
        """FR-9: Return value must be a tuple of 3 ints."""
        result = self._parse("red")
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)
        for component in result:
            self.assertIsInstance(component, int)


# ===================================================================
# 5. SETTINGS MANAGER TESTS (FR-10)
# ===================================================================
class TestSettingsManager(unittest.TestCase):
    """FR-10: JSON import/export of settings."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()
        cls.Manager = cls.mod.SettingsManager

    def test_export_creates_valid_json(self):
        """FR-10.2: Export must create a valid JSON file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            _run_cli("--export_settings", tmp_path, "--file", "dummy.png",
                     "--antialias", "off", "--layers", "1")
            with open(tmp_path, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)
        finally:
            for p in [tmp_path, "dummy.png"]:
                if os.path.exists(p):
                    os.remove(p)

    def test_export_contains_required_keys(self):
        """FR-10.1: Exported JSON must contain all persisted keys."""
        required_keys = {
            "width", "height", "circumradius", "margin", "line_width",
            "layers", "color_fill", "color_line", "color_background",
            "antialias", "file", "cull", "debug",
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            _run_cli("--export_settings", tmp_path, "--file", "dummy.png",
                     "--antialias", "off", "--layers", "1")
            with open(tmp_path, "r") as f:
                data = json.load(f)
            for key in required_keys:
                self.assertIn(key, data, f"Exported JSON missing key: {key}")
        finally:
            for p in [tmp_path, "dummy.png"]:
                if os.path.exists(p):
                    os.remove(p)

    def test_export_booleans_are_json_booleans(self):
        """FR-10.2: 'cull' and 'debug' must be stored as JSON booleans."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            tmp_path = f.name
        try:
            _run_cli("--export_settings", tmp_path, "--debug", "--cull",
                     "--file", "dummy.png", "--antialias", "off", "--layers", "1")
            with open(tmp_path, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data["cull"], bool)
            self.assertIsInstance(data["debug"], bool)
        finally:
            for p in [tmp_path, "dummy.png"]:
                if os.path.exists(p):
                    os.remove(p)

    def test_export_auto_appends_json_extension(self):
        """Export with a filename lacking .json must auto-append the extension."""
        tmp_dir = tempfile.mkdtemp()
        base_name = os.path.join(tmp_dir, "settings_no_ext")
        expected_path = base_name + ".json"
        try:
            _run_cli("--export_settings", base_name, "--file", "dummy.png",
                     "--antialias", "off", "--layers", "1")
            self.assertFalse(os.path.exists(base_name),
                             "File without .json extension should not exist")
            self.assertTrue(os.path.exists(expected_path),
                            "File with .json extension should have been created")
            with open(expected_path, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)
        finally:
            for p in [base_name, expected_path, "dummy.png"]:
                if os.path.exists(p):
                    os.remove(p)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)

    def test_import_applies_settings(self):
        """FR-10.3: Imported settings must override defaults."""
        settings = {
            "width": 512, "height": 512, "circumradius": 32.0,
            "margin": 8.0, "line_width": 4, "layers": 2,
            "color_fill": "blue", "color_line": "white",
            "color_background": "black", "antialias": "off",
            "file": "imported_output.png", "cull": False, "debug": True,
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(settings, f)
            settings_path = f.name
        try:
            _run_cli("--import_settings", settings_path)
            self.assertTrue(os.path.exists("imported_output.png"),
                            "Import did not apply the 'file' setting")
        finally:
            if os.path.exists(settings_path):
                os.remove(settings_path)
            if os.path.exists("imported_output.png"):
                os.remove("imported_output.png")

    def test_cli_overrides_imported_settings(self):
        """FR-10.3: CLI explicit args must override imported JSON values."""
        settings = {
            "width": 512, "height": 512, "layers": 2,
            "antialias": "off", "file": "from_json.png",
            "debug": False,
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(settings, f)
            settings_path = f.name
        override_file = "from_cli.png"
        try:
            _run_cli("--import_settings", settings_path, "--file", override_file)
            self.assertTrue(os.path.exists(override_file),
                            "CLI --file did not override JSON 'file' setting")
            self.assertFalse(os.path.exists("from_json.png"),
                             "JSON 'file' was used despite CLI override")
        finally:
            for p in [settings_path, override_file, "from_json.png"]:
                if os.path.exists(p):
                    os.remove(p)

    def test_import_missing_file_exits_nonzero(self):
        """FR-10.3/NFR: Importing a nonexistent JSON must exit with non-zero code."""
        code, _, _ = _run_cli("--import_settings", "nonexistent_file_12345.json",
                              expect_fail=True)
        self.assertNotEqual(code, 0)


# ===================================================================
# 6. CLI INTERFACE & DEFAULTS TESTS
# ===================================================================
class TestCLIDefaults(unittest.TestCase):
    """CLI argument parsing and default values."""

    def test_default_output_produces_png(self):
        """Defaults must produce a file called tessellation.png."""
        out_file = "tessellation.png"
        try:
            _run_cli("--antialias", "off", "--layers", "1")
            self.assertTrue(os.path.exists(out_file))
        finally:
            if os.path.exists(out_file):
                os.remove(out_file)

    def test_custom_output_filename(self):
        """--file must control the output filename."""
        out_file = "custom_test_output.png"
        try:
            _run_cli("--file", out_file, "--antialias", "off", "--layers", "1")
            self.assertTrue(os.path.exists(out_file))
        finally:
            if os.path.exists(out_file):
                os.remove(out_file)

    def test_png_extension_auto_appended(self):
        """FR-11: If filename lacks .png, it must be appended."""
        try:
            _run_cli("--file", "no_ext_test", "--antialias", "off", "--layers", "1")
            self.assertTrue(os.path.exists("no_ext_test.png"),
                            ".png was not appended to filename")
        finally:
            for f in ["no_ext_test", "no_ext_test.png"]:
                if os.path.exists(f):
                    os.remove(f)

    def test_debug_flag_produces_output(self):
        """FR-12: --debug must produce banner/parameter output on stdout or stderr."""
        code, stdout, stderr = _run_cli("--debug", "--antialias", "off",
                                         "--layers", "1", "--file", "debug_test.png")
        combined = stdout + stderr
        self.assertTrue(len(combined) > 0, "Debug mode produced no output")
        try:
            pass
        finally:
            if os.path.exists("debug_test.png"):
                os.remove("debug_test.png")

    def test_invalid_antialias_level_exits_nonzero(self):
        """Invalid --antialias value must exit non-zero."""
        code, _, _ = _run_cli("--antialias", "ultra", "--layers", "1",
                              "--file", "bad_aa.png", expect_fail=True)
        self.assertNotEqual(code, 0)
        if os.path.exists("bad_aa.png"):
            os.remove("bad_aa.png")


# ===================================================================
# 7. IMAGE OUTPUT VALIDATION TESTS
# ===================================================================
class TestImageOutput(unittest.TestCase):
    """Validate produced PNG files (dimensions, format, content)."""

    def _generate(self, filename, **kwargs):
        """Helper: generate an image with given params, return the path."""
        args = ["--file", filename, "--antialias", "off", "--layers", "1"]
        for k, v in kwargs.items():
            args.extend([f"--{k}", str(v)])
        _run_cli(*args)
        return filename

    def tearDown(self):
        for f in getattr(self, "_cleanup", []):
            if os.path.exists(f):
                os.remove(f)

    def test_output_is_valid_png(self):
        """Output file must be a valid PNG (correct magic bytes)."""
        self._cleanup = ["valid_png_test.png"]
        path = self._generate("valid_png_test.png")
        with open(path, "rb") as f:
            header = f.read(8)
        # PNG magic: 89 50 4E 47 0D 0A 1A 0A
        self.assertEqual(header, b"\x89PNG\r\n\x1a\n")

    def test_output_dimensions_match_request(self):
        """Image dimensions must match --width and --height."""
        from PIL import Image
        self._cleanup = ["dim_test.png"]
        self._generate("dim_test.png", width=800, height=600)
        with Image.open("dim_test.png") as img:
            self.assertEqual(img.size, (800, 600))

    def test_output_dimensions_default(self):
        """Default dimensions must be 1024x768."""
        from PIL import Image
        self._cleanup = ["default_dim_test.png"]
        self._generate("default_dim_test.png")
        with Image.open("default_dim_test.png") as img:
            self.assertEqual(img.size, (1024, 768))

    def test_background_color_fills_canvas(self):
        """Background color must fill the canvas (check corner pixel)."""
        from PIL import Image
        self._cleanup = ["bg_test.png"]
        self._generate("bg_test.png", width=100, height=100,
                       color_background="255,0,0", layers="1",
                       circumradius="10", cull="true")
        with Image.open("bg_test.png") as img:
            # Corner pixel (0,0) should be background color when cull is on and hex is small
            corner = img.getpixel((0, 0))
            self.assertEqual(corner[:3], (255, 0, 0),
                             f"Corner pixel {corner} is not the background color (255,0,0)")

    def test_zero_line_width_no_outline(self):
        """FR-7: line_width=0 should produce hexagons with no outline (fill only)."""
        from PIL import Image
        self._cleanup = ["no_outline_test.png"]
        self._generate("no_outline_test.png", width=200, height=200,
                       line_width=0, layers=1, circumradius=40,
                       color_fill="0,255,0", color_background="0,0,255")
        with Image.open("no_outline_test.png") as img:
            # Centre pixel should be the fill color (green)
            cx, cy = 100, 100
            pixel = img.getpixel((cx, cy))
            self.assertEqual(pixel[:3], (0, 255, 0),
                             f"Centre pixel {pixel} is not the fill color (0,255,0)")

    def test_single_layer_centre_cell(self):
        """1 layer = only centre hex. Centre pixel must be fill color."""
        from PIL import Image
        self._cleanup = ["centre_test.png"]
        self._generate("centre_test.png", width=200, height=200,
                       layers=1, circumradius=60, line_width=0,
                       color_fill="255,255,0", color_background="0,0,0")
        with Image.open("centre_test.png") as img:
            pixel = img.getpixel((100, 100))
            self.assertEqual(pixel[:3], (255, 255, 0),
                             f"Centre pixel {pixel} is not yellow fill")

    def test_antialias_off_matches_dimensions(self):
        """AA off: output must exactly match requested dimensions."""
        from PIL import Image
        self._cleanup = ["aa_off_test.png"]
        self._generate("aa_off_test.png", width=256, height=256, antialias="off")
        with Image.open("aa_off_test.png") as img:
            self.assertEqual(img.size, (256, 256))

    def test_antialias_low_matches_dimensions(self):
        """AA low: output must still be the requested dimensions after downsampling."""
        from PIL import Image
        self._cleanup = ["aa_low_test.png"]
        self._generate("aa_low_test.png", width=256, height=256, antialias="low")
        with Image.open("aa_low_test.png") as img:
            self.assertEqual(img.size, (256, 256))

    def test_antialias_high_matches_dimensions(self):
        """AA high: output must still be the requested dimensions after downsampling."""
        from PIL import Image
        self._cleanup = ["aa_high_test.png"]
        self._generate("aa_high_test.png", width=256, height=256, antialias="high")
        with Image.open("aa_high_test.png") as img:
            self.assertEqual(img.size, (256, 256))

    def test_file_size_nonzero(self):
        """Output file must have non-zero size."""
        self._cleanup = ["size_test.png"]
        self._generate("size_test.png")
        self.assertGreater(os.path.getsize("size_test.png"), 0)


# ===================================================================
# 8. VIEWPORT CULLING TESTS (FR-6)
# ===================================================================
class TestViewportCulling(unittest.TestCase):
    """FR-6: Viewport culling discards out-of-bounds hexagons."""

    def test_cull_reduces_or_keeps_polygon_count(self):
        """Culling enabled with auto-fill should not crash and should produce valid output."""
        out = "cull_test.png"
        try:
            _run_cli("--cull", "--layers", "0", "--antialias", "off",
                     "--file", out, "--width", "200", "--height", "200")
            self.assertTrue(os.path.exists(out))
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_cull_with_small_canvas_large_radius(self):
        """Culling with large hex on small canvas should still produce output."""
        out = "cull_small_test.png"
        try:
            _run_cli("--cull", "--circumradius", "200", "--width", "100",
                     "--height", "100", "--layers", "1", "--antialias", "off",
                     "--file", out)
            self.assertTrue(os.path.exists(out))
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_no_cull_keeps_edge_hexagons(self):
        """Without culling, auto-fill should include edge hexagons (file produced)."""
        out = "no_cull_test.png"
        try:
            _run_cli("--layers", "0", "--antialias", "off", "--file", out,
                     "--width", "200", "--height", "200")
            self.assertTrue(os.path.exists(out))
            self.assertGreater(os.path.getsize(out), 0)
        finally:
            if os.path.exists(out):
                os.remove(out)


# ===================================================================
# 9. EFFECTIVE SPACING RADIUS TESTS (FR-3)
# ===================================================================
class TestSpacingRadius(unittest.TestCase):
    """FR-3: Effective spacing radius R_s = R + margin/2."""

    @classmethod
    def setUpClass(cls):
        cls.mod = _import_main()

    def test_margin_zero_produces_touching_hexagons(self):
        """margin=0 means R_s = R, hexagons should touch."""
        from PIL import Image
        out = "margin_zero_test.png"
        try:
            _run_cli("--margin", "0", "--layers", "2", "--antialias", "off",
                     "--line_width", "0", "--circumradius", "40",
                     "--width", "300", "--height", "300",
                     "--color_fill", "255,0,0", "--color_background", "0,0,255",
                     "--file", out)
            with Image.open(out) as img:
                # Centre pixel must be fill
                self.assertEqual(img.getpixel((150, 150))[:3], (255, 0, 0))
        finally:
            if os.path.exists(out):
                os.remove(out)


# ===================================================================
# 10. TWO-PASS RENDERING TESTS (FR-7)
# ===================================================================
class TestTwoPassRendering(unittest.TestCase):
    """FR-7: Two-pass concentric stroke rendering produces visible outlines."""

    def test_outline_visible_between_layers(self):
        """With line_width > 0, outline color must appear in the image."""
        from PIL import Image
        out = "outline_test.png"
        try:
            _run_cli("--layers", "2", "--antialias", "off", "--line_width", "8",
                     "--circumradius", "40", "--width", "300", "--height", "300",
                     "--color_fill", "0,255,0", "--color_line", "255,0,0",
                     "--color_background", "0,0,0", "--file", out)
            with Image.open(out) as img:
                pixels = list(img.getdata())
                has_outline_color = any(p[:3] == (255, 0, 0) for p in pixels)
                self.assertTrue(has_outline_color,
                                "Outline color (255,0,0) not found in image")
        finally:
            if os.path.exists(out):
                os.remove(out)

    def test_no_outline_when_line_width_zero(self):
        """line_width=0: outline color must NOT appear (only fill + background)."""
        from PIL import Image
        out = "no_outline_check.png"
        try:
            _run_cli("--layers", "2", "--antialias", "off", "--line_width", "0",
                     "--circumradius", "40", "--width", "300", "--height", "300",
                     "--color_fill", "0,255,0", "--color_line", "255,0,0",
                     "--color_background", "0,0,0", "--file", out)
            with Image.open(out) as img:
                pixels = list(img.getdata())
                has_outline_color = any(p[:3] == (255, 0, 0) for p in pixels)
                self.assertFalse(has_outline_color,
                                 "Outline color found despite line_width=0")
        finally:
            if os.path.exists(out):
                os.remove(out)


# ===================================================================
# 11. ERROR HANDLING TESTS (NFR)
# ===================================================================
class TestErrorHandling(unittest.TestCase):
    """NFR: Graceful error handling with non-zero exit codes."""

    def test_invalid_color_exits_nonzero(self):
        """Invalid color string must cause a non-zero exit."""
        code, _, stderr = _run_cli("--color_fill", "not_a_color_xyz",
                                   "--antialias", "off", "--layers", "1",
                                   "--file", "err_test.png", expect_fail=True)
        self.assertNotEqual(code, 0)
        if os.path.exists("err_test.png"):
            os.remove("err_test.png")

    def test_malformed_json_import_exits_nonzero(self):
        """Malformed JSON file must cause a non-zero exit."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("{this is not valid json")
            bad_json = f.name
        try:
            code, _, _ = _run_cli("--import_settings", bad_json, expect_fail=True)
            self.assertNotEqual(code, 0)
        finally:
            os.remove(bad_json)

    def test_error_output_goes_to_stderr(self):
        """Error messages must be printed to stderr."""
        _, _, stderr = _run_cli("--color_fill", "not_a_color_xyz",
                                "--antialias", "off", "--layers", "1",
                                "--file", "err_stderr_test.png", expect_fail=True)
        self.assertTrue(len(stderr) > 0, "No error output on stderr")
        if os.path.exists("err_stderr_test.png"):
            os.remove("err_stderr_test.png")


# ===================================================================
# 12. ROUND-TRIP SETTINGS TEST (FR-10)
# ===================================================================
class TestSettingsRoundTrip(unittest.TestCase):
    """FR-10: Export then import must produce identical results."""

    def test_export_import_round_trip(self):
        """Exporting settings and re-importing must produce the same image dimensions."""
        from PIL import Image
        export_json = "round_trip_settings.json"
        out1 = "round_trip_1.png"
        out2 = "round_trip_2.png"
        try:
            # Generate with custom params and export
            _run_cli("--width", "400", "--height", "300", "--circumradius", "32",
                     "--layers", "2", "--antialias", "off", "--line_width", "4",
                     "--color_fill", "blue", "--color_background", "white",
                     "--file", out1, "--export_settings", export_json)
            # Re-import and generate
            _run_cli("--import_settings", export_json, "--file", out2)
            with Image.open(out1) as img1, Image.open(out2) as img2:
                self.assertEqual(img1.size, img2.size,
                                 "Round-trip produced different image dimensions")
        finally:
            for f in [export_json, out1, out2]:
                if os.path.exists(f):
                    os.remove(f)


# ===================================================================
# 12. EXECUTABLE (.exe) TESTS
# ===================================================================
EXE_FILE = os.path.join(os.path.dirname(__file__), "dist", "hextessellator.exe")


def _run_exe(*args, expect_fail=False):
    """Run dist/hextessellator.exe with the given CLI args and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [EXE_FILE, *args],
        capture_output=True, text=True, encoding="utf-8", timeout=120
    )
    if not expect_fail and result.returncode != 0:
        raise AssertionError(
            f"EXE exited with code {result.returncode}\n"
            f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}"
        )
    return result.returncode, result.stdout, result.stderr


@unittest.skipUnless(os.path.isfile(EXE_FILE), "dist/hextessellator.exe not found — build with pyinstaller first")
class TestExecutable(unittest.TestCase):
    """Smoke tests that run against the compiled dist/hextessellator.exe."""

    def test_exe_produces_png(self):
        """EXE must produce a valid PNG output file."""
        tmp_dir = tempfile.mkdtemp()
        out_png = os.path.join(tmp_dir, "exe_test.png")
        try:
            _run_exe("--file", out_png, "--antialias", "off", "--layers", "1")
            self.assertTrue(os.path.exists(out_png),
                            "EXE did not produce output PNG")
            self.assertGreater(os.path.getsize(out_png), 0,
                               "Output PNG is empty")
        finally:
            if os.path.exists(out_png):
                os.remove(out_png)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)

    def test_exe_export_auto_appends_json_extension(self):
        """EXE export with a filename lacking .json must auto-append the extension."""
        tmp_dir = tempfile.mkdtemp()
        base_name = os.path.join(tmp_dir, "exe_settings")
        expected_path = base_name + ".json"
        try:
            _run_exe("--export_settings", base_name, "--file",
                     os.path.join(tmp_dir, "dummy.png"),
                     "--antialias", "off", "--layers", "1")
            self.assertFalse(os.path.exists(base_name),
                             "File without .json extension should not exist")
            self.assertTrue(os.path.exists(expected_path),
                            "EXE should have created file with .json extension")
            with open(expected_path, "r") as f:
                data = json.load(f)
            self.assertIsInstance(data, dict)
        finally:
            for p in [base_name, expected_path, os.path.join(tmp_dir, "dummy.png")]:
                if os.path.exists(p):
                    os.remove(p)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)

    def test_exe_export_preserves_json_extension(self):
        """EXE export with a filename that already has .json must not double it."""
        tmp_dir = tempfile.mkdtemp()
        json_path = os.path.join(tmp_dir, "exe_settings.json")
        double_path = json_path + ".json"
        try:
            _run_exe("--export_settings", json_path, "--file",
                     os.path.join(tmp_dir, "dummy.png"),
                     "--antialias", "off", "--layers", "1")
            self.assertTrue(os.path.exists(json_path),
                            "File with .json extension should exist")
            self.assertFalse(os.path.exists(double_path),
                             "File should not have double .json extension")
        finally:
            for p in [json_path, double_path, os.path.join(tmp_dir, "dummy.png")]:
                if os.path.exists(p):
                    os.remove(p)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)

    def test_exe_debug_flag(self):
        """EXE --debug flag must produce debug output on stdout."""
        tmp_dir = tempfile.mkdtemp()
        out_png = os.path.join(tmp_dir, "debug_test.png")
        try:
            _, stdout, _ = _run_exe("--file", out_png, "--antialias", "off",
                                    "--layers", "1", "--debug")
            self.assertIn("HEX Grid Tessellator", stdout,
                          "Debug output expected when --debug is used")
        finally:
            if os.path.exists(out_png):
                os.remove(out_png)
            if os.path.exists(tmp_dir):
                os.rmdir(tmp_dir)


# ===================================================================
# RUNNER
# ===================================================================
if __name__ == "__main__":
    unittest.main(verbosity=2)
