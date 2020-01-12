import argparse
import logging
import string
import numpy as np
import os

from os.path import isfile

DESCRIPTION = """
  Normalise the given .m file to have max coordinate [-1, 1]
"""


def _build_args_parser():
    p = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                description=DESCRIPTION)

    p.add_argument('--surface', action='store', metavar='SURFACE', required=True,
                   type=str, help='Path of the .m mesh file to normalise.')

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

    logging.info('Loading and normalising the .m surface.')

    with open(args.surface, 'r') as inputfile, open(args.output, 'w') as outputfile:
        count = 0
        for line in inputfile:
           words = line.rstrip().split(' ')

           if line.rstrip() == "":
               continue

	   if words[0] == 'Vertex':
               count = count + 1

        i = 0
        coords = np.zeros((count,3), dtype=np.double)

        # rewind file to read again
        inputfile.seek(0)

        # populate coordinate arrays
        for line in inputfile:
           words = line.rstrip().split(' ')

           if line.rstrip() == "":
               continue

	   if words[0] == 'Vertex':
               coords[i,0] = np.double(words[2])
               coords[i,1] = np.double(words[3])
               coords[i,2] = np.double(words[4])
               i = i + 1

        # rewind file to read again
        inputfile.seek(0)

        index = 0
        for line in inputfile:
           words = line.rstrip().split(' ')

	   if words[0] == 'Vertex':
               # normalise each vertex
               area = np.sqrt(coords[index,0]**2 + coords[index,1]**2 + coords[index,2]**2)

               # normalise scale
               coords[index,0] = coords[index,0] / area
               coords[index,1] = coords[index,1] / area
               coords[index,2] = coords[index,2] / area

               outputfile.write('Vertex ' + str(index+1) + ' ' + string.join([str(coords[index,0]), str(coords[index,1]), str(coords[index,2])], sep = ' ') + '\n')
               index = index + 1
           else:
               # save all the polygon definitions unchanged
               outputfile.write(string.join(words, sep = ' ') + '\n')
        

if __name__ == "__main__":
    main()
