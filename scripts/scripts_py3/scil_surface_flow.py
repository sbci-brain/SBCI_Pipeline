#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
from os.path import splitext

import numpy as np
from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist


DESCRIPTION = """
Script to compute the surface positive constrained mass-stiffness flow [1].
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

    p.add_argument('out_surface',
                   help='Output surface (formats supported by VTK)')

    p.add_argument('-m', '--vts_mask',
                   help='Vertices mask, where to apply the flow (.npy)')

    p.add_argument('-n', '--nb_steps', type=int, default=100,
                   help='Number of steps for the flow [%(default)s]')

    p.add_argument('-s', '--step_size', type=float, default=1.0,
                   help='Flow step size [%(default)s]')

    p.add_argument('--out_flow',
                   help='Resulting surface flow (.hdf5)')

    # advanced Options
    p.add_argument('--subsample_flow', type=int, default=1,
                   help='subsample to flow output to reduce file size')

    p.add_argument('--gaussian_threshold', type=float, default=0.2,
                   help='DEBUG TOOL, advance only')

    p.add_argument('--angle_threshold', type=float, default=2,
                   help='DEBUG TOOL, advance only')

    p.add_argument('-v', action='store_true', dest='verbose',
                   help='Print the filtering information')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    assert_inputs_exist(parser, required=[args.surface], optional=[args.vts_mask])

    assert_outputs_exist(parser, args, [args.out_surface], optional=[args.out_flow])

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Check smoothing parameters
    if args.nb_steps < 4:
        parser.error("Number of steps should be 4 or higher")

    if args.step_size <= 0.0:
        parser.error("Step size should be strictly positive")

    if args.out_flow and splitext(args.out_flow)[1].lower() != ".hdf5":
        parser.error("Out flow must be in '.fib' format")

    # Load mesh
    mesh = load_mesh_from_file(args.surface)

    # Step size (zero for masked vertices)
    step_size_per_vts = args.step_size
    if args.vts_mask:
        mask = np.load(args.vts_mask)
        step_size_per_vts *= mask.astype(np.float64)

    # Memmap file name for the flow
    if args.out_flow:
        flow_file = args.out_flow
    else:
        flow_file = None

    # Compute Surface Flow
    vts = mesh.positive_mass_stiffness_smooth(
        nb_iter=args.nb_steps,
        diffusion_step=step_size_per_vts,
        flow_file=flow_file,
        gaussian_threshold=args.gaussian_threshold,
        angle_threshold=args.angle_threshold,
        subsample_file=args.subsample_flow)

    # Update vertices and save mesh
    mesh.set_vertices(vts)
    mesh.save(args.out_surface)


if __name__ == "__main__":
    main()
