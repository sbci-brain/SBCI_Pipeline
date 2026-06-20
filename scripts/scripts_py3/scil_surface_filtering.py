#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import numpy as np

from dipy.tracking.streamlinespeed import length

from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import (
    add_overwrite_arg, assert_inputs_exist, assert_outputs_exist)
from utils import intersection as stools

from dipy.utils.optpkg import optional_package
vtk_u, _, _ = optional_package('trimeshpy.vtk_util')

DESCRIPTION = """
Script to filter streamlines, and intersections, based on lengths.

 >>> scil_surface_filtering.py D__Surface_Flow/*flow*.vtk \\
        F__Surface_Enhanced_Tractography/*_1_i0_filtered.npz \\
        F__Surface_Enhanced_Tractography/*_1_i0_filtered.fib \\
        2_to_66.fib --out_intersections 2_to_66.npz \\
        --surfaces_id B__Concatenate_Label/*unique_id.npy \\
        --indices0 2  --indices1  66
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

    p.add_argument('surface_intersections',
                   help='Input intersection map (.npz)')

    p.add_argument('tractograms',
                   help='Input tractograms (.vtk or .fib)')

    p.add_argument('output_tractogram',
                   help='Output tractograms')

    p.add_argument('--out_intersections',
                   help='Output intersection map (.npz)')

    p.add_argument('--min_length', type=float, default=10.0,
                   help='Minimum length of a streamline in mm. [%(default)s]')
    p.add_argument('--max_length', type=float, default=300.0,
                   help='Maximum length of a streamline in mm. [%(default)s]')

    p.add_argument('--surfaces_id',
                   help='Input surfaces id for surfaces base segmentation')
    p.add_argument('--indices0', type=int, nargs='+', default=None,
                   help='Starting indices surfaces_id, default: None=any indices')
    p.add_argument('--indices1', type=int, nargs='+', default=None,
                   help='Ending Indices surfaces_id, default: None=any indices')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    assert_inputs_exist(
        parser, required=[args.tractograms],
        optional=[args.surface_intersections])

    output_file_list = [args.output_tractogram]
    if args.out_intersections:
        output_file_list.append(args.out_intersections)
        
    assert_outputs_exist(parser, args, output_file_list)
        
    if args.out_intersections and (args.surface_intersections.split(".")[-1].lower() != args.out_intersections.split(".")[-1].lower()):
        parser.error('in/out intersections, need to have the same format')

    # Load streamlines
    streamlines = vtk_u.load_streamlines(args.tractograms)

    # Compute lengths and generate mask
    streamlines_length = length(streamlines)
    valid_length = np.logical_and(streamlines_length > args.min_length,
                                  streamlines_length < args.max_length)

    # Load intersections
    inters_arrays = stools.load_surface_intersections(args.surface_intersections)

    mesh = load_mesh_from_file(args.surface)

    # Load Surfaces ID (e.g. labels)
    if args.surfaces_id:
        surfaces_id = np.load(args.surfaces_id)
        valid_id = stools.concatenated_intersections_filtering(
            mesh, inters_arrays[1], inters_arrays[4], surfaces_id,
            args.indices0, args.indices1)
        valid_streamlines = np.logical_and(valid_length, valid_id)
    else:
        valid_streamlines = valid_length

    # Filter and save streamlines
    filtered_streamlines = [streamlines[i] for i in range(len(streamlines))
                            if valid_streamlines[i]]
    
    lines_polydata = vtk_u.lines_to_vtk_polydata(filtered_streamlines, None)
    vtk_u.save_polydata(lines_polydata, args.output_tractogram, True)
    del streamlines, filtered_streamlines, lines_polydata

    if args.out_intersections:
        inters_arrays_out = []
        for curr_array in inters_arrays:
            valit_inter = curr_array[valid_streamlines]
            inters_arrays_out.append(valit_inter)
        stools.save_surface_intersections(args.out_intersections,
                                          *inters_arrays_out)


if __name__ == "__main__":
    main()
