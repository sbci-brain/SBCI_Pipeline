#!/bin/bash
# Python 3 / scilpy 2.x adaptation of ADNI_example/sbci_step4_process_surfaces.sh
#
# Per-subject: converts FreeSurfer surface files to VTK, flips coordinates,
# normalises sphere meshes, and extracts subject coordinates.
#
# Reference: https://github.com/sbci-brain/SBCI_Pipeline/blob/master/ADNI_example/sbci_step4_process_surfaces.sh
#
# Command mappings (Python 2 → Python 3):
#   python ${SCRIPT_PATH}/normalise_vtk.py  → python3 ${SBCI_PY3_SCRIPTS}/normalise_vtk.py
#   python ${SCRIPT_PATH}/get_coords.py     → python3 ${SBCI_PY3_SCRIPTS}/get_coords.py
#
# NOTE on scilpy 2.x:
#   scil_flip_surface.py  →  may be  scil_surface_flip.py  in scilpy 2.x
#
# Usage:
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   source ~/.bashrc_sbci_py3 && conda activate sbci_py3
#   cd /path/to/subject_dir
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/sbci_step4_process_surfaces_py3.sh

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

OUTPUTDIR=dwi_pipeline/sbci_connectome
SCDIR=dwi_pipeline/structure/t1_freesurfer

echo "Begin processing SBCI surfaces: $(date)"
mkdir -p "${OUTPUTDIR}"

# create .vtk meshes
mris_convert "${SCDIR}/surf/lh.sphere"   "${OUTPUTDIR}/lh_sphere.vtk"
mris_convert "${SCDIR}/surf/rh.sphere"   "${OUTPUTDIR}/rh_sphere.vtk"
mris_convert "${SCDIR}/surf/lh.white"    "${OUTPUTDIR}/lh_white.vtk"
mris_convert "${SCDIR}/surf/rh.white"    "${OUTPUTDIR}/rh_white.vtk"
mris_convert "${SCDIR}/surf/lh.inflated" "${OUTPUTDIR}/lh_inflated.vtk"
mris_convert "${SCDIR}/surf/rh.inflated" "${OUTPUTDIR}/rh_inflated.vtk"

# flip from RAS to LPS (required by SET)
# scilpy 2.x: scil_flip_surface.py → scil_surface_flip
scil_surface_flip "${OUTPUTDIR}/lh_sphere.vtk"   "${OUTPUTDIR}/lh_sphere_lps.vtk"   x y -f
scil_surface_flip "${OUTPUTDIR}/rh_sphere.vtk"   "${OUTPUTDIR}/rh_sphere_lps.vtk"   x y -f
scil_surface_flip "${OUTPUTDIR}/lh_white.vtk"    "${OUTPUTDIR}/lh_white_lps.vtk"    x y -f
scil_surface_flip "${OUTPUTDIR}/rh_white.vtk"    "${OUTPUTDIR}/rh_white_lps.vtk"    x y -f
scil_surface_flip "${OUTPUTDIR}/lh_inflated.vtk" "${OUTPUTDIR}/lh_inflated_lps.vtk" x y -f
scil_surface_flip "${OUTPUTDIR}/rh_inflated.vtk" "${OUTPUTDIR}/rh_inflated_lps.vtk" x y -f

mris_convert "${SCDIR}/surf/lh.sphere.reg" "${OUTPUTDIR}/lh_sphere_reg.vtk"
mris_convert "${SCDIR}/surf/rh.sphere.reg" "${OUTPUTDIR}/rh_sphere_reg.vtk"

scil_surface_flip "${OUTPUTDIR}/lh_sphere_reg.vtk" "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" x y -f
scil_surface_flip "${OUTPUTDIR}/rh_sphere_reg.vtk" "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" x y -f

# normalise spherical meshes to have radius 1
python3 "${SBCI_PY3_SCRIPTS}/normalise_vtk.py" \
        --surface "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" \
        --output  "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" -f

python3 "${SBCI_PY3_SCRIPTS}/normalise_vtk.py" \
        --surface "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" \
        --output  "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" -f

# extract subject coordinates
python3 "${SBCI_PY3_SCRIPTS}/get_coords.py" \
        --lh_surface "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" \
        --rh_surface "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" \
        --output     "${OUTPUTDIR}/subject_coords.npz" -f

echo "Finished processing SBCI surfaces: $(date)"
