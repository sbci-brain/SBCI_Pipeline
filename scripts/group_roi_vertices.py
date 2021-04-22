import argparse
import logging

import numpy as np
import scipy.io as scio

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

    p.add_argument('--lh_mask', action='store', metavar='LH_MASK', required=False, default=None,
                   type=str, help='Path of the .npz file for the left hemisphere mask.')

    p.add_argument('--rh_mask', action='store', metavar='RH_MASK', required=False, default=None,
                   type=str, help='Path of the .npz file for the right hemisphere mask.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the downsampled mesh mapping .npz file.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--matlab', action='store', metavar='MATLAB', required=True,
                   type=str, help='Path of the .mat file to save the output to.')

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

    if isfile(args.matlab):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.matlab))

    # load annotation files
    lh_annot = read_annot(args.lh_annot)
    rh_annot = read_annot(args.rh_annot)

    lh_labels = np.array(lh_annot[0])
    rh_labels = np.array(rh_annot[0])

    # apply any given masks
    if not args.lh_mask == None:
        logging.info('Adding mask to LH.')
        
        mask = np.load(args.lh_mask, allow_pickle=True)['mask']
        lh_labels[mask == 1] = -1

    if not args.rh_mask == None:
        logging.info('Adding mask to RH.')

        mask = np.load(args.rh_mask, allow_pickle=True)['mask']
        rh_labels[mask == 1] = -1

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)

    mapping = mesh['mapping']
    shape = mesh['shape']

    logging.info('Number of LH vertices: {0}'.format(shape[1]))
    logging.info('Number of RH vertices: {0}'.format(shape[2]))

    # set the label to the most frequent found in each mapping
    lh_vertices = np.array([stats.mode(lh_labels[mapping[i]])[0][0] for i in range(shape[1])])
    rh_vertices = np.array([stats.mode(rh_labels[mapping[i] - shape[4]])[0][0] for i in range(shape[1], shape[0])])

    # create the ROI name arrays, skipping those that are not included on the mesh
    idx = np.unique(lh_vertices)
    lh_names = np.concatenate((np.array(lh_annot[2]), ['missing']))[idx]

    idx = np.unique(rh_vertices)
    rh_names = np.concatenate((np.array(rh_annot[2]), ['missing']))[idx]

    # make sure the label ids correspond to the array indices of the names
    lh_label_map = dict(zip(np.unique(lh_vertices), range(len(np.unique(lh_vertices)))))
    new_lh_labels = np.array([lh_label_map[i] for i in lh_vertices])

    rh_label_map = dict(zip(np.unique(rh_vertices), range(len(np.unique(rh_vertices)))))
    new_rh_labels = np.array([rh_label_map[i] for i in rh_vertices]) + np.max(new_lh_labels) + 1

    logging.info('Number of LH ROIs: {0}'.format(len(np.unique(lh_vertices))))
    logging.info('Number of RH ROIs: {0}'.format(len(np.unique(rh_vertices))))

    # group vertices by ROI
    new_order = np.concatenate([np.argsort(lh_vertices), np.argsort(rh_vertices) + shape[1]])

    lh_names = ['LH_' + name for name in lh_names]
    rh_names = ['RH_' + name for name in rh_names]

    # save the results
    np.savez_compressed(args.output,
                        sorted_idx=new_order,
                        fs_labels=np.concatenate((lh_vertices, rh_vertices)),
                        sbci_labels=np.concatenate((new_lh_labels, new_rh_labels)),
                        names=np.concatenate((lh_names, rh_names)),
                        colors=None)

    scio.savemat(args.matlab, {'sorted_idx': new_order + 1,
                               'labels': np.concatenate((new_lh_labels, new_rh_labels)) + 1,
                               'names': np.concatenate((lh_names, rh_names))})


if __name__ == "__main__":
    main()
