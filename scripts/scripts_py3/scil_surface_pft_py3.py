#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Surface-seeded Particle Filtering Tractography (SET / PFT).

Python 3 port of the original scil_surface_pft_dipy.py (Python 2).

Seeds are loaded from a pre-computed surface .npz file produced by
scil_surface_seeds_from_map.py (contains tri_idx and tri_coord arrays).
The mesh vertices are used to convert barycentric surface coordinates
into 3-D mm positions, which are then used as PFT seed points.

Usage
-----
    python3 scil_surface_pft_py3.py  in_sh  in_map_include  in_map_exclude  \\
        in_surface  in_seeds  out_tractogram  [options]

Arguments
---------
    in_sh            : Spherical harmonic FODF image (.nii.gz)
    in_map_include   : PFT include probability map (.nii.gz)
    in_map_exclude   : PFT exclude probability map (.nii.gz)
    in_surface       : Concatenated flow surface (.vtk)
    in_seeds         : Pre-computed surface seeds from scil_surface_seeds_from_map.py (.npz)
    out_tractogram   : Output tractogram (.trk or .tck)

References
----------
[1] St-Onge, E., Daducci, A., Girard, G. and Descoteaux, M. 2018.
    Surface-enhanced tractography (SET). NeuroImage.
[2] Girard, G., Whittingstall K., Deriche, R., and Descoteaux, M. 2014.
    Towards quantitative connectivity analysis: reducing tractography biases.
    Neuroimage, 98, 266-278.
