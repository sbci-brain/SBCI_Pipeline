import argparse
import logging
import string
import numpy
import os

from os.path import isfile

DESCRIPTION = """
  Convert a .vtk mesh file to a .m mesh file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the .vtk mesh file to convert.')

    p.add_argument('--output', action='store', metavar='OUTPUT', required=True,
                   type=str, help='Path of the .m file to save the output to.')

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

    logging.info('Loading and converting the .vtk surface.')

    section = 0
    index = 1

    with open(args.surface, 'r') as inputfile, open(args.output, 'w') as outputfile:
        for line in inputfile:
           words = line.rstrip().split(' ')

           if line.rstrip() == "":
               continue

	   if words[0] == 'POINTS':
               section = 1
               index = 1
               continue

           if words[0] == 'POLYGONS':
               section = 2
               index = 1
               continue

           # vertex definitions
           if section == 1:
               for i in range(int(len(words) / 3)):
                   outputfile.write('Vertex ' + str(index) + ' ' + string.join(words[(3*i):(3+3*i)], sep = ' ') + '\n')
                   index = index + 1

           # polygon definitions
           if section == 2:
               a = str(int(words[1]) + 1)
               b = str(int(words[2]) + 1)
               c = str(int(words[3]) + 1)
               outputfile.write('Face ' + str(index) + ' ' + string.join([a,b,c], sep = ' ') + '\n')
               index = index + 1
            

if __name__ == "__main__":
    main()
