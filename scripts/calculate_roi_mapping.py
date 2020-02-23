import argparse
import logging
import numpy as np

from nibabel.freesurfer.io import read_annot
from collections import defaultdict, OrderedDict
from os.path import isfile

DESCRIPTION = """
  Generate a mapping between the high and low resolution parcellations.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_annot', action='store', metavar='LH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the left hemisphere.')

    p.add_argument('--rh_annot', action='store', metavar='RH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the right hemisphere.')

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

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load files
    rois = dict()

    lh_annot = read_annot(args.lh_annot)
    rh_annot = read_annot(args.rh_annot)

    rois[0] = lh_annot[0]
    rois[1] = rh_annot[0]

    lh_orig_n = len(rois[0])
    rh_orig_n = len(rois[1])
    orig_n = lh_orig_n + rh_orig_n

    offset = 0
    snapped = defaultdict(list)

    logging.info('Merging vertices into parcellation')

    # loop through all vertices on full mesh and assign them to the closest vertex on resampled mesh
    for surface_id in range(2):
        n = len(rois[surface_id])

        for i in range(n):
            index = rois[surface_id][i]
            snapped[index + offset].append(i + offset)

        offset = offset + n

    # get the shape of the original mesh, and the new mesh
    snapped = OrderedDict(sorted(snapped.items(), key=lambda t: t[0]))

    #print(snapped.keys())
    vertices = snapped.values()

    roi_n = len(snapped.keys())
    lh_roi_n = rh_roi_n = int(roi_n / 2)

    leftvertex = np.empty(lh_roi_n, np.int64)
    rightvertex = np.empty(rh_roi_n, np.int64)

    # save the shape of the original and new mesh
    shape = np.array([roi_n, lh_roi_n, rh_roi_n, orig_n, lh_orig_n, rh_orig_n])

    # save the results: mapping contains arrays of vertex numbers from original mesh that have been assigned to each
    # of the vertices of the downsampled mesh; shape has the number of vertices for both high and low resolution meshes.
    np.savez_compressed(args.output, mapping=vertices, shape=shape, lh_ids=leftvertex, rh_ids=rightvertex)


if __name__ == "__main__":
    main()
