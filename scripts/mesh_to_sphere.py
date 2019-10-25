import argparse
import logging
import numpy as np
import vtk

from os.path import isfile

DESCRIPTION = """
  Map the downsampled meshes to the sphere
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the right hemisphere.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--suffix', action='store', metavar='SUFFIX', required=True,
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
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # generate output filenames
    lh_filename = args.lh_surface.rsplit('.vtk')[0] + args.suffix + '.vtk'
    rh_filename = args.rh_surface.rsplit('.vtk')[0] + args.suffix + '.vtk'

    filenames = [lh_filename, rh_filename]

    # warn if they already exist
    for i in range(2):
        if isfile(filenames[i]):
            if args.overwrite:
                logging.info('Overwriting "{0}".'.format(filenames[i]))
            else:
                parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(filenames[i]))
    
    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    mapping = dict()
    mapping[0] = mesh['lh_ids']
    mapping[1] = mesh['rh_ids']

    # load the surfaces, downsampling as needed
    logging.info('Loading and resampling .vtk surface.')

    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    for i in range(2):
        n = len(mapping[i])

        points = surfaces[i].GetPoints()
        new_points = vtk.vtkPoints()
        new_points.SetNumberOfPoints(n)
    
        # find the points to use
        for j in range(n):
            new_points.SetPoint(j, points.GetPoint(mapping[i][j]))
 
        # create a polydata object and set its points
        poly = vtk.vtkPolyData()
        poly.SetPoints(new_points)

        # triangulate the points with vtkDelaunay3D
        delny = vtk.vtkDelaunay3D()
        delny.SetInputDataObject(poly)
        delny.SetTolerance(0.01)
     
        # extract the surface from the triangulation
        mapper = vtk.vtkGeometryFilter()
        mapper.SetInputConnection(delny.GetOutputPort())

        writer = vtk.vtkPolyDataWriter()
        writer.SetInputConnection(mapper.GetOutputPort())
        writer.SetFileName(filenames[i])
        writer.Update()


if __name__ == "__main__":
    main()

