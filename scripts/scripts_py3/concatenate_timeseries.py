#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port:
#   - dict.has_key(key) → key in dict (removed in Python 3)

import argparse
import logging
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Normalise and concatenate BOLD time series data from multiple runs.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', nargs='+', metavar='TIME_SERIES', required=True,
                   type=str, help='Paths of .npz files containing time series to concatenate.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the concatenated output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    for ts_file in args.time_series:
        if not isfile(ts_file):
            parser.error('The file "{0}" must exist.'.format(ts_file))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    combined = dict()

    for ts_file in args.time_series:
        logging.info('Processing: {0}'.format(ts_file))
        data = np.load(ts_file, allow_pickle=True)

        for key in data.keys():
            # Don't normalise the subcortical labels key
            if key == 'subcortical_labels':
                # Python 3 port: has_key() → key in dict (removed in Python 3)
                if key not in combined:
                    combined[key] = data[key]
                continue

            arr = data[key]

            # z-score normalise each run's data
            mean = np.mean(arr, axis=1, keepdims=True)
            std  = np.std(arr,  axis=1, keepdims=True)
            normalised = np.nan_to_num((arr - mean) / std)

            # Python 3 port: has_key() → key in dict
            if key not in combined:
                combined[key] = normalised
            else:
                combined[key] = np.concatenate([combined[key], normalised], axis=1)

    # save results
    np.savez_compressed(args.output, **combined)
    logging.info('Saved concatenated timeseries → {0}'.format(args.output))


if __name__ == "__main__":
    main()
