import argparse
import logging
import numpy as np
import vtk

from os.path import isfile

DESCRIPTION = """
  Print evaluation metrics for the given mesh.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface_a', action='store', metavar='LH_SURFACE_LO', required=True,
                   type=str, help='Path of the low resolution .vtk mesh file for the left hemisphere.')

    p.add_argument('--lh_surface_b', action='store', metavar='LH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface_a', action='store', metavar='RH_SURFACE_LO', required=True,
                   type=str, help='Path of the low resolution .vtk mesh file for the right hemisphere.')

    p.add_argument('--rh_surface_b', action='store', metavar='RH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the right hemisphere.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--save_to_mesh', action='store_true', dest='save_to_mesh',
                   help='If set, save .vtk files with added distance scaler.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def build_locator(mesh):
    locator = vtk.vtkCellLocator()
    locator.SetDataSet(mesh)
    locator.BuildLocator()

    return locator


def save_to_mesh(surface, data, offset, filename):
    writer = vtk.vtkPolyDataWriter()

    data_scaler = vtk.vtkFloatArray()
    data_scaler.SetNumberOfComponents(1)
    data_scaler.SetName('Relative Distance')

    root_data = np.sqrt(data)
    
    for i in range(surface.GetNumberOfPoints()):
        data_scaler.InsertNextValue(root_data[i + offset])

    surface.GetPointData().SetScalars(data_scaler)

    filename = filename.rsplit('.vtk')[0] + '_distance.vtk'
    writer.SetInputData(surface)
    writer.SetFileName(filename)
    writer.Update()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surfaces file exists
    if not isfile(args.lh_surface_b):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface_b))

    if not isfile(args.lh_surface_a):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface_a))

    if not isfile(args.rh_surface_b):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface_b))

    if not isfile(args.rh_surface_a):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface_a))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces and initialise cell locator algorithms
    logging.info('Loading surfaces.')

    A_surfaces = {}
    A_surfaces[0] = load_vtk(args.lh_surface_a)
    A_surfaces[1] = load_vtk(args.rh_surface_a)

    A_locators = {}
    A_locators[0] = build_locator(A_surfaces[0])
    A_locators[1] = build_locator(A_surfaces[1])

    A_names = [args.lh_surface_a, args.rh_surface_a]

    B_surfaces = {}
    B_surfaces[0] = load_vtk(args.lh_surface_b)
    B_surfaces[1] = load_vtk(args.rh_surface_b)
    
    B_locators = {}
    B_locators[0] = build_locator(B_surfaces[0])
    B_locators[1] = build_locator(B_surfaces[1])

    B_names = [args.lh_surface_b, args.rh_surface_b]
    
    # objects to populate with every loop
    closest_pt = [0, 0, 0]
    cell = vtk.vtkGenericCell()
    cell_id = vtk.reference(0)
    sub_id = vtk.reference(0)
    d = vtk.reference(0)

    A_n = A_surfaces[0].GetNumberOfPoints() + A_surfaces[1].GetNumberOfPoints()
    B_n = B_surfaces[0].GetNumberOfPoints() + B_surfaces[1].GetNumberOfPoints()

    A_to_B = np.zeros(A_n)
    B_to_A = np.zeros(B_n)

    logging.info('Calculating metrics.')

    offset = 0

    # calculate distance from A to B
    for i in range(2):
        for j in range(A_surfaces[i].GetNumberOfPoints()):
            current_pt = A_surfaces[i].GetPoint(j)

            B_locators[i].FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

            dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)
 
            A_to_B[j + offset] = dist

        if args.save_to_mesh:
            save_to_mesh(A_surfaces[i], A_to_B, offset, A_names[i])

    	offset = offset + A_surfaces[i].GetNumberOfPoints()

    offset = 0

    # calculate distance from B to A
    for i in range(2):
        for j in range(B_surfaces[i].GetNumberOfPoints()):
            current_pt = B_surfaces[i].GetPoint(j)

            A_locators[i].FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

            dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)
 
            B_to_A[j + offset] = dist

        if args.save_to_mesh:
            save_to_mesh(B_surfaces[i], B_to_A, offset, B_names[i])

    	offset = offset + B_surfaces[i].GetNumberOfPoints()

    A_to_B = np.sqrt(A_to_B)
    B_to_A = np.sqrt(B_to_A)

    dst_a = np.max(A_to_B)
    dst_b = np.max(B_to_A)

    hausdorff_dst = max(dst_a, dst_b)

    np.savez_compressed(args.output, mesha=A_to_B, meshb=B_to_A, hausdorff=hausdorff_dst)


if __name__ == "__main__":
    main()

