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

    p.add_argument('--lh_surface_hi', action='store', metavar='LH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the left hemisphere.')

    p.add_argument('--lh_surface_lo', action='store', metavar='LH_SURFACE_LO', required=True,
                   type=str, help='Path of the low resolution .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface_hi', action='store', metavar='RH_SURFACE_HI', required=True,
                   type=str, help='Path of the high resolution .vtk mesh file for the right hemisphere.')

    p.add_argument('--rh_surface_lo', action='store', metavar='RH_SURFACE_LO', required=True,
                   type=str, help='Path of the low resolution .vtk mesh file for the right hemisphere.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

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


def calculate_area(mesh):
    quality = vtk.vtkMeshQuality()
    quality.SetInputData(mesh)
    quality.SetTriangleQualityMeasureToArea()
    quality.Update()

    area = quality.GetOutput().GetCellData().GetArray("Quality")
    result = np.array([area.GetValue(i) for i in range(area.GetNumberOfTuples())])

    return result


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surfaces file exists
    if not isfile(args.lh_surface_hi):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface_hi))

    if not isfile(args.lh_surface_lo):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface_lo))

    if not isfile(args.rh_surface_hi):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface_hi))

    if not isfile(args.rh_surface_lo):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface_lo))

    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces and initialise cell locator algorithms
    logging.info('Loading surfaces.')

    lh_hi_res = load_vtk(args.lh_surface_hi)
    rh_hi_res = load_vtk(args.rh_surface_hi)
    lh_lo_res = load_vtk(args.lh_surface_lo)
    rh_lo_res = load_vtk(args.rh_surface_lo)

    lh_hi_locator = build_locator(lh_hi_res)
    rh_hi_locator = build_locator(rh_hi_res)
    lh_lo_locator = build_locator(lh_lo_res)
    rh_lo_locator = build_locator(rh_lo_res)

    closest_pt = [0, 0, 0]
    cell = vtk.vtkGenericCell()
    cell_id = vtk.reference(0)
    sub_id = vtk.reference(0)
    d = vtk.reference(0)

    lo_n = lh_lo_res.GetNumberOfPoints() + rh_lo_res.GetNumberOfPoints()
    hi_n = lh_hi_res.GetNumberOfPoints() + rh_hi_res.GetNumberOfPoints()

    lo_to_hi = np.zeros(lo_n)
    hi_to_lo = np.zeros(hi_n)

    logging.info('Calculating metrics.')

    for i in range(lh_lo_res.GetNumberOfPoints()):
        current_pt = lh_lo_res.GetPoint(i)

        lh_hi_locator.FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

        dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)

        lo_to_hi[i] = dist

    offset = lh_lo_res.GetNumberOfPoints()

    for i in range(rh_lo_res.GetNumberOfPoints()):
        current_pt = rh_lo_res.GetPoint(i)

        rh_hi_locator.FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

        dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)

        lo_to_hi[i + offset] = dist

    for i in range(lh_hi_res.GetNumberOfPoints()):
        current_pt = lh_hi_res.GetPoint(i)

        lh_lo_locator.FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

        dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)

        hi_to_lo[i] = dist

    offset = lh_hi_res.GetNumberOfPoints()

    for i in range(rh_hi_res.GetNumberOfPoints()):
        current_pt = rh_hi_res.GetPoint(i)

        rh_lo_locator.FindClosestPoint(current_pt, closest_pt, cell, cell_id, sub_id, d)

        dist = np.sum((np.array(current_pt) - np.array(closest_pt)) ** 2)

        hi_to_lo[i + offset] = dist

    lo_to_hi = np.sqrt(lo_to_hi)
    hi_to_lo = np.sqrt(hi_to_lo)

    dst_a = np.max(lo_to_hi)
    dst_b = np.max(hi_to_lo)

    hausdorff_dst = max(dst_a, dst_b)

    print "Hausdorff distance: " + str(hausdorff_dst)

    lh_lo_area = calculate_area(lh_lo_res)
    rh_lo_area = calculate_area(rh_lo_res)

    lo_area = np.concatenate([lh_lo_area, rh_lo_area])

    print "Mean triangle area for meshA: " + str(np.mean(lo_area))
    print "SD triangle area for meshA: " + str(np.std(lo_area))

    lh_hi_area = calculate_area(lh_hi_res)
    rh_hi_area = calculate_area(rh_hi_res)

    hi_area = np.concatenate([lh_hi_area, rh_hi_area])

    print "Mean triangle area for meshB: " + str(np.mean(hi_area))
    print "SD triangle area for meshB: " + str(np.std(hi_area))

    np.savez_compressed(args.output, mesha=lo_to_hi, meshb=hi_to_lo)


if __name__ == "__main__":
    main()

