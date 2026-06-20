#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

import numpy as np
import trimeshpy
from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist
from utils.intersection import Surface_type


DESCRIPTION = """
Script to concatenate surfaces together in a single file (vtk or freesurfer).
"""

EPILOG = """
References:
[1] St-Onge, E., Daducci, A., Girard, G. and Descoteaux, M. 2018.
    Surface-enhanced tractography (SET). NeuroImage.
"""


def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('surfaces', nargs='+',
                   help='Input basic surfaces; i.e. white matter'
                        '(supported by VTK)')

    p.add_argument('-o', '--out_concatenated_surface', required=True,
                   help='Output Concatenated surface * Ordered with input order'
                        '\n [{surfaces}, {inner_surfaces}, {outer_surfaces}]')

    p.add_argument('--out_surface_id',
                   help='Output surface id (one per vertex) (.npy)')

    p.add_argument('--inner_surfaces', nargs='+', default=[],
                   help='Input inner surfaces; i.e. gray nuclei, ROI'
                        '(supported by VTK)')

    p.add_argument('--outer_surfaces', nargs='+', default=[],
                   help='Input outer surfaces; i.e. gray matter, ventricles'
                        '(supported by VTK)')

    p.add_argument('--out_surface_type_map',
                   help='Output surface type (one per vertex) (.npy)')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    assert_inputs_exist(parser, required=args.surfaces, optional=args.inner_surfaces + args.outer_surfaces)
    assert_outputs_exist(parser, args, [args.out_concatenated_surface],
                         optional=[args.out_surface_id, args.out_surface_type_map])

    vts_list = []
    tri_list = []
    id_list = []
    surface_type_list = []

    current_nb_vts = 0
    all_surfaces = args.surfaces + args.inner_surfaces + args.outer_surfaces
    s_types = (list(Surface_type.BASE * np.ones(len(args.surfaces)))
               + list(Surface_type.INNER * np.ones(len(args.inner_surfaces)))
               + list(Surface_type.OUTER * np.ones(len(args.outer_surfaces))))

    for i in range(len(all_surfaces)):
        mesh = load_mesh_from_file(all_surfaces[i])
        nb_vts = mesh.get_nb_vertices()
        vts_list.append(mesh.get_vertices())
        tri_list.append(mesh.get_triangles() + current_nb_vts)
        id_list.append(i * np.ones([nb_vts]))

        surface_type_list.append(s_types[i] * np.ones([nb_vts]))

        current_nb_vts += nb_vts

    all_vts = np.vstack(vts_list)
    all_tris = np.vstack(tri_list)
    c_mesh = trimeshpy.TriMesh_Vtk(all_tris, all_vts)
    c_mesh.save(args.out_concatenated_surface)

    if args.out_surface_id:
        np.save(args.out_surface_id, np.hstack(id_list))

    if args.out_surface_type_map:
        np.save(args.out_surface_type_map, np.hstack(surface_type_list))


if __name__ == "__main__":
    main()
