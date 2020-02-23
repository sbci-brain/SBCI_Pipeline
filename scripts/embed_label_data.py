import argparse
import logging
import numpy as np
import vtk

from os.path import isfile
from nibabel.freesurfer.io import read_annot

DESCRIPTION = """
  Save parcellation labels to the given .vtk files
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the right hemisphere.')

    p.add_argument('--lh_annot', action='store', metavar='LH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the left hemisphere.')

    p.add_argument('--rh_annot', action='store', metavar='RH_ANNOT', required=True,
                   type=str, help='Path of the .annot file for the right hemisphere.')

    p.add_argument('--suffix', action='store', metavar='SUFFIX', required=False,
                   type=str, default='_', help='Suffix of output files.')

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

    # make sure the files exist
    if not isfile(args.lh_annot):
        parser.error('The file "{0}" must exist.'.format(args.lh_annot))

    if not isfile(args.rh_annot):
        parser.error('The file "{0}" must exist.'.format(args.rh_annot))

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
    
    # load annotation files
    labels = dict()
    labels[0] = read_annot(args.lh_annot)
    labels[1] = read_annot(args.rh_annot)

    # load the surfaces, downsampling as needed
    logging.info('Loading and setting scalers to .vtk surface.')

    surfaces = dict()
    surfaces[0] = load_vtk(args.lh_surface)
    surfaces[1] = load_vtk(args.rh_surface)

    writer = vtk.vtkPolyDataWriter()

    for j in range(2):
        data_source = labels[j][0]
        data_scaler = vtk.vtkFloatArray()
        data_scaler.SetNumberOfComponents(1)
        data_scaler.SetName('Labels')
        
        for k in range(surfaces[j].GetNumberOfPoints()):
            data_scaler.InsertNextValue(data_source[k])

        surfaces[j].GetPointData().SetScalars(data_scaler)

        filename = filenames[j]
        writer.SetInputData(surfaces[j])
        writer.SetFileName(filename)
        writer.Update()


if __name__ == "__main__":
    main()

