import argparse
import logging
import numpy as np
import vtk

from collections import defaultdict, OrderedDict
from os.path import isfile

DESCRIPTION = """
  Register the time series from subject to average space.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the left hemisphere.')

    p.add_argument('--lh_average', action='store', metavar='LH_AVERAGE', required=True,
                   type=str, help='Path of the average sphere .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the right hemisphere.')

    p.add_argument('--rh_average', action='store', metavar='RH_AVERAGE', required=True,
                   type=str, help='Path of the average sphere .vtk mesh file for the right hemisphere.')

    p.add_argument('--snapped_fibers', action='store', metavar='SNAPPED_FIBERS', required=True,
                   type=str, help='Path of the .npz file containing snapped fibers.')

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


# load all the required surfaces and build locator algorithms
def initialise_surfaces(surface_files):
    surfaces = dict()
    points = dict()
    locators = dict()

    # load all grid surfaces 
    surfaces[0] = load_vtk(surface_files[1])
    surfaces[1] = load_vtk(surface_files[3])

    # initialise locator algorithms for the downsampled mesh
    locators[0] = vtk.vtkPointLocator()
    locators[0].SetDataSet(surfaces[0])
    locators[0].BuildLocator()

    locators[1] = vtk.vtkPointLocator()
    locators[1].SetDataSet(surfaces[1])
    locators[1].BuildLocator()

    # load points for registered surfaces
    points[0] = load_vtk(surface_files[0]).GetPoints()
    points[1] = load_vtk(surface_files[2]).GetPoints()

    return surfaces, points, locators


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.lh_average):
        parser.error('The file "{0}" must exist.'.format(args.lh_average))

    if not isfile(args.rh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    if not isfile(args.rh_average):
        parser.error('The file "{0}" must exist.'.format(args.rh_average))

    if not isfile(args.snapped_fibers):
        parser.error('The file "{0}" must exist.'.format(args.snapped_fibers))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading .vtk surfaces, mapping, and intersections.')

    # load the subject surfaces, the vertices of the average surfaces, and initialise cell locator algorithms
    surfaces, points, locators = initialise_surfaces([args.lh_surface, args.lh_average, args.rh_surface, args.rh_average])

    # load time series and set up result arrays 
    snapped_fibers = np.load(args.snapped_fibers)

    v_ids0 = snapped_fibers['v_ids0']
    v_ids1 = snapped_fibers['v_ids1']
    surf_ids0 = snapped_fibers['surf_ids0']
    surf_ids1 = snapped_fibers['surf_ids1']

    n = len(v_ids0)

    logging.info('Registering to nearest vertex.')

    for i in xrange(n):
        if surf_ids0[i] > 1 or surf_ids1[i] > 1:
            continue

        surface_id_in = int(surf_ids0[i])
        id_in = int(v_ids0[i])

        # find the closest point and triangle of the lower resolution mesh to a given vertex on the full mesh
        index_in = locators[surface_id_in].FindClosestPoint(points[surface_id_in].GetPoint(id_in))

        ################################

        surface_id_out = int(surf_ids1[i])
        id_out = int(v_ids1[i])

        # snap the out point to the closest vertex on the mesh
        index_out = locators[surface_id_out].FindClosestPoint(points[surface_id_out].GetPoint(id_out))

        v_ids0[i] = index_in
        v_ids1[i] = index_out

    # save the results
    np.savez_compressed(args.output,
                        v_ids0=v_ids0,
                        surf_ids0=surf_ids0,
                        v_ids1=v_ids1,
                        surf_ids1=surf_ids1)


if __name__ == "__main__":
    main()
