#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging

import numpy as np
from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist

from utils.seed import generate_seed_map_from_mesh


DESCRIPTION = """
Script to generate a surface seeding map (weighting per triangle on the surface)
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
                   help='Input surface (Freesurfer or supported by VTK)')

    p.add_argument('output_seed_triangle_map',
                   help="Surface map, one per triangle (.npy)")

    g_mask = p.add_mutually_exclusive_group()
    g_mask.add_argument('--vts_mask',
                        help='Mask for mesh vertices (boolean 1d np array)')
    g_mask.add_argument('--triangles_mask',
                        help='Mask for mesh triangles (boolean 1d np array)')
    g_mask.add_argument('--previous_density',
                        help='Map of the tracking resulting density map (1d np array)')
    g_mask.add_argument('--zeros_map', action='store_true',
                        help='Zeros map per triangles, to initialize (1d np array)')
    g_mask.add_argument('--sum_maps', nargs='+', default=[],
                        help='Sum given weights maps (1d np array)')

    g_weight = p.add_mutually_exclusive_group()
    g_weight.add_argument('--vts_weight',
                          help='Weight per vertex (1d numpy array)')
    g_weight.add_argument('--triangle_weight',
                          help='Weight per triangle (1d numpy array)')
    g_weight.add_argument('--triangle_area_weighting', action='store_true',
                          help='Weight per triangle area')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    assert_inputs_exist(
        parser,
        required=[args.surface],
        optional=[args.vts_mask, args.triangles_mask, args.vts_weight, args.triangle_weight]
    )

    assert_outputs_exist(parser, args, [args.output_seed_triangle_map])

    # Test input
    # Load mesh
    mesh = load_mesh_from_file(args.surface)

    # Weighting method
    vts_weight = None
    triangle_weight = None
    if args.vts_weight:
        vts_weight = np.load(args.vts_weight)
    elif args.triangle_weight:
        triangle_weight = np.load(args.triangle_weight)
    elif args.triangle_area_weighting:
        triangle_weight = mesh.triangles_area()

    # Surface seeding mask
    vts_mask = None
    triangles_mask = None
    if args.vts_mask:
        vts_mask = np.load(args.vts_mask)
    elif args.triangles_mask:
        triangles_mask = np.load(args.triangles_mask)
    elif args.previous_density:
        if triangle_weight is None:
            logging.error("previous_density need to be used with triangle_weight")

        prev_density = np.load(args.previous_density)
        sum_density = prev_density.sum()
        if sum_density > 0.0:
            prev_density /= sum_density

        triangle_weight /= triangle_weight.sum()
        triangle_weight -= prev_density
        triangle_weight[triangle_weight < 0.0] = 0.0

    elif args.zeros_map:
        zeros_map = np.zeros(mesh.get_nb_triangles())
        np.save(args.output_seed_triangle_map, zeros_map)
        return

    elif args.sum_maps:
        summed_map = np.zeros(mesh.get_nb_triangles())
        for file_name in args.sum_maps:
            summed_map += np.load(file_name)

        np.save(args.output_seed_triangle_map, summed_map)
        return

    # Generate Seed map
    tri_prob_map = generate_seed_map_from_mesh(
        mesh,
        vertices_weights=vts_weight,
        triangles_weights=triangle_weight,
        vertices_mask=vts_mask,
        triangles_mask=triangles_mask
    )

    np.save(args.output_seed_triangle_map, tri_prob_map)


if __name__ == "__main__":
    main()
