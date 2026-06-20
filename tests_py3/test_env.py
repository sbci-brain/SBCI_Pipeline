#!/usr/bin/env python3
"""
Quick import check — run this first to verify the Python environment
is set up correctly before submitting any cluster jobs.

Usage:
    python3 tests_py3/test_env.py
"""

import sys
import importlib

REQUIRED = [
    ("numpy",                   "numpy"),
    ("scipy",                   "scipy"),
    ("nibabel",                 "nibabel"),
    ("dipy",                    "dipy"),
    ("vtk",                     "vtk"),
    ("trimeshpy",               "trimeshpy"),
    ("trimeshpy.io",            "trimeshpy.io"),
    ("trimeshpy.vtk_util",      "trimeshpy.vtk_util"),
    ("scilpy.io.utils",         "scilpy.io.utils"),
    ("scilpy.io.image",         "scilpy.io.image"),
    ("scilpy.tracking.utils",   "scilpy.tracking.utils"),
    ("dipy.tracking.local_tracking",   "dipy.tracking.local_tracking"),
    ("dipy.tracking.streamlinespeed",  "dipy.tracking.streamlinespeed"),
    ("dipy.tracking.streamline",       "dipy.tracking.streamline"),
    ("dipy.tracking.metrics",          "dipy.tracking.metrics"),
    ("dipy.direction",                 "dipy.direction"),
]

SPECIFIC_NAMES = [
    ("trimeshpy.io",          "load_mesh_from_file"),
    ("scilpy.io.utils",       "assert_inputs_exist"),
    ("scilpy.io.utils",       "assert_outputs_exist"),
    ("scilpy.io.utils",       "add_overwrite_arg"),
    ("scilpy.io.image",       "get_data_as_mask"),
    ("scilpy.tracking.utils", "get_theta"),
    ("dipy.tracking.streamlinespeed", "length"),
    ("dipy.tracking.streamlinespeed", "compress_streamlines"),
    ("dipy.tracking.streamline",      "set_number_of_points"),
]

def check_imports():
    print(f"Python {sys.version}\n")
    all_ok = True

    print("=== Package imports ===")
    for label, module in REQUIRED:
        try:
            importlib.import_module(module)
            print(f"  OK  {label}")
        except ImportError as e:
            print(f"  FAIL  {label}: {e}")
            all_ok = False

    print("\n=== Specific names ===")
    for module, name in SPECIFIC_NAMES:
        try:
            mod = importlib.import_module(module)
            getattr(mod, name)
            print(f"  OK  {module}.{name}")
        except ImportError as e:
            print(f"  FAIL  {module}.{name}: import error: {e}")
            all_ok = False
        except AttributeError:
            print(f"  FAIL  {module}.{name}: name not found in module")
            all_ok = False

    print()
    if all_ok:
        print("All checks passed.")
    else:
        print("Some checks failed — fix the environment before running scripts.")
        sys.exit(1)

if __name__ == "__main__":
    check_imports()
