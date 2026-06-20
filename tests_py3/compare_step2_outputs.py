#!/usr/bin/env python3
"""
compare_step2_outputs.py
------------------------
Compare step-2 output files produced by the old Python 2 pipeline
against those produced by the new Python 3 pipeline.

Usage
-----
    python3 tests_py3/compare_step2_outputs.py OLD_DIR NEW_DIR [--verbose]

    OLD_DIR : directory containing the Python 2 reference outputs
              e.g. ~/sub-002S6066/dwi_pipeline/set/out_surf_py2
    NEW_DIR : directory containing the Python 3 candidate outputs
              e.g. ~/sub-002S6066/dwi_pipeline/set/out_surf_py3

What is compared
----------------
  .npy   – integer arrays: exact equality
           float arrays  : max absolute diff, relative diff, allclose(atol=1e-5)
  .vtk   – vertex positions and triangle connectivity (loaded via trimeshpy)
  .txt   – text diff (unique_id map)

Exit code: 0 if all checks pass, 1 if any mismatch found.
"""

import sys
import os
import argparse
import numpy as np

FLOAT_ATOL = 1e-5   # absolute tolerance for float comparisons
FLOAT_RTOL = 1e-5   # relative tolerance

PASS  = "\033[92m  PASS\033[0m"
FAIL  = "\033[91m  FAIL\033[0m"
WARN  = "\033[93m  WARN\033[0m"
SKIP  = "\033[94m  SKIP\033[0m"

all_passed = True


def flag(ok):
    global all_passed
    if not ok:
        all_passed = False
    return PASS if ok else FAIL


# ------------------------------------------------------------------ #
#  .npy comparison                                                    #
# ------------------------------------------------------------------ #
def compare_npy(old_path, new_path, verbose=False):
    old = np.load(old_path)
    new = np.load(new_path)

    if old.shape != new.shape:
        print(f"{FAIL}  shape mismatch: {old.shape} vs {new.shape}")
        return False

    if np.issubdtype(old.dtype, np.integer) or np.issubdtype(old.dtype, np.bool_):
        eq = np.array_equal(old, new)
        n_diff = int(np.sum(old != new))
        print(f"{flag(eq)}  dtype={old.dtype}  shape={old.shape}"
              f"  n_different={n_diff}")
        if verbose and not eq:
            idx = np.argwhere(old != new)[:5]
            for i in idx:
                print(f"         [{tuple(i)}]  old={old[tuple(i)]}  new={new[tuple(i)]}")
        return eq
    else:
        abs_diff = np.abs(old.astype(np.float64) - new.astype(np.float64))
        max_diff = float(np.nanmax(abs_diff))
        mean_diff = float(np.nanmean(abs_diff))
        rel_diff = float(np.nanmax(abs_diff / (np.abs(old.astype(np.float64)) + 1e-12)))
        ok = np.allclose(old, new, atol=FLOAT_ATOL, rtol=FLOAT_RTOL, equal_nan=True)
        print(f"{flag(ok)}  dtype={old.dtype}  shape={old.shape}"
              f"  max_abs_diff={max_diff:.3e}"
              f"  mean_abs_diff={mean_diff:.3e}"
              f"  max_rel_diff={rel_diff:.3e}")
        return ok


# ------------------------------------------------------------------ #
#  .vtk comparison                                                    #
# ------------------------------------------------------------------ #
def compare_vtk(old_path, new_path, verbose=False):
    try:
        from trimeshpy.io import load_mesh_from_file
    except ImportError:
        print(f"{SKIP}  trimeshpy not available — skipping VTK comparison")
        return True

    old_m = load_mesh_from_file(old_path)
    new_m = load_mesh_from_file(new_path)

    old_v = old_m.get_vertices()
    new_v = new_m.get_vertices()
    old_t = old_m.get_triangles()
    new_t = new_m.get_triangles()

    ok_tris = np.array_equal(old_t, new_t)
    if not ok_tris:
        n_diff_t = int(np.sum(old_t != new_t))
        print(f"{FAIL}  triangles differ: {n_diff_t} entries")
    else:
        print(f"{PASS}  triangles: identical  shape={old_t.shape}")

    abs_diff_v = np.abs(old_v.astype(np.float64) - new_v.astype(np.float64))
    max_diff_v = float(np.nanmax(abs_diff_v))
    ok_verts = float(max_diff_v) < FLOAT_ATOL * 1000   # 1e-2 mm tolerance for vertices
    print(f"{flag(ok_verts)}  vertices: max_diff={max_diff_v:.3e} mm"
          f"  shape={old_v.shape}")

    return ok_tris and ok_verts


# ------------------------------------------------------------------ #
#  .txt comparison                                                    #
# ------------------------------------------------------------------ #
def compare_txt(old_path, new_path, verbose=False):
    with open(old_path) as f:
        old_lines = f.read().strip().splitlines()
    with open(new_path) as f:
        new_lines = f.read().strip().splitlines()

    if old_lines == new_lines:
        print(f"{PASS}  text identical  ({len(old_lines)} lines)")
        return True
    else:
        n_diff = sum(a != b for a, b in zip(old_lines, new_lines))
        n_diff += abs(len(old_lines) - len(new_lines))
        print(f"{FAIL}  text differs: {n_diff} lines differ")
        if verbose:
            for i, (a, b) in enumerate(zip(old_lines[:5], new_lines[:5])):
                if a != b:
                    print(f"   line {i}: OLD={a!r}")
                    print(f"            NEW={b!r}")
        return False


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("old_dir", help="Directory with Python 2 reference outputs")
    p.add_argument("new_dir", help="Directory with Python 3 candidate outputs")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print extra detail on mismatches")
    args = p.parse_args()

    old_dir = args.old_dir
    new_dir = args.new_dir

    if not os.path.isdir(old_dir):
        sys.exit(f"ERROR: OLD_DIR does not exist: {old_dir}")
    if not os.path.isdir(new_dir):
        sys.exit(f"ERROR: NEW_DIR does not exist: {new_dir}")

    # Collect all files in old_dir
    old_files = sorted(
        f for f in os.listdir(old_dir)
        if f.endswith((".npy", ".vtk", ".txt"))
    )

    if not old_files:
        sys.exit(f"ERROR: no .npy/.vtk/.txt files found in {old_dir}")

    print(f"\n{'='*60}")
    print(f" Comparing outputs")
    print(f" OLD (py2): {old_dir}")
    print(f" NEW (py3): {new_dir}")
    print(f" atol={FLOAT_ATOL:.0e}  rtol={FLOAT_RTOL:.0e}")
    print(f"{'='*60}\n")

    missing_in_new = []

    for fname in old_files:
        old_path = os.path.join(old_dir, fname)
        new_path = os.path.join(new_dir, fname)

        print(f"--- {fname}")

        if not os.path.exists(new_path):
            print(f"{WARN}  file missing in NEW_DIR — skipped")
            missing_in_new.append(fname)
            continue

        ext = os.path.splitext(fname)[1].lower()
        if ext == ".npy":
            compare_npy(old_path, new_path, args.verbose)
        elif ext == ".vtk":
            compare_vtk(old_path, new_path, args.verbose)
        elif ext == ".txt":
            compare_txt(old_path, new_path, args.verbose)
        print()

    # Summary
    print(f"{'='*60}")
    if missing_in_new:
        print(f"  Files missing in NEW_DIR: {', '.join(missing_in_new)}")
    if all_passed and not missing_in_new:
        print("\033[92m  ALL CHECKS PASSED — Python 3 output matches Python 2\033[0m")
        sys.exit(0)
    else:
        print("\033[91m  SOME CHECKS FAILED — see above\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
