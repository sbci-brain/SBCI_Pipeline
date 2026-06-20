#!/bin/bash
# Python 3 / scilpy 2.x adaptation of ADNI_example/sbci_step3_run_set.sh
#
# Faithful port of the canonical ADNI step3 script.
# Reference: https://github.com/sbci-brain/SBCI_Pipeline/blob/master/ADNI_example/sbci_step3_run_set.sh
#
# Command mappings (Python 2 → Python 3):
#   scil_surface_seed_map.py       → python3 $SBCI_PY3/scil_surface_seed_map.py
#   scil_surface_seeds_from_map.py → python3 $SBCI_PY3/scil_surface_seeds_from_map.py
#   scil_surface_pft_dipy.py       → python3 $SBCI_PY3/scil_surface_pft_py3.py
#                                    (same positional-arg order; surface .npz seeds preserved)
#   scil_convert_tractogram.py     → scil_tractogram_convert  (scilpy 2.x rename)
#                                    + --reference (required for .trk source)
#                                    + --legacy_vtk (VTK format compatible with vtkPolyDataReader)
#   python trim_cortical_fibers.py → python3 $SBCI_PY3/trim_cortical_fibers.py
#                                    (note: py3 script uses --streamlines plural)
#   scil_surface_combine_flow.py   → python3 $SBCI_PY3/scil_surface_combine_flow.py
#   scil_surface_filtering.py      → python3 $SBCI_PY3/scil_surface_filtering.py
#
# Usage: called once per RUN value, RUN passed as $1 (same as original).
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   source ~/.bashrc_sbci_py3
#   cd /path/to/sub-XXXXX
#   for r in $(seq 1 $N_RUNS); do
#       bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/sbci_step3_run_set_py3.sh $r
#   done

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

if [ -z "${SCRIPT_PATH+x}" ]; then
    SCRIPT_PATH="${SBCI_PATH}/scripts"
fi

# RUN is the first positional argument, matching the original script
RUN=${1}

echo "Begin processing SET (Python 3): $(date)"
echo "  RUN=${RUN}  STEPS=${STEPS}  N_SEED=${N_SEED}  RNG=${RNG}"
echo "  SBCI_PY3_SCRIPTS: ${SBCI_PY3_SCRIPTS}"

cd dwi_pipeline

# ------------------------------------------------------------------ #
#  1. Generate per-run surface seeding map                            #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seed_map.py" \
    set/out_surf/flow_${STEPS}_1.vtk \
    set/out_surf/seeding_map_rand_loop_${RUN}.npy \
    --triangle_weight set/out_surf/seeding_map_0.npy -f

# ------------------------------------------------------------------ #
#  2. Generate surface seeds (.npz)                                   #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seeds_from_map.py" \
    set/out_surf/flow_${STEPS}_1.vtk \
    set/out_surf/seeding_map_rand_loop_${RUN}.npy \
    ${N_SEED}000 \
    set/out_surf/seeds_random_loop${RUN}.npz \
    --random_number_generator ${RUN} -f

mkdir -p set/streamline

# ------------------------------------------------------------------ #
#  3. PFT tractography (surface-seeded)                               #
#                                                                     #
#  scil_surface_pft_py3.py is the Python 3 port of                   #
#  scil_surface_pft_dipy.py.  Same positional-argument order:        #
#    in_sh  in_map_include  in_map_exclude  in_surface  seeds.npz    #
#  Seeds are in LPS mm → converted to FODF voxel indices internally. #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_pft_py3.py" \
    diffusion/fodf/fodf.nii.gz \
    structure/set_map_include.nii.gz \
    structure/set_map_exclude.nii.gz \
    set/out_surf/flow_${STEPS}_1.vtk \
    set/out_surf/seeds_random_loop${RUN}.npz \
    set/streamline/set_random_loop${RUN}.trk \
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

# ------------------------------------------------------------------ #
#  4. Convert tractogram .trk → .fib (VTK polydata)                  #
#     --reference : required when source is .trk                      #
#     --legacy_vtk: writes old-style VTK readable by vtkPolyDataReader#
# ------------------------------------------------------------------ #
scil_tractogram_convert \
    set/streamline/set_random_loop${RUN}.trk \
    set/streamline/set_random_loop${RUN}.fib \
    --reference diffusion/fodf/fodf.nii.gz \
    --legacy_vtk \
    -f

# ------------------------------------------------------------------ #
#  5. Trim cortical fibers                                            #
#     (original used --streamline singular; our py3 script uses      #
#     --streamlines plural — behaviour is identical)                  #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/trim_cortical_fibers.py" \
    --surfaces     set/out_surf/flow_${STEPS}_1.vtk \
    --surface_map  set/preprocess/surfaces_type.npy \
    --surface_mask set/out_surf/intersections_mask.npy \
    --aparc        set/preprocess/aparc.a2009s+aseg.nii.gz \
    --rois         ${ROIS[*]} \
    --streamlines  set/streamline/set_random_loop${RUN}.fib \
    --out_tracts   set/streamline/set_random_loop${RUN}_cut.fib \
    --output       set/streamline/intersections_random_loop${RUN}.npz \
    -f

# ------------------------------------------------------------------ #
#  6. Combine surface flow with trimmed streamlines                   #
#     Output: _combined.fib  (matches ADNI canonical naming)         #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_combine_flow.py" \
    set/out_surf/flow_${STEPS}_1.vtk \
    set/out_surf/flow_${STEPS}_1.hdf5 \
    set/streamline/intersections_random_loop${RUN}.npz \
    set/streamline/set_random_loop${RUN}_cut.fib \
    set/streamline/set_random_loop${RUN}_combined.fib \
    --compression_rate 0.2

# ------------------------------------------------------------------ #
#  7. Filter streamlines by length                                    #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_filtering.py" \
    set/out_surf/flow_${STEPS}_1.vtk \
    set/streamline/intersections_random_loop${RUN}.npz \
    set/streamline/set_random_loop${RUN}_combined.fib \
    set/streamline/set_random_loop${RUN}_filtered.fib \
    --out_intersections \
        set/streamline/intersections_random_loop${RUN}_filtered.npz \
    --min_length 10 \
    --max_length 250 \
    -f

cd ..

echo "Finished processing SET (Python 3): $(date)"
