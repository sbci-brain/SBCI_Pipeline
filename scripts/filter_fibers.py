import argparse
import logging
import numpy as np
import tractconverter as tc

from os.path import isfile

from dipy.tracking import metrics
from dipy.tracking.streamline import length
from scilpy.io.vtk_streamlines import load_vtk_streamlines, save_vtk_streamlines

DESCRIPTION = """
  Filter fibers by length and loops angles.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--streamlines', action='store', metavar='STREAMLINES', required=True,
                   type=str, help='Path of the .fib file of tractography from SET.')

    p.add_argument('--intersections', action='store', metavar='INTERSECTIONS', required=True,
                   type=str, help='Path of the .npz file of intersections output by SET.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the intersections to.')

    p.add_argument('--output_tracts', action='store', metavar='OUTPUT_TRACTS', required=False, default=None,
                   type=str, help='Path of the .fib file to save the filtered tracts to.')

    p.add_argument('--angle', action='store', metavar='ANGLE', required=False, default=360,
                   type=float, help='Maximum angle for loops before filtering.')

    p.add_argument('--min_length', action='store', metavar='MIN_LENGTH', required=False, default=20,
                   type=int, help='Minimum length (in mm increments) for streamlines before before filtering.')

    p.add_argument('--max_length', action='store', metavar='MAX_LENGTH', required=False, default=200,
                   type=int, help='Maximum length (in mm increments) for streamlines before before filtering.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure all the given files exist
    if not isfile(args.streamlines):
        parser.error('The file "{0}" must exist.'.format(args.streamlines))

    if not isfile(args.intersections):
        parser.error('The file "{0}" must exist.'.format(args.intersections))

    # make sure that files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    if not args.output_tracts is None:
        if isfile(args.output_tracts):
            if args.overwrite:
                logging.info('Overwriting "{0}".'.format(args.output_tracts))
            else:
                parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output_tracts))

    # load the surfaces
    logging.info('Loading tractography and intersections.')

    # load the intersections file
    intersections = np.load(args.intersections, allow_pickle=True)

    surf_ids0 = intersections['surf_ids0']
    surf_ids1 = intersections['surf_ids1']
    tri_ids0 = intersections['tri_ids0']
    tri_ids1 = intersections['tri_ids1']
    pts0 = intersections['pts0']
    pts1 = intersections['pts1']

    # load the streamlines
    streamlines = load_vtk_streamlines(args.streamlines)

    logging.info('Filtering streamlines with angles >= {0} and length outside range {1}-{2}mm.'.format(args.angle, args.min_length, args.max_length))

    n = len(tri_ids0)
    i = 0
    mask = np.zeros(n, np.bool)

    # create the mask for filtering
    for s in streamlines:
        s_filter = (length(s) <= args.max_length) & (length(s) >= args.min_length)

        if s_filter:
            s_filter = (metrics.winding(s) < args.angle)
        
        mask[i] = s_filter
        
        i = i + 1

    # save the filtered tractography if requested
    if not args.output_tracts is None:
        filtered_tracts = np.array(streamlines)[mask]
        save_vtk_streamlines(filtered_tracts, args.output_tracts, binary = True)

    remaining = np.sum(mask)
    logging.info('Removed {0} streamlines with {1} remaining.'.format(n - remaining, remaining))

    # save the results
    np.savez_compressed(args.output,
                        pts0=pts0[mask],
                        tri_ids0=tri_ids0[mask],
                        surf_ids0=surf_ids0[mask],
                        pts1=pts1[mask],
                        tri_ids1=tri_ids1[mask],
                        surf_ids1=surf_ids1[mask])


if __name__ == "__main__":
    main()
