import argparse
import logging

import numpy as np
import scipy.io as scio

from scipy import sparse
from os.path import isfile

DESCRIPTION = """
  Convert the raw binary output of concon to .npz and .mat files.
"""

def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--input', action='store', metavar='INPUT', required=True,
                   type=str, help='Path of the file containing kernel data.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .mat file to output.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.input):
        parser.error('The file "{0}" must exist.'.format(args.input))

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

    dtype = np.dtype([("x", np.int32), ("y", np.int32), ("lambda", np.double)])

    with open(args.input, 'rb') as raw_file:
        N = int(np.fromfile(raw_file, dtype=np.int32, count = 1))

        logging.info('Loading {0}x{0} kernel matrix.'.format(N))    

        result = np.fromfile(raw_file, dtype=dtype)

    kernel = np.zeros((N,N), dtype=np.double)

    logging.info('Converting to MATLAB matrix.'.format(N))    

    # convert to a matrix
    kernel[result['x'], result['y']] = result['lambda']

    # free memory
    result = None

    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    shape = mesh['shape']

    # left and right hemispheres are swapped in concon so swap them back here
    A = kernel[0:shape[2],0:shape[2]].copy() 
    B = kernel[shape[2]:,shape[2]:].copy() 
    C = kernel[shape[2]:,0:shape[2]].copy()
    D = kernel[0:shape[2],shape[2]:].copy()

    kernel[0:shape[1],0:shape[1]] = B
    kernel[shape[1]:,shape[1]:] = A
    kernel[shape[1]:,0:shape[1]] = D
    kernel[0:shape[1],shape[1]:] = C

    # normalise the matrix to make a probability distribution
    intersections = np.load(args.intersections, allow_pickle=True)
    N = len(intersections['v_ids0'].astype(np.int64))
    kernel = kernel / N

    # save the results
    #scio.savemat(args.output + '.mat', {'sc': kernel})
    scio.savemat(args.output, {'sc': np.triu(kernel)})
    sparse.save_npz(args.output + '.npz', sparse.csr_matrix(kernel))

if __name__ == "__main__":
    main()
