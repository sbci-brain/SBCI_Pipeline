import argparse
import logging
import nibabel as nib
import numpy as np

import scipy.io as scio

from os.path import isfile

DESCRIPTION = """
  Extract BOLD series for left and right white surfaces from HCP results.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--time_series', action='store', metavar='TIME_SERIES', required=True,
                   type=str, help='Path of the .gii file containing functional time series.')

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

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load data
    fmri_data = nib.load(args.time_series)
    header = fmri_data.header.get_axis(1)

    lh_n = header.to_mapping(1)[0].surface_number_of_vertices
    lh_count = header.to_mapping(1)[0].index_count
    lh_offset = header.to_mapping(1)[0].index_offset
    
    rh_n = header.to_mapping(1)[1].surface_number_of_vertices
    rh_count = header.to_mapping(1)[1].index_count
    rh_offset = header.to_mapping(1)[1].index_offset

    lh_indices = np.array(header.vertex[lh_offset:(lh_offset+lh_count)])
    rh_indices = np.array(header.vertex[rh_offset:(rh_offset+rh_count)])

    ts_size = fmri_data.header.get_axis(0).size

    # save time series for left and right hemispheres
    lh_time_series = np.zeros((ts_size, lh_n))
    rh_time_series = np.zeros((ts_size, rh_n))

    lh_time_series[:,lh_indices] = fmri_data.dataobj[:, lh_offset:(lh_offset+lh_count)]
    rh_time_series[:,rh_indices] = fmri_data.dataobj[:, rh_offset:(rh_offset+rh_count)]

    tmp_time_series = dict()

    for idx, (name, slc, bm) in enumerate(header.iter_structures()):
        if idx < 2:
            continue

        tmp_time_series[idx] = fmri_data.dataobj[:,slc].T

    sc_time_series = dict()

    sc_time_series['label_18'] = tmp_time_series[4]
    sc_time_series['label_54'] = tmp_time_series[5]
    sc_time_series['label_11'] = tmp_time_series[7]
    sc_time_series['label_50'] = tmp_time_series[8]
    sc_time_series['label_17'] = tmp_time_series[13]
    sc_time_series['label_53'] = tmp_time_series[14]
    sc_time_series['label_13'] = tmp_time_series[15]
    sc_time_series['label_52'] = tmp_time_series[16]
    sc_time_series['label_12'] = tmp_time_series[17]
    sc_time_series['label_51'] = tmp_time_series[18]
    sc_time_series['label_10'] = tmp_time_series[19]
    sc_time_series['label_49'] = tmp_time_series[20]

    sc_time_series['label_16'] = tmp_time_series[6]
    sc_time_series['label_26'] = tmp_time_series[2]
    sc_time_series['label_58'] = tmp_time_series[3]

    sc_time_series['lh_time_series'] = lh_time_series.T
    sc_time_series['rh_time_series'] = rh_time_series.T

    #np.savez_compressed(args.cor_output, lh_time_series=lh_time_series.T, 
    #                                     rh_time_series=rh_time_series.T)

    kwargs = {key: sc_time_series[key] for key in sc_time_series.keys()}
    np.savez_compressed(args.output, **kwargs)


if __name__ == "__main__":
    main()
