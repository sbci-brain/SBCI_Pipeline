#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scil_surface_from_volume.py  —  Python 3 port / replacement for the
scilpy 1.x command of the same name (removed from scilpy 2.x).

Extracts an isosurface from a labelled volumetric image (NIfTI) and saves it
as a VTK PolyData mesh.  Mirrors the SBCI-pipeline calling convention:

  scil_surface_from_volume.py <volume.nii.gz> <output.vtk>
      --index  <label_value>
      --closing <n>          (morphological closing iterations)
      --opening <n>          (morphological opening iterations)
      --smooth  <n>          (Laplacian smoothing iterations)
      --vox2vtk              (convert voxel coords → scanner/mm coords)
      --fill                 (fill internal holes before meshing)
      --max_label            (use highest label instead of --index if set)
      -f                     (overwrite output)
"""

import argparse
import logging
import numpy as np
import nibabel as nib
import vtk
import vtk.util.numpy_support as ns

from scipy import ndimage
from os.path import isfile

DESCRIPTION = __doc__


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('volume',
                   type=str, help='Input labelled volume (.nii / .nii.gz).')

    p.add_argument('output',
                   type=str, help='Output surface mesh (.vtk).')

    p.add_argument('--index', type=int, default=None,
                   help='Label index to extract as a surface.')

    p.add_argument('--closing', type=int, default=0,
                   help='Number of morphological closing iterations [%(default)s].')

    p.add_argument('--opening', type=int, default=0,
                   help='Number of morphological opening iterations [%(default)s].')

    p.add_argument('--smooth', type=int, default=0,
                   help='Number of Laplacian surface smoothing iterations [%(default)s].')

    p.add_argument('--vox2vtk', action='store_true',
                   help='Convert vertex coordinates from voxel to scanner (mm) space.')

    p.add_argument('--fill', action='store_true',
                   help='Fill internal holes in the binary mask before meshing.')

    p.add_argument('--max_label', action='store_true',
                   help='Extract the label with the highest index value in the volume '
                        '(overrides --index).')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def _binary_mask(data, index):
    """Return a boolean mask for voxels matching *index*."""
    return (data == index).astype(np.uint8)


def _morphological_ops(mask, closing=0, opening=0, fill=False):
    """Apply closing, opening, and optional hole-filling to a binary mask."""
    struct = ndimage.generate_binary_structure(3, 1)   # 6-connectivity

    if closing > 0:
        for _ in range(closing):
            mask = ndimage.binary_dilation(mask, structure=struct).astype(np.uint8)
        for _ in range(closing):
            mask = ndimage.binary_erosion(mask, structure=struct).astype(np.uint8)

    if opening > 0:
        for _ in range(opening):
            mask = ndimage.binary_erosion(mask, structure=struct).astype(np.uint8)
        for _ in range(opening):
            mask = ndimage.binary_dilation(mask, structure=struct).astype(np.uint8)

    if fill:
        # flood-fill from a corner to find background, invert = interior holes
        filled = ndimage.binary_fill_holes(mask.astype(bool))
        mask = filled.astype(np.uint8)

    return mask


def _marching_cubes(mask, affine, vox2vtk):
    """Run VTK marching cubes on *mask* and return vtkPolyData."""
    # Build a vtkImageData from the numpy mask
    dims = mask.shape

    img_data = vtk.vtkImageData()
    img_data.SetDimensions(dims[0], dims[1], dims[2])
    img_data.SetSpacing(1.0, 1.0, 1.0)
    img_data.SetOrigin(0.0, 0.0, 0.0)

    flat = mask.flatten(order='F').astype(np.float32)
    vtk_arr = ns.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_FLOAT)
    vtk_arr.SetName('mask')
    img_data.GetPointData().SetScalars(vtk_arr)

    # Marching cubes at iso-value 0.5
    mc = vtk.vtkMarchingCubes()
    mc.SetInputData(img_data)
    mc.SetValue(0, 0.5)
    mc.Update()

    surface = mc.GetOutput()

    if surface.GetNumberOfPoints() == 0:
        raise RuntimeError('Marching cubes produced no surface — '
                           'check that the label exists in the volume.')

    # Optionally transform vertices from voxel indices to scanner (mm) coords
    if vox2vtk and affine is not None:
        pts_np = ns.vtk_to_numpy(surface.GetPoints().GetData())

        # pts_np are ijk (col-major / VTK ordering) — convert to RAS mm
        ones = np.ones((pts_np.shape[0], 1), dtype=pts_np.dtype)
        pts_h = np.hstack([pts_np, ones])
        pts_mm = (affine @ pts_h.T).T[:, :3]

        vtk_pts = vtk.vtkPoints()
        vtk_pts.SetData(ns.numpy_to_vtk(pts_mm.astype(np.float32), deep=True))
        surface.SetPoints(vtk_pts)

    return surface


def _smooth_surface(surface, n_iter):
    """Apply Laplacian smoothing to *surface* for *n_iter* iterations."""
    if n_iter <= 0:
        return surface

    smoother = vtk.vtkSmoothPolyDataFilter()
    smoother.SetInputData(surface)
    smoother.SetNumberOfIterations(n_iter)
    smoother.Update()

    return smoother.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    if not isfile(args.volume):
        parser.error('The file "{0}" must exist.'.format(args.volume))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(
                args.output))

    logging.info('Loading volume: {0}'.format(args.volume))
    img = nib.load(args.volume)
    data = np.asarray(img.dataobj).astype(np.int32)
    affine = img.affine

    # Determine which label to extract
    if args.max_label:
        index = int(data.max())
        logging.info('Using max label: {0}'.format(index))
    elif args.index is not None:
        index = args.index
    else:
        parser.error('Must specify --index <label> or --max_label.')

    logging.info('Extracting label {0} ...'.format(index))
    mask = _binary_mask(data, index)

    if mask.sum() == 0:
        parser.error('Label {0} is not present in the volume.'.format(index))

    mask = _morphological_ops(mask, closing=args.closing,
                              opening=args.opening, fill=args.fill)

    logging.info('Running marching cubes ...')
    surface = _marching_cubes(mask, affine, vox2vtk=args.vox2vtk)

    if args.smooth > 0:
        logging.info('Smoothing surface ({0} iterations) ...'.format(args.smooth))
        surface = _smooth_surface(surface, args.smooth)

    logging.info('Saving surface: {0}  ({1} pts, {2} cells)'.format(
        args.output,
        surface.GetNumberOfPoints(),
        surface.GetNumberOfCells()))

    writer = vtk.vtkPolyDataWriter()
    writer.SetInputData(surface)
    writer.SetFileName(args.output)
    writer.Update()


if __name__ == '__main__':
    main()
