import argparse
import logging
import numpy as np
import vtk

from scipy import sparse
from os.path import isfile

DESCRIPTION = """
  Generate mask for points within a radius epsilon on the surface.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path to the LH surface .vtk file to use.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path to the RH surface .vtk file to use.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--epsilon', action='store', metavar='EPSILON', required=True,
                   type=float, help='Max radius for mask calculation.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to output.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


# load all the required surfaces and build locator algorithms
def initialise_surfaces(surface_files):
    surfaces = dict()
    locators = dict()

    for i, filename in enumerate(surface_files):
        surfaces[i] = load_vtk(filename)

        # point locators are used to quickly 
        # search for points on a given surface
        locators[i] = vtk.vtkPointLocator()
        locators[i].SetDataSet(surfaces[i])
        locators[i].BuildLocator()

    return surfaces, locators


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.rh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    if not isfile(args.mesh):
        parser.error('The file "{0}" must exist.'.format(args.mesh))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces and initialise cell locator algorithms
    logging.info('Loading .vtk surfaces, mapping, and intersections.')

    surfaces, locators = initialise_surfaces([args.lh_surface, args.rh_surface])

    # load the mapping
    mesh = np.load(args.mesh, allow_pickle=True)

    mapping = mesh['mapping']
    shape = mesh['shape']

    logging.info('Calculating mask with epsilon = ' + str(args.epsilon) + '.')

    # prepare variables for density calculation
    result = vtk.vtkIdList()
    density = np.zeros(shape[0])
    offset = surfaces[0].GetNumberOfPoints()

    mask_matrix = sparse.dok_matrix((shape[0], shape[0]), dtype=np.bool)

    # calculate epsilon ball density at each vertex
    for i in range(2):
	for j in xrange(surfaces[i].GetNumberOfPoints()):
            current_pt = surfaces[i].GetPoint(j)

            locators[0].FindPointsWithinRadius(args.epsilon, current_pt, result)

            ids = np.array([result.GetId(x) for x in range(result.GetNumberOfIds())])
            mask_matrix[ids, j+(i*offset)] = True
            mask_matrix[j+(i*offset), ids] = True

            locators[1].FindPointsWithinRadius(args.epsilon, current_pt, result)

            ids = np.array([result.GetId(x) for x in range(result.GetNumberOfIds())]) 
            mask_matrix[ids+offset, j+(i*offset)] = True
            mask_matrix[j+(i*offset), ids+offset] = True


    logging.info('Saving results.')

    # save the results
    sparse.save_npz(args.output, mask_matrix.tocsr())


if __name__ == "__main__":
    main()
