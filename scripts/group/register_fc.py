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

    p.add_argument('--time_series', action='store', metavar='LH_TIME_SERIES', required=True,
                   type=str, help='Path of the .npz file containing functional time series.')

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

    # load all low res surfaces 
    surfaces[0] = load_vtk(surface_files[0])
    surfaces[1] = load_vtk(surface_files[2])

    # initialise locator algorithms for the downsampled mesh
    locators[0] = vtk.vtkCellLocator()
    locators[0].SetDataSet(surfaces[0])
    locators[0].BuildLocator()

    locators[1] = vtk.vtkCellLocator()
    locators[1].SetDataSet(surfaces[1])
    locators[1].BuildLocator()

    # load points for high res surfaces
    points[0] = load_vtk(surface_files[1]).GetPoints()
    points[1] = load_vtk(surface_files[3]).GetPoints()

    return surfaces, points, locators


def calculate_weights(cell, intersection):
    poly_pts = cell.GetPoints()
    ids = np.array([cell.GetPointIds().GetId(j) for j in range(poly_pts.GetNumberOfPoints())])
    tri = np.array([poly_pts.GetPoint(j) for j in range(poly_pts.GetNumberOfPoints())])

    norm = np.cross(tri[1] - tri[0], tri[2] - tri[0])
    area = (norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2])

    if area < 1e-14:
        log.error('area must be > 1e-14')

    norm = norm / area

    result = np.array([0.0, 0.0, 0.0])

    for i in range(3):
        coord = np.cross(intersection - tri[(i+1) % 3], intersection - tri[(i+2) % 3])

        result[i] = np.dot(coord, norm)

    # populate the result arrays
    return ids, result


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

    if not isfile(args.time_series):
        parser.error('The file "{0}" must exist.'.format(args.time_series))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading .vtk surfaces, mapping, and intersections.')

    # load the subject surfaces, the vertices of the average surfaces, and initialise cell locator algorithms
    surfaces, points, locators = initialise_surfaces([args.lh_surface, args.lh_average, args.rh_surface, args.rh_average])

    lh_surf_n = surfaces[0].GetNumberOfPoints()
    rh_surf_n = surfaces[1].GetNumberOfPoints()
    surf_n = lh_surf_n + rh_surf_n

    lh_orig_n = points[0].GetNumberOfPoints()
    rh_orig_n = points[1].GetNumberOfPoints()
    orig_n = lh_orig_n + rh_orig_n

    # load time series and set up result arrays 
    time_series_data = np.load(args.time_series)

    time_series = dict()
    time_series[0] = time_series_data['lh_time_series']
    time_series[1] = time_series_data['rh_time_series']
 
    final_time_series = dict()
    final_time_series[0] = np.zeros((lh_orig_n, time_series[0].shape[1]), np.double)
    final_time_series[1] = np.zeros((rh_orig_n, time_series[1].shape[1]), np.double)

    final_weights = dict()
    final_weights[0] = np.zeros((lh_orig_n,1), np.double)
    final_weights[1] = np.zeros((rh_orig_n,1), np.double)

    # initialise pointers for cell locator
    intersection = [0, 0, 0]
    cell_id = vtk.reference(0)
    sub_id = vtk.reference(0)
    d = vtk.reference(0)

    logging.info('Snapping mesh to nearest downsampled vertices.')

    # loop through all vertices on full mesh and assign them to the closest vertex on resampled mesh
    for surface_id in range(2):
        n = points[surface_id].GetNumberOfPoints()

        for i in range(n):
            # find the closest point and triangle of the lower resolution mesh to a given vertex on the full mesh
            locators[surface_id].FindClosestPoint(points[surface_id].GetPoint(i), intersection, cell_id, sub_id, d)

            # convert point to barycentric coordinates
            ids, weights = calculate_weights(surfaces[surface_id].GetCell(cell_id.get()), intersection)

            #for j in range(3):
                #final_time_series[surface_id][ids[j],:] += time_series[surface_id][i,:] * weights[j]
                #final_weights[surface_id][ids[j]] += weights[j]
            final_time_series[surface_id][i] = (time_series[surface_id][ids[0],:] * weights[0] +
                                                time_series[surface_id][ids[1],:] * weights[1] +
                                                time_series[surface_id][ids[2],:] * weights[2]) / np.sum(weights)

    #print(np.sum(final_weights[0] == 0))
    #print(np.sum(final_weights[1] == 0))
    #final_weights[0][final_weights[0] == 0] = 1
    #final_weights[1][final_weights[1] == 0] = 1

    #final_time_series[0] = final_time_series[0] / final_weights[0]
    #final_time_series[1] = final_time_series[1] / final_weights[1]

    # save the results
    np.savez_compressed(args.output, lh_time_series=final_time_series[0], rh_time_series=final_time_series[1])


if __name__ == "__main__":
    main()
