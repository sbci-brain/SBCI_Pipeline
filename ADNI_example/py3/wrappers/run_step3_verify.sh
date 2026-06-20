#!/bin/bash
# Verification wrapper for sbci_step3_run_set_py3.sh
#
# Runs all N_RUNS passes of the Python 3 step3 pipeline, writing
# streamline outputs to a SEPARATE directory:
#   set/streamline_py3/   (instead of set/streamline/)
#
# Uses the same logic as the canonical ADNI sbci_step3_run_set.sh but
# with Python 3 commands and _py3 output directories.
#
# Tractography is stochastic, so exact match with a previous Python 2 run
# is not expected unless random seeds happen to yield identical tracks.
# We verify that all expected output files are generated and non-empty.
#
# Usage (from subject root, e.g. sub-002S6066/):
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   source ~/.bashrc_sbci_py3
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/run_step3_verify.sh

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

echo "==================================================="
echo " SET tractography VERIFICATION RUN (Python 3)"
echo " Writing to: set/streamline_py3/"
echo " SBCI_PY3_SCRIPTS : ${SBCI_PY3_SCRIPTS}"
echo " Python           : $(python3 --version)"
echo " N_RUNS=${N_RUNS}  STEPS=${STEPS}  N_SEED=${N_SEED}  RNG=${RNG}"
echo " Begin: $(date)"
echo "==================================================="

cd dwi_pipeline

STREAMDIR=set/streamline_py3
mkdir -p "${STREAMDIR}"

for RUN in $(seq 1 "${N_RUNS}"); do
    echo ""
    echo "--- RUN ${RUN} / ${N_RUNS}  $(date) ---"

    # ---------------------------------------------------------------- #
    #  1. Per-run surface seeding map                                  #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seed_map.py" \
        set/out_surf/flow_${STEPS}_1.vtk \
        "${STREAMDIR}/seeding_map_rand_loop_${RUN}.npy" \
        --triangle_weight set/out_surf/seeding_map_0.npy -f

    # ---------------------------------------------------------------- #
    #  2. Surface seeds (.npz)                                         #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seeds_from_map.py" \
        set/out_surf/flow_${STEPS}_1.vtk \
        "${STREAMDIR}/seeding_map_rand_loop_${RUN}.npy" \
        ${N_SEED}000 \
        "${STREAMDIR}/seeds_random_loop${RUN}.npz" \
        --random_number_generator ${RUN} -f

    # ---------------------------------------------------------------- #
    #  3. PFT tractography (surface-seeded, same method as Python 2)  #
    #     scil_surface_pft_py3.py = Python 3 port of                  #
    #     scil_surface_pft_dipy.py with coordinate-space fix           #
    #     (LPS mm seeds → FODF voxel indices before tracking)         #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_pft_py3.py" \
        diffusion/fodf/fodf.nii.gz \
        structure/set_map_include.nii.gz \
        structure/set_map_exclude.nii.gz \
        set/out_surf/flow_${STEPS}_1.vtk \
        "${STREAMDIR}/seeds_random_loop${RUN}.npz" \
        "${STREAMDIR}/set_random_loop${RUN}.trk" \
        --algo prob \
        --step 0.2 \
        --theta 20 \
        --sfthres 0.1 \
        --max_length 250 \
        --random_seed $((RNG + RUN)) \
        --compress 0.2 \
        --particles 15 \
        --back 2 \
        --forward 1 \
        -f

    # ---------------------------------------------------------------- #
    #  4. Convert .trk → .fib (VTK polydata)                          #
    #     --reference : required for .trk input                        #
    #     --legacy_vtk: needed for vtkPolyDataReader compatibility     #
    # ---------------------------------------------------------------- #
    scil_tractogram_convert \
        "${STREAMDIR}/set_random_loop${RUN}.trk" \
        "${STREAMDIR}/set_random_loop${RUN}.fib" \
        --reference diffusion/fodf/fodf.nii.gz \
        --legacy_vtk \
        -f

    # ---------------------------------------------------------------- #
    #  5. Trim cortical fibers                                         #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/trim_cortical_fibers.py" \
        --surfaces     set/out_surf/flow_${STEPS}_1.vtk \
        --surface_map  set/preprocess/surfaces_type.npy \
        --surface_mask set/out_surf/intersections_mask.npy \
        --aparc        set/preprocess/aparc.a2009s+aseg.nii.gz \
        --rois         ${ROIS[*]} \
        --streamlines  "${STREAMDIR}/set_random_loop${RUN}.fib" \
        --out_tracts   "${STREAMDIR}/set_random_loop${RUN}_cut.fib" \
        --output       "${STREAMDIR}/intersections_random_loop${RUN}.npz" \
        -f

    # ---------------------------------------------------------------- #
    #  6. Combine surface flow                                         #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_combine_flow.py" \
        set/out_surf/flow_${STEPS}_1.vtk \
        set/out_surf/flow_${STEPS}_1.hdf5 \
        "${STREAMDIR}/intersections_random_loop${RUN}.npz" \
        "${STREAMDIR}/set_random_loop${RUN}_cut.fib" \
        "${STREAMDIR}/set_random_loop${RUN}_combined.fib" \
        --compression_rate 0.2

    # ---------------------------------------------------------------- #
    #  7. Filter by length                                             #
    # ---------------------------------------------------------------- #
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_filtering.py" \
        set/out_surf/flow_${STEPS}_1.vtk \
        "${STREAMDIR}/intersections_random_loop${RUN}.npz" \
        "${STREAMDIR}/set_random_loop${RUN}_combined.fib" \
        "${STREAMDIR}/set_random_loop${RUN}_filtered.fib" \
        --out_intersections \
            "${STREAMDIR}/intersections_random_loop${RUN}_filtered.npz" \
        --min_length 10 \
        --max_length 250 \
        -f

    echo "    RUN ${RUN} done."
done

cd ..

echo ""
echo "==================================================="
echo " Run complete: $(date)"
echo ""
echo " Outputs in: dwi_pipeline/${STREAMDIR}/"
ls -lh "dwi_pipeline/${STREAMDIR}/" 2>/dev/null || true
echo ""
echo " Sanity check (expect 4 non-empty files per RUN):"
ALL_OK=1
for RUN in $(seq 1 "${N_RUNS}"); do
    for f in \
        "dwi_pipeline/${STREAMDIR}/set_random_loop${RUN}_filtered.fib" \
        "dwi_pipeline/${STREAMDIR}/intersections_random_loop${RUN}_filtered.npz"
    do
        if [ -s "${f}" ]; then
            echo "  OK      ${f}  ($(du -h "${f}" | cut -f1))"
        else
            echo "  MISSING ${f}"
            ALL_OK=0
        fi
    done
done
if [ "${ALL_OK}" -eq 1 ]; then
    echo ""
    echo "  ALL EXPECTED OUTPUTS PRESENT"
else
    echo ""
    echo "  SOME OUTPUTS MISSING — check log above"
fi
echo "==================================================="
