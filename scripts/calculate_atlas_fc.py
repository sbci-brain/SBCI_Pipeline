import argparse
import logging
import nibabel as nib
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Calculate the functional connectivity (using Pearson Correlation) for the given mapping.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', action='store', metavar='LH_TIME_SERIES', required=True,
                   type=str, help='Path of the .npz file containing functional time series.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--atlas', action='store', metavar='ATLAS', required=True,
                   type=str, help='Path to the atlas for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

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


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.time_series):
        parser.error('The file "{0}" must exist.'.format(args.time_series))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    if not isfile(args.atlas):
        parser.error('The file "{0}" must exist.'.format(args.atlas))

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

    # load atlas
    atlas = np.load(args.atlas, allow_pickle=True)
    grouping = np.concatenate((atlas['lh_labels'], atlas['rh_labels'] + 10000))
    rois = np.unique(grouping)
    rois = rois[(rois != -1) & (rois != 9999)]

    logging.info('Loading timeseries data.')

    # load time series for left and right hemispheres
    time_series_data = np.load(args.time_series)
    time_series_data = np.concatenate((time_series_data['lh_time_series'], time_series_data['rh_time_series']))

    logging.info('TS length:' + str(time_series_data.shape))
    logging.info('Calculating mean signal for ' + str(shape[0]) + ' vertices.')

    # initialise an array to fill in the loop
    mean_time_series = np.empty([shape[0], time_series_data.shape[1]], dtype=np.float64)

    # calculate mean signal at each 
    # vertice given the current mapping
    for i in range(shape[0]):
        vertex = mapping[i]
        mean_time_series[i, :] = np.mean(time_series_data[vertex, :], axis=0)

    n = len(rois)

    # initialise an array to fill in the loop
    result = np.zeros([n, n], dtype=np.float64)

    logging.info('Calculating FC.')

    # calculate fc a each given roi in the current mapping
    for i in range(n):
        logging.info('Calculating FC for ROI: {0}'.format(rois[i]))
        mask = (grouping == rois[i])
        roi_a = mean_time_series[mask, :]

        for j in range(i, n):
            if i == j:
                result[i, j] = 0
                continue

            mask = (grouping == rois[j])
            roi_b = mean_time_series[mask, :]

            result[i, j] = corr2(roi_a, roi_b)

    # save the results
    np.savez_compressed(args.output, fc=result)


if __name__ == "__main__":
    main()
