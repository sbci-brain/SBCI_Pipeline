import argparse
import logging
import numpy as np
import vtk
import re

from os.path import isfile
import vtk.util.numpy_support as ns

DESCRIPTION = """
  Downsample an ICO surface to the given resolution
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE',
                   type=str, help='Path of the .vtk mesh file to downsample.')

    p.add_argument('--res', action='store', metavar='REDUCTION', required=True,
                   type=str, help='Resolution from 0-7 corresponding to 2 + (10*4^res) vertices')

    p.add_argument('--output', action='store', metavar='SUFFIX', required=True,
                   type=str, help='Path of the .vtk mesh file to output.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surfaces file exists
    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    # warn output already exists
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))
    
    # get the target resolution
    res = re.findall(r"\d+", args.res)
    res = int(res[-1])

    # make sure the resolution is between 0-7
    if res > 7 or res < 0:
        logging.error('Target ico surface must be between (0,7).')

    # load the surfaces, downsampling as needed
    logging.info('Resampling to ico surface resolution: {0}.'.format(res))
    
    surface = load_vtk(args.surface)

    pointdata = ns.vtk_to_numpy(surface.GetPoints().GetData())
    orig_res = np.argwhere(2 + (10*4**np.arange(0,8)) == pointdata.shape[0]).flatten()

    if np.any(orig_res):
        orig_res = orig_res[0]
        logging.info('Original resolution is: {0}'.format(orig_res))

        if orig_res < res:
            logging.error('Surface is lower resolution than target')
    else:
        logging.error('Surface does not have the correct number of vertices to be an ICO (0-7) surface')

    polydata = ns.vtk_to_numpy(surface.GetPolys().GetData())
    triangles = np.vstack([polydata[1::4], polydata[2::4], polydata[3::4]]).T
    
    if not triangles.shape[0] == (20*4**orig_res):
        logging.error('Surface does not have the correct number of triangles')
    
    # recursively downsample the triangles
    for j in range(orig_res-1, res-1, -1):
        N = 2 + (10*4**j) - 1
        new_tri = np.zeros((20*4**j, 3)).astype(int)
        old_tri = np.argwhere(np.all(triangles > N, axis=1))

        logging.info('Merging triangles to ico{0}'.format(j))
        
        for k in range(0, old_tri.shape[0]):
            v_idx = triangles[old_tri[k],:]
            f_idx = np.sum(np.isin(triangles, v_idx), axis=1) == 2
            to_merge = triangles[f_idx,:]

            new_tri[k,:] = (np.sum(to_merge*(to_merge <= N), axis=0))
    
        triangles = new_tri
    
    # get the vertex ids
    v_ids = np.arange(0, 2 + (10*4**res), 1)
    vertices = pointdata[v_ids,:]

    # create the new downsampled surface
    new_points = vtk.vtkPoints()
    new_points.SetData(ns.numpy_to_vtk(vertices))
  
    new_polydata = np.ones((3*20*4**res, 1))
    new_polydata[0::3,0] = triangles[:,0]
    new_polydata[1::3,0] = triangles[:,1]
    new_polydata[2::3,0] = triangles[:,2]

    new_triangles = vtk.vtkCellArray()
    for i in range(0,triangles.shape[0]):
        new_triangles.InsertNextCell(3)
        new_triangles.InsertCellPoint(int(triangles[i,0]))
        new_triangles.InsertCellPoint(int(triangles[i,1]))
        new_triangles.InsertCellPoint(int(triangles[i,2]))

    new_surface = vtk.vtkPolyData()
    new_surface.SetPoints(new_points)
    new_surface.SetPolys(new_triangles)
    
    writer = vtk.vtkPolyDataWriter()
    writer.SetInputData(new_surface)
    writer.SetFileName(args.output)
    writer.Update()


if __name__ == "__main__":
    main()

