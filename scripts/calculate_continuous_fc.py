import argparse
import logging
import nibabel as nib
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Calculate the continuous functional connectivity (using Pearson Correlation) for the given mapping.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', action='store', metavar='LH_TIME_SERIES', required=True,
                   type=str, help='Path of the .npz file containing functional time series.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


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

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    mapping = mesh['mapping']
    shape = mesh['shape']

    # load time series for left and right hemispheres
    logging.info('Loading timeseries data.')

    time_series_data = np.load(args.time_series)
    time_series_data = np.concatenate((time_series_data['lh_time_series'], time_series_data['rh_time_series']))

    logging.info('TS length:' + str(time_series_data.shape))
    logging.info('Calculating signal for ' + str(shape[0]) + ' vertices.')

    # initialise an array to fill in the loop
    result = np.zeros([shape[0], shape[0]], dtype=np.float64)

    logging.info('Calculating FC.')

    # calculate continuous fc a each given roi in the current mapping
    for i in range(shape[0]):
        roi_a = time_series_data[mapping[i], :]
        roi_a = roi_a[~np.all(roi_a == 0, axis=1)]

        X_mX = roi_a - roi_a.mean(axis=1).reshape((-1, 1))
        ssX = (X_mX**2).sum(axis=1).reshape((-1, 1))
        
        for j in range(i, shape[0]):
            if i == j:
                result[i, j] = 0
                continue

            roi_b = time_series_data[mapping[j], :]
            roi_b = roi_b[~np.all(roi_b == 0, axis=1)]

            Y_mY = roi_b - roi_b.mean(axis=1).reshape((-1, 1))
            ssY = (Y_mY**2).sum(axis=1).reshape((1, -1))

            corr = np.dot(X_mX, Y_mY.T) / np.sqrt(np.dot(ssX, ssY))

            # in the unlikely case of perfect correlation, atanh is not defined
            clipped_cor = corr.clip(-1+1e-12,1-1e-12)

            result[i, j] = np.tanh(np.mean(np.arctanh(clipped_cor)))

    # save the results
    np.savez_compressed(args.output, fc=result)


if __name__ == "__main__":
    main()
