import argparse
import logging

import numpy as np
from scipy import stats

from nibabel.freesurfer.io import read_annot
from os.path import isfile

DESCRIPTION = """
  Map atlas annotation files to downsampled surface.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_annot', action='store', metavar='LH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the left hemisphere.')

    p.add_argument('--rh_annot', action='store', metavar='RH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the right hemisphere.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the downsampled mesh mapping .npz file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the files exist
    if not isfile(args.lh_annot):
        parser.error('The file "{0}" must exist.'.format(args.lh_annot))

    if not isfile(args.rh_annot):
        parser.error('The file "{0}" must exist.'.format(args.rh_annot))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load annotation files
    lh_annot = read_annot(args.lh_annot)
    rh_annot = read_annot(args.rh_annot)

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)

    mapping = mesh['mapping']
    shape = mesh['shape']

    # set the label to the most frequent found in each mapping
    lh_vertices = [stats.mode(lh_annot[0][mapping[i]])[0][0] for i in range(shape[1])]
    rh_vertices = [stats.mode(rh_annot[0][mapping[i] - shape[4]])[0][0] for i in range(shape[1], shape[0])]

    # group vertices by ROI
    new_order = np.concatenate([np.argsort(lh_vertices), np.argsort(rh_vertices) + shape[1]])

    # save the results
    np.savez_compressed(args.output,
                        sorted_idx=new_order,
                        lh_labels=lh_vertices,
                        rh_labels=rh_vertices,
                        lh_colors=lh_annot[1],
                        rh_colors=rh_annot[1],
                        lh_names=np.array(lh_annot[2]),
                        rh_names=np.array(rh_annot[2]))


if __name__ == "__main__":
    main()
