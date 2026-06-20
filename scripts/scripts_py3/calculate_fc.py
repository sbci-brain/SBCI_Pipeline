#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port:
#   - xrange() → range()
#   - (n * (n+1)) / 2  →  (n * (n+1)) // 2  (integer division for array size)
#   - labels iteration: np.load returns arrays; handle None sentinel

import argparse
import logging
import nibabel as nib
import numpy as np
import scipy.io as scio

from os.path import isfile, splitext

DESCRIPTION = """
  Calculate the functional connectivity (using Pearson Correlation) for the given mapping.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', action='store', metavar='TIME_SERIES', required=True,
                   type=str, help='Path of the .npz file containing functional time series.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--ts', action='store_true', dest='ts',
                   help='If set, also save mean BOLD signal to file.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# calculate the 2D (vector) Pearson correlation
def corr2(X, Y):
    X_mX = X - X.mean(axis=1).reshape((-1, 1))
    Y_mY = Y - Y.mean(axis=1).reshape((-1, 1))

    ssX = (X_mX**2).sum(axis=1).reshape((-1, 1))
    ssY = (Y_mY**2).sum(axis=1).reshape((1, -1))

    return np.dot(X_mX, Y_mY.T) / np.sqrt(np.dot(ssX, ssY))


def _npz_key(label):
    if isinstance(label, bytes):
        return label.decode('utf-8')
    if isinstance(label, np.bytes_):
        return label.astype(str).item()
    return str(label)


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.time_series):
        parser.error('The file "{0}" must exist.'.format(args.time_series))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    if args.ts:
        ts_output = splitext(args.output)[0] + '_ts.mat'

        if isfile(ts_output):
            if args.overwrite:
                logging.info('Overwriting "{0}".'.format(ts_output))
            else:
                parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(ts_output))

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)

    mapping = mesh['mapping']
    shape = mesh['shape']

    logging.info('Loading timeseries data.')

    # load time series for left and right hemispheres
    full_time_series_data = np.load(args.time_series, allow_pickle=True)
    time_series_data = np.concatenate((full_time_series_data['lh_time_series'],
                                       full_time_series_data['rh_time_series']))

    logging.info('TS length: ' + str(time_series_data.shape))
    logging.info('Calculating mean signal for ' + str(shape[0]) + ' vertices.')

    # initialise an array to fill in the loop
    mean_time_series = np.empty([shape[0], time_series_data.shape[1]], dtype=np.float64)

    # calculate mean signal at each vertex given the current mapping
    for i in range(shape[0]):
        vertex = mapping[i]
        mean_time_series[i, :] = np.mean(time_series_data[vertex, :], axis=0)

    logging.info('Calculating FC.')

    n = shape[0]
    # Python 3 port: integer division // for array size
    fc = np.ones((n * (n+1)) // 2)
    index = 0

    # calculate the FC using an upper triangular indexing scheme
    # Python 3 port: xrange() → range()
    for i in range(n-1):
        index += 1
        offset = n - i

        # calculate the correlation between the current vertex and all the vertices that come after it
        fc[index:(index+offset-1)] = corr2(mean_time_series[i:(i+1), :],
                                           mean_time_series[(i+1):, :]).ravel()

        # used for upper triangular indices
        index += offset-1

    result = np.zeros((n, n))
    result[np.triu_indices(n)] = fc

    # replace all nans with 0s
    result = np.nan_to_num(result)

    sub_sub_fc = None
    sub_surf_fc = None

    # Python 3: np.load with allow_pickle may return numpy array wrapping None
    raw_labels = full_time_series_data['subcortical_labels']
    # unwrap scalar object array (allow_pickle=True artefact)
    if raw_labels.ndim == 0:
        labels = raw_labels.item()
    else:
        labels = raw_labels

    # calculate subcortical FC
    if labels is not None and len(labels) > 0:
        logging.info('Calculating FC for subcortical regions.')

        n_sub = len(labels)
        sub_mean_time_series = np.empty([n_sub, time_series_data.shape[1]], dtype=np.float64)

        for i in range(n_sub):
            sub_mean_time_series[i, :] = np.mean(full_time_series_data[_npz_key(labels[i])], axis=0)

        # Python 3 port: integer division //
        fc_sub = np.ones((n_sub * (n_sub+1)) // 2)
        index = 0

        # Python 3 port: xrange() → range()
        for i in range(n_sub-1):
            index += 1
            offset = n_sub - i

            fc_sub[index:(index+offset-1)] = corr2(sub_mean_time_series[i:(i+1), :],
                                                    sub_mean_time_series[(i+1):, :]).ravel()
            index += offset-1

        sub_sub_fc = np.zeros((n_sub, n_sub))
        sub_sub_fc[np.triu_indices(n_sub)] = fc_sub

        # replace all nans with 0s
        sub_sub_fc = np.nan_to_num(sub_sub_fc)

        # calculate the cortico-subcortical FC
        sub_surf_fc = np.ones((n_sub, shape[0]))

        for i in range(n_sub):
            sub_surf_fc[i, :] = corr2(sub_mean_time_series[i:(i+1), :],
                                      mean_time_series[:, :]).ravel()

        # replace all nans with 0s
        sub_surf_fc = np.nan_to_num(sub_surf_fc)

    # save the results
    if labels is not None and len(labels) > 0:
        scio.savemat(args.output, {'fc': result,
                                   'sub_sub_fc': sub_sub_fc,
                                   'sub_surf_fc': sub_surf_fc})
        if args.ts:
            scio.savemat(ts_output, {'cortical_ts': mean_time_series,
                                     'subcortical_ts': sub_mean_time_series})
    else:
        scio.savemat(args.output, {'fc': result})
        if args.ts:
            scio.savemat(ts_output, {'cortical_ts': mean_time_series})


if __name__ == "__main__":
    main()
