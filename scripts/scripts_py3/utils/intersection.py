#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

from collections import namedtuple
from enum import IntEnum

import numpy as np

# Optionnal imports
from dipy.utils.optpkg import optional_package
vtk, _, _ = optional_package('vtk')

# VTK ratio precision, used for verify if the intersection is equal
RATIO_EPS = 1e-09

REMOVED_INDICES = np.iinfo(np.int32).min

# TODO find a better solution
OUT_PTS = vtk.vtkPoints()  # CARE GLOBAL cannot be PARALLEL
OUT_IDS = vtk.vtkIdList()  # CARE GLOBAL cannot be PARALLEL


class Surface_type(IntEnum):
    # Order need to be from Outer to inner
    OUTER = 0
    BASE = 1
    INNER = 2

    # for text save
    def __str__(self):
        return str(int(self))


class Intersection(
        namedtuple('Intersection', ['streamline_index',
                                    'segment_index',
                                    'is_going_in',
                                    'surface_index',
                                    'triangle_index',
                                    'point',
                                    'ratio',
                                    'surface_type'])):
    # Optmisation, makes it immutable
    __slots__ = ()

    def __str__(self):
        return " ".join(str(x) for x in self)

    # Redefine the Sort (lesser than)
    def __lt__(self, other):
        # return self.ratio < other.ratio
        # 1) First sort by streamline id
        if self.streamline_index < other.streamline_index:
            return True
        elif self.streamline_index == other.streamline_index:
            # 2) Sort by segment id
            if self.segment_index < other.segment_index:
                return True
            elif self.segment_index == other.segment_index:
                # 3) if ratio is near equal
                if np.abs(self.ratio - other.ratio) < RATIO_EPS:
                    # 4) Sort by surface type
                    # More complex sorting
                    if self.is_going_in:
                        if other.is_going_in:
                            # both are going in (sort by surface type)
                            return self.surface_type < other.surface_type
                        else:
                            # self is going in, other is going out
                            return False  # (go out first, other < self)
                    else:
                        if other.is_going_in:
                            # other is going in, self is going out
                            return True  # (go out first, self < other)
                        else:
                            # both are going out (sort by reverse surface type)
                            return other.surface_type < self.surface_type
                elif self.ratio < other.ratio:
                    # Sort by ratio
                    return True

        return False


# Intersection id in and out
Cut = namedtuple('Cut', ['id_in', 'id_out'])


# Functions to compute intersections
def obbtree_from_polydata(vtk_polydata):
    obb_tree = vtk.vtkOBBTree()
    obb_tree.SetDataSet(vtk_polydata)
    obb_tree.BuildLocator()
    return obb_tree


# TODO optimize (maybe cython)
def seg_intersect_trees(pt0, pt1, trees, streamline_id, segment_id, surf_types):
    global OUT_PTS, OUT_IDS
    # OUT_PTS.Reset() # (vtk already reset_them) vtk.vtkPoints() took to much time
    # OUT_IDS.Reset() # (vtk already reset_them) vtk.vtkIdList() took to much time
    intersections = []
    # For all surfaces (trees), compute a segment intersection
    for tree_id in range(len(trees)):
        cur_tree = trees[tree_id]
        p0_in_out = cur_tree.IntersectWithLine(pt0, pt1, OUT_PTS, OUT_IDS)
        for i in range(OUT_PTS.GetNumberOfPoints()):
            ratio = ratio_from_pts(pt0, pt1, OUT_PTS.GetPoint(i))
            is_going_in = point_went_inside(p0_in_out)
            surface_type = surf_types[tree_id]
            inter = Intersection(streamline_id, segment_id, is_going_in, tree_id, OUT_IDS.GetId(i), OUT_PTS.GetPoint(i), ratio, surface_type)
            intersections.append(inter)
    return intersections


