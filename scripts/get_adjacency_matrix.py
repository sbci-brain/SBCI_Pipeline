import argparse
import logging
import vtk

import scipy.io as scio
import numpy as np

from os.path import isfile

DESCRIPTION = """
  Extract an adjacency matrix for vertices that are connected by a single edge.
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

    # load the surfaces
    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    # find the number of vertices on each surface
    lh_n = surfaces[0].GetPoints().GetNumberOfPoints()
    rh_n = surfaces[1].GetPoints().GetNumberOfPoints()

    # somewhere to put the results
    result = np.zeros((lh_n + rh_n, lh_n + rh_n), np.bool)

    for i in range(lh_n + rh_n):
        hemisphere = int(i >= lh_n) 

        vertex = i - (lh_n * hemisphere)

        # find the triangles the vertex is a part of
        cellIdList = vtk.vtkIdList()
        surfaces[hemisphere].GetPointCells(vertex, cellIdList)

        # for each triangle the vertex belongs
        for j in range(cellIdList.GetNumberOfIds()): 
            pointIdList = vtk.vtkIdList() 
            surfaces[hemisphere].GetCellPoints(cellIdList.GetId(j), pointIdList)

            # find the other vertices belonging to that triangle
            for k in range(pointIdList.GetNumberOfIds()):
                result[i, pointIdList.GetId(k) + (lh_n * hemisphere)] = True

    # save the results
    scio.savemat(args.output, {'adjacency': result})


if __name__ == "__main__":
    main()
