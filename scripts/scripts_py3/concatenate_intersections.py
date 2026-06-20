#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Replacement for scil_concatenate_surfaces_intersections.py (Python 2 scilpy command).
# Concatenates multiple SET intersection .npz files into a single output .npz file.
#
# Usage:
#   python3 concatenate_intersections.py file1.npz file2.npz ... \
#           --output_intersections combined.npz -f

import argparse
import logging
import numpy as np
from os.path import isfile

DESCRIPTION = """
  Concatenate multiple surface intersection .npz files into one.
  Replaces scil_concatenate_surfaces_intersections.py from scilpy 1.x.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('input_intersections', nargs='+',
                   type=str, help='Input intersection .npz files to concatenate.')

    p.add_argument('--output_intersections', required=True,
                   type=str, help='Output concatenated intersection .npz file.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    for f in args.input_intersections:
        if not isfile(f):
            parser.error('The file "{0}" must exist.'.format(f))

    if isfile(args.output_intersections):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output_intersections))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(
                args.output_intersections))

    # Collect arrays from all files
    combined = {}

    for fname in args.input_intersections:
        logging.info('Loading: {0}'.format(fname))
        data = np.load(fname, allow_pickle=True)

        for key in data.keys():
            arr = data[key]
            if key in combined:
                combined[key] = np.concatenate([combined[key], arr], axis=0)
            else:
                combined[key] = arr.copy()

    n_total = len(next(iter(combined.values())))
    logging.info('Total intersections: {0}'.format(n_total))

    np.savez_compressed(args.output_intersections, **combined)
    logging.info('Saved → {0}'.format(args.output_intersections))


if __name__ == "__main__":
    main()
