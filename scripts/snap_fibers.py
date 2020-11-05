import argparse
import logging
import numpy as np
import vtk

from scipy import sparse
from os.path import isfile

DESCRIPTION = """
  Snap streamline endpoints to the nearest vertex of the given surface meshes.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the right hemisphere.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections output by SET.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the intersections to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


# snap the given point to the nearest vertex of the given triangle
def snap_to_closest_vertex(cell, intersection):
    poly_pts = cell.GetPoints()
    triangle = np.array([poly_pts.GetPoint(j) for j in range(poly_pts.GetNumberOfPoints())])

    # vectorise squared euler distance between the intersection and the triangle, return index of closest vertex
    dist = np.sum((triangle - intersection)**2, axis=1)
    tri_id = np.argmin(dist)
    vertex_id = cell.GetPointIds().GetId(tri_id)

    # populate the result arrays
    return vertex_id


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    logging.info('Loading .vtk surfaces, mapping, and intersections.')
    for filename in [args.lh_surface, args.rh_surface, args.intersections]:
        if not isfile(filename):
            parser.error('The file "{0}" must exist.'.format(filename))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces
    logging.info('Loading .vtk surfaces and intersections.')

    # load all surfaces
    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    # triangle indices
    lh_limit = surfaces[0].GetNumberOfCells() - 1
    rh_limit = surfaces[0].GetNumberOfCells() + surfaces[1].GetNumberOfCells() - 2

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)
    n = len(intersections['tri_ids0'])

    tri_ids0 = intersections['tri_ids0']
    tri_ids1 = intersections['tri_ids1']
    pts0 = intersections['pts0']
    pts1 = intersections['pts1']

    logging.info('Snapping intersections to nearest vertices.')

    all_id_in = np.empty(n)
    all_id_out = np.empty(n)
    surf_ids_in = np.empty(n)
    surf_ids_out = np.empty(n)

    filter_arr = np.ones(n, dtype=bool)

    logging.info(lh_limit)
    logging.info(rh_limit)

    for i in xrange(n):
        id_in = tri_ids0[i]
        id_out = tri_ids1[i]

        if id_in > rh_limit or id_out > rh_limit:
            filter_arr[i] = False
            continue
        
        surface_id_in = 0 if id_in <= lh_limit else 1
	id_in = id_in - surface_id_in*lh_limit

        # snap the in point to the closest vertex on the mesh
        index_in = snap_to_closest_vertex(surfaces[surface_id_in].GetCell(id_in), pts0[i])

        ################################

        surface_id_out = 0 if id_out <= lh_limit else 1
	id_out = id_out - surface_id_out*lh_limit

        # snap the in point to the closest vertex on the mesh
        # snap the out point to the closest vertex on the mesh
        index_out = snap_to_closest_vertex(surfaces[surface_id_out].GetCell(id_out), pts1[i])

        all_id_in[i] = index_in
        all_id_out[i] = index_out
        surf_ids_in[i] = surface_id_in
        surf_ids_out[i] = surface_id_out

    logging.info('Saving results.')

    # save the results
    np.savez_compressed(args.output,
                        v_ids0=all_id_in[filter_arr],
                        v_ids1=all_id_out[filter_arr],
                        surf_ids0=surf_ids_in[filter_arr],
                        surf_ids1=surf_ids_out[filter_arr])


if __name__ == "__main__":
    main()
