#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scil_surface_map_from_volume.py  —  Python 3 port / replacement for the
scilpy 1.x command of the same name (removed from scilpy 2.x).

For each vertex of a VTK surface, samples the nearest voxel value from a
NIfTI volume and saves the result as a .npy array.  Mirrors the SBCI-pipeline
calling convention:

  scil_surface_map_from_volume.py <surface.vtk> <volume.nii.gz> <output.npy>
      --binarize                 (convert to binary mask)
      --binarize_value <thresh>  (threshold for binarization; default 0.5)
      -f                         (overwrite output)
"""

import argparse
import logging
import numpy as np
import nibabel as nib
import vtk
import vtk.util.numpy_support as ns

from os.path import isfile

DESCRIPTION = __doc__


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('surface',
                   type=str, help='Input surface mesh (.vtk).')

    p.add_argument('volume',
                   type=str, help='Input volume image (.nii / .nii.gz).')

    p.add_argument('output',
                   type=str, help='Output per-vertex map (.npy).')

    p.add_argument('--binarize', action='store_true',
                   help='Convert sampled values to a binary (0/1) mask.')

    p.add_argument('--binarize_value', type=float, default=0.5,
                   help='Threshold for binarization — voxels >= this value '
                        'are set to 1 [%(default)s].')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def _load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    if not isfile(args.volume):
        parser.error('The file "{0}" must exist.'.format(args.volume))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(
                args.output))

    # Load surface
    logging.info('Loading surface: {0}'.format(args.surface))
    polydata = _load_vtk(args.surface)
    n_pts = polydata.GetNumberOfPoints()
    vertices = ns.vtk_to_numpy(polydata.GetPoints().GetData())   # (N, 3) mm coords

    # Load volume
    logging.info('Loading volume: {0}'.format(args.volume))
    img = nib.load(args.volume)
    data = np.asarray(img.dataobj, dtype=np.float64)
    inv_affine = np.linalg.inv(img.affine)

    # Sample volume at each vertex using nearest-neighbour interpolation
    ones = np.ones((n_pts, 1), dtype=np.float64)
    verts_h = np.hstack([vertices.astype(np.float64), ones])      # (N, 4)
    ijk = (inv_affine @ verts_h.T).T[:, :3]                       # fractional voxel coords

    # Round to nearest voxel and clip to valid range
    shape = np.array(data.shape[:3])
    ijk_round = np.clip(np.round(ijk).astype(int), 0, shape - 1)

    values = data[ijk_round[:, 0], ijk_round[:, 1], ijk_round[:, 2]]

    # Optionally binarize
    if args.binarize:
        values = (values >= args.binarize_value).astype(np.float64)

    logging.info('Sampled {0} vertex values. Saving → {1}'.format(n_pts, args.output))
    np.save(args.output, values)


if __name__ == '__main__':
    main()
