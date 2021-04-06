import argparse
import logging
import nibabel as nib
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Normalise and concatenate BOLD time series data.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', nargs='+', action='store', metavar='TIME_SERIES', required=True,
                   type=str, help='Path of the files containing functional time series to be concatenated.')

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
    for filename in args.time_series:
        if not isfile(filename):
            parser.error('The file "{0}" must exist.'.format(filename))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    data = dict()

    for filename in args.time_series:
       time_series_data = np.load(filename)

       for key in time_series_data.files:
           ts_std = time_series_data[key]
           ts_std = (ts_std - ts_std.mean(1, keepdims=True)) / ts_std.std(1, keepdims=True)
           ts_std = np.nan_to_num(ts_std)

           if data.has_key(key) == False:
               data[key] = ts_std 
           else:
               data[key] = np.concatenate((data[key], ts_std), axis=1) 
           
    # save the results
    kwargs = {key: data[key] for key in data.keys()}
    np.savez_compressed(args.output, **kwargs)
###
###    time_series_lh = None
###    time_series_rh = None
###
###    for filename in args.time_series:
###        time_series_data = np.load(filename)
###
###        ts_std = time_series_data['lh_time_series']
###        ts_std = (ts_std - ts_std.mean(1, keepdims=True)) / ts_std.std(1, keepdims=True)
###        ts_std = np.nan_to_num(ts_std)
###
###        if time_series_lh is None:
###            time_series_lh = ts_std 
###        else:
###            time_series_lh = np.concatenate(time_series_lh, ts_std) 
###
###        ts_std = time_series_data['rh_time_series']
###        ts_std = (ts_std - ts_std.mean(1, keepdims=True)) / ts_std.std(1, keepdims=True)
###        ts_std = np.nan_to_num(ts_std)
###
###        if time_series_rh is None:
###            time_series_rh = ts_std 
###        else:
###            time_series_rh = np.concatenate(time_series_rh, ts_std) 
###
    # save the results
    #np.savez_compressed(args.output, lh_time_series=time_series_lh, rh_time_series=time_series_rh)


if __name__ == "__main__":
    main()
