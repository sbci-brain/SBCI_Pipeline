#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port of SBCI_Pipeline/scripts/concon/convert_raw.py
# Converts binary kernel output from c3_main (concon) into scipy sparse + MATLAB formats.
#
# The c3_main binary writes a sequence of records: each record is a pair of
# (row, col) 32-bit integers followed by a 64-bit float lambda value.
# The script reads them, assembles an N×N kernel matrix (block-swapping
# hemispheres), and saves as .mat / sparse .npz.

import argparse
import logging
import numpy as np
import scipy.io as scio

from scipy import sparse
from os.path import getsize, isfile, splitext

DESCRIPTION = """
  Convert raw binary kernel output from c3_main (concon) to .mat / .npz format.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--input', action='store', metavar='INPUT', required=True,
                   type=str, help='Path of the raw binary kernel .raw file from c3_main.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of snapped intersections.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path of the mesh mapping .npz file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Output path prefix (without extension). '
                                  'Produces <output>.mat and <output>.npz.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # ---- Input validation ------------------------------------------------
    for fname in [args.input, args.intersections, args.mesh]:
        if not isfile(fname):
            parser.error('The file "{0}" must exist.'.format(fname))

    root, ext = splitext(args.output)
    if ext == '.mat':
        mat_output = args.output
        npz_output = root + '.npz'
    else:
        mat_output = args.output + '.mat'
        npz_output = args.output + '.npz'

    for fname in [mat_output, npz_output]:
        if isfile(fname):
            if args.overwrite:
                logging.info('Overwriting "{0}".'.format(fname))
            else:
                parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(fname))

    # ---- Load mesh shape --------------------------------------------------
    mesh = np.load(args.mesh, allow_pickle=True)
    shape = mesh['shape']
    mesh_n = int(shape[0])            # total vertices (LH + RH)
    lh_n = int(shape[1])              # LH vertices
    rh_n = int(shape[2])              # RH vertices

    logging.info('Mesh shape: N={0}, LH={1}, RH={2}'.format(mesh_n, lh_n, rh_n))

    # ---- Read binary kernel data -----------------------------------------
    # dtype: two 32-bit signed ints (x, y) + one 64-bit float (lambda)
    record_dtype = np.dtype([('x', np.int32), ('y', np.int32), ('lam', np.float64)])

    logging.info('Reading binary kernel data from: {0}'.format(args.input))
    with open(args.input, 'rb') as raw_file:
        header = np.fromfile(raw_file, dtype=np.int32, count=1)
        if header.size != 1:
            parser.error('The raw file "{0}" is missing its int32 matrix-size header.'.format(args.input))
        N = int(header[0])
        records = np.fromfile(raw_file, dtype=record_dtype)

    if N != mesh_n:
        parser.error('Raw matrix size N={0} differs from mesh N={1}.'.format(N, mesh_n))

    expected_bytes = 4 + len(records) * record_dtype.itemsize
    actual_bytes = getsize(args.input)
    if expected_bytes != actual_bytes:
        parser.error('Raw file "{0}" has trailing or partial bytes.'.format(args.input))

    logging.info('{0} kernel entries read.'.format(len(records)))

    rows = records['x'].astype(np.int64)
    cols = records['y'].astype(np.int64)
    vals = records['lam']

    # ---- Build dense kernel matrix (concon indices are 0-based) ----------
    # The .raw file stores the FULL symmetric matrix — both (i,j) and (j,i)
    # entries are present for every non-zero pair.  Do NOT symmetrise:
    # adding kernel.T would double all off-diagonal values.
    kernel = np.zeros((N, N), dtype=np.float64)
    valid = (rows >= 0) & (cols >= 0) & (rows < N) & (cols < N)
    kernel[rows[valid], cols[valid]] = vals[valid]

    # Left and right hemispheres are swapped in concon, so swap them back.
    A = kernel[0:rh_n, 0:rh_n].copy()
    B = kernel[rh_n:, rh_n:].copy()
    C = kernel[rh_n:, 0:rh_n].copy()
    D = kernel[0:rh_n, rh_n:].copy()

    kernel[0:lh_n, 0:lh_n] = B
    kernel[lh_n:, lh_n:] = A
    kernel[lh_n:, 0:lh_n] = D
    kernel[0:lh_n, lh_n:] = C

    # ---- Save results ----------------------------------------------------
    sc_sparse = sparse.csr_matrix(kernel)

    logging.info('Saving kernel matrix → {0}'.format(mat_output))
    scio.savemat(mat_output, {'sc': np.triu(kernel)})

    logging.info('Saving sparse kernel matrix → {0}'.format(npz_output))
    sparse.save_npz(npz_output, sc_sparse)


if __name__ == "__main__":
    main()
