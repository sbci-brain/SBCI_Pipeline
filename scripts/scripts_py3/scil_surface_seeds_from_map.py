#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import logging

import numpy as np

from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist
from utils.seed import generate_seeds_from_map, save_surface_seeds

DESCRIPTION = """
Script to generate surface seeds from a seeding map 
    generated from "scil_surface_seed_map.py"
"""

EPILOG = """
References:
[1] St-Onge, E., Daducci, A., Girard, G. and Descoteaux, M. 2018.
    Surface-enhanced tractography (SET). NeuroImage.
"""


def check_surface_seed_support(parser, path):
    extension = os.path.splitext(path)[1].lower()
    if extension != ".npz":
        parser.error('Format of "{}" not supported.'.format(path))


def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('surface',
                   help='Input surface (Freesurfer or supported by VTK)')

    p.add_argument('seed_map',
                   help='Input seeding map (.npy)')

    p.add_argument('nb_seed', type=int,
                   help='Number of seeds to generate')

    p.add_argument('output_seeds',
                   help="Surface seeds file (.npz) ['tri_idx', 'tri_coord']")

    p.add_argument('-r', '--random_number_generator', type=int, default=0,
                   help='Seeds random number generator [default: %(default)s]')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    assert_inputs_exist(parser, required=[args.surface, args.seed_map])

    assert_outputs_exist(parser, args, [args.output_seeds])
    check_surface_seed_support(parser, args.output_seeds)

    # Load mesh
    mesh = load_mesh_from_file(args.surface)
    tri_prob_map = np.load(args.seed_map)

    # Generate Seeds
    tri_idx, tri_coord = generate_seeds_from_map(mesh, tri_prob_map, args.nb_seed, args.random_number_generator)

    save_surface_seeds(args.output_seeds, tri_idx, tri_coord)


if __name__ == "__main__":
    main()
