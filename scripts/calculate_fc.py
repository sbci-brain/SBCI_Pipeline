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
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

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

    if args.ts == True:
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
    full_time_series_data = np.load(args.time_series)
    time_series_data = np.concatenate((full_time_series_data['lh_time_series'], 
                                       full_time_series_data['rh_time_series']))

    logging.info('TS length:' + str(time_series_data.shape))
    logging.info('Calculating mean signal for ' + str(shape[0]) + ' vertices.')

    # initialise an array to fill in the loop
    mean_time_series = np.empty([shape[0], time_series_data.shape[1]], dtype=np.float64)

    # calculate mean signal at each 
    # vertice given the current mapping
    for i in range(shape[0]):
        vertex = mapping[i]
        mean_time_series[i, :] = np.mean(time_series_data[vertex, :], axis=0)

    logging.info('Calculating FC.')

    n = shape[0]
    fc = np.ones(((n * (n+1)) / 2))
    index = 0

    # calculate the FC using an upper triangular indexing scheme
    for i in xrange(n-1):
        index += 1
        offset = n - i

        # calculate the correlation between the current vertex all the vertices in the vector that come after it
        fc[index:(index+offset-1)] = corr2(mean_time_series[i:(i+1), :], mean_time_series[(i+1):, :]).ravel()

        # used for upper triangular indices
        index += offset-1

    result = np.zeros((n,n))
    result[np.triu_indices(n)] = fc

    # replace all nans with 0s
    result = np.nan_to_num(result)

    sub_sub_fc = None
    sub_surf_fc = None

    labels = full_time_series_data['subcortical_labels']

    # calculate subcortical FC
    if not labels is None:
        logging.info('Calculating FC for subcortical regions.')
         
        n = len(labels)
        sub_mean_time_series = np.empty([n, time_series_data.shape[1]], dtype=np.float64)
        
        for i in range(n):
            sub_mean_time_series[i,:] = np.mean(full_time_series_data[labels[i]], axis=0)
   
        fc = np.ones(((n * (n+1)) / 2))
        index = 0

        # calculate the subcortico-subcortical FC using an upper triangular indexing scheme
        for i in xrange(n-1):
            index += 1
            offset = n - i

            fc[index:(index+offset-1)] = corr2(sub_mean_time_series[i:(i+1), :], 
                                               sub_mean_time_series[(i+1):, :]).ravel()

            # used for upper triangular indices
            index += offset-1

        sub_sub_fc = np.zeros((n,n))
        sub_sub_fc[np.triu_indices(n)] = fc

        # replace all nans with 0s
        sub_sub_fc = np.nan_to_num(sub_sub_fc)

        # calculate the cortico-subcortical FC
        sub_surf_fc = np.ones((n, shape[0]))

        # calculate the subcortico-subcortical FC using an upper triangular indexing scheme
        for i in range(n):
            sub_surf_fc[i,:] = corr2(sub_mean_time_series[i:(i+1), :], mean_time_series[:,:]).ravel()

        # replace all nans with 0s
        sub_surf_fc = np.nan_to_num(sub_surf_fc)

    # save the results
    if not labels is None:
        scio.savemat(args.output, {'fc': result, 
                                   'sub_sub_fc': sub_sub_fc, 
                                   'sub_surf_fc': sub_surf_fc})
        if args.ts == True:
            scio.savemat(ts_output, {'cortical_ts': mean_time_series,
                                     'subcortical_ts': sub_mean_time_series})
    else:
        scio.savemat(args.output, {'fc': result})
        if args.ts == True:
            scio.savemat(ts_output, {'cortical_ts': mean_time_series})


if __name__ == "__main__":
    main()
