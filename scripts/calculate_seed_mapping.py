import argparse
import logging
import numpy as np
import scipy.sparse as sparse

from os.path import isfile

DESCRIPTION = """
  Calculate the correlation between functional and structural connectivity (using Pearson Correlation) for the given mapping.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--seed_id', action='store', metavar='SEED_ID', required=True,
                   type=int, help='ID for the region to use as a seed.')

    p.add_argument('--hemisphere', action='store', metavar='SEED_ID', required=True,
                   type=int, help='Hemisphere the roi is located on (0 = left, 1 = right).')

    p.add_argument('--time_series', action='store', metavar='TIME_SERIES', required=True,
                   type=str, help='Path of the file containing functional timeseries data.')

    p.add_argument('--sc_matrix', action='store', metavar='SC_MATRIX', required=True,
                   type=str, help='Path of the file containing structural connectivity matrix.')

    p.add_argument('--roi', action='store', metavar='ROI', required=True,
                   type=str, help='Path of the file containing roi vertex ids.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

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
        parser.error('The file "{0}" must exist.'.format(args.fc_matrix))

    if not isfile(args.roi):
        parser.error('The file "{0}" must exist.'.format(args.roi))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    if not (args.hemisphere == 0) or (args.hemisphere == 1):
        parser.error('The hemisphere must be 0=left or 1=right.')

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
    n = shape[0]

    # load regions
    roi = np.load(args.roi, allow_pickle=True)

    lh_labels = roi['lh_labels']
    rh_labels = roi['rh_labels']

    if args.hemisphere == 0:
        rh_labels[:] = 30000
    else:
        lh_labels[:] = 30000

    labels = np.concatenate([lh_labels, rh_labels])

    # TODO: use names instead of IDs, so LH_ or RH_ name
    #lh_names=np.array(lh_annot[2])
    #rh_names=np.array(rh_annot[2])

    # load the FC matrix timeseries data (need to calculate fc again based on seed)
    time_series = np.load(args.time_series)
    lh_timeseries = time_series['lh_time_series']
    rh_timeseries = time_series['rh_time_series']

    time_series_data = np.concatenate([lh_timeseries, rh_timeseries])

    logging.info('Calculating mean signal for ' + str(shape[0]) + ' vertices.')

    mean_time_series = np.empty([shape[0], time_series_data.shape[1]], dtype=np.float64)
    seed_time_series = np.empty([1, time_series_data.shape[1]], dtype=np.float64)

    # calculate mean signal for each resampled vertex
    for i in range(shape[0]):
        vertex = np.array(mapping[i])
        mean_time_series[i, :] = np.mean(time_series_data[vertex, :], axis=0)

    region_mask = np.array(range(shape[0]))
    region_mask = region_mask[labels == args.seed_id]

    # calculate mean for the region of interest
    region_mapping = np.concatenate(mapping[region_mask])
    seed_time_series[0, :] = np.mean(time_series_data[region_mapping, :], axis=0)

    logging.info('Calculating FC strength.')

    mask = (labels == args.seed_id)
    fc_mapping = np.zeros(n, dtype=np.float64)
    fc_mapping[mask] = 1

    for i in range(shape[0]):
        if not fc_mapping[i] == 1:
            fc_mapping[i] = np.corrcoef(seed_time_series[0, :], mean_time_series[i, :])[0,1]
            
        if np.isnan(fc_mapping[i]):
            fc_mapping[i] = -2

    logging.info('Calculating SC strength.')

    # load the SC matrix (sc is caluclated by summing rows)
    sc_matrix = np.array(sparse.load_npz(args.sc_matrix).todense())
    sc_mapping = np.sum(sc_matrix[mask, :], axis=0)

    if np.any(sc_mapping[mask]):
        sc_mapping[mask] = 1

    # save the results
    np.savez_compressed(args.output, fc_mapping=fc_mapping, sc_mapping=sc_mapping)


if __name__ == "__main__":
    main()
