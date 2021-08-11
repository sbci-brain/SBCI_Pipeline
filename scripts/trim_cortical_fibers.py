import argparse
import logging
import nibabel as nib
import numpy as np
import vtk
import vtk.util.numpy_support as ns

from os.path import isfile

from collections import namedtuple, Counter
from dipy.tracking import metrics
from dipy.tracking.streamline import length, set_number_of_points, compress_streamlines
from scilpy.io.vtk_streamlines import load_vtk_streamlines, save_vtk_streamlines

import scilpy.surface.intersection as stools

DESCRIPTION = """
  Trim streamlines that are outside the cortical surface, cut those that go
  through subcortical regions, and filter those that do not intersect at least two ROIs.
"""

# constants 
DEPTH_THR = 2
SAMPLE_SIZE = 0.2
COMPRESSION_RATE = 0.2

# somewhere to store generated streamlines and their intersections
class ROI_Streamlines(
    namedtuple('ROI_Streamlines', ['streamlines', 
                                   'ids_in', 'ids_out', 
                                   'pts_in', 'pts_out', 
                                   'surf_in', 'surf_out'])):

    # add new streamlines to the class object
    def extend(self, roi_sl):
        # compress the new streamlines to save space
        for i in range(len(roi_sl.streamlines)):
            streamline = roi_sl.streamlines[i]
            roi_sl.streamlines[i] = compress_streamlines(streamline, COMPRESSION_RATE)

        # add streamlines and intersection information
        self.streamlines.extend(roi_sl.streamlines)
        self.ids_in.extend(roi_sl.ids_in)
        self.ids_out.extend(roi_sl.ids_out)
        self.pts_in.extend(roi_sl.pts_in)
        self.pts_out.extend(roi_sl.pts_out)
        self.surf_in.extend(roi_sl.surf_in)
        self.surf_out.extend(roi_sl.surf_out)

    # save all current intersections to a file
    def save_intersections(self, filename):
        # convert ids of None to -1 for saving
        tmp_ids_in = np.array(self.ids_in)
        tmp_ids_in[tmp_ids_in == None] = -1
        tmp_ids_in = tmp_ids_in.astype(int)

        # convert ids of None to -1 for saving
        tmp_ids_out = np.array(self.ids_out)
        tmp_ids_out[tmp_ids_out == None] = -1
        tmp_ids_out = tmp_ids_out.astype(int)

        # save interscetions to a .npz file
        np.savez(filename,
                 surf_ids0 = self.surf_in,
                 tri_ids0 = tmp_ids_in,
                 pts0 = self.pts_in,
                 surf_ids1 = self.surf_out,
                 tri_ids1 = tmp_ids_out,
                 pts1 = self.pts_out)

    # save all the current streamlines
    def save_streamlines(self, filename):
        save_vtk_streamlines(self.streamlines, filename, binary = True)
    

