import argparse
import logging
import numpy as np
import string
import vtk

from os.path import isfile
from scipy.spatial import Delaunay

DESCRIPTION = """
  Map the downsampled meshes to the sphere
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE',
                   type=str, help='Path of the .vtk mesh file for a hemisphere.')

    p.add_argument('--points', action='store', metavar='POINTS', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Suffix of output files.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surfaces file exists
    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    if not isfile(args.points):
        parser.error('The file "{0}" must exist.'.format(args.points))

    # warn if they already exist
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))
    
    # load the surfaces, downsampling as needed
    logging.info('Loading and resampling .vtk surface.')

    # load mapping
    mesh = np.load(args.points, allow_pickle=True)
    mesh = mesh['points']
    points = load_vtk(args.surface).GetPoints()

    n = len(mesh)
    new_points = np.zeros((n, 3), np.float64)
    
    # find the points to use
    for i in range(n):
        new_points[i, 0:3] = points.GetPoint(mesh[i])
 
    # triangulate the points using the delaunay algorithm
    delny = Delaunay(new_points, 'Qbb Qc Qz Q12')

    point_ids = np.unique(delny.convex_hull)
    point_ids = np.sort(point_ids)

    # relabel vertices to account for points removed in the triangulation
    new_points = np.copy(delny.convex_hull)
    index = 0

    for i in np.setdiff1d(range(n), point_ids):
        indices = (delny.convex_hull >= i)
        new_points[indices] = new_points[indices] - 1

    logging.info('Merged {0} points during triangulation.'.format(str(n - len(point_ids))))

    # write the new .vtk file
    poly_count = new_points.shape[0]
    index = 0

    with open(args.output, 'w') as outputfile:
        outputfile.write('# vtk DataFile Version 4.2\n')
        outputfile.write('vtk output\n')
        outputfile.write('ASCII\n')
        outputfile.write('DATASET POLYDATA\n')
        outputfile.write('POINTS ' + str(len(point_ids)) + ' float\n')

        firstface = True

        for i in point_ids:
            a = str(delny.points[i, 0]))
            b = str(delny.points[i, 1]))
            c = str(delny.points[i, 2]))

            outputfile.write(string.join([a,b,c], sep = ' ') + ' ')

            index = index + 1

            if (index % 3) == 0:
                outputfile.write('\n')

        if not (index % 3) == 0:
            outputfile.write('\n')
       
        outputfile.write('\nPOLYGONS ' + str(poly_count) + ' ' + str(poly_count*4) + '\n')

        for i in range(poly_count):
            a = str(new_points[i, 0])
            b = str(new_points[i, 1])
            c = str(new_points[i, 2])

            outputfile.write('3 ' + string.join([a,b,c], sep = ' ') + '\n')


if __name__ == "__main__":
    main()

