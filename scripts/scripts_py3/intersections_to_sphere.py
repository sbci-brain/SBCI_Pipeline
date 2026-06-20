#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python 3 port of SBCI_Pipeline/scripts/intersections_to_sphere.py
#
# Maps SET streamline endpoint intersections (on the WM surface) to the
# registration sphere (lh/rh_sphere_reg_norm.vtk) and saves the sphere
# coordinates as sphere_intersections.npz for downstream use by
# get_fibers_barycentric.py.
#
# Key design notes (learned from data diagnostics):
#
#   1. VALID FILTER — surface TYPE, not hemisphere
#      surf_ids0/surf_ids1 in the filtered intersections encode the
#      SURFACE TYPE stored in surfaces_type.npy:
#          1  = white-matter surface (both LH and RH)
#          2+ = subcortical ROI surfaces
#      Filter: keep only intersections where BOTH endpoints are on white
#      matter (surf_ids0 == 1 AND surf_ids1 == 1).
#
#   2. HEMISPHERE — derived from triangle index
#      The hemisphere (LH=0, RH=1) is determined from surfaces_id.npy:
#      LH white cells come first in surfaces.vtk (indices 0..lh_n-1),
#      RH white cells follow (indices lh_n..lh_n+rh_n-1).
#      We build tri_to_hemi[global_tri_id] = 0/1/-1 from surfaces_id.npy.
#
#   3. BARYCENTRIC MAPPING — same triangle index convention
#      The WM white surface and lh/rh_sphere_reg share the same
#      vertex/triangle topology (FreeSurfer guarantee: same count, same
#      ordering).  Triangle local index i on the WM surface is the same
#      anatomical region as triangle i on sphere.reg.
#      Given barycentric coords in WM triangle i → apply to sphere.reg
#      triangle i → normalise to unit sphere.
#
#   4. IMPLEMENTATION — fully vectorised numpy, no per-cell VTK calls.

import argparse
import logging
import numpy as np
import vtk
import vtk.util.numpy_support as ns

from os.path import isfile

