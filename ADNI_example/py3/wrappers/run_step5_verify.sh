#!/bin/bash
# Verification run for sbci_step5_structural_py3.sh
#
# Runs Python 3 step 5 (structural connectivity) using:
#   - Filtered intersections from the Python 3 step 3 run
#     (set/streamline_py3/intersections_random_loop*_filtered.npz)
#   - Surface files from the Python 2 step 2 run (set/out_surf/...)
#   - Sphere surfaces from Python 3 step 4 run (sbci_connectome_py3/)
#   - Grid/template files from OUTPUT_PATH (step 1, shared)
#
# Writes all step 5 outputs to  dwi_pipeline/sbci_connectome_py3/
# so they can be compared with  dwi_pipeline/sbci_connectome/  (Python 2).
#
# All these outputs are DETERMINISTIC, so they should be identical to
# or very close to the Python 2 run.
#
# Usage (from subject root, e.g. sub-002S6066/):
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/run_step5_verify.sh

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

OUTPUTDIR=dwi_pipeline/sbci_connectome_py3    # ← py3 output, separate from py2
SETDIR=dwi_pipeline/set

if [ -z "${CONCON_PATH+x}" ]; then
    CONCON_PATH="${SBCI_PATH}/concon"
fi

echo "==================================================="
echo " SBCI Step 5 VERIFICATION RUN (Python 3)"
echo " Writing to: ${OUTPUTDIR}/"
echo " Reading intersections from: ${SETDIR}/streamline_py3/"
echo " Using step-4 spheres from: ${OUTPUTDIR}/"
echo " SBCI_PY3_SCRIPTS : ${SBCI_PY3_SCRIPTS}"
echo " CONCON_PATH      : ${CONCON_PATH}"
echo " OUTPUT_PATH      : ${OUTPUT_PATH}"
echo " RESOLUTION       : ${RESOLUTION}"
echo " BANDWIDTH        : ${BANDWIDTH}"
echo " Python           : $(python3 --version)"
echo " Begin: $(date)"
echo "==================================================="

mkdir -p "${OUTPUTDIR}"

# ------------------------------------------------------------------ #
#  1. Concatenate Python 3 step 3 filtered intersections              #
#     (reads from set/streamline_py3/ not set/streamline/)            #
# ------------------------------------------------------------------ #
echo ""
echo "--- Concatenating filtered intersections (py3 step-3 outputs) ---"

INTERSECTIONS=""
for ((RUN = 1; RUN <= N_RUNS; RUN++)); do
    INTERSECTIONS="${INTERSECTIONS} ${SETDIR}/streamline_py3/intersections_random_loop${RUN}_filtered.npz"
done

python3 "${SBCI_PY3_SCRIPTS}/concatenate_intersections.py" \
        ${INTERSECTIONS} \
        --output_intersections "${SETDIR}/streamline_py3/set_filtered_intersections.npz" -f

# ------------------------------------------------------------------ #
#  2. Snap fibers to nearest surface vertex                           #
# ------------------------------------------------------------------ #
echo ""
echo "--- Snapping fibers ---"

python3 "${SBCI_PY3_SCRIPTS}/snap_fibers.py" \
        --surfaces      "${SETDIR}/out_surf/surfaces.vtk" \
        --surface_map   "${SETDIR}/preprocess/surfaces_id.npy" \
        --intersections "${SETDIR}/streamline_py3/set_filtered_intersections.npz" \
        --output        "${OUTPUTDIR}/snapped_fibers.npz" -f

# ------------------------------------------------------------------ #
#  3. Convert snapped intersections to concon TSV format              #
# ------------------------------------------------------------------ #
echo ""
echo "--- Converting to concon sphere format ---"

python3 "${SBCI_PY3_SCRIPTS}/concon/intersections_to_sphere.py" \
        --lh_surface    "${OUTPUTDIR}/lh_sphere_reg_lps.vtk" \
        --rh_surface    "${OUTPUTDIR}/rh_sphere_reg_lps.vtk" \
        --intersections "${OUTPUTDIR}/snapped_fibers.npz" \
        --output        "${OUTPUTDIR}/subject_xing_sphere_avg_coords.tsv" -f

# ------------------------------------------------------------------ #
#  4. Run concon c3_main kernel computation                           #
# ------------------------------------------------------------------ #
echo ""
echo "--- Running concon c3_main kernel ---"

