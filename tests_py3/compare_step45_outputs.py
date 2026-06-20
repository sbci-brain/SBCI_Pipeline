#!/usr/bin/env python3
"""
compare_step45_outputs.py
--------------------------
Compares Python 2 vs Python 3 outputs from SBCI pipeline steps 4 and 5.

Since steps 4 and 5 are fully deterministic (no random numbers), the outputs
should be IDENTICAL.  This script reports any deviations.

Usage (run from subject root on the cluster):
  python3 /path/to/SBCI_Pipeline/tests_py3/compare_step45_outputs.py \\
      --py2_dir dwi_pipeline/sbci_connectome \\
      --py3_dir dwi_pipeline/sbci_connectome_py3 \\
      --resolution 5 \\
      --bandwidth 0.1

All arguments have defaults matching typical ADNI SBCI config values.
"""

import argparse
import os
import sys
import numpy as np

try:
    import scipy.io as scio
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #

def _ok(msg):
    print(f'  ✓  {msg}')

def _warn(msg):
    print(f'  ⚠  {msg}', file=sys.stderr)

def _fail(msg):
    print(f'  ✗  {msg}', file=sys.stderr)


def compare_npz(path2, path3, label):
    """Compare two .npz files key-by-key."""
    if not os.path.exists(path2):
        _fail(f'{label}: Py2 file missing: {path2}')
        return
    if not os.path.exists(path3):
        _fail(f'{label}: Py3 file missing: {path3}')
        return

    d2 = np.load(path2, allow_pickle=True)
    d3 = np.load(path3, allow_pickle=True)

    keys2 = set(d2.keys())
    keys3 = set(d3.keys())

    if keys2 != keys3:
        _warn(f'{label}: key mismatch — Py2={sorted(keys2)}  Py3={sorted(keys3)}')
    else:
        _ok(f'{label}: keys match {sorted(keys2)}')

    for key in sorted(keys2 & keys3):
        a2 = np.asarray(d2[key])
        a3 = np.asarray(d3[key])

        if a2.shape != a3.shape:
            _fail(f'{label}[{key}]: shape Py2={a2.shape}  Py3={a3.shape}')
            continue

        if a2.dtype.kind in ('U', 'S', 'O'):
            if np.array_equal(a2, a3):
                _ok(f'{label}[{key}]: identical  shape={a2.shape}')
            else:
                _fail(f'{label}[{key}]: content differs  shape={a2.shape}')
            continue

        try:
            a2f = a2.astype(float)
            a3f = a3.astype(float)
        except (ValueError, TypeError):
            if np.array_equal(a2, a3):
                _ok(f'{label}[{key}]: identical')
            else:
                _fail(f'{label}[{key}]: differs (non-numeric)')
            continue

        max_diff = np.nanmax(np.abs(a3f - a2f))
        rel_diff = max_diff / (np.nanmean(np.abs(a2f)) + 1e-12)

        if max_diff == 0.0:
            _ok(f'{label}[{key}]: IDENTICAL  shape={a2.shape}')
        elif max_diff < 1e-6:
            _ok(f'{label}[{key}]: max_diff={max_diff:.2e}  (float precision)  shape={a2.shape}')
        elif rel_diff < 0.001:
            _warn(f'{label}[{key}]: max_diff={max_diff:.4f}  rel={rel_diff:.2e}  shape={a2.shape}')
        else:
            _fail(f'{label}[{key}]: SIGNIFICANT diff  max={max_diff:.4f}  rel={rel_diff:.2e}  shape={a2.shape}')


