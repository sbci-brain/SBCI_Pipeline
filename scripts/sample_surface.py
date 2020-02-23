import argparse
import logging
import vtk

import numpy as np

from os.path import isfile

DESCRIPTION = """
  Downsample a .vtk surface and output the new .vtk file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to downsample.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--reduction', action='store', metavar='REDUCTION', required=True,
                   type=float, help='Percentage of vertices to remove from the surface meshes.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


# function to downsample the surface
def downsample_surface(surface_file, reduction):
    decimate = vtk.vtkDecimatePro()
    clean = vtk.vtkCleanPolyData()

    # load the surface
    surface = load_vtk(surface_file)

    locator = vtk.vtkPointLocator()
    locator.SetDataSet(surface)
    locator.BuildLocator()

    # To guarantee a given level of reduction, 
    # the ivar PreserveTopology must be off; the ivar Splitting is on; 
    # the ivar BoundaryVertexDeletion is on; and the ivar MaximumError is set to VTK_DOUBLE_MAX
    # reduce the number of vertices in the mesh
    decimate.SetInputData(surface)
    decimate.SetTargetReduction(reduction)
    decimate.PreserveTopologyOff()
    decimate.SplittingOn()
    decimate.BoundaryVertexDeletionOn()
    decimate.SetMaximumError(vtk.VTK_DOUBLE_MAX)

    clean.SetInputConnection(decimate.GetOutputPort())
    clean.Update()

    points = clean.GetOutput().GetPoints()
    N = surface.GetNumberOfPoints()
    n = points.GetNumberOfPoints()

    result = -1 * np.ones(n, np.int64)

    # find the points to use
    for i in range(n):
        index = locator.FindClosestPoint(points.GetPoint(i))
        
        if np.array_equal(points.GetPoint(i), surface.GetPoints().GetPoint(index)):
            result[i] = index

    if np.sum(result < 0) > 0:
        logging.info('Warning: Not all points correspond to higher resolution mesh.')

    return result


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surface file exists
    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # make sure the reduction is between 0-1
    if args.reduction >= 1 or args.reduction <= 0:
        parser.error('Reduction percentage must be between than (0,1).')

    logging.info('Loading and resampling the .vtk surface.')

    # perform the downsampling
    result = downsample_surface(args.surface, args.reduction)

    # save the results
    np.savez_compressed(args.output, points=result)


if __name__ == "__main__":
    main()
