import argparse
import logging
import vtk

import scipy.io as scio
import numpy as np

import vtk.util.numpy_support as ns
from os.path import isfile, splitext

DESCRIPTION = """
  Extract points from a .vtk surface and output as a .mat file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to extract points from.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to extract points from.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surface file exists
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.rh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    points = dict()
    points[0] = load_vtk(args.lh_surface).GetPoints()
    points[1] = load_vtk(args.rh_surface).GetPoints()

    lh_n = points[0].GetNumberOfPoints()
    rh_n = points[1].GetNumberOfPoints()

    result = np.zeros((lh_n + rh_n, 5), np.float)

    for i in range(lh_n + rh_n):
        hemisphere = int(i >= lh_n) 

	result[i, 0] = i - (hemisphere * lh_n) + 1
        result[i, 1] = hemisphere
        result[i, 2:5] = points[hemisphere].GetPoint(i - (lh_n * hemisphere))

    triangles = dict()

    polydata = ns.vtk_to_numpy(load_vtk(args.lh_surface).GetPolys().GetData())
    triangles[0] = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T
    polydata = ns.vtk_to_numpy(load_vtk(args.rh_surface).GetPolys().GetData())
    triangles[1] = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T

    tri_n = triangles[0].shape[0]

    tri_result = np.zeros((triangles[0].shape[0] + triangles[1].shape[0], 5), np.float)

    points[0] = ns.vtk_to_numpy(load_vtk(args.lh_surface).GetPoints().GetData())
    points[1] = ns.vtk_to_numpy(load_vtk(args.rh_surface).GetPoints().GetData())

    for i in [0,1]:
        vertices = np.reshape(points[i][triangles[i],:], (triangles[i].shape[0], 3, 3))

        for j in range(vertices.shape[0]):
            normal = np.cross(vertices[j,1,:] - vertices[j,0,:], vertices[j,2,:] - vertices[j,0,:])
            area = np.linalg.norm(normal) / 2

            #CxA = np.cross(vertices[j,2,:],vertices[j,0,:])
            #BxA = np.cross(vertices[j,1,:],vertices[j,0,:])
            #AxB = np.cross(vertices[j,0,:],vertices[j,1,:])
            #CxB = np.cross(vertices[j,2,:],vertices[j,1,:])
            #BxC = np.cross(vertices[j,1,:],vertices[j,2,:])
            #AxC = np.cross(vertices[j,0,:],vertices[j,2,:])

            #CAB = np.inner(CxA, BxA) / (np.linalg.norm(CxA) * np.linalg.norm(BxA))
            #ABC = np.inner(AxB, CxB) / (np.linalg.norm(AxB) * np.linalg.norm(CxB))
            #BCA = np.inner(BxC, AxC) / (np.linalg.norm(BxC) * np.linalg.norm(AxC))

            tri_result[j + (tri_n * i), 0] = i + 1
            tri_result[j + (tri_n * i), 1:4] = triangles[i][j,:] + 1
            tri_result[j + (tri_n * i), 4] = area
            #tri_result[j + (tri_n * i), 4] = np.arccos(CAB) + np.arccos(ABC) + np.arccos(BCA) - np.pi

    # save the results
    scio.savemat(args.output, {'lh_T': tri_result[0:tri_n, 1:4],
                               'rh_T': tri_result[tri_n:, 1:4],
                               'lh_V': result[0:lh_n, 2:5],
                               'rh_V': result[lh_n:, 2:5],
                               'lh_area': tri_result[0:tri_n, 4],
                               'rh_area': tri_result[tri_n:, 4]})

if __name__ == "__main__":
    main()
