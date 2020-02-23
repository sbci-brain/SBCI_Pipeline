import argparse
import logging
import numpy as np
import vtk

from os.path import isfile

DESCRIPTION = """
  Map the downsampled sphere to other meshes (eg lh_white, lh_inflated).
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the right hemisphere.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfaces (.npz).')

    p.add_argument('--suffix', action='store', metavar='SUFFIX', required=True,
                   type=str, help='Suffix of output files.')

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
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # generate output filenames
    lh_filename = args.lh_surface.rsplit('.vtk')[0] + args.suffix + '.vtk'
    rh_filename = args.rh_surface.rsplit('.vtk')[0] + args.suffix + '.vtk'

    filenames = [lh_filename, rh_filename]

    # warn if they already exist
    for i in range(2):
        if isfile(filenames[i]):
            if args.overwrite:
                logging.info('Overwriting "{0}".'.format(filenames[i]))
            else:
                parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(filenames[i]))
    
    # load mapping
    mesh = np.load(args.mesh, allow_pickle=True)
    mapping = mesh['mapping']
    ids = np.concatenate([mesh['lh_ids'], mesh['rh_ids']])

    # load the surfaces, downsampling as needed
    logging.info('Loading and resampling .vtk surface.')

    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    n = len(mesh['lh_ids'])
    lh_orig = mesh['shape'][4]

    for i in range(len(ids)):
        side = int(i >= n)
        snap_point = surfaces[side].GetPoints().GetPoint(ids[i])

        for j in mapping[i]:
            surfaces[side].GetPoints().SetPoint(j - (side*lh_orig), snap_point)

    for i in range(2):
        cleaner = vtk.vtkCleanPolyData()
        cleaner.SetInputData(surfaces[i])
        cleaner.ConvertPolysToLinesOn()

        triangle = vtk.vtkTriangleFilter()
        triangle.SetInputConnection(cleaner.GetOutputPort())
        triangle.PassVertsOff()
        triangle.PassLinesOff()

        writer = vtk.vtkPolyDataWriter()
        writer.SetInputConnection(triangle.GetOutputPort())
        writer.SetFileName(filenames[i])
        writer.Update()


if __name__ == "__main__":
    main()