DESCRIPTION = """
  Map SET intersection endpoints from the WM surface to the registration
  sphere and save as sphere_intersections.npz.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)
    p.add_argument('--lh_reg_surface', required=True,
                   help='LH registration sphere (lh_sphere_reg_norm.vtk).')
    p.add_argument('--rh_reg_surface', required=True,
                   help='RH registration sphere (rh_sphere_reg_norm.vtk).')
    p.add_argument('--set_surfaces', required=True,
                   help='Full concatenated SET surface (surfaces.vtk).')
    p.add_argument('--set_surface_map', required=True,
                   help='surfaces_id.npy — vertex → surface-ID (0=LH white, '
                        '1=RH white, 2+=other).')
    p.add_argument('--intersections', required=True,
                   help='Filtered intersections .npz '
                        '(tri_ids0, pts0, surf_ids0, ...).')
    p.add_argument('--output', required=True,
                   help='Output sphere_intersections.npz.')
    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='Overwrite output if it already exists.')
    return p


def _load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()


def _mesh_arrays(polydata):
    """Return (vertices, triangles) as numpy arrays from a vtkPolyData."""
    verts = ns.vtk_to_numpy(polydata.GetPoints().GetData()).astype(np.float64)
    raw   = ns.vtk_to_numpy(polydata.GetPolys().GetData())
    tris  = np.vstack([raw[1::4], raw[2::4], raw[3::4]]).T.astype(np.int64)
    return verts, tris


def _bary_coords_batch(tri_verts, pts):
    """
    Barycentric coordinates for N points in N triangles.
    tri_verts : (N, 3, 3)
    pts       : (N, 3)
    Returns   : (N, 3)
    """
    v0 = tri_verts[:, 1] - tri_verts[:, 0]
    v1 = tri_verts[:, 2] - tri_verts[:, 0]
    normals = np.cross(v0, v1)
    area2   = np.einsum('ij,ij->i', normals, normals)
    safe_a  = np.maximum(area2, 1e-28)
    nhat    = normals / safe_a[:, None]

    bary = np.empty((len(pts), 3), dtype=np.float64)
    for k in range(3):
        edge = np.cross(pts - tri_verts[:, (k+1) % 3],
                        pts - tri_verts[:, (k+2) % 3])
        bary[:, k] = np.einsum('ij,ij->i', edge, nhat)

    return bary


def _check_local_ids(name, local_ids, mask, n_cells, parser):
    bad = mask & ((local_ids < 0) | (local_ids >= n_cells))
    if np.any(bad):
        first = int(np.flatnonzero(bad)[0])
        parser.error(
            '{0}: local triangle id {1} is outside [0, {2}) at endpoint index {3}.'.format(
                name, int(local_ids[first]), int(n_cells), first))


def main():
    parser = _build_args_parser()
    args   = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    for fname in [args.lh_reg_surface, args.rh_reg_surface,
                  args.set_surfaces, args.set_surface_map, args.intersections]:
        if not isfile(fname):
            parser.error('The file "{0}" must exist.'.format(fname))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite.'.format(
                args.output))

    # ------------------------------------------------------------------ #
    #  Load surfaces                                                       #
    # ------------------------------------------------------------------ #
    logging.info('Loading surfaces.')

    # surfaces_id.npy: vertex → surface ID (0=LH white, 1=RH white, 2+=other)
    surface_map = np.load(args.set_surface_map)
    all_surf    = _load_vtk(args.set_surfaces)

    # All triangles from the concatenated surface
    all_verts, all_tris = _mesh_arrays(all_surf)
    n_tris = len(all_tris)

    # ── triangle → hemisphere map ────────────────────────────────────────
    # LH white cells: surface_map == 0 for ALL 3 vertices
    # RH white cells: surface_map == 1 for ALL 3 vertices
    tri_to_surface = np.zeros(n_tris, dtype=np.int64)
    for sid in np.unique(surface_map):
        mask     = (surface_map == sid)
        tri_mask = np.any(mask[all_tris], axis=1)
        tri_to_surface[tri_mask] = sid

    # ── per-hemisphere: local vertices + triangles ───────────────────────
    wm_verts = {}
    wm_tris  = {}
    for sid in [0, 1]:
        hmask = (surface_map == sid)
        tri_mask = np.any(hmask[all_tris], axis=1)
        tris_sub = all_tris[tri_mask] - np.min(all_tris[tri_mask])
        wm_verts[sid] = all_verts[hmask]
        wm_tris[sid]  = tris_sub
        logging.info(f'  WM {sid}: {len(wm_tris[sid])} tris, {len(wm_verts[sid])} verts.')

    lh_n_cells = len(wm_tris[0])
    logging.info(f'LH cells: {lh_n_cells},  RH cells: {len(wm_tris[1])}')

    # ── registration sphere surfaces ─────────────────────────────────────
    reg_verts = {}
    reg_tris  = {}
    for k, path in enumerate([args.lh_reg_surface, args.rh_reg_surface]):
        v, t = _mesh_arrays(_load_vtk(path))
        reg_verts[k] = v
        reg_tris[k]  = t

    for sid in [0, 1]:
        wm_n = len(wm_tris[sid])
        sp_n = len(reg_tris[sid])
        if wm_n != sp_n:
            logging.warning(
                f'Hemisphere {sid}: WM tris={wm_n} != sphere tris={sp_n}. '
                'Topology mismatch — barycentric mapping may be inaccurate.')
        else:
            logging.info(f'Hemisphere {sid}: topology OK ({wm_n} cells).')

    # ------------------------------------------------------------------ #
    #  Load intersections                                                  #
    # ------------------------------------------------------------------ #
    logging.info('Loading intersections.')
    inters   = np.load(args.intersections, allow_pickle=True)
    n        = len(inters['tri_ids0'])
    tri_ids0 = inters['tri_ids0'].astype(np.int64)
    tri_ids1 = inters['tri_ids1'].astype(np.int64)
    pts0     = inters['pts0'].astype(np.float64)
    pts1     = inters['pts1'].astype(np.float64)
    si0      = inters['surf_ids0'].astype(np.int64)
    si1      = inters['surf_ids1'].astype(np.int64)
    surf_ids_in = tri_to_surface[tri_ids0]
    surf_ids_out = tri_to_surface[tri_ids1]

    logging.info(f'surf_ids0 unique: {np.unique(si0)}')
    logging.info(f'surf_ids1 unique: {np.unique(si1)}')
    logging.info(f'surf_in  unique: {np.unique(surf_ids_in)}')
    logging.info(f'surf_out unique: {np.unique(surf_ids_out)}')

    # ── Valid filter: BOTH endpoints on white-matter surface (type == 1) ─
    # surf_ids encodes surface TYPE: 1=white matter (LH or RH), 2+=subcortical
    valid = (si0 == 1) & (si1 == 1)
    logging.info(f'Cortical-cortical intersections: {valid.sum()} / {n}')

    # ── Hemisphere from triangle index (NOT from surf_ids0) ──────────────
    logging.info(f'surf_in  (valid) unique: {np.unique(surf_ids_in[valid])}')
    logging.info(f'surf_out (valid) unique: {np.unique(surf_ids_out[valid])}')

    # Local triangle indices within each hemisphere surface
    # LH: global [0 .. lh_n_cells-1]        → local = global
    # RH: global [lh_n_cells .. +rh_n-1]    → local = global - lh_n_cells
    local_ids0 = np.where(surf_ids_in  == 1, tri_ids0 - lh_n_cells, tri_ids0)
    local_ids1 = np.where(surf_ids_out == 1, tri_ids1 - lh_n_cells, tri_ids1)

    for sid in [0, 1]:
        _check_local_ids('in', local_ids0, valid & (surf_ids_in == sid),
                         len(wm_tris[sid]), parser)
        _check_local_ids('out', local_ids1, valid & (surf_ids_out == sid),
                         len(wm_tris[sid]), parser)

    # ------------------------------------------------------------------ #
    #  Vectorised barycentric mapping: WM surface → registration sphere   #
    # ------------------------------------------------------------------ #
    logging.info('Mapping white-matter intersections to sphere coordinates.')

    vtx_in  = np.zeros((n, 3), dtype=np.float64)
    vtx_out = np.zeros((n, 3), dtype=np.float64)

    for sid in [0, 1]:
        n_sid = len(wm_tris[sid])

        # ── In-endpoints on this hemisphere ──────────────────────────
        mask_in = valid & (surf_ids_in == sid)
        if mask_in.any():
            lids  = local_ids0[mask_in]
            wm_tv = wm_verts[sid][wm_tris[sid][lids]]       # (M,3,3)
            bary  = _bary_coords_batch(wm_tv, pts0[mask_in])
            sp_tv = reg_verts[sid][reg_tris[sid][lids]]     # (M,3,3)
            cart  = np.einsum('mi,mij->mj', bary, sp_tv)
            norms = np.linalg.norm(cart, axis=1, keepdims=True)
            vtx_in[mask_in] = cart / np.where(norms > 0, norms, 1.0)

        # ── Out-endpoints on this hemisphere ─────────────────────────
        mask_out = valid & (surf_ids_out == sid)
        if mask_out.any():
            lids  = local_ids1[mask_out]
            wm_tv = wm_verts[sid][wm_tris[sid][lids]]
            bary  = _bary_coords_batch(wm_tv, pts1[mask_out])
            sp_tv = reg_verts[sid][reg_tris[sid][lids]]
            cart  = np.einsum('mi,mij->mj', bary, sp_tv)
            norms = np.linalg.norm(cart, axis=1, keepdims=True)
            vtx_out[mask_out] = cart / np.where(norms > 0, norms, 1.0)

    n_valid = valid.sum()
    logging.info(f'Saving results ({n_valid} / {n} valid intersections).')

    np.savez_compressed(args.output,
                        surf_in  = surf_ids_in[valid].astype(np.float64),
                        surf_out = surf_ids_out[valid].astype(np.float64),
                        vtx_in   = vtx_in[valid],
                        vtx_out  = vtx_out[valid])


if __name__ == '__main__':
    main()
