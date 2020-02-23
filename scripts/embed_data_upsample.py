import argparse
import logging
import numpy as np
import vtk

from os.path import isfile

DESCRIPTION = """
  Save the given data to the given .vtk files upsampling where needed.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE',
                   type=str, help='Path of the .vtk mesh file for the right hemisphere.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--data', action='store', metavar='DATA', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

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
    shape = mesh['shape']

    # load the surfaces, downsampling as needed
    logging.info('Loading and setting scalers to .vtk surface.')

    surfaces = dict()
    writer = vtk.vtkPolyDataWriter()

    data = np.load(args.data, allow_pickle=True)

    for i in range(len(data.files)):
        surfaces[0] = load_vtk(args.lh_surface)
        surfaces[1] = load_vtk(args.rh_surface)

        for j in range(2):
            offset = j * shape[1]

            data_source = data[data.files[i]]
                
            data_scaler = vtk.vtkFloatArray()
            data_scaler.SetNumberOfValues(shape[j+4])
            data_scaler.SetNumberOfComponents(1)
            data_scaler.SetName(data.files[i])
            
            for k in range(shape[j+1]):
                vertex = np.array(mapping[k+offset]) - (j * shape[4])

                for v in vertex:
                    data_scaler.InsertValue(v, data_source[k+offset])

            surfaces[j].GetPointData().SetScalars(data_scaler)

            filename = filenames[j].rsplit('.vtk')[0] + data.files[i] + '.vtk'
            writer.SetInputData(surfaces[j])
            writer.SetFileName(filename)
            writer.Update()


if __name__ == "__main__":
    main()

