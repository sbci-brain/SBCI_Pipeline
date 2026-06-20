#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port of SBCI_Pipeline/scripts/concon/normalise_m.py
# Changes:
#   - import string; string.join(...) → ' '.join(...)
#   - Three-pass algorithm preserved (count, read, write)

import argparse
import logging
import numpy as np
from os.path import isfile

DESCRIPTION = """
  Normalise a .m mesh file so all vertices lie on the unit sphere (radius = 1).
  Each vertex coordinate triplet is divided by its Euclidean length.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the input .m mesh file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the output normalised .m mesh file.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # Pass 1: count vertices
    n_vertices = 0
    with open(args.surface, 'r') as f:
        for line in f:
            if line.startswith('Vertex'):
                n_vertices += 1

    # Pass 2: read vertex coordinates into array
    vertices = np.zeros((n_vertices, 3), dtype=float)
    with open(args.surface, 'r') as f:
        idx = 0
        for line in f:
            if line.startswith('Vertex'):
                parts = line.strip().split()
                # format: "Vertex <id> <x> <y> <z>"
                vertices[idx, 0] = float(parts[2])
                vertices[idx, 1] = float(parts[3])
                vertices[idx, 2] = float(parts[4])
                idx += 1

    # Pass 3: write normalised output
    with open(args.surface, 'r') as infile, open(args.output, 'w') as outfile:
        v_idx = 0
        for line in infile:
            if line.startswith('Vertex'):
                parts = line.strip().split()
                vid = parts[1]
                x, y, z = vertices[v_idx]
                # Python 3 port: np.sqrt (matches original 'area = np.sqrt(...)')
                area = np.sqrt(x*x + y*y + z*z)
                if area > 0.0:
                    x, y, z = x/area, y/area, z/area
                # Python 3 port: ' '.join() replaces string.join()
                outfile.write('Vertex ' + vid + ' ' +
                              ' '.join([str(x), str(y), str(z)]) + '\n')
                v_idx += 1
            else:
                outfile.write(line)


if __name__ == "__main__":
    main()
