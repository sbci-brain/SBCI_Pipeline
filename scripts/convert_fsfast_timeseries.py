import argparse
import logging
import nibabel as nib
import numpy as np

from os.path import isfile, splitext

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

    p.add_argument('--sub_time_series', action='store', metavar='SUB_TIME_SERIES', required=False, default=None,
                   type=str, help='Path of the file containing functional time series for the right hemisphere.')

    p.add_argument('--aparc', action='store', metavar='APARC', required=False, default='',
                   type=str, help='Path of the parcellation image used for subcortical volumes.')

    p.add_argument('--sub_rois', nargs='+', metavar='SUB_ROIS', required=False, default=None,
                   type=int, help='Labels of the subcortical ROIs to calculate the FC for.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    has_subcortical = (args.aparc != '') & (args.sub_time_series != None) & (args.sub_rois != None)

    if (has_subcortical == False) and (args.aparc != ''):
        parser.error('Must have atlas, ROI list, and time series for subcortical signal')

    if (has_subcortical == False) and (args.sub_time_series != None):
        parser.error('Must have atlas, ROI list, and time series for subcortical signal')

    if (has_subcortical == False) and (args.sub_rois != None):
        parser.error('Must have atlas, ROI list, and time series for subcortical signal')

    # make sure the input files exist
    if not isfile(args.lh_time_series):
        parser.error('The file "{0}" must exist.'.format(args.lh_time_series))

    if not isfile(args.rh_time_series):
        parser.error('The file "{0}" must exist.'.format(args.rh_time_series))

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

    time_series = dict()

    logging.info('Calculating timeseries for subcortical regions')   
 
    # load time series for subcortical regions
    if has_subcortical == True:
        ts_data = nib.load(args.sub_time_series)
        ts_data = ts_data.get_data()

        # load label images
        label_img = nib.load(args.aparc)
        label_data = label_img.get_data().astype('int')

        for roi in args.sub_rois:
            xyz = np.nonzero(label_data == roi)

            label_name = 'label_' + str(roi)
            time_series[label_name] = ts_data[xyz]

    # save the results
    time_series['lh_time_series'] = time_series_data_lh
    time_series['rh_time_series'] = time_series_data_rh
    time_series['subcortical_labels'] = ['label_' + lbl for lbl in map(str, args.sub_rois)]

    kwargs = {key: time_series[key] for key in time_series.keys()}
    np.savez_compressed(args.output, **kwargs)


if __name__ == "__main__":
    main()