def seg_intersect_trees2(pt0, pt1, mesh_tree, streamline_id, segment_id, triangle_mask, triangle_type):
    global OUT_PTS, OUT_IDS
    # OUT_PTS.Reset() # (vtk already reset_them) vtk.vtkPoints() took to much time
    # OUT_IDS.Reset() # (vtk already reset_them) vtk.vtkIdList() took to much time
    intersections = []
    # For all surfaces (trees), compute a segment intersection
    p0_in_out = mesh_tree.IntersectWithLine(pt0, pt1, OUT_PTS, OUT_IDS)
    for i in range(OUT_PTS.GetNumberOfPoints()):
        ratio = ratio_from_pts(pt0, pt1, OUT_PTS.GetPoint(i))
        is_going_in = point_went_inside(p0_in_out)
        tri_id = OUT_IDS.GetId(i)
        # if triangle inside mask
        if triangle_mask[tri_id]:
            inter_type = triangle_type[tri_id]
            inter = Intersection(streamline_id, segment_id, is_going_in, 0,
                                 tri_id, OUT_PTS.GetPoint(i), ratio, inter_type)
            intersections.append(inter)
    return intersections


def intersection_from_seed(tri_idx, surf_id, pts, streamline_id):
    return Intersection(streamline_id, 0, True, surf_id, tri_idx, tuple(pts), 0.0, Surface_type.BASE)


def intersection_from_seed2(tri_idx, pts, streamline_id):
    return Intersection(streamline_id, 0, True, 0, tri_idx, tuple(pts), 0.0, Surface_type.BASE)


def intersections_in_mask(intersections, all_masks, all_meshes):
    intersections_in = []
    for inter in intersections:
        mask = all_masks[inter.surface_index]
        triangles = all_meshes[inter.surface_index].get_triangles()
        if (mask is None) or is_intersection_in_mask(inter, mask, triangles):
            intersections_in.append(inter)
    return intersections_in

def is_intersection_in_mask(intersection, mask, triangles):
    # np.all(mask[rh_lh][tris[rh_lh][idList.GetId(0)]])
    tri = intersection.triangle_index
    vts_idx = triangles[tri]
    return np.all(mask[vts_idx])


def generate_streamline_cuts(inters, only_endpoints=True):
    # no intersections
    if not inters:
        return []

    # 1) Cut by outer surface
    # Last in to first out
    last_in = -1
    interval_list = []
    for i in range(len(inters)):
        inter = inters[i]
        if inter.surface_type == Surface_type.OUTER:
            if inter.is_going_in:
                # if last_in is None: "# Went in twice"
                last_in = i
            else:
                if last_in is not None and (last_in + 1 < i):
                    interval_list.append((last_in + 1, i))
                    last_in = None
                # else: "# Went out twice"
                #    last_in = None ?

    if inters and last_in is not None and (last_in + 1 < len(inters)):
        interval_list.append((last_in + 1, len(inters)))

    cuts = []
    # 2) Cut by basic or inner surface
    # First in to Last out
    for interval in interval_list:
        first_in = None
        last_out = None
        for i in range(interval[0], interval[1]):
            inter = inters[i]
            if inter.surface_type == Surface_type.BASE:
                # Add only if going in the good orientation (in or out)
                if inter.is_going_in:
                    if first_in is None:
                        first_in = i
                elif first_in is not None:
                    last_out = i
            elif inter.surface_type == Surface_type.INNER:
                # Add on both ways
                if first_in is None:
                    first_in = i
                else:
                    last_out = i
        if (first_in is not None) and (last_out is not None):
            cuts.append(Cut(first_in, last_out))

    # for interval in interval_list:
    #     cuts.append(interval[0], interval[1]-1))
    return cuts


def filter_streamline(streamline, inters, cuts):
    new_streamlines = []
    for cut in cuts:
        iter_in = inters[cut.id_in]
        iter_out = inters[cut.id_out]
        new_streamline = streamline[iter_in.segment_index:iter_out.segment_index + 1]
        new_streamline[0, :] = iter_in.point
        new_streamline[-1, :] = iter_out.point
        new_streamlines.append(new_streamline)
    return new_streamlines


def filter_intersections(inters, cuts, only_endpoints=True):
    new_inters = []
    if only_endpoints:
        for cut in cuts:
            new_inters += [inters[cut.id_in], inters[cut.id_out]]
    else:
        for cut in cuts:
            for i in range(cut[cut.id_in], cut.id_out):
                new_inters.append(inters[i])

    return new_inters


def point_went_inside(p0_in_out):
    # WENT_INSIDE = 1
    # WENT_OUTSIDE = -1
    return p0_in_out == 1


def ratio_from_pts(pt0, pt1, x):
    return pts_dist(pt0, x) / pts_dist(pt0, pt1)


