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

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the downsampled mesh .npz file.')

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
    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.intersections))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading mapping and intersections.')

    # load mapping for the given resolution
    mesh = np.load(args.mesh, allow_pickle=True)

    mapping = mesh['mapping']
    shape = mesh['shape']

    areas = np.empty(shape[0])

    for i in range(shape[0]):
      areas[i] = len(mapping[i])

    # load intersections that have already been snapped to nearest vertices of full mesh
    intersections = np.load(args.intersections, allow_pickle=True)

    surf_in = intersections['surf_ids0'].astype(np.int64)
    surf_out = intersections['surf_ids1'].astype(np.int64)
    id_in = intersections['v_ids0'].astype(np.int64)
    id_out = intersections['v_ids1'].astype(np.int64)

    id_in[surf_in == 1] = id_in[surf_in == 1] + shape[4]
    id_out[surf_out == 1] = id_out[surf_out == 1] + shape[4]

    logging.info('Calculating SC for ' + str(len(id_in)) + ' streamlines.')

    id_in_buf = id_in.copy()
    id_out_buf = id_out.copy()

    # map intersections to the given resolution
    for i in range(shape[0]):
        id_in[np.in1d(id_in_buf, mapping[i])] = i
        id_out[np.in1d(id_out_buf, mapping[i])] = i

    sc_matrix = sparse.dok_matrix((shape[0], shape[0]), dtype=np.double)

    # calculate the structural connectivity
    for i in range(len(id_in)):
        sc_matrix[id_in[i], id_out[i]] += 1
    
        # only count self connections once
        if not id_in[i] == id_out[i]:
            sc_matrix[id_out[i], id_in[i]] += 1

    # get the mean connectivity
    for i in range(shape[0]):
        area_a = areas[i]

        for j in range(i, shape[0]):
            if i == j:
                sc_matrix[i, j] = 0
                continue

            if args.count == False:
                area_b = areas[j]
                sc_matrix[i, j] = sc_matrix[i, j] / (area_a * area_b)
            
            sc_matrix[j, i] = sc_matrix[i, j]

    # save results
    sparse.save_npz(args.output, sc_matrix.tocsr())


if __name__ == "__main__":
    main()
