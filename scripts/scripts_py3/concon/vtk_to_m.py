#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port of SBCI_Pipeline/scripts/concon/vtk_to_m.py
# Changes:
#   - import string; string.join(...) → ' '.join(...)

import argparse
import logging
from os.path import isfile

DESCRIPTION = """
  Convert a .vtk mesh file to a .m mesh file (Matlab/concon format).
  Vertices are written as "Vertex <id> <x> <y> <z>"
  Faces   are written as "Face   <id> <v0+1> <v1+1> <v2+1>"
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the input .vtk mesh file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the output .m mesh file.')

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

    section = 0   # 0 = header, 1 = POINTS, 2 = POLYGONS
    vertex_id = 1
    face_id   = 1

    with open(args.surface, 'r') as infile, open(args.output, 'w') as outfile:
        for line in infile:
            stripped = line.strip()

            if 'POINTS' in stripped and section == 0:
                section = 1
                continue
            elif section == 1 and ('POLYGONS' in stripped or 'CELLS' in stripped):
                section = 2
                continue
            elif section >= 2 and stripped.startswith('3 '):
                # polygon / cell entry
                pass

            if section == 1 and stripped:
                tokens = stripped.split()
                try:
                    coords = [float(t) for t in tokens]
                except ValueError:
                    continue

                # write one Vertex line per triplet
                for j in range(0, len(coords), 3):
                    chunk = coords[j:j+3]
                    if len(chunk) == 3:
                        # Python 3 port: ' '.join() replaces string.join()
                        outfile.write('Vertex ' + str(vertex_id) + ' ' +
                                      ' '.join(str(v) for v in chunk) + '\n')
                        vertex_id += 1

            elif section == 2 and stripped:
                tokens = stripped.split()
                try:
                    indices = [int(t) for t in tokens]
                except ValueError:
                    continue

                # POLYGONS line starts with count, then groups of (n, v0, v1, v2, ...)
                # VTK legacy: each cell is "3 v0 v1 v2"
                if len(tokens) == 4 and int(tokens[0]) == 3:
                    v0, v1, v2 = indices[1]+1, indices[2]+1, indices[3]+1
                    # Python 3 port: ' '.join() replaces string.join()
                    outfile.write('Face ' + str(face_id) + ' ' +
                                  ' '.join([str(v0), str(v1), str(v2)]) + '\n')
                    face_id += 1
                elif len(tokens) > 1:
                    # POLYGONS header: "POLYGONS n_faces n_total"
                    # or cell-array header — skip
                    pass


if __name__ == "__main__":
    main()
