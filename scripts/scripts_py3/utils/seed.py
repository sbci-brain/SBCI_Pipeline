#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import logging

import numpy as np


def save_surface_seeds(sseeds_fname, triangles_indices, trilinear_coordinates):
    np.savez(sseeds_fname,
             tri_idx=triangles_indices,
             tri_coord=trilinear_coordinates)


def load_surface_seeds(sseeds_fname):
    seeds = np.load(sseeds_fname)
    tri_idx = seeds['tri_idx']
    tri_coord = seeds['tri_coord']
    return tri_idx, tri_coord


def generate_seed_map_from_mesh(mesh, vertices_weights=None, triangles_weights=None,
                                vertices_mask=None, triangles_mask=None):
    # Test input format
    #   Only one weighting methods, and test array size
    if vertices_weights is not None:
        if triangles_weights is not None:
            logging.error("Only one seedings weights can be used")
        if len(vertices_weights) != mesh.get_nb_vertices():
            logging.error("vertices_weights, is not the same size as vertices")

    if vertices_mask is not None:
        if triangles_mask is not None:
            logging.error("Only one seeding mask can be used")
        if len(vertices_mask) != mesh.get_nb_vertices():
            logging.error("vertices_mask, is not the same size as vertices")

    if triangles_weights is not None and len(triangles_weights) != mesh.get_nb_triangles():
        logging.error("triangles_weights, is not the same size as triangles")
    if triangles_mask is not None and len(triangles_mask) != mesh.get_nb_triangles():
        logging.error("triangles_mask, is not the same size as triangles")

    # Covert vertices based metrics to triangles (weights and mask)
    if vertices_weights is not None:
        triangles_weights = vertices_to_triangles_weights(mesh, vertices_weights)

    if vertices_mask is not None:
        triangles_mask = vertices_to_triangles_mask(mesh, vertices_mask)

    # Compute probability per triangle (based on weights and mask)
    tri_prob_map = get_triangle_probability(
        triangles_weights=triangles_weights, triangles_mask=triangles_mask)

    return tri_prob_map


def generate_seeds_from_map(mesh, tri_prob_map, nb_seed, rand_gen=None):
    # Compute probability per triangle (based on weights and mask)
    # Pick random triangles
    tri_idx = get_random_triangle_indices(
        mesh, nb_seed, prob=tri_prob_map, rand_gen=rand_gen)

    # pick random trilinear coordinates
    tri_coord = get_random_trilinear_coordinates(nb_seed, rand_gen=rand_gen)
    return tri_idx, tri_coord


def generate_seeds_from_mesh(mesh, nb_seed, vertices_weights=None, triangles_weights=None,
                             vertices_mask=None, triangles_mask=None, rand_gen=None):
    # Compute probability per triangle (based on weights and mask)
    tri_prob = generate_seed_map_from_mesh(mesh,
                                           vertices_weights=vertices_weights,
                                           triangles_weights=triangles_weights,
                                           vertices_mask=vertices_mask,
                                           triangles_mask=triangles_mask)

    return generate_seeds_from_map(mesh, tri_prob, nb_seed, rand_gen=rand_gen)


def get_random_triangle_indices(mesh, nb_seed, prob=None, rand_gen=None):
    np.random.seed(rand_gen)
    return np.random.choice(mesh.get_nb_triangles(), size=nb_seed, p=prob)


def get_random_trilinear_coordinates(nb_seed, rand_gen=None):
    # choose vertices randomly (on each triangle)
    # http://mathworld.wolfram.com/TrianglePointPicking.html
    np.random.seed(rand_gen)
    tri_coord = np.random.rand(nb_seed, 3)
    is_upper_triangle = (tri_coord[:, 1:].sum(axis=-1) > 1.0)
    tri_coord[is_upper_triangle] = 1.0 - tri_coord[is_upper_triangle]
    tri_coord[:, 0] = 1.0 - (tri_coord[:, 1] + tri_coord[:, 2])
    return tri_coord


def get_triangle_probability(triangles_weights=None, triangles_mask=None):
    if triangles_weights is not None:
        tri_prob = triangles_weights.astype(np.float64)
        if triangles_mask is not None:
            tri_prob *= triangles_mask.astype(np.float64)
    else:
        if triangles_mask is not None:
            tri_prob = triangles_mask.astype(np.float64)
        else:  # If both are None
            return None

    # Normalize probabilities (sum to 1)
    return tri_prob / tri_prob.sum()


def vertices_to_triangles_weights(mesh, vts_weights):
    return np.mean(vts_weights[mesh.get_triangles()], axis=1)


def vertices_to_triangles_mask(mesh, vts_mask):
    return np.any(vts_mask[mesh.get_triangles()], axis=1)


def get_vertices_from_seeds(mesh, triangles_idx, trilinear_coord):
    tri_vts = get_triangles_vertices(mesh, triangles_idx)
    return get_vertices_from_trilinear_coordinates(tri_vts, trilinear_coord)


def get_normals_from_seeds(mesh, triangles_idx, trilinear_coord):
    tri_vts_normals = mesh.vertices_normal()[mesh.get_triangles()[triangles_idx]]
    return get_vertices_from_trilinear_coordinates(tri_vts_normals, trilinear_coord)


def get_triangles_vertices(mesh, triangles_idx):
    return mesh.get_vertices()[mesh.get_triangles()[triangles_idx]]


def get_vertices_from_trilinear_coordinates(triangles_vts, trilinear_coord):
    # equivalent to: seed_pts = (a * b[..., np.newaxis]).sum(axis=1)
    return np.einsum('ijk,ij...->ik', triangles_vts, trilinear_coord)


def get_trilinear_coordinates_from_vertices(triangles_vts, pts,
                                            force_inside=False):
    # https://gamedev.stackexchange.com/questions/23743/whats-the-most-efficient-way-to-find-barycentric-coordinates
    v0 = triangles_vts[:, 1] - triangles_vts[:, 0]
    v1 = triangles_vts[:, 2] - triangles_vts[:, 0]
    v2 = pts - triangles_vts[:, 0]
    d00 = np.sum(v0 * v0, axis=-1)
    d01 = np.sum(v0 * v1, axis=-1)
    d11 = np.sum(v1 * v1, axis=-1)
    d20 = np.sum(v2 * v0, axis=-1)
    d21 = np.sum(v2 * v1, axis=-1)
    invdenom = 1.0 / (d00 * d11 - d01 * d01)

    tri_coord = np.zeros_like(pts)
    tri_coord[:, 1] = (d11 * d20 - d01 * d21) * invdenom
    tri_coord[:, 2] = (d00 * d21 - d01 * d20) * invdenom
    tri_coord[:, 0] = 1.0 - tri_coord[:, 1] - tri_coord[:, 2]

    if force_inside:
        tri_coord[tri_coord < 0] = 0.0
        tri_coord /= np.sum(tri_coord, axis=-1, keepdims=True)

    return tri_coord


def closest_initial_dir(direction_getter, seed_pts, seed_dirs):
    new_dirs = np.zeros_like(seed_dirs)
    for i in range(len(seed_pts)):
        pts = seed_pts[i]
        init_dir = seed_dirs[i]

        max_dot = 0.0
        directions = direction_getter.initial_direction(pts)
        for j in range(len(directions)):
            p_dir = directions[j]
            dot_v = np.dot(init_dir, p_dir)
            abs_dot = np.abs(dot_v)

            if abs_dot > max_dot:
                max_dot = abs_dot
                if dot_v < 0:
                    new_dirs[i] = -p_dir
                else:
                    new_dirs[i] = p_dir

    return new_dirs
