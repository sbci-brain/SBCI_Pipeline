import argparse
import logging
import numpy as np
import vtk

from os.path import isdir, isfile, join

DESCRIPTION = """
  Convert snapped intersections to spherical coordinates and save as a concon format .tsv file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--lh_surface', action='store', metavar='LH_SURFACE', required=True,
                   type=str, help='Path of the high resolution sphere .vtk mesh file for the left hemisphere.')

    p.add_argument('--rh_surface', action='store', metavar='RH_SURFACE', required=True,
                   type=str, help='Path of the high resolution sphere .vtk mesh file for the right hemisphere.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of snapped intersections.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .tsv file to save the output to (concon format).')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def initialise_surfaces(surface_files):
    surfaces = dict()

    for i in range(len(surface_files)):
       surfaces[i] = load_vtk(surface_files[i])

    return surfaces


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surfaces file exists
    if not isfile(args.lh_surface):
        parser.error('The file "{0}" must exist.'.format(args.lh_surface))

    if not isfile(args.rh_surface):
        parser.error('The file "{0}" must exist.'.format(args.rh_surface))

    # make sure the intersections.npz file exists
    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.intersections))

    # make sure files are not overwritten by accident
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces (downsampling if needed) and initialise cell locator algorithms
    logging.info('Loading the .vtk surfaces and snapped intersections data.')
    surfaces = initialise_surfaces([args.lh_surface, args.rh_surface])

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)

    pts_in = intersections['v_ids0']
    pts_out = intersections['v_ids1']
    surf_in = intersections['surf_ids0']
    surf_out = intersections['surf_ids1']

    # subcortical regions not yet supported
    mask = (surf_in <= 1) & (surf_out <= 1)
    pts_in = pts_in[mask]
    pts_out = pts_out[mask]
    surf_in = surf_in[mask]
    surf_out = surf_out[mask]

    n = len(pts_in)
    result = np.empty((n, 10), dtype='O')

    logging.info('Converting snapped intersections to spherical coordinates (concon format).')

    with open(args.output, 'w') as outfile:
        outfile.write("#%i\n" % (n))
        
        for i in range(n):
            surface_id = surf_in[i]

            norm = surfaces[surface_id].GetPoint(int(pts_in[i]))
            area = np.sqrt(norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2])

            norm = norm / area

            result[i,0] = 0
            result[i,1] = int(1 - surf_in[i])
            result[i,2:5] = norm

            ################################

            surface_id = surf_out[i]

            norm = surfaces[surface_id].GetPoint(int(pts_out[i]))
            area = np.sqrt(norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2])

            norm = norm / area
    
            result[i,5] = 0
            result[i,6] = int(1 - surf_out[i])
            result[i,7:10] = norm

            outfile.write("%i\t %i\t %f\t %f\t %f\t %i\t %i\t %f\t %f\t %f\n" % (result[i,0], result[i,1], result[i,2], result[i,3], result[i,4],
                                                                                 result[i,5], result[i,6], result[i,7], result[i,8], result[i,9]))
    
            if i % 100000 == 0:
                logging.info('Processing intersection: ' + str(i))

    
if __name__ == "__main__":
    main()
