import argparse
import logging
import numpy as np
import vtk

from scipy import sparse
from os.path import isfile

import vtk.util.numpy_support as ns

DESCRIPTION = """
  Snap streamline endpoints to the nearest vertex of the given surface meshes.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surfaces', action='store', metavar='SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the concatenated surfaces.')

    p.add_argument('--surface_map', action='store', metavar='SURFACE_MAP', required=True,
                   type=str, help='Path of the surface map for the vertices.')

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


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    logging.info('Loading .vtk surfaces, mapping, and intersections.')
    for filename in [args.surfaces, args.surface_map, args.intersections]:
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
    all_surfaces = load_vtk(args.surfaces)

    # load surface map
    surface_map = np.load(args.surface_map)

    # get left and right hemisphere
    surfaces = dict()
    surfaces[0] = get_surface_by_id(all_surfaces, surface_map, 0)
    surfaces[1] = get_surface_by_id(all_surfaces, surface_map, 1)

    lh_limit = surfaces[0].GetNumberOfCells()# - 1

    # triangle indices
    surf_ids = np.zeros(all_surfaces.GetNumberOfCells(), dtype=int)

    polydata = ns.vtk_to_numpy(all_surfaces.GetPolys().GetData())
    triangles = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T

    logging.info('Mapping triangles to sruface.')

    for surf_id in np.unique(surface_map):
        mask = (surface_map == surf_id)
        tri_mask = np.any(mask[triangles], axis=1)
        surf_ids[tri_mask] = surf_id

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)
    n = len(intersections['tri_ids0'])

    tri_ids0 = intersections['tri_ids0'].astype(int)
    tri_ids1 = intersections['tri_ids1'].astype(int)
    pts0 = intersections['pts0']
    pts1 = intersections['pts1']
    surf_ids0 = intersections['surf_ids0']
    surf_ids1 = intersections['surf_ids1']

    logging.info('Snapping intersections to nearest vertices.')

    vtx_ids_in = np.empty(n)
    vtx_ids_out = np.empty(n)
    surf_ids_in = np.empty(n)
    surf_ids_out = np.empty(n)

    for i in xrange(n):
        id_in = tri_ids0[i]
        id_out = tri_ids1[i]
        
        # set in and out id to a default
        index_in = index_out = 0

        # get the surfaces belonging to the triangles
        if surf_ids0[i] == 1:
            surface_id_in = surf_ids[tri_ids0[i]]
        else:
            surface_id_in = surf_ids0[i] 

        if surf_ids1[i] == 1:
            surface_id_out = surf_ids[tri_ids1[i]]
        else:
            surface_id_out = surf_ids1[i] 
        
        if surface_id_in <= 1:
            # snap the in point to the closest vertex on the mesh
	    id_in = id_in - surface_id_in*lh_limit
            index_in = snap_to_closest_vertex(surfaces[surface_id_in].GetCell(int(id_in)), pts0[i])

        ################################

        if surface_id_out <= 1:
            # snap the out point to the closest vertex on the mesh
	    id_out = id_out - surface_id_out*lh_limit
            index_out = snap_to_closest_vertex(surfaces[surface_id_out].GetCell(int(id_out)), pts1[i])

        vtx_ids_in[i] = index_in
        vtx_ids_out[i] = index_out
        surf_ids_in[i] = surface_id_in
        surf_ids_out[i] = surface_id_out

    logging.info('Saving results.')

    # save the results
    np.savez_compressed(args.output,
                        v_ids0=vtx_ids_in,
                        v_ids1=vtx_ids_out,
                        surf_ids0=surf_ids_in,
                        surf_ids1=surf_ids_out)


if __name__ == "__main__":
    main()
