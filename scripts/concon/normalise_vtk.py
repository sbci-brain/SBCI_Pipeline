import argparse
import logging
import string
import numpy as np
import os

from os.path import isfile

DESCRIPTION = """
  Normalise the given .vtk file to have max coordinate [-1, 1]
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to normalise.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .vtk file to save the output to.')

    p.add_argument('-f', action='store_true', dest='overwrite',
                   help='If set, overwrite files if they already exist.')

    return p


def main():
    parser = _build_args_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    # make sure the surface file exists
    if not isfile(args.surface):
        parser.error('The file "{0}" must exist.'.format(args.surface))

    # make sure files are not accidently overwritten
    if isfile(args.output):
        if args.overwrite:
            logging.info('Overwriting "{0}".'.format(args.output))
            os.remove(args.output)
        else:
            parser.error('The file "{0}" already exists. Use -f to overwrite it.'.format(args.output))

    logging.info('Loading and normalising the .m surface.')

    with open(args.surface, 'r') as inputfile, open(args.output, 'w') as outputfile:
        section = 0

        for line in inputfile:
           words = line.rstrip().split(' ')

           if words[0] == 'POLYGONS':
               section = 2

           # vertex definitions
           if section == 1:
               for i in range(int(len(words) / 3)):
                   coords = np.array(words[(3*i):(3+3*i)]).astype(np.float)

                   # normalise each vertex
                   area = np.sqrt(coords[0]**2 + coords[1]**2 + coords[2]**2)

                   # normalise scale
                   coords[0] = coords[0] / area
                   coords[1] = coords[1] / area
                   coords[2] = coords[2] / area
                   
                   outputfile.write(string.join(coords.astype(np.str), sep = ' ') + ' ')

               outputfile.write('\n')
               continue

           if words[0] == 'POINTS':
               section = 1
               coords = np.zeros((int(words[1]), 3), dtype=np.double)

           outputfile.write(line)


if __name__ == "__main__":
    main()
