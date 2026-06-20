# Python 3 SBCI scripts

This directory contains the Python 3 implementations used by the converted
SBCI workflow.

Notable compatibility fixes include honoring the requested random seed in
`scil_surface_seeds_from_map.py`, allowing empty inner and outer surface lists
in `scil_surface_concatenate.py`, and replacing deprecated NumPy scalar aliases
with explicit-width types.

For installation and workflow instructions, see
`ADNI_example/py3/env_setup/README.md` from the repository root.
