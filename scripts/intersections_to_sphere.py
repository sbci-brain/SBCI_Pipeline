import argparse
import logging
import numpy as np
import vtk

from collections import defaultdict, OrderedDict
from os.path import isfile

import scipy.io as scio
from scipy import sparse

import vtk.util.numpy_support as ns

DESCRIPTION = """
  Register the time series from subject to average space.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_reg_surface', action='store', metavar='LH_SET_SURFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_reg_surface', action='store', metavar='RH_SET_URFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the right hemisphere.')

    p.add_argument('--set_surfaces', action='store', metavar='SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the concatenated surfaces.')

    p.add_argument('--set_surface_map', action='store', metavar='SURFACE_MAP', required=True,
                   type=str, help='Path of the surface map for the vertices.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections output by SET.')

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


def get_surface_by_id(surfaces, surface_map, surf_id):
    # create a mask for the surface ID and get vertices
    mask = (surface_map == surf_id)
    vertices = ns.vtk_to_numpy(surfaces.GetPoints().GetData())[mask]

    # find triangles with any vertex within the mask
    polydata = ns.vtk_to_numpy(surfaces.GetPolys().GetData())
    triangles = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T
    triangles = triangles[np.any(mask[triangles], axis=1)]
    triangles = triangles - np.min(triangles)

    # set all the vertices
    vtk_points = vtk.vtkPoints()
    vtk_points.SetData(ns.numpy_to_vtk(vertices, deep=True))

    # set all the triangles
    vtk_triangles = np.hstack(
        np.c_[np.ones(len(triangles)).astype(np.int) * 3, triangles])
    vtk_triangles = ns.numpy_to_vtkIdTypeArray(vtk_triangles, deep=True)
    vtk_cells = vtk.vtkCellArray()
    vtk_cells.SetCells(len(triangles), vtk_triangles)

    # create the surface
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(vtk_points)
    polydata.SetPolys(vtk_cells)
    
    return polydata


def bary_helper(point_a, point_b):
    return np.array([point_a[1] * point_b[2] - point_a[2] * point_b[1],
                     point_a[2] * point_b[0] - point_a[0] * point_b[2],
                     point_a[0] * point_b[1] - point_a[1] * point_b[0]])


def to_bary_coords(cell, intersection):
    poly_pts = cell.GetPoints()
    tri = np.array([poly_pts.GetPoint(j) for j in range(poly_pts.GetNumberOfPoints())])

    norm = bary_helper(tri[1] - tri[0], tri[2] - tri[0])
    area = norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2]

    if area < 1e-14:
        log.error('area must be > 1e-14')

    norm = norm / area

    result = np.array([0.0, 0.0, 0.0])

    for i in range(3):
        coord = bary_helper(intersection - tri[(i+1) % 3], intersection - tri[(i+2) % 3])

        result[i] = np.dot(coord, norm)

    # populate the result arrays
    return result


def to_cart_coords(cell, coord):
    poly_pts = cell.GetPoints()
    tri = np.transpose(np.array([poly_pts.GetPoint(j) for j in range(poly_pts.GetNumberOfPoints())]))

    vtx = tri.dot(coord)
    norm = np.sqrt(vtx[0]*vtx[0] + vtx[1]*vtx[1] + vtx[2]*vtx[2])

    return vtx/norm


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    logging.info('Loading .vtk surfaces, mapping, and intersections.')
    for filename in [args.lh_reg_surface, args.rh_reg_surface, args.set_surfaces, args.set_surface_map, args.intersections]:
        if not isfile(filename):
            parser.error('The file "{0}" must exist.'.format(filename))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Mapping triangles to surface.')

    # load surface map
    set_surfaces = load_vtk(args.set_surfaces)
    set_surface_map = np.load(args.set_surface_map)

    # find surface indices from intersection triangle
    surf_ids = np.zeros(set_surfaces.GetNumberOfCells(), dtype=int)

    polydata = ns.vtk_to_numpy(set_surfaces.GetPolys().GetData())
    triangles = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T

    for surf_id in np.unique(set_surface_map):
        mask = (set_surface_map == surf_id)
        tri_mask = np.any(mask[triangles], axis=1)
        surf_ids[tri_mask] = surf_id

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)
    n = len(intersections['tri_ids0'])

    # load original white surfaces
    surfaces = dict()
    surfaces[0] = get_surface_by_id(set_surfaces, set_surface_map, 0)
    surfaces[1] = get_surface_by_id(set_surfaces, set_surface_map, 1)
    lh_limit = surfaces[0].GetNumberOfCells()# - 1

    # load the registered sphere surfaces
    reg_surfaces = dict()
    reg_surfaces[0] = load_vtk(args.lh_reg_surface);
    reg_surfaces[1] = load_vtk(args.rh_reg_surface);

    tri_ids0 = intersections['tri_ids0'].astype(int)
    tri_ids1 = intersections['tri_ids1'].astype(int)
    pts0 = intersections['pts0']
    pts1 = intersections['pts1']

    surf_ids_in = np.empty(n)
    surf_ids_out = np.empty(n)

    vtx_in = np.empty([n,3])
    vtx_out = np.empty([n,3])

    vtx_x_in = np.empty(n)
    vtx_y_in = np.empty(n)
    vtx_z_in = np.empty(n)
    vtx_x_out = np.empty(n)
    vtx_y_out = np.empty(n)
    vtx_z_out = np.empty(n)

    logging.info('Converting white coordinates to spherical coordinates.')

    for i in xrange(n):
        id_in = tri_ids0[i]
        id_out = tri_ids1[i]
        
        # set in and out id to a default
        index_in = index_out = 0

        # get the surfaces belonging to the triangles
        surface_id_in = surf_ids[tri_ids0[i]]
        surface_id_out = surf_ids[tri_ids1[i]]

        if surface_id_in <= 1:
            # convert to barycentric coordinates
	    id_in = id_in - surface_id_in*lh_limit

            bary_coord = to_bary_coords(surfaces[surface_id_in].GetCell(int(id_in)), pts0[i])
            sphere_coord = to_cart_coords(reg_surfaces[surface_id_in].GetCell(int(id_in)), bary_coord)

            vtx_in[i] = sphere_coord;

        if surface_id_out <= 1:
            # convert to barycentric coordinates
	    id_out = id_out - surface_id_out*lh_limit
             
            bary_coord = to_bary_coords(surfaces[surface_id_out].GetCell(int(id_out)), pts1[i])
            sphere_coord = to_cart_coords(reg_surfaces[surface_id_out].GetCell(int(id_out)), bary_coord)

            vtx_out[i] = sphere_coord;

        surf_ids_in[i] = surface_id_in
        surf_ids_out[i] = surface_id_out

    logging.info('Saving results.')

    mask = (surf_ids_in <= 1) & (surf_ids_out <= 1)

    # save the results
    np.savez_compressed(args.output,
                        surf_in=surf_ids_in[mask],
                        surf_out=surf_ids_out[mask],
                        vtx_in=vtx_in[mask],
                        vtx_out=vtx_out[mask])


if __name__ == "__main__":
    main()