def compare_vtk_points(path2, path3, label):
    """Compare vertex coordinates of two .vtk files (read as text)."""
    if not os.path.exists(path2):
        _fail(f'{label}: Py2 file missing: {path2}')
        return
    if not os.path.exists(path3):
        _fail(f'{label}: Py3 file missing: {path3}')
        return

    pts2, pts3 = [], []
    for path, lst in [(path2, pts2), (path3, pts3)]:
        in_pts = False
        with open(path, 'r') as f:
            for line in f:
                stripped = line.strip()
                if 'POINTS' in stripped:
                    in_pts = True
                    continue
                if in_pts and any(k in stripped for k in ('POLYGONS', 'CELLS', 'POINT_DATA')):
                    break
                if in_pts and stripped:
                    try:
                        lst.extend([float(v) for v in stripped.split()])
                    except ValueError:
                        pass

    if len(pts2) != len(pts3):
        _fail(f'{label}: point count mismatch  Py2={len(pts2)//3}  Py3={len(pts3)//3}')
        return

    arr2 = np.array(pts2).reshape(-1, 3)
    arr3 = np.array(pts3).reshape(-1, 3)

    max_diff = np.max(np.abs(arr2 - arr3))
    if max_diff == 0.0:
        _ok(f'{label}: IDENTICAL  n_vertices={arr2.shape[0]}')
    elif max_diff < 1e-5:
        _ok(f'{label}: max_diff={max_diff:.2e}  (float precision)  n_vertices={arr2.shape[0]}')
    else:
        _fail(f'{label}: max vertex diff={max_diff:.6f}  n_vertices={arr2.shape[0]}')


def compare_mat(path2, path3, label):
    """Compare two .mat files key-by-key."""
    if not HAS_SCIPY:
        _warn(f'{label}: scipy not available, skipping .mat comparison')
        return
    if not os.path.exists(path2):
        _fail(f'{label}: Py2 file missing: {path2}')
        return
    if not os.path.exists(path3):
        _fail(f'{label}: Py3 file missing: {path3}')
        return

    m2 = scio.loadmat(path2)
    m3 = scio.loadmat(path3)

    # Filter out MATLAB metadata keys
    keys2 = {k for k in m2 if not k.startswith('_')}
    keys3 = {k for k in m3 if not k.startswith('_')}

    if keys2 != keys3:
        _warn(f'{label}: key mismatch — Py2={sorted(keys2)}  Py3={sorted(keys3)}')

    for key in sorted(keys2 & keys3):
        a2 = np.asarray(m2[key], dtype=float)
        a3 = np.asarray(m3[key], dtype=float)

        if a2.shape != a3.shape:
            _fail(f'{label}[{key}]: shape Py2={a2.shape}  Py3={a3.shape}')
            continue

        max_diff = np.nanmax(np.abs(a3 - a2))
        rel_diff = max_diff / (np.nanmean(np.abs(a2)) + 1e-12)

        if max_diff == 0.0:
            _ok(f'{label}[{key}]: IDENTICAL  shape={a2.shape}')
        elif max_diff < 1e-6:
            _ok(f'{label}[{key}]: max_diff={max_diff:.2e}  (float precision)  shape={a2.shape}')
        elif rel_diff < 0.001:
            _warn(f'{label}[{key}]: max_diff={max_diff:.4f}  rel={rel_diff:.2e}  shape={a2.shape}')
        else:
            _fail(f'{label}[{key}]: SIGNIFICANT diff  max={max_diff:.4f}  rel={rel_diff:.2e}  shape={a2.shape}')


