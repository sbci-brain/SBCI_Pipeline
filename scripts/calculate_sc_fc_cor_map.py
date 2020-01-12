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

    p.add_argument('--fc_matrix', action='store', metavar='FC_MATRIX', required=True,
                   type=str, help='Path of the file containing functional connectivity matrix.')

    p.add_argument('--sc_matrix', action='store', metavar='SC_MATRIX', required=True,
                   type=str, help='Path of the file containing structural connectivity matrix.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--conditional', action='store', type=int, metavar='CONDITIONAL', default=None,
                    help='If set greater than 1, correlations are calculated only on vertices with WM connections to at least n other vertices.')

    p.add_argument('--fisher', action='store_true', dest='fisher', default=False,
                    help='Perform a Fisher z-transform on the FC before calculating correlation.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.fc_matrix):
        parser.error('The file "{0}" must exist.'.format(args.fc_matrix))

    if not isfile(args.sc_matrix):
        parser.error('The file "{0}" must exist.'.format(args.sc_matrix))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    if not (args.conditional is None) and (args.conditional < 2):
        parser.error('Minimum vector length for conditional correlations must be greater than 1')

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

    logging.info('Calculating FC/SC correlation.')

    # load sc matrix and make dense
    sc = np.array(sparse.load_npz(args.sc_matrix).todense())

    # load fc and convert to upper triangle matrix
    fc = np.zeros((n,n))
    fc[np.triu_indices(n, 0)] = np.load(args.fc_matrix)['fc']

    # perform fisher transformation
    if args.fisher:
        fc = np.arctanh(fc)

    # calculate the FC using an upper triangular indexing scheme
    result = np.zeros(n)

    for i in xrange(n):
        lower = i
        upper = i+1
        
        # get the whole row from the triangular matrix
	if i == 0:
            fc_row = fc[i, upper:]
            sc_row = sc[i, upper:]
        elif i == (n-1):
            fc_row = np.transpose(fc[0:lower, i])
            sc_row = np.transpose(sc[0:lower, i])
        else:
            fc_row = np.concatenate((np.transpose(fc[0:lower, i]), fc[i, upper:]))
            sc_row = np.concatenate((np.transpose(sc[0:lower, i]), sc[i, upper:]))

        if args.conditional > 1:
            conditional_msk = sc_row > 0
            
            # if not enough connections, set correlation to 0 and move on
            if (sc[i,i] == 0) or (np.sum(conditional_msk) < args.conditional):
                result[i] = 0
                continue
            
            fc_row = fc_row[conditional_msk]
            sc_row = sc_row[conditional_msk]

        # remove nans from the matrices (caused by unknown regions)
        mask_idx = ~np.isnan(fc_row)

        # if all values in the row are nans, set the result to nan and move on
        if not np.any(mask_idx):
            #result[i] = np.nan
            result[i] = -2
            continue

        result[i] = np.corrcoef(fc_row[mask_idx], sc_row[mask_idx])[0,1]

        if np.isnan(result[i]):
            result[i] = -2

    # save the results
    np.savez_compressed(args.output, corr_map=result)


if __name__ == "__main__":
    main()
