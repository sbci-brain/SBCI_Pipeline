#!/usr/bin/env python3
"""
Compare Python 2 and Python 3 SBCI Step 6 functional outputs.

Usage, from a subject root on Longleaf:
  python3 /path/to/SBCI_Pipeline/tests_py3/compare_step6_outputs.py \
      --py2_dir dwi_pipeline/sbci_connectome \
      --py3_dir dwi_pipeline/sbci_connectome_py3_step6 \
      --resolution ico4
"""

import argparse
import os
import sys

import numpy as np
import scipy.io as scio


def _ok(msg):
    print(f'  ✓  {msg}')


def _warn(msg):
    print(f'  ⚠  {msg}', file=sys.stderr)


def _fail(msg):
    print(f'  ✗  {msg}', file=sys.stderr)


def _numeric_compare(a2, a3, label, atol=1e-8, rtol=1e-6):
    if a2.shape != a3.shape:
        _fail(f'{label}: shape Py2={a2.shape}  Py3={a3.shape}')
        return

    if a2.dtype.kind in ('U', 'S', 'O') or a3.dtype.kind in ('U', 'S', 'O'):
        if np.array_equal(a2, a3):
            _ok(f'{label}: IDENTICAL  shape={a2.shape}')
        else:
            _fail(f'{label}: content differs  shape={a2.shape}')
        return

    a2 = np.asarray(a2, dtype=float)
    a3 = np.asarray(a3, dtype=float)
    diff = np.abs(a3 - a2)
    max_diff = float(np.nanmax(diff)) if diff.size else 0.0
    mean_abs = float(np.nanmean(np.abs(a2))) if a2.size else 0.0
    rel = max_diff / (mean_abs + 1e-12)

    if max_diff == 0.0:
        _ok(f'{label}: IDENTICAL  shape={a2.shape}')
    elif max_diff <= atol or rel <= rtol:
        _ok(f'{label}: max_diff={max_diff:.2e}  rel={rel:.2e}  shape={a2.shape}')
    else:
        _fail(f'{label}: SIGNIFICANT diff  max={max_diff:.4g}  rel={rel:.2e}  shape={a2.shape}')


def compare_npz(path2, path3, label):
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

    if keys2 == keys3:
        _ok(f'{label}: keys match {sorted(keys2)}')
    else:
        _fail(f'{label}: key mismatch Py2={sorted(keys2)} Py3={sorted(keys3)}')

    for key in sorted(keys2 & keys3):
        _numeric_compare(np.asarray(d2[key]), np.asarray(d3[key]), f'{label}[{key}]')


def compare_mat(path2, path3, label):
    if not os.path.exists(path2):
        _fail(f'{label}: Py2 file missing: {path2}')
        return
    if not os.path.exists(path3):
        _fail(f'{label}: Py3 file missing: {path3}')
        return

    m2 = scio.loadmat(path2)
    m3 = scio.loadmat(path3)
    keys2 = {k for k in m2 if not k.startswith('_')}
    keys3 = {k for k in m3 if not k.startswith('_')}

    if keys2 == keys3:
        _ok(f'{label}: keys match {sorted(keys2)}')
    else:
        _fail(f'{label}: key mismatch Py2={sorted(keys2)} Py3={sorted(keys3)}')

    for key in sorted(keys2 & keys3):
        _numeric_compare(np.asarray(m2[key]), np.asarray(m3[key]), f'{label}[{key}]')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--py2_dir', default='dwi_pipeline/sbci_connectome',
                        help='Python 2 output directory.')
    parser.add_argument('--py3_dir', default='dwi_pipeline/sbci_connectome_py3_step6',
                        help='Python 3 Step 6 output directory.')
    parser.add_argument('--resolution', default='ico4',
                        help='Resolution suffix used in fc_avg_<resolution>.mat.')
    args = parser.parse_args()

    print('\n' + '=' * 60)
    print('  SBCI Step 6  Py2 vs Py3 comparison')
    print(f'  Py2: {args.py2_dir}')
    print(f'  Py3: {args.py3_dir}')
    print(f'  Resolution: {args.resolution}')
    print('=' * 60 + '\n')

    for run_name in sorted(x for x in os.listdir(args.py2_dir) if x.startswith('RUN')):
        compare_npz(
            os.path.join(args.py2_dir, run_name, 'fc_ts.npz'),
            os.path.join(args.py3_dir, run_name, 'fc_ts.npz'),
            f'{run_name}/fc_ts.npz')

    compare_npz(
        os.path.join(args.py2_dir, 'fc_ts.npz'),
        os.path.join(args.py3_dir, 'fc_ts.npz'),
        'fc_ts.npz')

    compare_mat(
        os.path.join(args.py2_dir, f'fc_avg_{args.resolution}.mat'),
        os.path.join(args.py3_dir, f'fc_avg_{args.resolution}.mat'),
        f'fc_avg_{args.resolution}.mat')

    compare_mat(
        os.path.join(args.py2_dir, f'fc_avg_{args.resolution}_ts.mat'),
        os.path.join(args.py3_dir, f'fc_avg_{args.resolution}_ts.mat'),
        f'fc_avg_{args.resolution}_ts.mat')

    print('\n' + '=' * 60)
    print('  Done.')
    print('=' * 60 + '\n')


if __name__ == '__main__':
    main()