def compare_tsv(path2, path3, label):
    """Compare two TSV files numerically."""
    if not os.path.exists(path2):
        _fail(f'{label}: Py2 file missing: {path2}')
        return
    if not os.path.exists(path3):
        _fail(f'{label}: Py3 file missing: {path3}')
        return

    with open(path2) as f:
        lines2 = f.readlines()
    with open(path3) as f:
        lines3 = f.readlines()

    if len(lines2) != len(lines3):
        _fail(f'{label}: line count Py2={len(lines2)}  Py3={len(lines3)}')
        return

    # First line is the fiber count comment "#N"
    _ok(f'{label}: line count = {len(lines2)}')

    # Parse numeric content (skip comment lines)
    nums2 = []
    nums3 = []
    for l2, l3 in zip(lines2[1:], lines3[1:]):
        try:
            nums2.append([float(v) for v in l2.strip().split()])
            nums3.append([float(v) for v in l3.strip().split()])
        except ValueError:
            pass

    if not nums2:
        return

    a2 = np.array(nums2)
    a3 = np.array(nums3)
    max_diff = np.max(np.abs(a2 - a3))
    if max_diff == 0.0:
        _ok(f'{label}: IDENTICAL')
    elif max_diff < 1e-5:
        _ok(f'{label}: max_diff={max_diff:.2e}  (float precision)')
    else:
        _fail(f'{label}: max_diff={max_diff:.6f}')


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--py2_dir', default='dwi_pipeline/sbci_connectome',
                   help='Python 2 output directory [%(default)s]')
    p.add_argument('--py3_dir', default='dwi_pipeline/sbci_connectome_py3',
                   help='Python 3 output directory [%(default)s]')
    p.add_argument('--resolution', default='5',
                   help='ICO resolution string used in filenames [%(default)s]')
    p.add_argument('--bandwidth', default='0.1',
                   help='Bandwidth string used in filenames [%(default)s]')
    args = p.parse_args()

    d2 = args.py2_dir
    d3 = args.py3_dir
    res = args.resolution
    bw  = args.bandwidth

    print(f'\n{"="*60}')
    print(f'  SBCI Steps 4 + 5  Py2 vs Py3 comparison')
    print(f'  Py2: {d2}')
    print(f'  Py3: {d3}')
    print(f'  Resolution: {res}   Bandwidth: {bw}')
    print(f'{"="*60}\n')

    # ---- Step 4 outputs (DETERMINISTIC → expect IDENTICAL) ---------- #
    print('─── Step 4: surface processing ───')
    compare_vtk_points(
        f'{d2}/lh_sphere_reg_norm.vtk',
        f'{d3}/lh_sphere_reg_norm.vtk',
        'lh_sphere_reg_norm.vtk')
    compare_vtk_points(
        f'{d2}/rh_sphere_reg_norm.vtk',
        f'{d3}/rh_sphere_reg_norm.vtk',
        'rh_sphere_reg_norm.vtk')
    compare_npz(
        f'{d2}/subject_coords.npz',
        f'{d3}/subject_coords.npz',
        'subject_coords.npz')

    # ---- Step 5 outputs (DETERMINISTIC → expect IDENTICAL) ---------- #
    print('\n─── Step 5: structural connectivity ───')
    compare_npz(
        f'{d2}/snapped_fibers.npz',
        f'{d3}/snapped_fibers.npz',
        'snapped_fibers.npz')
    compare_tsv(
        f'{d2}/subject_xing_sphere_avg_coords.tsv',
        f'{d3}/subject_xing_sphere_avg_coords.tsv',
        'subject_xing_sphere_avg_coords.tsv')
    compare_mat(
        f'{d2}/smoothed_sc_avg_{bw}_{res}.mat',
        f'{d3}/smoothed_sc_avg_{bw}_{res}.mat',
        f'smoothed_sc_avg_{bw}_{res}.mat')
    compare_mat(
        f'{d2}/sub_sc_avg_{bw}_{res}.mat',
        f'{d3}/sub_sc_avg_{bw}_{res}.mat',
        f'sub_sc_avg_{bw}_{res}.mat')
    compare_npz(
        f'{d2}/sphere_intersections.npz',
        f'{d3}/sphere_intersections.npz',
        'sphere_intersections.npz')
    compare_mat(
        f'{d2}/mesh_intersections_{res}.mat',
        f'{d3}/mesh_intersections_{res}.mat',
        f'mesh_intersections_{res}.mat')

    print(f'\n{"="*60}')
    print('  Done.  ✓=identical/close  ⚠=small diff  ✗=significant diff')
    print(f'{"="*60}\n')


if __name__ == '__main__':
    main()