"${CONCON_PATH}/c3_main" \
    Compute_Kernel \
    --subj subject \
    --sigma "${BANDWIDTH}" \
    --epsilon 0.001 \
    --final_thold 0.000000001 \
    --OPT_VAL_exp_num_kern_samps 6 \
    --OPT_VAL_exp_num_harm_samps 5 \
    --OPT_VAL_num_harm 33 \
    --LOAD_xing_path "${OUTPUTDIR}/" \
    --LOAD_xing_postfix "_xing_sphere_avg_coords.tsv" \
    --LOAD_kernel_path "" \
    --LOAD_kernel_postfix "" \
    --LOAD_mask_file MASK \
    --SAVE_Compute_Kernel_prefix "${OUTPUTDIR}/" \
    --SAVE_Compute_Kernel_postfix "_avg_${BANDWIDTH}_${RESOLUTION}.raw" \
    --LOAD_grid_file "${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.m" \
    --LOAD_rh_grid_file "${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.m"

# ------------------------------------------------------------------ #
#  5. Convert raw kernel → MATLAB + NPZ                              #
# ------------------------------------------------------------------ #
echo ""
echo "--- Converting raw kernel output ---"

python3 "${SBCI_PY3_SCRIPTS}/concon/convert_raw.py" \
        --input         "${OUTPUTDIR}/subject_avg_${BANDWIDTH}_${RESOLUTION}.raw" \
        --intersections "${OUTPUTDIR}/snapped_fibers.npz" \
        --mesh          "${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz" \
        --output        "${OUTPUTDIR}/smoothed_sc_avg_${BANDWIDTH}_${RESOLUTION}" -f

# ------------------------------------------------------------------ #
#  6. Subcortical SC                                                  #
# ------------------------------------------------------------------ #
echo ""
echo "--- Calculating subcortical SC ---"

python3 "${SBCI_PY3_SCRIPTS}/calculate_subcortical_sc.py" \
        --intersections "${OUTPUTDIR}/snapped_fibers.npz" \
        --grid          "${OUTPUT_PATH}/grid_coords_${RESOLUTION}.npz" \
        --coordinates   "${OUTPUTDIR}/subject_coords.npz" \
        --bandwidth     "${BANDWIDTH}" \
        --output        "${OUTPUTDIR}/sub_sc_avg_${BANDWIDTH}_${RESOLUTION}.mat" -f

# ------------------------------------------------------------------ #
#  7. Map intersections to registration sphere space                  #
# ------------------------------------------------------------------ #
echo ""
echo "--- Mapping intersections to sphere ---"

python3 "${SBCI_PY3_SCRIPTS}/intersections_to_sphere.py" \
        --lh_reg_surface  "${OUTPUTDIR}/lh_sphere_reg_norm.vtk" \
        --rh_reg_surface  "${OUTPUTDIR}/rh_sphere_reg_norm.vtk" \
        --set_surfaces    "${SETDIR}/out_surf/surfaces.vtk" \
        --set_surface_map "${SETDIR}/preprocess/surfaces_id.npy" \
        --intersections   "${SETDIR}/streamline_py3/set_filtered_intersections.npz" \
        --output          "${OUTPUTDIR}/sphere_intersections.npz" -f

# ------------------------------------------------------------------ #
#  8. Get barycentric fiber coordinates on grid mesh                  #
# ------------------------------------------------------------------ #
echo ""
echo "--- Getting barycentric fiber coordinates ---"

python3 "${SBCI_PY3_SCRIPTS}/get_fibers_barycentric.py" \
        --lh_surface    "${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.vtk" \
        --rh_surface    "${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.vtk" \
        --intersections "${OUTPUTDIR}/sphere_intersections.npz" \
        --output        "${OUTPUTDIR}/mesh_intersections_${RESOLUTION}.mat" -f

# ------------------------------------------------------------------ #
#  Sanity check                                                       #
# ------------------------------------------------------------------ #
echo ""
echo "==================================================="
echo " Step 5 outputs in ${OUTPUTDIR}/ :"
ALL_OK=1
for f in \
    "${OUTPUTDIR}/snapped_fibers.npz" \
    "${OUTPUTDIR}/subject_xing_sphere_avg_coords.tsv" \
    "${OUTPUTDIR}/smoothed_sc_avg_${BANDWIDTH}_${RESOLUTION}.mat" \
    "${OUTPUTDIR}/smoothed_sc_avg_${BANDWIDTH}_${RESOLUTION}.npz" \
    "${OUTPUTDIR}/sub_sc_avg_${BANDWIDTH}_${RESOLUTION}.mat" \
    "${OUTPUTDIR}/sphere_intersections.npz" \
    "${OUTPUTDIR}/mesh_intersections_${RESOLUTION}.mat"
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
