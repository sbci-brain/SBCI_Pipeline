#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging

import numpy as np
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist

from utils.intersection import REMOVED_INDICES


DESCRIPTION = """
Script to concatenate surfaces map together in a single array (npy).
If used with --unique_id, return a --out_id_map for connectivity matrices;
  the "intersections_mask.npy", can be used for a single unique id per input.
"""

EPILOG = """
References:
[1] St-Onge, E., Daducci, A., Girard, G. and Descoteaux, M. 2018.
    Surface-enhanced tractography (SET). NeuroImage.
"""


def buildArgsParser():
    p = argparse.ArgumentParser(description=DESCRIPTION, epilog=EPILOG,
                                formatter_class=argparse.RawTextHelpFormatter)

    p.add_argument('surfaces_map', nargs='+',
                   help='Input surface maps, '
                        'concatenate array along the first axis (npy)')

    p.add_argument('-o', '--out_map', required=True,
                   help='Output combined surface (npy) map; *using input order'
                        '\n [{surfaces}, {inner_surfaces}, {outer_surfaces}]')

    p.add_argument('--inner_surfaces_map', nargs='+', default=[],
                   help='Input inner surfaces maps; i.e. gray nuclei, ROI'
                        '(supported by VTK)')

    p.add_argument('--outer_surfaces_map', nargs='+', default=[],
                   help='Input outer surfaces; i.e. gray matter, ventricles'
                        '(supported by VTK)')

    # Unique ID, for connectivity mapping
    p.add_argument('--unique_id', action='store_true',
                   help='Output unique ID, id save values are used')

    p.add_argument('--out_id_map',
                   help='If unique_id is used, output ID mapping (.txt)')

    p.add_argument('--indices_to_remove', type=int, nargs='+', default=[],
                   help='indices to remove, e.g. "-1 0" for Freesurfer annot'
                        ' removed value will be put to "-1"')

    p.add_argument('--removed_id_val', type=int, default=REMOVED_INDICES,
                   help='ID for removed indices [%(default)s]')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()

    assert_inputs_exist(parser, required=args.surfaces_map, optional=args.inner_surfaces_map + args.outer_surfaces_map)
    assert_outputs_exist(parser, args, [args.out_map], optional=[args.out_id_map])

    all_maps_file = args.surfaces_map + args.inner_surfaces_map + args.outer_surfaces_map

    if args.out_id_map and not args.unique_id:
        logging.error("--out_id_map should be used with --unique_id")

    if args.indices_to_remove and not args.unique_id:
        logging.error("--indices_to_remove should be used with --unique_id")

    vts_coo_id = []
    id_map_info = ""
    if not args.unique_id:
        for s_map in all_maps_file:
            vts_label = np.load(s_map)
            vts_coo_id.append(vts_label)

    else:
        current_id = 0
        for s_map in all_maps_file:
            vts_label = np.load(s_map).astype(np.int64)

            # Put Max value for int, to masked values
            vts_label_mask = ~np.in1d(vts_label, args.indices_to_remove + [args.removed_id_val])

            # replace all  args.indices_to_remove  to  args.removed_id_val
            new_vts_label = np.full_like(vts_label, args.removed_id_val)

            # Get the number of label, with their id
            u, vts_uid = np.unique(vts_label[vts_label_mask], return_inverse=True)
            nb_u = len(u)
            vts_uid += current_id
            new_vts_label[vts_label_mask] = vts_uid

            vts_coo_id.append(new_vts_label)

            # Save info
            id_map_info += s_map + "\n "
            id_map_info += str(np.arange(current_id, current_id + nb_u)) + "\n "
            id_map_info += str(u) + "\n"

            # Update the current label id
            current_id += nb_u

    combined_map = np.concatenate(vts_coo_id)
    np.save(args.out_map, combined_map)

    if args.out_id_map:
        np.savetxt(args.out_id_map, [id_map_info], fmt="%s")


if __name__ == "__main__":
    main()
