import argparse
import logging
import vtk
import re

import numpy as np

from os.path import isfile

DESCRIPTION = """
  Downsample a .vtk surface and output the new .vtk file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .npz file to save the output to.')

    p.add_argument('--resolution', action='store', metavar='REDUCTION', required=True,
                   type=str, help='Resolution from 0-7 corresponding to 2 + (10*4^n) vertices')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


# helper function to load the .vtk surfaces
def load_vtk(filename):
    reader = vtk.vtkPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()

    return reader.GetOutput()


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
        else:
            logging.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    res = re.findall(r"\d+", args.resolution)
    res = int(res[-1])

    # make sure the resolution is between 0-7
    if res > 7 or res < 0:
        logging.error('Ico surface must be between (0,7).')

    # perform the downsampling
    logging.info('Resampling to icosphere resolution: {0}.'.format(res))
    result = np.arange(0, 2 + (10*4**res), 1)

    # save the results
    np.savez_compressed(args.output, points=result)


if __name__ == "__main__":
    main()
                                           
