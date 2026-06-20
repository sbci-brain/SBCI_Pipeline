#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging

import nibabel as nib
from nibabel.freesurfer.io import read_annot, read_label, read_morph_data
import numpy as np
from trimeshpy.io import load_mesh_from_file
from scilpy.io.utils import add_overwrite_arg, assert_inputs_exist, assert_outputs_exist
from trimeshpy import vtk_util as vtk_u


DESCRIPTION = """
Script to load cortical surface (vtk or freeSurfer),
to afterward visualize with mask or labels (annot).
This script can also smooth surfaces, save vts masks.
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

    # Vertices mask (is applied on all input vertices metrics)
    p.add_argument('--vts_mask', help='Input vertices mask \n' +
                   ' is applied on other vertices metrics')

    # Labels, masks or metrics,
    group = p.add_mutually_exclusive_group()
    group.add_argument('-a', '--annot', help='Input annot')
    group.add_argument('-l', '--label', help='Input label')
    group.add_argument('-m', '--morph', help='Morph label')
    group.add_argument('--vts_scalar', help='Input vertices scalar')
    group.add_argument('--vts_color', help='Input vertices color')
    group.add_argument('--vts_label', help='Input vertices label')
    group.add_argument('--image_mask', help='Input image mask')
    group.add_argument('--vts_val', type=float, default=None,
                       help='Input a single value')

    p.add_argument('-i', '--indices', type=int, nargs='+',
                   help='Color only the selected annot (generate mask)')

    p.add_argument('--inverse_mask', action='store_true',
                   help='Exclude chosen index (inverse mask)')

    # Outputs
    p.add_argument('--save_vts_mask',
                   help='Output masked vertices (boolean 1d numpy array),' +
                   ' from selected indices')

    p.add_argument('--save_vts_scalar',
                   help='Output vertices scalar (float 1d numpy array),' +
                   ' could be used for seeding weights or scalar plot')

    p.add_argument('--save_vts_color',
                   help='Output vertices color (float 2d numpy array),' +
                   ' shape:[nb_vts,3] -> [0-255]')

    p.add_argument('--save_vts_label',
                   help='Output vertices labels (int 1d numpy array)')

    p.add_argument('--masked_labels_value', type=int, default=0,
                   help='Output vertices labels (int 1d numpy array)')

    # Visualization
    viz_g = p.add_mutually_exclusive_group()
    viz_g.add_argument('-v', '--visualize', action='store_true',
                       help='Visualize surface with VTK')

    viz_g.add_argument('--save_image',
                       help='save the resulting image (png)')

    p.add_argument('--no_scalar_for_masked', action='store_true',
                   help='Unselected scalar (masked) vertices are removed from '
                        'scalar visualisation (no color in the lookup table)')

    p.add_argument('--no_scalar_at', type=float, default=None,
                   help='Given value is removed from scalar visualisation'
                        '(no color in the lookup table), 0 is often chosen')

    p.add_argument('--white', action='store_true',
                   help='Visualize selected indices with white')

    add_overwrite_arg(p)
    return p


def main():
    parser = buildArgsParser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    assert_inputs_exist(
        parser, required=[args.surface],
        optional=[args.vts_mask, args.annot, args.label, args.morph, args.vts_scalar, args.vts_color, args.vts_label,
                  args.image_mask]
    )

    output_file_list = []
    if args.save_vts_mask:
        output_file_list.append(args.save_vts_mask)
    if args.save_vts_scalar:
        output_file_list.append(args.save_vts_scalar)
    if args.save_vts_label:
        output_file_list.append(args.save_vts_label)
    if args.save_vts_color:
        output_file_list.append(args.save_vts_color)

    if output_file_list:
        assert_outputs_exist(parser, args, output_file_list)
    elif not (args.visualize or args.save_image):
        parser.error('No output to be done')

    if args.indices and not (args.annot or args.vts_label):
        logging.warning("IGNORED --indices; no --annot specified")

    # Load mesh
    mesh = load_mesh_from_file(args.surface)

    # Init vertices array: mask, color scalar
    selected_vts = None
    vts_scalar = None
    vts_color = None
    vts_label = None

    # Load vertices mask
    if args.vts_mask:
        if args.vts_mask.split(".")[-1].lower() == "npy":
            selected_vts = np.load(args.vts_mask).astype(np.bool_)
        else:
            selected_vts = np.loadtxt(args.vts_mask, dtype=np.bool_)

        if len(selected_vts) != mesh.get_nb_vertices():
            logging.warning("Warning len(args.vts_mask) != nb_vertices()")
            selected_vts = selected_vts[:mesh.get_nb_vertices()]

    # Load vertices based map
    if args.annot or args.vts_label:
        if args.annot:
            # Load labels, color and name from the annot file
            [vts_label, label_color, label_name] = read_annot(args.annot)
            vts_color = label_color[:, :3][vts_label]

        elif args.vts_label:
            # Load labels
            if args.vts_label.split(".")[-1].lower() == "npy":
                vts_label = np.load(args.vts_label)
            else:
                vts_label = np.loadtxt(args.vts_label, dtype=np.int64)

            if len(vts_label) != mesh.get_nb_vertices():
                # Resize to vts length
                logging.warning("Warning len(args.vts_label) != nb_vertices()")
                vts_label = vts_label[:mesh.get_nb_vertices()]

            # Generate label color
            unique_label = np.unique(vts_label)
            nb_label = len(unique_label)
            label_color = np.random.randint(0, 255, (nb_label, 3))
            vts_color = np.zeros([mesh.get_nb_vertices(), 3])

            for i in range(nb_label):
                label_i = unique_label[i]
                vts_color[vts_label == label_i] = label_color[i]

        if args.indices:
            annot_vts = np.zeros([len(vts_label)], dtype=np.bool_)
            for index in args.indices:
                annot_vts = np.logical_or(annot_vts, (vts_label == index))
        else:
            annot_vts = np.ones([len(vts_label)], dtype=np.bool_)

        if selected_vts is not None:
            selected_vts = np.logical_and(selected_vts, annot_vts)
        else:
            selected_vts = annot_vts

    elif args.label:
        [labeled_vts, labeled_scalars] = read_label(args.label, True)
        vts_scalar = np.zeros([mesh.get_nb_vertices()])
        vts_scalar[labeled_vts] = labeled_scalars

    elif args.morph:
        vts_scalar = read_morph_data(args.morph)

    elif args.vts_scalar:
        if args.vts_scalar.split(".")[-1].lower() == "npy":
            vts_scalar = np.load(args.vts_scalar)
        else:
            vts_scalar = np.loadtxt(args.vts_scalar, dtype=np.float64)

        if len(vts_scalar) != mesh.get_nb_vertices():
            logging.warning("Warning len(args.vts_scalar) != nb_vertices() ")
            vts_scalar = vts_scalar[:mesh.get_nb_vertices()]

    elif args.vts_color:
        if args.vts_color.split(".")[-1].lower() == "npy":
            vts_color = np.load(args.vts_color)
        else:
            vts_color = np.loadtxt(args.vts_color, dtype=np.float64)

        if len(vts_color) != mesh.get_nb_vertices():
            logging.warning("Warning len(args.vts_color) != nb_vertices() ")
            vts_color = vts_color[:mesh.get_nb_vertices()]

    elif args.image_mask:
        img_mask = nib.load(args.image_mask)
        img_shape = img_mask.get_fdata().shape
        img_data = np.squeeze(img_mask.get_fdata()).astype(np.bool_)

        vox_3d_id = np.rint(
            vtk_u.vtk_to_vox(mesh.get_vertices(), img_mask)).astype(np.int64)
        vox_1d_id = np.ravel_multi_index(vox_3d_id.T, img_shape)
        img_vts = img_data.flat[vox_1d_id]

        if selected_vts is not None:
            selected_vts = np.logical_and(selected_vts, img_vts)
        else:
            selected_vts = img_vts

    elif args.vts_val is not None:
        if selected_vts is not None:
            vts_scalar = np.zeros([mesh.get_nb_vertices()], dtype=np.float64)
            vts_scalar[selected_vts] = args.vts_val
        else:
            vts_scalar = args.vts_val * np.ones([mesh.get_nb_vertices()])
        selected_vts = vts_scalar.astype(np.bool_)

    if selected_vts is not None:
        if args.inverse_mask:
            selected_vts = np.logical_not(selected_vts)

        if vts_scalar is not None:
            vts_scalar[np.logical_not(selected_vts)] = 0.0

        if vts_label is not None:
            vts_label[np.logical_not(selected_vts)] = args.masked_labels_value

        if vts_color is None:
            vts_color = np.zeros([mesh.get_nb_vertices(), 3])
            vts_color[selected_vts] = [255, 255, 255]
        elif args.white:
            vts_color[selected_vts] = [255, 255, 255]

        vts_color[np.logical_not(selected_vts)] = [0, 0, 0]

    if args.save_vts_mask:
        if selected_vts is not None:
            np.save(args.save_vts_mask, selected_vts)
        else:
            logging.error("No vertices mask to save")

    if args.save_vts_scalar:
        if vts_scalar is not None:
            np.save(args.save_vts_scalar, vts_scalar)
        else:
            logging.error("No vertices scalar to save")

    if args.save_vts_label:
        if vts_label is not None:
            np.save(args.save_vts_label, vts_label)
        else:
            logging.error("No vertices labels to save")

    if args.save_vts_color:
        if vts_color is not None:
            np.save(args.save_vts_color, vts_color)
        else:
            logging.error("No vertices color to save")

    # Visualize
    if args.visualize or args.save_image:
        # Display scalar or color
        if vts_scalar is not None:
            if args.no_scalar_for_masked and selected_vts is not None:
                vts_scalar[np.logical_not(selected_vts)] = np.nan
            if args.no_scalar_at is not None:
                vts_scalar[np.isclose(vts_scalar, args.no_scalar_at)] = np.nan
            mesh.set_scalars(vts_scalar)
        elif vts_color is not None:
            mesh.set_colors(vts_color)
        if args.visualize:
            mesh.display()
        elif args.save_image:
            mesh.save_png(args.save_image)


if __name__ == "__main__":
    main()
