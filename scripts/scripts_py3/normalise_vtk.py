#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port of SBCI_Pipeline/scripts/normalise_vtk.py
# Changes:
#   - import string; string.join(...) → ' '.join(...)
#   - np.float / np.str removed aliases → float / str
#   - Added shebang and encoding declaration

import argparse
import logging
import numpy as np
from os.path import isfile

DESCRIPTION = """
  Normalise a VTK surface mesh so all vertices lie on the unit sphere (radius = 1).
  Each vertex coordinate triplet is divided by its Euclidean length.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the input .vtk mesh file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the output normalised .vtk mesh file.')

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

    section = 0   # 0 = header, 1 = POINTS, 2 = past POINTS

    with open(args.surface, 'r') as infile, open(args.output, 'w') as outfile:
        for line in infile:
            stripped = line.strip()

            # Detect section transitions
            if 'POINTS' in stripped and section == 0:
                section = 1
                outfile.write(line)
                continue
            elif section == 1 and any(kw in stripped for kw in
                                      ('POLYGONS', 'CELLS', 'CELL_TYPES',
                                       'POINT_DATA', 'CELL_DATA', 'LINES')):
                section = 2
                outfile.write(line)
                continue

            if section == 1 and stripped:
                # Parse coordinate tokens — VTK writers may put 1 or 3 triplets per line
                tokens = stripped.split()
                try:
                    coords = [float(t) for t in tokens]
                except ValueError:
                    # Non-numeric line (shouldn't happen in POINTS section, but pass through)
                    outfile.write(line)
                    continue

                # Normalise each triplet to unit length
                result = []
                for j in range(0, len(coords), 3):
                    chunk = coords[j:j+3]
                    if len(chunk) == 3:
                        x, y, z = chunk
                        # Python 3 port: np.sqrt used in original (area = np.sqrt(...))
                        area = np.sqrt(x*x + y*y + z*z)
                        if area > 0.0:
                            x, y, z = x/area, y/area, z/area
                        result.extend([x, y, z])
                    else:
                        result.extend(chunk)

                # Python 3 port: string.join() → ' '.join()
                outfile.write(' '.join(str(v) for v in result) + '\n')
            else:
                outfile.write(line)


if __name__ == "__main__":
    main()