"""

import argparse
import logging

import numpy as np
import nibabel as nib
import nibabel.affines          # ensure apply_affine is accessible
from nibabel.streamlines import LazyTractogram

from dipy.data import get_sphere, HemiSphere
from dipy.direction import (ProbabilisticDirectionGetter,
                            DeterministicMaximumDirectionGetter)
from dipy.io.utils import get_reference_info, create_tractogram_header
from dipy.tracking.local_tracking import ParticleFilteringTracking
from dipy.tracking.stopping_criterion import (ActStoppingCriterion,
                                              CmcStoppingCriterion)
from dipy.tracking.streamlinespeed import compress_streamlines

from trimeshpy.io import load_mesh_from_file

from scilpy.io.utils import (add_overwrite_arg, add_sh_basis_args,
                             add_verbose_arg, assert_inputs_exist,
                             assert_outputs_exist, parse_sh_basis_arg,
                             assert_headers_compatible, add_compression_arg,
                             verify_compression_th)
from scilpy.tracking.utils import get_theta

from utils.seed import load_surface_seeds, get_vertices_from_seeds, get_normals_from_seeds


def _build_arg_parser():
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='References: [1] St-Onge et al. (2018). NeuroImage.\n'
               '           [2] Girard et al. (2014). Neuroimage.')
    p._optionals.title = 'Generic options'

    # Positional arguments — same order as original scil_surface_pft_dipy.py
    p.add_argument('in_sh',
                   help='Spherical harmonic FODF file (.nii.gz).')
    p.add_argument('in_map_include',
                   help='PFT probability map for including streamlines (.nii.gz).')
    p.add_argument('in_map_exclude',
                   help='PFT probability map for excluding streamlines (.nii.gz).')
    p.add_argument('in_surface',
                   help='Concatenated flow surface (.vtk).')
    p.add_argument('in_seeds',
                   help='Pre-computed surface seeds from scil_surface_seeds_from_map.py (.npz).')
    p.add_argument('out_tractogram',
                   help='Output tractogram (.trk or .tck).')

    track_g = p.add_argument_group('Tracking options')
    track_g.add_argument('--algo', default='prob', choices=['det', 'prob'],
                         help='Tracking algorithm. [%(default)s]')
    track_g.add_argument('--step', dest='step_size', type=float, default=0.5,
                         help='Step size (treated as voxels, matching original\n'
                              'scil_surface_pft_dipy.py behaviour; seeds are in\n'
                              'voxel-index space with affine=eye(4)). [%(default)s]')
    track_g.add_argument('--max_length', type=float, default=300.,
                         help='Maximum streamline length in steps '
                              '(controls maxlen=max_length/step_size). [%(default)s]')
    track_g.add_argument('--theta', type=float,
                         help='Max angle between steps. ["det"=45, "prob"=20]')
    track_g.add_argument('--act', action='store_true',
                         help='Use ACT instead of CMC stopping criterion.')
    track_g.add_argument('--sfthres', dest='sf_threshold',
                         type=float, default=0.1,
                         help='Spherical function relative threshold. [%(default)s]')
    track_g.add_argument('--sfthres_init', dest='sf_threshold_init',
                         type=float, default=0.5,
                         help='SF threshold for initial direction. [%(default)s]')
    add_sh_basis_args(track_g)

    pft_g = p.add_argument_group('PFT options')
    pft_g.add_argument('--particles', type=int, default=15,
                       help='Number of PFT particles. [%(default)s]')
    pft_g.add_argument('--back', dest='back_tracking', type=float, default=2.,
                       help='PFT back-tracking distance in mm. [%(default)s]')
    pft_g.add_argument('--forward', dest='forward_tracking', type=float, default=1.,
                       help='PFT forward-tracking distance in mm. [%(default)s]')

    out_g = p.add_argument_group('Output options')
    out_g.add_argument('--all', dest='keep_all', action='store_true',
                       default=True,
                       help='Keep all streamlines including classifier-excluded '
                            '(matches original scil_surface_pft_dipy.py behaviour; '
                            'downstream trim_cortical_fibers.py does the real filtering).')
    out_g.add_argument('--random_seed', type=int,
                       help='Random number generator seed.')
    add_overwrite_arg(out_g)
    add_compression_arg(out_g)
    add_verbose_arg(p)

    return p


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.getLevelName(args.verbose))

    required = [args.in_sh, args.in_map_include, args.in_map_exclude,
                args.in_surface, args.in_seeds]
    assert_inputs_exist(parser, required)
    assert_outputs_exist(parser, args, args.out_tractogram)
    assert_headers_compatible(parser, [args.in_sh,
                                       args.in_map_include,
                                       args.in_map_exclude])

    if not nib.streamlines.is_supported(args.out_tractogram):
        parser.error('Invalid output streamline format (must be .trk or .tck): '
                     '{}'.format(args.out_tractogram))

    if args.max_length < 0:
        parser.error('--max_length must be > 0, got {}.'.format(args.max_length))

    verify_compression_th(args.compress_th)

    if args.particles <= 0:
        parser.error('--particles must be >= 1.')
    if args.back_tracking <= 0:
        parser.error('--back must be > 0.')
    if args.forward_tracking <= 0:
        parser.error('--forward must be > 0.')

    # ------------------------------------------------------------------ #
    #  Load FODF and build direction getter                               #
    # ------------------------------------------------------------------ #
    fodf_sh_img = nib.load(args.in_sh)
    if not np.allclose(np.mean(fodf_sh_img.header.get_zooms()[:3]),
                       fodf_sh_img.header.get_zooms()[0], atol=1e-3):
        parser.error('SH file is not isotropic — tracking cannot run robustly.')

    tracking_sphere = HemiSphere.from_sphere(get_sphere('repulsion724'))
    if not np.allclose(np.linalg.norm(tracking_sphere.vertices, axis=1), 1.):
        raise RuntimeError('Tracking sphere should be unit-normed.')

    sh_basis, is_legacy = parse_sh_basis_arg(args)
    theta = get_theta(args.theta, args.algo)

    dgklass = (DeterministicMaximumDirectionGetter if args.algo == 'det'
               else ProbabilisticDirectionGetter)

    dg = dgklass.from_shcoeff(
        fodf_sh_img.get_fdata(dtype=np.float64),   # match original: .get_data().astype(np.double)
        max_angle=theta,
        sphere=tracking_sphere,
        basis_type=sh_basis,
        legacy=is_legacy,
        pmf_threshold=args.sf_threshold,
        relative_peak_threshold=args.sf_threshold_init)

    # ------------------------------------------------------------------ #
    #  Load PFT maps and build stopping criterion                         #
    # ------------------------------------------------------------------ #
    map_include_img = nib.load(args.in_map_include)
    map_exclude_img = nib.load(args.in_map_exclude)
    voxel_size = float(np.average(map_include_img.header['pixdim'][1:4]))

    if not args.act:
        tissue_classifier = CmcStoppingCriterion(
            map_include_img.get_fdata(dtype=np.float32),
            map_exclude_img.get_fdata(dtype=np.float32),
            step_size=args.step_size,
            average_voxel_size=voxel_size)
    else:
        tissue_classifier = ActStoppingCriterion(
            map_include_img.get_fdata(dtype=np.float32),
            map_exclude_img.get_fdata(dtype=np.float32))

    # ------------------------------------------------------------------ #
    #  Load surface seeds and convert to FODF voxel indices              #
    #                                                                     #
    #  The .npz file contains:                                            #
    #    tri_idx   : (N,) triangle indices into the surface mesh          #
    #    tri_coord : (N, 3) barycentric coordinates within each triangle  #
    #                                                                     #
    #  get_vertices_from_seeds() gives 3-D positions in LPS scanner mm  #
    #  (surfaces were flipped from FreeSurfer RAS to LPS by step 2).    #
    #                                                                     #
    #  Coordinate chain:                                                  #
    #    LPS mm  →  RAS mm (flip x, y)  →  FODF voxel index              #
    #                                                                     #
    #  Dipy's ParticleFilteringTracking with affine=np.eye(4) operates  #
    #  in voxel-index space, so seeds must be converted to voxel space.  #
    # ------------------------------------------------------------------ #
    logging.info('Loading surface: %s', args.in_surface)
    mesh = load_mesh_from_file(args.in_surface)

    logging.info('Loading surface seeds: %s', args.in_seeds)
    tri_idx, tri_coord = load_surface_seeds(args.in_seeds)
    seeds_lps = get_vertices_from_seeds(mesh, tri_idx, tri_coord).astype(np.float64)
    logging.info('  %d seed points in LPS mm', len(seeds_lps))

    # LPS mm → RAS mm (nibabel affines are always voxel→rasmm/RAS)
    lps_to_ras = np.diag([-1., -1., 1., 1.])
    seeds_ras = nib.affines.apply_affine(lps_to_ras, seeds_lps)

    # RAS mm → FODF voxel indices
    inv_affine = np.linalg.inv(fodf_sh_img.affine)
    seeds_vox = nib.affines.apply_affine(inv_affine, seeds_ras)
    logging.info('  Voxel range  x=[%.1f, %.1f]  y=[%.1f, %.1f]  z=[%.1f, %.1f]',
                 seeds_vox[:, 0].min(), seeds_vox[:, 0].max(),
                 seeds_vox[:, 1].min(), seeds_vox[:, 1].max(),
                 seeds_vox[:, 2].min(), seeds_vox[:, 2].max())

    # ------------------------------------------------------------------ #
    #  Run PFT tracking in voxel-index space                              #
    #                                                                     #
    #  affine=np.eye(4) means "seed coordinates ARE the voxel indices"   #
    #  (consistent with how scilpy's scil_tracking_pft works).           #
    # ------------------------------------------------------------------ #
    # Nudge seeds slightly inward (away from surface normal) so the tracker
    # does not start exactly on the mesh boundary.
    # Matches original exactly: seeds_vts -= step_size/100 * normals_vox
    # (seeds and normals are both in voxel space; step_size is in voxel units)
    normals_lps = get_normals_from_seeds(mesh, tri_idx, tri_coord).astype(np.float64)
    normals_ras = normals_lps * np.array([-1., -1., 1.])           # LPS→RAS flip
    normals_vox = normals_ras @ inv_affine[:3, :3].T               # RAS→voxel (linear only)
    seeds_vox -= (args.step_size / 100.0) * normals_vox

    # max_steps mirrors original: int(max_length / step_size) + 1
    # step_size is in voxels, max_length is user-provided (same units)
    max_steps = int(args.max_length / args.step_size) + 1

    pft_streamlines = ParticleFilteringTracking(
        dg,
        tissue_classifier,
        seeds_vox,
        np.eye(4),
        max_cross=1,
        step_size=args.step_size,   # voxel units — matches original's direct pass-through
        maxlen=max_steps,
        pft_back_tracking_dist=args.back_tracking,
        pft_front_tracking_dist=args.forward_tracking,
        particle_count=args.particles,
        return_all=args.keep_all,
        random_seed=args.random_seed)

    # No length filter here — matches original scil_surface_pft_dipy.py which
    # saves ALL streamlines from PFT; trim_cortical_fibers.py does real filtering.
    streamlines = pft_streamlines

    if args.compress_th:
        streamlines = (
            compress_streamlines(s, args.compress_th)
            for s in streamlines)

    # ------------------------------------------------------------------ #
    #  Save tractogram                                                    #
    #                                                                     #
    #  Streamlines from tracking are in voxel-index space.               #
    #  affine_to_rasmm=fodf_sh_img.affine converts them to RAS mm when  #
    #  the .trk file is written.                                          #
    # ------------------------------------------------------------------ #
    tractogram = LazyTractogram(lambda: streamlines,
                                affine_to_rasmm=fodf_sh_img.affine)

    filetype = nib.streamlines.detect_format(args.out_tractogram)
    reference = get_reference_info(fodf_sh_img)
    header = create_tractogram_header(filetype, *reference)

    nib.streamlines.save(tractogram, args.out_tractogram, header=header)
    logging.info('Tractogram saved: %s', args.out_tractogram)


if __name__ == '__main__':
    main()
