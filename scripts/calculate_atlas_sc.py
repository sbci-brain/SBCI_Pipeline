import argparse
import logging
import nibabel as nib
import numpy as np

import scipy.io as scio

from os.path import isfile

DESCRIPTION = """
  Calculate the functional connectivity (using Pearson Correlation) for the given mapping.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--atlas', action='store', metavar='ATLAS', required=True,
                   type=str, help='Path to the atlas for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--mask_indices', type=int, nargs='+', default=[-1],
                   help='List of freesurfer label indices to ignore when calculating connectivity.')

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
    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.time_series))

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

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    mapping = mesh['mapping']
    shape = mesh['shape']

    # load atlas
    atlas = np.load(args.atlas, allow_pickle=True)
    mask = np.isin(atlas['fs_labels'], args.mask_indices, invert=True)

    # load intersections that have already been snapped to nearest vertices of full mesh
    intersections = np.load(args.intersections, allow_pickle=True)

    id_in = intersections['v_ids0'].astype(np.int)
    id_out = intersections['v_ids1'].astype(np.int)
    surf_in = intersections['surf_ids0']
    surf_out = intersections['surf_ids1']

    # only keep the white matter surfaces from the intersections 
    # file and map rh vertex ids to the full brain indices
    id_in[surf_in == 1] = id_in[surf_in == 1] + shape[4]
    id_out[surf_out == 1] = id_out[surf_out == 1] + shape[4]

    id_in = id_in[(surf_in <= 1) & (surf_out <= 1)]
    id_out = id_out[(surf_in <= 1) & (surf_out <= 1)]

    # initialise an array to fill in the loop
    result = np.zeros([shape[0], shape[0]], dtype=np.float64)

    logging.info('Calculating SC for ' + str(len(id_in)) + ' streamlines.')

    id_in_buf = id_in.copy()
    id_out_buf = id_out.copy()

    # map intersections to the given resolution
    for i in range(shape[0]):
        id_in[np.in1d(id_in_buf, mapping[i])] = i
        id_out[np.in1d(id_out_buf, mapping[i])] = i

    # calculate the structural connectivity
    for i in range(len(id_in)):
        result[id_in[i], id_out[i]] += 1
      
        # only count self connections once
        if not id_in[i] == id_out[i]:
            result[id_out[i], id_in[i]] += 1

    # get the mean connectivity
    for i in range(shape[0]):
        for j in range(i, shape[0]):
            if i == j:
                result[i, j] = 0
                continue

    result = result[mask,:]
    result = result[:,mask]

    logging.info(result.shape)

    # save the results
    scio.savemat(args.output, {'sc': result})


if __name__ == "__main__":
    main()
