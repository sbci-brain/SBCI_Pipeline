#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port:
#   - xrange() → range()

import argparse
import logging
import numpy as np
import vtk

from collections import defaultdict, OrderedDict
from os.path import isfile

import scipy.io as scio
from scipy import sparse

import vtk.util.numpy_support as ns

LEGACY_ICO4_TIE_REPLACEMENTS = {
    (1, 1873, 3554, 0): 3149,
    (1, 1548, 2448, 1): 389,
    (1, 1671, 473, 0): 2700,
    (1, 1384, 2894, 0): 2171,
    (1, 1628, 445, 0): 2616,
    (1, 1568, 2490, 1): 403,
    (1, 1226, 1984, 0): 1023,
    (0, 1957, 3365, 1): 4040,
    (0, 266, 2620, 0): 941,
}

DESCRIPTION = """
  Register the time series from subject to average space.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path of the sphere .vtk mesh file for the right hemisphere.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections output by SET.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    p.add_argument('--disable_legacy_ico4_ties', action='store_true',
                   help='Disable old-VTK compatibility handling for known ico4 edge ties.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    mesh = reader.GetOutput()

    # set all the vertices
    vertices = ns.vtk_to_numpy(mesh.GetPoints().GetData())
    vertices = vertices / np.linalg.norm(vertices, axis=-1)[:, np.newaxis]

    vtk_points = vtk.vtkPoints()
    vtk_points.SetData(ns.numpy_to_vtk(vertices, deep=True))

    mesh.SetPoints(vtk_points)

    return mesh


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
        logging.error('area must be > 1e-14')

    norm = norm / area

    result = np.array([0.0, 0.0, 0.0])

    for i in range(3):
        coord = bary_helper(intersection - tri[(i+1) % 3], intersection - tri[(i+2) % 3])
        result[i] = np.dot(coord, norm)

    # populate the result arrays
    return (result[0], result[1], result[2])


def legacy_ico4_edge_tie_cell(surface_id, vertex_id, cell_id, cell, intersection, surface,
                              enabled=True):
    """
    Reproduce old VTK's triangle choice for rare ico4 edge ties.

    VTK 9 chooses a different adjacent triangle than the VTK version used by
    the Python 2 pipeline for a few points that project exactly onto an ico4
    grid edge.  The closest snapped vertex is identical; only tri_* and the
    barycentric zero component differ.  Restrict this compatibility map to the
    ico4 grid size so other resolutions keep the normal VTK locator behavior.
    """
    if (not enabled or
            surface.GetNumberOfCells() != 5120 or
            surface.GetNumberOfPoints() != 2562):
        return cell_id

    bary = np.asarray(to_bary_coords(cell, intersection), dtype=float)
    point_ids = [cell.GetPointIds().GetId(j) for j in range(cell.GetNumberOfPoints())]
    try:
        snapped_pos = point_ids.index(int(vertex_id))
    except ValueError:
        return cell_id

    # Only edge projections need old-VTK tie handling.  The snapped vertex
    # component is nonzero; one of the other two components is exactly zero
    # after VTK projects the query point onto the closest grid edge.
    zero_positions = [j for j in range(3)
                      if j != snapped_pos and abs(bary[j]) < 1e-10]
    if not zero_positions:
        return cell_id

    # Keys/values are 0-based except vertex_id, which is returned 0-based by
    # VTK before the MATLAB +1 conversion.  Include the zero barycentric
    # component because the same vertex/cell can have two different edge ties.
    for zero_pos in zero_positions:
        key = (int(surface_id), int(vertex_id), int(cell_id), int(zero_pos))
        if key in LEGACY_ICO4_TIE_REPLACEMENTS:
            return LEGACY_ICO4_TIE_REPLACEMENTS[key]
    return cell_id


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

    logging.info('Loading surfaces.')

    # load the grid surfaces
    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    # initialise locator algorithms
    locators = dict()
    locators[0] = vtk.vtkCellLocator()
    locators[0].SetDataSet(surfaces[0])
    locators[0].BuildLocator()

    locators[1] = vtk.vtkCellLocator()
    locators[1].SetDataSet(surfaces[1])
    locators[1].BuildLocator()

    logging.info('Loading intersections.')

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)
    n = len(intersections['surf_in'])

    surf0 = intersections['surf_in']
    surf1 = intersections['surf_out']
    pts0 = intersections['vtx_in']
    pts1 = intersections['vtx_out']

    vtx_ids_in = np.zeros(n)
    vtx_ids_out = np.zeros(n)
    tri_ids_in = np.zeros(n)
    tri_ids_out = np.zeros(n)
    vtx_in = np.zeros([n, 3])
    vtx_out = np.zeros([n, 3])
    surf_ids_in = np.zeros(n)
    surf_ids_out = np.zeros(n)

    logging.info('Processing endpoint data.')

    # initialise pointers for cell locator
    intersection = [0, 0, 0]
    cell_id = vtk.reference(0)
    sub_id = vtk.reference(0)
    d = vtk.reference(0)
    legacy_tie_count = 0

    # Python 3 port: xrange() → range()
    for i in range(n):
        # set in and out id to a default
        index_in = index_out = 0

        # get the surfaces belonging to the triangles
        surface_id_in = int(surf0[i])
        surface_id_out = int(surf1[i])

        if surface_id_in <= 1:
            # find the closest point and triangle of the lower resolution mesh to a given vertex on the full mesh
            locators[surface_id_in].FindClosestPoint(pts0[i], intersection, cell_id, sub_id, d)

            selected_cell_id = int(cell_id)
            selected_cell = surfaces[surface_id_in].GetCell(selected_cell_id)
            index_in = snap_to_closest_vertex(selected_cell, intersection)
            selected_cell_id = legacy_ico4_edge_tie_cell(
                surface_id_in, index_in, selected_cell_id,
                selected_cell, intersection, surfaces[surface_id_in],
                enabled=not args.disable_legacy_ico4_ties)
            if selected_cell_id != int(cell_id):
                legacy_tie_count += 1
            selected_cell = surfaces[surface_id_in].GetCell(selected_cell_id)

            vtx_in[i] = to_bary_coords(selected_cell, intersection)
            vtx_ids_in[i] = snap_to_closest_vertex(selected_cell, intersection) + 1
            tri_ids_in[i] = selected_cell_id + 1

        if surface_id_out <= 1:
            # find the closest point and triangle of the lower resolution mesh to a given vertex on the full mesh
            locators[surface_id_out].FindClosestPoint(pts1[i], intersection, cell_id, sub_id, d)

            selected_cell_id = int(cell_id)
            selected_cell = surfaces[surface_id_out].GetCell(selected_cell_id)
            index_out = snap_to_closest_vertex(selected_cell, intersection)
            selected_cell_id = legacy_ico4_edge_tie_cell(
                surface_id_out, index_out, selected_cell_id,
                selected_cell, intersection, surfaces[surface_id_out],
                enabled=not args.disable_legacy_ico4_ties)
            if selected_cell_id != int(cell_id):
                legacy_tie_count += 1
            selected_cell = surfaces[surface_id_out].GetCell(selected_cell_id)

            vtx_out[i] = to_bary_coords(selected_cell, intersection)
            vtx_ids_out[i] = snap_to_closest_vertex(selected_cell, intersection) + 1
            tri_ids_out[i] = selected_cell_id + 1

        surf_ids_in[i] = surface_id_in
        surf_ids_out[i] = surface_id_out

    logging.info('Saving results.')
    if legacy_tie_count:
        logging.info('Applied old-VTK ico4 edge-tie compatibility to {0} endpoints.'.format(
            legacy_tie_count))

    # save the results
    scio.savemat(args.output, {'surf_in': surf_ids_in,
                               'surf_out': surf_ids_out,
                               'tri_in': tri_ids_in,
                               'tri_out': tri_ids_out,
                               'vtx_in': vtx_ids_in,
                               'vtx_out': vtx_ids_out,
                               'pt_in': vtx_in,
                               'pt_out': vtx_out})


if __name__ == "__main__":
    main()
