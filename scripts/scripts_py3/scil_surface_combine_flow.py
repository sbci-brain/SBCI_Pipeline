#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function

import argparse
import logging
import numpy as np

from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import assert_inputs_exist, assert_outputs_exist
from utils.intersection import load_surface_intersections
from utils.seed import get_trilinear_coordinates_from_vertices
from dipy.tracking.streamlinespeed import compress_streamlines

from dipy.utils.optpkg import optional_package
vtk_u, _, _ = optional_package('trimeshpy.vtk_util')

DESCRIPTION = """
Script to visualize surface collision generated from
'scil_surface_tractogram_filtering.py'.
"""

EPILOG = """
References:
[1] St-Onge, E., Daducci, A., Girard, G. and Descoteaux, M. 2018.
    Surface-enhanced tractography (SET). NeuroImage.
"""


def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('surface',
                   help='Tractograms initial flow (.fib), \n' +
                        'one per surfaces, inputs order is important')

    p.add_argument('surface_flow',
                   help='Tractograms initial flow (.hdf5), \n' +
                        'one per surfaces, inputs order is important')

    p.add_argument('surface_intersections',
                   help="Surface intersections file (.npz)")

    p.add_argument('tractogram',
                   help="tractogram (.fib)")

    p.add_argument('output_tractogram',
                   help="out tractogram (.fib)")

    p.add_argument('--compression_rate', type=float, default=0.1,
                   help='Maximum compression in mm. [default: %(default)s]')

    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    """input_list = [args.surface_intersections, args.tractogram]
    input_list.extend(args.surfaces_flow)
    input_list.extend(args.surfaces)
    assert_inputs_exist(parser, required=input_list)
    assert_outputs_exists(parser, args, [args.output_tractogram])"""


    # Load intersections
    if args.surface_intersections.split(".")[-1].lower() == "npz":
        inters_ar = load_surface_intersections(args.surface_intersections)
    streamlines = vtk_u.load_streamlines(args.tractogram)

    # Load streamlines and flow
    surface_fib = vtk_u.load_streamlines(args.surface_flow)
    nb_fib = len(surface_fib)
    flow = np.reshape(np.stack(surface_fib), [nb_fib, -1, 3])
    mesh = load_mesh_from_file(args.surface)

    # Combine both ends of the flow to the streamlines
    new_streamlines = []
    for i in range(len(streamlines)):
        flow_before = None
        if inters_ar[0][i] == 1:
            flow_before = flow_from_intersection(inters_ar[1][i], inters_ar[2][i], mesh, flow)
        
        flow_after = None
        if inters_ar[3][i] == 1:
            flow_after = flow_from_intersection(inters_ar[4][i], inters_ar[5][i], mesh, flow)[::-1]  # reversed flow

        mid = streamlines[i]
        if flow_before is not None:
            if flow_after is not None:
                new_line = np.concatenate((flow_before, mid, flow_after))
            else:
                new_line = np.concatenate((flow_before, mid))
        elif flow_after is not None:
            new_line = np.concatenate((mid, flow_after))
        else:
            new_line = mid

        # Compress resulting streamlines, since data is to big
        new_streamlines.append(
            compress_streamlines(new_line, args.compression_rate))

    # Remove temporary files, and save results
    del flow, mesh, streamlines
    lines_polydata = vtk_u.lines_to_vtk_polydata(new_streamlines, None)
    vtk_u.save_polydata(lines_polydata, args.output_tractogram, True)


def flow_from_intersection(tri_id, pts, mesh, flow):
    tri = mesh.get_triangles()[tri_id]
    tri_vts = mesh.get_vertices()[tri]
    tri_coord = np.squeeze(
        get_trilinear_coordinates_from_vertices(
            tri_vts.reshape([1, 3, 3]),
            pts.reshape([1, 3]),
            force_inside=True))

    return (flow[tri[0]] * tri_coord[0]
            + flow[tri[1]] * tri_coord[1]
            + flow[tri[2]] * tri_coord[2])


if __name__ == "__main__":
    main()
