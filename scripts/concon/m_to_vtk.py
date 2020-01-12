import argparse
import logging
import string
import numpy
import os

from os.path import isfile

DESCRIPTION = """
  Convert a .m mesh file to a .vtk file.
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the .m mesh file to convert.')

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

    logging.info('Loading and converting the .vtk surface.')

    vtx_count = 0
    poly_count = 0
    index = 0

    with open(args.surface, 'r') as inputfile, open(args.output, 'w') as outputfile:
        for line in inputfile:
           words = line.rstrip().split(' ')

           if line.rstrip() == "":
               continue

	   if words[0] == 'Vertex':
               vtx_count = vtx_count + 1

           if words[0] == 'Face':
               poly_count = poly_count + 1

        # rewind file to start
        inputfile.seek(0)
 
        outputfile.write('# vtk DataFile Version 4.2\n')
        outputfile.write('vtk output\n')
        outputfile.write('ASCII\n')
        outputfile.write('DATASET POLYDATA\n')
        outputfile.write('POINTS ' + str(vtx_count) + ' float\n')

        firstface = True

        for line in inputfile:
           words = line.rstrip().split(' ')

           if line.rstrip() == "":
               continue

	   if words[0] == 'Vertex':
               outputfile.write(string.join(words[2:5], sep = ' ') + ' ')

               index = index + 1

               if (index % 3) == 0:
                   outputfile.write('\n')

           if words[0] == 'Face':
               if firstface:
                   outputfile.write('\nPOLYGONS ' + str(poly_count) + ' ' + str(poly_count*4) + '\n')
                   firstface = False

               a = str(int(words[2]) - 1)
               b = str(int(words[3]) - 1)
               c = str(int(words[4]) - 1)

               outputfile.write('3 ' + string.join([a,b,c], sep = ' ') + '\n')


if __name__ == "__main__":
    main()
