import argparse
import logging
import numpy as np
import vtk

from scipy import sparse
from os.path import isfile

DESCRIPTION = """
  Map tract endpoints to vertices on the downsampled surface and calculate SC matrix.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--sc_matrix', action='store', metavar='SC_MATRIX', required=True,
                   type=str, help='Path of the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--atlas', action='store', metavar='ATLAS', required=True,
                   type=str, help='Path to the atlas for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file of structural connectivity matrix.')

    p.add_argument('--count', action='store_true', dest='count',
                   help='If set, SC is calculated as total count instead of mean count.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.sc_matrix):
        parser.error('The file "{0}" must exist.'.format(args.sc_matrix))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    if not isfile(args.atlas):
        parser.error('The file "{0}" must exist.'.format(args.atlas))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading mapping and intersections.')

    # load the SC matrix and convert to full
    sc = sparse.load_npz(args.sc_matrix)
    sc = sc.toarray()

    # load atlas
    atlas = np.load(args.atlas, allow_pickle=True)
    grouping = np.concatenate((atlas['lh_labels'], atlas['rh_labels'] + 10000))
    rois = np.unique(grouping)
    rois = rois[(rois != -1) & (rois != 9999)]

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    mapping = mesh['mapping']
    shape = mesh['shape']

    areas = np.empty(shape[0])

    for i in range(shape[0]):
      areas[i] = len(mapping[i])

    n = len(rois)

    logging.info('Calculating SC for ' + str(n) + ' rois.')

    # initialise an array to fill in the loop
    sc_matrix = np.zeros((n, n))
    
    # normalise as is defined for continuous SC
    np.fill_diagonal(sc, 0)
    sc = sc / np.sum(sc)

    # calculate the structural connectivity
    for i in range(n):
        roi_a = (grouping == rois[i])
        roi_a_len = np.sum(roi_a)
        area_a = areas[roi_a]

        for j in range(i, n):
            if i == j:
                continue

            roi_b = (grouping == rois[j])

            area_b = areas[roi_b]
            area_ab = area_a.reshape(1,-1) * area_b.reshape(-1,1)
            
            region_mask = (roi_a | roi_b)
            region_sc = sc[region_mask, :]
            region_sc = region_sc[:, region_mask]
            region_sc = region_sc[roi_a_len:, :roi_a_len]

            if args.count == True:
                sc_matrix[i, j] = np.sum(region_sc * area_ab)
            else:
                sc_matrix[i, j] = np.sum(region_sc * area_ab) / (sum(area_a) * sum(area_b))

    # save results
    np.savez_compressed(args.output, sc=sc_matrix)


if __name__ == "__main__":
    main()
