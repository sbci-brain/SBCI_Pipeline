import argparse
import logging
import numpy as np
import vtk

from scipy import sparse
from os.path import isfile

DESCRIPTION = """
  Calculate the density of fiber count within a radius of each vertex on the surface.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path to the LH surface .vtk file to use.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path to the RH surface .vtk file to use.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path to the .npz file of intersections that have been snapped to nearest vertices.')

    p.add_argument('--mesh', action='store', metavar='MESH', required=True,
                   type=str, help='Path to the mapping for the resolution of the surfacecs (.npz).')

    p.add_argument('--epsilon', action='store', metavar='EPSILON', required=True,
                   type=float, help='Radius for epsilon ball density calculation.')

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

    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.intersections))

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

    # load the intersections that have already been snapped to nearest vertices of full mesh
    cut = np.load(args.intersections, allow_pickle=True)

    surf_ids0 = cut['surf_ids0'].astype(np.int64)
    surf_ids1 = cut['surf_ids1'].astype(np.int64)
    pts0 = cut['v_ids0'].astype(np.int64)
    pts1 = cut['v_ids1'].astype(np.int64)

    # only keep the white matter surfaces from the intersections 
    # file and map rh vertex ids to the full brain indices
    pts0[surf_ids0 == 1] = pts0[surf_ids0 == 1] + shape[4]
    pts1[surf_ids1 == 1] = pts1[surf_ids1 == 1] + shape[4]

    pts0 = pts0[(surf_ids0 <= 1) & (surf_ids1 <= 1)]
    pts1 = pts1[(surf_ids0 <= 1) & (surf_ids1 <= 1)]

    # prepare vairables for the loop
    id_in_buf = pts0.copy()
    id_out_buf = pts1.copy()

    # map intersections to the lower resolution mesh
    for i in range(shape[0]):
        pts0[np.in1d(id_in_buf, mapping[i])] = i
        pts1[np.in1d(id_out_buf, mapping[i])] = i

    # calculate the number of streamline endpoints at each vertex, 
    # using a mask so that self connections are only counted once.
    mask = ~((pts0 - pts1) == 0)
    pts1 = pts1[mask]

    id_in = np.bincount(pts0)
    id_out = np.bincount(pts1)

    id_in = np.pad(id_in, (0, shape[0] - id_in.shape[0]), 'constant')
    id_out = np.pad(id_out, (0, shape[0] - id_out.shape[0]), 'constant')

    counts = id_in + id_out

    logging.info('Calculating density with epsilon = ' + str(args.epsilon) + '.')

    # prepare variables for density calculation
    result = vtk.vtkIdList()
    density = np.zeros(shape[0])
    offset = 0

    # calculate epsilon ball density at each vertex
    for i in range(len(surfaces)):
	for j in xrange(surfaces[i].GetNumberOfPoints()):
            current_pt = surfaces[i].GetPoint(j)

            locators[i].FindPointsWithinRadius(args.epsilon, current_pt, result)

            ids = np.array([result.GetId(x) for x in range(result.GetNumberOfIds())])
            density[offset + j] = np.mean(counts[ids + offset])

        offset = offset + surfaces[i].GetNumberOfPoints()

    logging.info('Saving results.')

    # save the results
    np.savez_compressed(args.output, density=density)


if __name__ == "__main__":
    main()