def pts_dist(pt0, pt1):
    return np.sqrt(np.sum((pt1 - pt0)**2))


def pt_in_surf(pt0, tree):
    if tree.InsideOrOutside(pt0) == -1:
        return True
    else:
        return False

# Function to change save / load intersections


def intersections_list_to_arrays(inters):
    nb_inters = len(inters) // 2
    surf_ids0 = np.zeros([nb_inters], dtype=np.int32)
    surf_ids1 = np.zeros([nb_inters], dtype=np.int32)
    tri_ids0 = np.zeros([nb_inters], dtype=np.int32)
    tri_ids1 = np.zeros([nb_inters], dtype=np.int32)
    pts0 = np.zeros([nb_inters, 3], dtype=np.float64)
    pts1 = np.zeros([nb_inters, 3], dtype=np.float64)

    for i in range(nb_inters):
        inter_in = inters[2 * i]
        inter_out = inters[2 * i + 1]

        surf_ids0[i] = inter_in.surface_index
        surf_ids1[i] = inter_out.surface_index

        tri_ids0[i] = inter_in.triangle_index
        tri_ids1[i] = inter_out.triangle_index

        pts0[i] = inter_in.point
        pts1[i] = inter_out.point

    return surf_ids0, tri_ids0, pts0, surf_ids1, tri_ids1, pts1


def intesection_from_txt_line(txt_line):
    # split each element with space (except the tuple vertex)
    v = txt_line.rstrip('\n').replace(", ", ",").split(" ")
    # get the vertex tuple "(%f,%f,%f)"
    pt = tuple([float(f) for f in v[5][1:-1].split(",")])
    return Intersection(int(v[0]), int(v[1]), bool(v[2]), int(v[3]), int(v[4]),
                        pt, float(v[6]), Surface_type(int(v[7])))


def save_surface_intersections(map_fname, surf_ids0, tri_ids0, pts0,
                               surf_ids1, tri_ids1, pts1):
    np.savez(map_fname,
             surf_ids0=surf_ids0,
             tri_ids0=tri_ids0,
             pts0=pts0,
             surf_ids1=surf_ids1,
             tri_ids1=tri_ids1,
             pts1=pts1)


def load_surface_intersections(sseeds_fname):
    inters = np.load(sseeds_fname)
    surf_ids0 = inters['surf_ids0']
    tri_ids0 = inters['tri_ids0']
    pts0 = inters['pts0']

    surf_ids1 = inters['surf_ids1']
    tri_ids1 = inters['tri_ids1']
    pts1 = inters['pts1']
    return surf_ids0, tri_ids0, pts0, surf_ids1, tri_ids1, pts1


def save_intersections_to_txt(fname, inters):
    with open(fname, 'w') as fp:
        for item in inters:
            fp.write(str(item) + '\n')


def load_intersections_from_txt(fname):
    inters = []
    with open(fname, 'r') as fp:
        txt_line = fp.readline()
        while txt_line:
            inter = intesection_from_txt_line(txt_line)
            txt_line = fp.readline()
            inters.append(inter)
    return inters


def concatenated_intersections_filtering(
        concatenated_surface, tri_ids0, tri_ids1, vts_labels,
        starting_labels=None, ending_labels=None):
    # return a mask (true or false) for filtered intersections

    triangle_map = concatenated_surface.get_triangles()

    global REMOVED_INDICES
    nb_intersections = len(tri_ids0)
    all_id = np.unique(vts_labels[vts_labels != REMOVED_INDICES])

    if starting_labels is None:
        starting_labels = all_id

    if ending_labels is None:
        ending_labels = all_id

    starting_labels = np.asarray(starting_labels)
    ending_labels = np.asarray(ending_labels)

    mask = np.zeros(nb_intersections, dtype=np.bool_)

    for i in range(nb_intersections):
        labels_a = vts_labels[triangle_map[tri_ids0[i]]]
        labels_b = vts_labels[triangle_map[tri_ids1[i]]]

        if ((np.any(np.in1d(labels_a, starting_labels))
             and np.any(np.in1d(labels_b, ending_labels)))
            or ((np.any(np.in1d(labels_a, ending_labels))
                and np.any(np.in1d(labels_b, starting_labels))))):
            mask[i] = True

    return mask
