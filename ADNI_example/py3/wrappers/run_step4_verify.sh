#!/bin/bash
# Verification run for sbci_step4_process_surfaces_py3.sh
#
# Runs Python 3 step 4 (surface processing) and writes outputs to a
# SEPARATE directory  dwi_pipeline/sbci_connectome_py3/  so we can
# compare side-by-side with the Python 2 outputs in sbci_connectome/.
#
# All outputs are deterministic (mris_convert + normalise_vtk + get_coords),
# so the results should be IDENTICAL to the Python 2 run.
#
# Usage (from subject root, e.g. sub-002S6066/):
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/run_step4_verify.sh

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

SCDIR=dwi_pipeline/structure/t1_freesurfer
OUTPUTDIR=dwi_pipeline/sbci_connectome_py3    # ← py3 output, separate from py2

echo "==================================================="
echo " SBCI Step 4 VERIFICATION RUN (Python 3)"
echo " Writing to: ${OUTPUTDIR}/"
echo " SBCI_PY3_SCRIPTS : ${SBCI_PY3_SCRIPTS}"
echo " Python           : $(python3 --version)"
echo " Begin: $(date)"
echo "==================================================="

mkdir -p "${OUTPUTDIR}"

# ------------------------------------------------------------------ #
#  1. Convert FreeSurfer spheres to VTK                               #
# ------------------------------------------------------------------ #
echo ""
echo "--- Converting FreeSurfer surfaces ---"

mris_convert "${SCDIR}/surf/lh.sphere.reg" "${OUTPUTDIR}/lh_sphere_reg.vtk"
mris_convert "${SCDIR}/surf/rh.sphere.reg" "${OUTPUTDIR}/rh_sphere_reg.vtk"

# ------------------------------------------------------------------ #
#  2. Flip RAS → LPS                                                  #
# ------------------------------------------------------------------ #
echo "--- Flipping RAS → LPS (scilpy 2.x: scil_surface_flip) ---"

scil_surface_flip "${OUTPUTDIR}/lh_sphere_reg.vtk" "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" x y -f
scil_surface_flip "${OUTPUTDIR}/rh_sphere_reg.vtk" "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" x y -f

# ------------------------------------------------------------------ #
#  3. Normalise to unit sphere                                        #
# ------------------------------------------------------------------ #
echo "--- Normalising to unit sphere ---"

python3 "${SBCI_PY3_SCRIPTS}/normalise_vtk.py" \
        --surface "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" \
        --output  "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" -f

python3 "${SBCI_PY3_SCRIPTS}/normalise_vtk.py" \
        --surface "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" \
        --output  "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" -f

# ------------------------------------------------------------------ #
#  4. Extract subject coordinates                                     #
# ------------------------------------------------------------------ #
echo "--- Extracting subject coordinates ---"

python3 "${SBCI_PY3_SCRIPTS}/get_coords.py" \
        --lh_surface "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" \
        --rh_surface "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" \
        --output     "${OUTPUTDIR}/subject_coords.npz" -f

# ------------------------------------------------------------------ #
#  Sanity check                                                       #
# ------------------------------------------------------------------ #
echo ""
echo "==================================================="
echo " Step 4 outputs in ${OUTPUTDIR}/ :"
ALL_OK=1
for f in \
    "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" \
    "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" \
    "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" \
    "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" \
    "${OUTPUTDIR}/subject_coords.npz"
do
    if [ -s "${f}" ]; then
        echo "  OK      ${f}  ($(du -h "${f}" | cut -f1))"
    else
        echo "  MISSING ${f}"
        ALL_OK=0
    fi
done
if [ "${ALL_OK}" -eq 1 ]; then
    echo ""
    echo "  ALL EXPECTED OUTPUTS PRESENT"
else
    echo ""
    echo "  SOME OUTPUTS MISSING — check log above"
fi
echo " Finished: $(date)"
echo "==================================================="
