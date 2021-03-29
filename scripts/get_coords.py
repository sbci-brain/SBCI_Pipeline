import argparse
import logging
import vtk

import scipy.io as scio
import numpy as np

from os.path import isfile, splitext

DESCRIPTION = """
  Extract points from a .vtk surface and output as a .mat file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to extract points from.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to extract points from.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surface file exists
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.rh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    points = dict()
    points[0] = load_vtk(args.lh_surface).GetPoints()
    points[1] = load_vtk(args.rh_surface).GetPoints()

    lh_n = points[0].GetNumberOfPoints()
    rh_n = points[1].GetNumberOfPoints()

    result = np.zeros((lh_n + rh_n, 5), np.float)

    for i in range(lh_n + rh_n):
        hemisphere = int(i >= lh_n) 

        result[i, 0] = i
        result[i, 1] = hemisphere
        result[i, 2:5] = points[hemisphere].GetPoint(i - (lh_n * hemisphere))

    # save the results
    if splitext(args.output)[1] == '.npz':
        np.savez_compressed(args.output, coords=result)
    else:
        scio.savemat(args.output, {'coords': result})

if __name__ == "__main__":
    main()
