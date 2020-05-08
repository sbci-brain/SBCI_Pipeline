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

    p.add_argument('--intersections', nargs='+', default=[], required=True,
                   type=str, help='Path of the .npz files of intersections that have been snapped to nearest vertices.')

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
    for intersections in args.intersections:
        if not isfile(intersections):
            parser.error('The file "{0}" must exist.'.format(intersections))

    # make sure files are not overwritten by accident
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    # load the surfaces (downsampling if needed) and initialise cell locator algorithms
    logging.info('Loading the .vtk surfaces and snapped intersections data.')
    surfaces = initialise_surfaces([args.lh_surface, args.rh_surface])

    result = np.empty(10, dtype='O')

    logging.info('Converting snapped intersections to spherical coordinates (concon format).')

    # total number of fibers
    N = 0

    with open(args.output, 'w') as outfile:
      for intersections_file in args.intersections:
        # load the intersections file
        logging.info('Processing intersections from: ' + intersections_file)
        intersections = np.load(intersections_file, allow_pickle=True)

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
 
        for i in range(n):
          surface_id = surf_in[i]

          norm = surfaces[surface_id].GetPoint(int(pts_in[i]))
          area = np.sqrt(norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2])

          norm = norm / area

          result[0] = 0
          result[1] = int(1 - surf_in[i])
          result[2:5] = norm

          ################################

          surface_id = surf_out[i]

          norm = surfaces[surface_id].GetPoint(int(pts_out[i]))
          area = np.sqrt(norm[0]*norm[0] + norm[1]*norm[1] + norm[2]*norm[2])

          norm = norm / area
  
          result[5] = 0
          result[6] = int(1 - surf_out[i])
          result[7:10] = norm

          outfile.write("%i\t %i\t %f\t %f\t %f\t %i\t %i\t %f\t %f\t %f\n" % (result[0], result[1], result[2], result[3], result[4],
                                                                               result[5], result[6], result[7], result[8], result[9]))
  
          if i % 100000 == 0:
              logging.info('Processing intersection: ' + str(N + i))

        N = N + n

    # need to append the total fiber count to the first line
    with open(args.output, 'r+') as outfile:
      file_contents = outfile.read()

      outfile.seek(0, 0)
      outfile.write("#%i\n" % (N))
      outfile.write(file_contents)
    

if __name__ == "__main__":
    main()
