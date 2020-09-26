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

    # load annotation files
    lh_annot = read_annot(args.lh_annot)
    rh_annot = read_annot(args.rh_annot)

    lh_labels = np.array(lh_annot[0])
    rh_labels = np.array(rh_annot[0])

    # create the ROI name arrays, skipping those that are not included on the mesh
    idx = np.unique(lh_labels)
    lh_names = np.concatenate((np.array(lh_annot[2]), ['unknown']))[idx]

    idx = np.unique(rh_labels)
    rh_names = np.concatenate((np.array(rh_annot[2]), ['unknown']))[idx]

    # make sure the label ids correspond to the array indices of the names
    lh_label_map = dict(zip(np.unique(lh_labels), range(len(np.unique(lh_labels)))))
    lh_labels = np.array([lh_label_map[i] for i in lh_labels])

    rh_label_map = dict(zip(np.unique(rh_labels), range(len(np.unique(rh_labels)))))
    rh_labels = np.array([rh_label_map[i] for i in rh_labels])

    # create dictionary and calculate sizes for loop
    rois = dict()

    rois[0] = lh_labels
    rois[1] = rh_labels

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
            index = rois[surface_id][i] + (surface_id*10000)
            
            snapped[index].append(i + offset)

        offset = offset + n

    # sort and save mapping
    snapped = OrderedDict(sorted(snapped.items(), key=lambda t: t[0]))

    # get the shape of the original mesh, and the new mesh
    lh_roi_n = (len(np.unique(rois[0])))
    rh_roi_n = (len(np.unique(rois[1])))
    roi_n = lh_roi_n + rh_roi_n

    logging.info('Number of ROIs: {0}'.format(str(roi_n)))

    # save the shape of the original and new mesh
    shape = np.array([roi_n, lh_roi_n, rh_roi_n, orig_n, lh_orig_n, rh_orig_n])

    lh_names = ['LH_' + name for name in lh_names]
    rh_names = ['RH_' + name for name in rh_names]

    # save the results: mapping contains arrays of vertex numbers from original mesh that have been assigned to each
    # of the vertices of the downsampled mesh; shape has the number of vertices for both high and low resolution meshes.
    np.savez_compressed(args.output, mapping=snapped.values(), 
                        shape=shape, labels=snapped.keys(), 
                        roi_names=np.concatenate((lh_names, rh_names)))


if __name__ == "__main__":
    main()
