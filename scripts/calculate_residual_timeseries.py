import argparse
import logging
import nibabel as nib
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Regress out the given confounders from the timeseries data.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_time_series', action='store', metavar='LH_TIME_SERIES', required=True,
                   type=str, help='Path of the file containing functional time series for the left hemisphere.')

    p.add_argument('--rh_time_series', action='store', metavar='RH_TIME_SERIES', required=True,
                   type=str, help='Path of the file containing functional time series for the right hemisphere.')

    p.add_argument('--motion', action='store', metavar='MOTION', required=False, default='',
                   type=str, help='Path to the motion nuisance regressor file.')

    p.add_argument('--wm', action='store', metavar='WM', required=False, default='',
                   type=str, help='Path to the motion nuisance regressor file.')

    p.add_argument('--vcsf', action='store', metavar='VCSF', required=False, default='',
                   type=str, help='Path to the motion nuisance regressor file.')

    p.add_argument('--gsl', action='store', metavar='GSL', required=False, default='',
                   type=str, help='Path to the motion nuisance regressor file.')

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
    if not isfile(args.lh_time_series):
        parser.error('The file "{0}" must exist.'.format(args.lh_time_series))

    if not isfile(args.rh_time_series):
        parser.error('The file "{0}" must exist.'.format(args.rh_time_series))

    if not args.motion == '' and not isfile(args.motion):
        parser.error('The file "{0}" must exist.'.format(args.motion))

    if not args.wm == '' and not isfile(args.wm):
        parser.error('The file "{0}" must exist.'.format(args.wm))

    if not args.vcsf == '' and not isfile(args.vcsf):
        parser.error('The file "{0}" must exist.'.format(args.vcsf))

    if not args.gsl == '' and not isfile(args.gsl):
        parser.error('The file "{0}" must exist.'.format(args.gsl))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load time series for left and right hemispheres
    time_series_lh = nib.load(args.lh_time_series)
    time_series_data_lh = time_series_lh.get_data()
    time_series_data_lh = time_series_data_lh[:, 0, 0, :]

    time_series_rh = nib.load(args.rh_time_series)
    time_series_data_rh = time_series_rh.get_data()
    time_series_data_rh = time_series_data_rh[:, 0, 0, :]

    # load confounder data
    n = time_series_data_rh.shape[1]
    confounders = np.ones([1, n])

    # TODO: remove magic numbers
    if not args.motion == '':
        confounders = np.concatenate([confounders, np.genfromtxt(args.motion, dtype=np.float64).T[1:7, :]])

    if not args.wm == '':
        confounders = np.concatenate([confounders, np.genfromtxt(args.wm, dtype=np.float64).T[0:5, :]])

    if not args.vcsf == '':
        confounders = np.concatenate([confounders, np.genfromtxt(args.vcsf, dtype=np.float64).T[0:5, :]])

    if not args.gsl == '':
        confounders = np.concatenate([confounders, np.genfromtxt(args.gsl).reshape([1, n])])

    confounders = confounders.T

    XTX_inverse = np.linalg.inv(np.dot(confounders.T, confounders))
    P = np.dot(np.dot(confounders, XTX_inverse), confounders.T) 
    I = np.eye(confounders.shape[0])

    lh_residuals = np.zeros(time_series_data_lh.shape)
    rh_residuals = np.zeros(time_series_data_rh.shape)

    logging.info('Calculating timeseries for left hemisphere')   

    for i in range(time_series_lh.shape[0]):
	lh_residuals[i, :] = np.dot(I, time_series_data_lh[i, :]) - np.dot(P, time_series_data_lh[i, :])

    logging.info('Calculating timeseries for right hemisphere')   

    for i in range(time_series_rh.shape[0]):
	rh_residuals[i, :] = np.dot(I, time_series_data_rh[i, :]) - np.dot(P, time_series_data_rh[i, :])

    # save the results
    np.savez_compressed(args.output, lh_time_series=lh_residuals, rh_time_series=rh_residuals)


if __name__ == "__main__":
    main()
