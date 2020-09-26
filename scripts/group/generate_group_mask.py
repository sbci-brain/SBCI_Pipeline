import argparse
import logging
import numpy as np
import vtk

from os.path import isfile
from nibabel.freesurfer.io import read_annot

DESCRIPTION = """
  Mask any unknown vertices from individual meshes that do not already coincide with the average mesh
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--root', action='store', metavar='ROOT', required=True,
                   type=str, help='Path of the folder containing the subjects.')

    p.add_argument('--subjects', action='store', metavar='SUBJECTS', required=True,
                   type=str, help='Path of the file with a list of required subjects.')

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Name of the surface files to use.')

    p.add_argument('--annot', action='store', metavar='ANNOT', required=True,
                   type=str, help='Name of the annotation files to use.')

    p.add_argument('--avg_surface', action='store', metavar='AVG_SURFACE', required=True,
                   type=str, help='Name of the surface files to use.')

    p.add_argument('--avg_annot', action='store', metavar='AVG_ANNOT', required=True,
                   type=str, help='Name of the annotation files to use.')

    p.add_argument('--out_mask', action='store', metavar='OUTPUT', default=None, required=False,
                   type=str, help='output file.')

    p.add_argument('--out_mesh', action='store', metavar='OUTPUT', default=None, required=False,
                   type=str, help='output file.')

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

    # make sure the surfaces file exists
    #if not isfile(args.surface):
    #    parser.error('The file "{0}" must exist.'.format(args.surface))

    #if not isfile(args.annot):
    #    parser.error('The file "{0}" must exist.'.format(args.annot))

    #if not isfile(args.avg_surface):
    #    parser.error('The file "{0}" must exist.'.format(args.avg_surface))

    #if not isfile(args.avg_annot):
    #    parser.error('The file "{0}" must exist.'.format(args.rh_annot))

    # warn if they already exist
    if not args.out_mask == None and isfile(args.out_mask):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.out_mask))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.out_mask))

    if not args.out_mesh == None and isfile(args.out_mesh):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.out_mesh))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.out_mesh))

    roi_points = np.empty((0,3))

    logging.info('Generating mask from registered surfaces.')

    # load unknown vertices from each registered surface
    with open(args.subjects, 'r') as subjectfile:
        for line in subjectfile:
            subject = line.rstrip()
            logging.info('Generating mask from subject {0}.'.format(subject))
            
            surface = load_vtk('{0}/{1}/{2}'.format(args.root, subject, args.surface))
            labels = read_annot('{0}/{1}/{2}'.format(args.root, subject, args.annot))

            idx = np.where(labels[0] == -1)[0]
            n = len(idx)

            points = np.empty((n, 3))

            for i in range(n):
                points[i,:] = surface.GetPoint(idx[i])

            roi_points = np.append(roi_points, points, 0)

    logging.info('Joining with template mask.')

    # load unknown vertices from the average surface
    avg_surface = load_vtk(args.avg_surface)
    avg_labels = read_annot(args.avg_annot)

    idx = np.where(avg_labels[0] == -1)[0]
    n = len(idx)

    points = np.empty((n, 3))

    for i in range(n):
         points[i,:] = surface.GetPoint(idx[i])

    # join the average points to the individual points
    roi_points = np.append(roi_points, points, 0)

    logging.info('Mapping to template space.')
    
    # map the mask to the average surface
    locator = vtk.vtkPointLocator()
    locator.SetDataSet(avg_surface)
    locator.BuildLocator()

    N = avg_surface.GetNumberOfPoints()
    mask = np.zeros(N, np.int64)

    for i in range(roi_points.shape[0]):
        idx = locator.FindClosestPoint(roi_points[i,:])
        mask[idx] = 1

    # output a mesh for display
    if not args.out_mesh == None:
        data_scaler = vtk.vtkFloatArray()
        data_scaler.SetNumberOfComponents(1)
        data_scaler.SetName('Labels')
            
        for k in range(avg_surface.GetNumberOfPoints()):
            data_scaler.InsertNextValue(mask[k])
    
        avg_surface.GetPointData().SetScalars(data_scaler)
    
        writer = vtk.vtkPolyDataWriter()
        writer.SetInputData(avg_surface)
        writer.SetFileName(args.out_mesh)
        writer.Update()

    # output the actual mask
    if not args.out_mask == None:
        np.savez_compressed(args.out_mask, mask=mask)


if __name__ == "__main__":
    main()