def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surfaces', action='store', metavar='SURFACES', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the concatenated surfaces.')

    p.add_argument('--surface_map', action='store', metavar='SURFACE_MAP', required=True,
                   type=str, help='Path of the surface map for the vertices.')

    p.add_argument('--surface_mask', action='store', metavar='SURFACE_MASK', required=True,
                   type=str, help='Mask for where intersections should be calculated.')

    p.add_argument('--aparc', action='store', metavar='APARC', required=True,
                   type=str, help='Path of the parcellation image used for subcortical volumes.')

    p.add_argument('--rois', type=int, nargs='+', required=True,
                   help='List of roi indices to include.')

    p.add_argument('--streamlines', action='store', metavar='STREAMLINES', required=True,
                   type=str, help='Path of the .fib file of tractography from SET.')

    p.add_argument('--out_tracts', action='store', metavar='OUT_TRACTS', required=True,
                   type=str, help='Path of the .fib file to save the filtered tracts to.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the intersections to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


# trim streamlines to be within the cortical surface, splitting if needed
def trim_cortical_streamline(streamline, sl_id, locator, surface_mask, surface_type):
    # loop variables
    n = len(streamline)

    interceptions = []

    # find all points that the streamline intersects with any of the surfaces
    for j in range(0, n - 1):
        pt1 = streamline[j] * [-1, -1, 1]
        pt2 = streamline[j+1] * [-1, -1, 1]

        result = stools.seg_intersect_trees2(pt1, pt2, locator, 
                                             sl_id, j, 
                                             surface_mask, surface_type)

        result.sort()
        interceptions.extend(result)

    last_in = -1
    intervals = []
    
    # cut the streamline into segments for each time it goes into and out of the pial surface
    for j in range(len(interceptions)):
        interception = interceptions[j]

        if interception.surface_type == stools.Surface_type.OUTER:
            if interception.is_going_in == True:
                last_in = j
            else:
                if last_in is not None and (last_in + 1 < j):
                    intervals.append((last_in + 1, j))
                    last_in = None

    if last_in is not None and (last_in + 1 < len(interceptions)):
        intervals.append((last_in + 1, len(interceptions)))

    ids_in = []
    ids_out = []
    new_streamlines = []

    # loop through each line segment and check for 
    # intersections with the white and subcortical surfaces
    for interval in intervals:
        first_in = None
        last_out = None
        first_id = None
        last_id = None

        for j in range(interval[0], interval[1]):
            interception = interceptions[j]
            
            if interception.surface_type == stools.Surface_type.BASE:
                if interception.is_going_in == True:
                    if first_in is None:
                        first_in = j
                        first_id = interception.triangle_index
                elif first_in is not None:
                    last_out = j
                    last_id = interception.triangle_index
            elif interception.surface_type == stools.Surface_type.INNER:
                if first_in is None:
                    first_in = j
                    first_id = None
                else:
                    last_out = j
                    last_id = None
        
        if first_in is None:
            first_in = interval[0]
        if last_out is None:
            last_out = interval[1]-1

        inter_in = interceptions[first_in]
        inter_out = interceptions[last_out]
        new_streamline = streamline[inter_in.segment_index:inter_out.segment_index + 1]

        new_streamline[0, :] = inter_in.point * np.array([-1,-1,1])
        new_streamline[-1, :] = inter_out.point * np.array([-1,-1,1])
            
        new_streamlines.append(new_streamline)
        ids_in.append(first_id)
        ids_out.append(last_id)

    # if no intersections found, save whole streamline
    if not intervals:
        new_streamlines.append(streamline)
        ids_in.append(None)
        ids_out.append(None)

    return new_streamlines, ids_in, ids_out


# split streamlines into #ROIs choose 2 fibers and filter out non-intersecting tracts 
def split_subcortical_streamline(streamline, label_data, rois, tri_in, tri_out):
    # somewhere to put results
    new_streamlines = []
    ids_in = []
    ids_out = []
    pts_in = []
    pts_out = []
    surf_in = []
    surf_out = []

    # check if the streamline passes through any subcortical regions
    n_subcortical = np.sum(np.isin(rois, np.unique(label_data)))

    # check if the streamline intersects with the cortical surface
    n_cortical = np.count_nonzero([tri_in, tri_out])

    # if just cortical to cortical, return whole streamline
    if n_subcortical == 0 and n_cortical == 2:
        return ROI_Streamlines([streamline], [tri_in], [tri_out], [streamline[0]], [streamline[-1]], [1], [1])

    # if only one endpoint, discard streamline
    if n_cortical + n_subcortical < 2:
        return ROI_Streamlines([], [], [], [], [], [], [])
  
    intersection = []

    # if cortical surface is an endpoint, manually add it as a ROI
    if tri_in is not None:
        intersection.append(-1)
    if tri_out is not None:
        intersection.append(0)

    roi_count = Counter(label_data)

    # split the streamline based on intersections with subcortical regions
    for roi in roi_count:
        if np.isin(roi, rois) and roi_count[roi] > DEPTH_THR:
            intersection.append(roi)

    # create a library of ROIs for ordering the final SC matrix
    roi_map = { rois[i] : i + 2 for i in range(0, len(rois)) }
    roi_map[0] = 1
    roi_map[-1] = 1

    # split the streamline into nchoose(len(intersection),2) segments
    for i in range(0, len(intersection)-1):
        for j in range(i+1, len(intersection)):
            roi_a = intersection[i]
            roi_b = intersection[j]

            tri_a = None
            tri_b = None

            roi_idx_a = None
            roi_idx_b = None

            # find all the points where the streamline passed through ROI A
            if roi_a < 1:
                label_roi_a = len(streamline) if roi_a == 0 else 0
            if roi_a > 0:
                tmp_idx = np.where(label_data == roi_a)[0]+1
                tmp_idx = np.split(tmp_idx, np.where(np.diff(tmp_idx) != 1)[0]+1)
                tmp_idx = [x for x in tmp_idx if x.size >= DEPTH_THR]

                roi_idx_a = tmp_idx

            # find all the points where the streamline passed through ROI B
            if roi_b < 1:
                label_roi_b = len(streamline) if roi_b == 0 else 0
            else:
                tmp_idx = np.where(label_data == roi_b)[0]+1
                tmp_idx = np.split(tmp_idx, np.where(np.diff(tmp_idx) != 1)[0]+1)
                tmp_idx = [x for x in tmp_idx if x.size >= DEPTH_THR]

                roi_idx_b = tmp_idx

            # if neither ROI is a subcortical region
            if roi_idx_a is None and roi_idx_b is None:
                start_idx = min(label_roi_a, label_roi_b)
                end_idx = max(label_roi_a, label_roi_b)

                # make sure in and out are the right way around
                if label_roi_b < label_roi_a:
                    tmp_roi = roi_a
                    roi_a = roi_b
                    roi_b = tmp_roi 

                tri_a = tri_in
                tri_b = tri_out

            # if just ROI B is a subcortical region
            elif roi_idx_a is None:
                if len(roi_idx_b) == 0:
                    continue

                if label_roi_a == 0:
                    start_idx = label_roi_a
                    end_idx = roi_idx_b[0][0]

                    tri_a = tri_in
                else:
                    start_idx = roi_idx_b[-1][-1]
                    end_idx = label_roi_a

                    tmp_roi = roi_a
                    roi_a = roi_b
                    roi_b = tmp_roi 
                    
                    tri_b = tri_out

            # if just ROI A is a subcortical region
            elif roi_idx_b is None:
                if len(roi_idx_a) == 0:
                    continue

                if label_roi_b == 0:
                    start_idx = label_roi_b
                    end_idx = roi_idx_a[0][0]

                    tmp_roi = roi_a
                    roi_a = roi_b
                    roi_b = tmp_roi 

                    tri_a = tri_in
                else:
                    start_idx = roi_idx_a[-1][-1]
                    end_idx = label_roi_b

                    tri_b = tri_out

            # if both ROIs are subcortical regions
            else:
                if len(roi_idx_a) == 0 or len(roi_idx_b) == 0:
                    continue

                combined_idx = zip(roi_idx_a, [roi_a]*len(roi_idx_a)) \
                                   + zip(roi_idx_b, [roi_b]*len(roi_idx_b))

                combined_idx = sorted(combined_idx, key = lambda x:x[0][0])
                combined_mask = [x[1] for x in combined_idx]
                combined_idx = np.array(combined_idx)[np.concatenate([[True], np.diff(combined_mask) != 0])]

                combined_roi = [x[1] for x in combined_idx]
                combined_idx = [x[0] for x in combined_idx]

                max_dist = 0

                # if the streamline zigzags in and out of the two regions,
                # we just want to save the segment that is longest
                for u in range(0,len(combined_idx)-1):
                    dist = combined_idx[u+1][0] - combined_idx[u][-1]
                        
                    if dist > max_dist:
                        start_idx = combined_idx[u][-1]
                        end_idx = combined_idx[u+1][0]
                        roi_a = combined_roi[u]
                        roi_b = combined_roi[u+1]

                        max_dist = dist

            # sanity check, should never happen
            if end_idx < start_idx:
                logging.warning('End index before start')

            # split the streamline between the 2 ROIs
            split = streamline[start_idx:end_idx]
            
            # only keep if has at least one segment
            if len(split) > 1:
                new_streamlines.append(split)
                ids_in.append(tri_a)
                ids_out.append(tri_b)
                pts_in.append(split[0])
                pts_out.append(split[-1])
                surf_in.append(roi_map[roi_a])
                surf_out.append(roi_map[roi_b])
    
    return ROI_Streamlines(new_streamlines, ids_in, ids_out, pts_in, pts_out, surf_in, surf_out)
                

def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    if not isfile(args.surfaces):
        parser.error('The file "{0}" must exist.'.format(args.surfaces))

    if not isfile(args.surface_map):
        parser.error('The file "{0}" must exist.'.format(args.surface_map))

    if not isfile(args.streamlines):
        parser.error('The file "{0}" must exist.'.format(args.streamlines))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    if isfile(args.out_tracts):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.out_tracts))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.out_tracts))

    # load the surfaces
    logging.info('Loading .vtk surfaces and streamlines.')
    all_surfaces = load_vtk(args.surfaces)

    # load surface map
    surface_map = np.load(args.surface_map)

    # load mask for intersections
    surface_mask = np.load(args.surface_mask)

    # find triangles with any vertex within the mask
    vertices = ns.vtk_to_numpy(all_surfaces.GetPolys().GetData())
    triangles = np.vstack([vertices[1::4], vertices[2::4], vertices[3::4]]).T

    surface_mask = surface_mask[triangles]
    surface_mask = np.all(surface_mask, axis=1)
    surface_map = surface_map[triangles[:,0]]

    # locator for quickly finding intersections
    locator = vtk.vtkOBBTree()
    locator.SetDataSet(all_surfaces)
    locator.BuildLocator()

    # load the streamlines
    streamlines = load_vtk_streamlines(args.streamlines)

    # load label images
    label_img = nib.load(args.aparc)
    label_data = label_img.get_data().astype('int')
    voxel_dim = label_img.get_header()['pixdim'][1:4]
    
    # calculate transform from voxel to mm coordinates
    affine = np.array(label_img.affine, dtype=float)
    affine = np.linalg.inv(affine)
    transform = affine[:3, :3].T
    offset = affine[:3, 3] + 0.5

    logging.info('Trimming, splitting, and filtering {0} streamlines.'.format(len(streamlines)))
    print(args.rois)

    new_streamlines = ROI_Streamlines([],[],[],[],[],[],[])

    for i in xrange(len(streamlines)):
        # just one segment
        # filter as error
        if len(streamlines[i]) < 3:
            continue

        # trim and split cortical intersections
        trimmed_streamlines, tri_in, tri_out = trim_cortical_streamline(streamlines[i], i, locator, surface_mask, surface_map)

        # split subcortical intersections
        for j in range(len(trimmed_streamlines)):
            # resample streamline to allow for fine level
            # intersections with subcortical regions
            fiber_len = length(trimmed_streamlines[j])
            n_points = int(fiber_len / SAMPLE_SIZE)
 
            if n_points < 3:
               continue

            resampled_streamline = set_number_of_points(trimmed_streamlines[j], n_points)

            # find voxels that the streamline passes through
            inds = np.dot(resampled_streamline, transform)
            inds = inds + offset

            if inds.min().round(decimals = 6) < 0:
                logging.error('Streamline has points that map to negative voxel indices')

            ii, jj, kk = inds.astype(int).T
            sl_labels = label_data[ii, jj, kk]

            # split fibers among intersecting regions and return all intersections
            split_streamlines = split_subcortical_streamline(resampled_streamline, sl_labels, args.rois, tri_in[j], tri_out[j])

            # fill the results arrays
            new_streamlines.extend(split_streamlines)

    logging.info('Saving {0} final streamlines.'.format(len(new_streamlines.streamlines)))
    
    # save the results
    new_streamlines.save_streamlines(args.out_tracts)
    new_streamlines.save_intersections(args.output)


if __name__ == "__main__":
    main()
