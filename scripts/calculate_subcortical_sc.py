import argparse
import logging
import vtk

import numpy as np
import scipy.io as scio

from sklearn.neighbors import KernelDensity
from os.path import isfile

DESCRIPTION = """
  Map tract endpoints to vertices on the downsampled surface and calculate SC matrix.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--grid', action='store', metavar='GRID', required=True,
                   type=str, help='Path to the xyz coordinates of vertices on the spheres .npz file.')

    p.add_argument('--coordinates', action='store', metavar='COORDINATES', required=True,
                   type=str, help='Path to the xyz coordinates of vertices on the spheres .npz file.')

    p.add_argument('--bandwidth', action='store', metavar='BANDWIDTH', default=0.05,
                   type=float, help='Bandwidth parameter for kernel smoothing.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file of structural connectivity matrix.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def to_latlon(coords):
    r = np.sqrt((np.sum(coords*coords, axis=1)))
    lat = np.arcsin(coords[:,2]/r)
    lon = np.arctan2(coords[:,1], coords[:,0])

    return np.vstack([lat, lon]).T

def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the input files exist
    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.intersections))

    if not isfile(args.grid):
        parser.error('The file "{0}" must exist.'.format(args.grid))

    if not isfile(args.coordinates):
        parser.error('The file "{0}" must exist.'.format(args.coordinates))

    # make sure the bandwidth is reasonable
    if not args.bandwidth >= 0:
        parser.error('The bandwidth must be non-negative.'.format(args.mesh))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading mapping and intersections.')

    # load coordinates and convert from cartesian to lattitude,longitude
    coords = np.load(args.coordinates, allow_pickle=True)['coords']
    lh_latlon = to_latlon(coords[coords[:,1] == 0, 2:5])
    rh_latlon = to_latlon(coords[coords[:,1] == 1, 2:5])

    # grid points to evaluate SC on
    grid = np.load(args.grid, allow_pickle=True)['coords']
    lh_grid = to_latlon(grid[grid[:,1] == 0, 2:5])
    rh_grid = to_latlon(grid[grid[:,1] == 1, 2:5])

    lh_points = np.sum(grid[:,1] == 0)
 
    # load intersections that have already been snapped to nearest vertices of full mesh
    intersections = np.load(args.intersections, allow_pickle=True)

    surf_in = intersections['surf_ids0'].astype(np.int64)
    surf_out = intersections['surf_ids1'].astype(np.int64)
    id_in = intersections['v_ids0'].astype(np.int64)
    id_out = intersections['v_ids1'].astype(np.int64)

    in_mask = surf_in >= 2
    out_mask = surf_out >= 2

    logging.info('Calculating SC for subcortical-subcortical streamlines.')

    # subcortical to subcortical
    print(np.unique(surf_in))
    rois = np.concatenate([np.unique(surf_in), np.unique(surf_out)])
    rois = np.unique(rois[rois >= 2])

    logging.info('ROIs: {0}'.format(rois))

    n = len(rois)
    subsub_mask = in_mask & out_mask
    subsub_sc = np.zeros([n,n])

    tmp_id_id = surf_in[subsub_mask] - 2
    tmp_id_out = surf_out[subsub_mask] - 2

    # calculate the structural connectivity
    for i in range(len(tmp_id_id)):
        subsub_sc[tmp_id_id[i], tmp_id_out[i]] += 1
    
        # only count self connections once
        if not tmp_id_id[i] == tmp_id_out[i]:
            subsub_sc[tmp_id_out[i], tmp_id_id[i]] += 1

    logging.info('Calculating SC for subcortical-cortical streamlines.')

    # subcortical to cortical
    subwhite_mask = in_mask ^ out_mask
    tmp_id_in = id_in[subwhite_mask]    
    tmp_id_out = id_out[subwhite_mask]    
    tmp_surf_in = surf_in[subwhite_mask]
    tmp_surf_out = surf_out[subwhite_mask]

    logging.info('Smoothing {0} streamlines.'.format(sum(subwhite_mask)))

    # use guassian kde to smooth the sc similar to cortical-cortical SC
    kernel = KernelDensity(bandwidth=args.bandwidth, metric='haversine',
                           kernel='gaussian', algorithm='ball_tree')

    subwhite_sc = np.zeros([n,grid.shape[0]])

    for i in range(n):
        surf_data = np.zeros(lh_latlon.shape[0] + rh_latlon.shape[0])       

        # left hemisphere
        tmp_out_mask = (tmp_surf_in == (i+2)) & (tmp_surf_out == 0)
        tmp_in_mask = (tmp_surf_out == (i+2)) & (tmp_surf_in == 0)

        vtx_ids = np.concatenate([tmp_id_in[tmp_in_mask], tmp_id_out[tmp_out_mask]])

        white_coords = lh_latlon[vtx_ids,:]
        total_size = white_coords.shape[0]

        if not white_coords.shape[0] == 0:
            kernel.fit(white_coords)
            subwhite_sc[i,0:lh_points] = (np.exp(kernel.score_samples(lh_grid)) * white_coords.shape[0])

        idx, cnt = np.unique(vtx_ids, return_counts=True)
        surf_data[idx] = cnt

        # right hemisphere
        tmp_out_mask = (tmp_surf_in == (i+2)) & (tmp_surf_out == 1)
        tmp_in_mask = (tmp_surf_out == (i+2)) & (tmp_surf_in == 1)

        vtx_ids = np.concatenate([tmp_id_in[tmp_in_mask], tmp_id_out[tmp_out_mask]])

	white_coords = rh_latlon[vtx_ids,:]
        total_size = total_size + white_coords.shape[0]

        if not white_coords.shape[0] == 0:
            kernel.fit(white_coords)
            subwhite_sc[i,lh_points:] = (np.exp(kernel.score_samples(rh_grid)) * white_coords.shape[0]) 

        #subwhite_sc[i,:] = subwhite_sc[i,:] / total_size

        idx, cnt = np.unique(vtx_ids, return_counts=True)
        surf_data[idx + lh_latlon.shape[0]] = cnt

    #subwhite_sc = subwhite_sc / len(id_in)
        
    # save results
    scio.savemat(args.output, {'sub_sub_sc': subsub_sc, 
                               'sub_surf_sc': subwhite_sc})


if __name__ == "__main__":
    main()
