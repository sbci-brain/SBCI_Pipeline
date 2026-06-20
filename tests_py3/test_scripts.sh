#!/bin/bash
# Portable viability test for the SBCI Python scripts.
# Tests scil_surface.py, scil_surface_map_concatenate.py,
# scil_surface_concatenate.py, scil_surface_seed_map.py, and
# scil_surface_seeds_from_map.py using the bundled test data.
#
# Prerequisites:
#   - FreeSurfer loaded (for mris_convert)
#   - Conda environment activated (e.g. conda activate new_sbci)
#   - Run from the repo root:  bash tests_py3/test_scripts.sh
#
# Cluster (SLURM) example:
#   sbatch tests_py3/test_scripts.sh

#SBATCH --job-name=sbci_py3_test
#SBATCH --output=tests_py3/test_scripts_%j.log
#SBATCH --time=00:15:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1

set -e

REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SCRIPTS="$REPO_ROOT/scripts/scripts_py3"
DATA="$REPO_ROOT/tests_py3/scilpy/data"
RESULTS="${SBCI_TEST_RESULTS:-$REPO_ROOT/tests_py3/results}"
N_SEED=10000   # small number for a quick test

echo "============================================"
echo " SBCI Python scripts viability test"
echo " Repo:    $REPO_ROOT"
echo " Python:  $(python3 --version)"
echo "============================================"

# --- Step 0: import check ---
echo ""
echo "[0/6] Checking Python imports..."
python3 "$REPO_ROOT/tests_py3/test_env.py"

# --- Step 1: set up results directory ---
echo ""
echo "[1/6] Setting up results directory..."
rm -rf "$RESULTS"
mkdir -p "$RESULTS"
cp "$DATA"/*.annot "$DATA"/lh.pial "$DATA"/rh.pial \
   "$DATA"/lh.white "$DATA"/rh.white "$DATA"/roi_00004.vtk \
   "$RESULTS"/

# --- Step 2: convert FreeSurfer surfaces to VTK ---
echo ""
echo "[2/6] Converting FreeSurfer surfaces to VTK (mris_convert)..."
cd "$RESULTS"
for surf in lh.pial rh.pial lh.white rh.white; do
    mris_convert --to-scanner "$surf" "${surf}.vtk"
    scil_surface_flip "${surf}.vtk" "${surf//\./_}_lps.vtk" x y -f
done

# --- Step 3: generate vertex masks from annotation ---
echo ""
echo "[3/6] Generating vertex masks (scil_surface.py)..."
for hemi in lh rh; do
    python3 "$SCRIPTS/scil_surface.py" ${hemi}_white_lps.vtk \
        --annot ${hemi}.aparc.a2009s.annot \
        --save_vts_label ${hemi}_labels.npy -f

    python3 "$SCRIPTS/scil_surface.py" ${hemi}_white_lps.vtk \
        --vts_val 0.0 --save_vts_mask ${hemi}_zero_mask.npy -f

    python3 "$SCRIPTS/scil_surface.py" ${hemi}_white_lps.vtk \
        --annot ${hemi}.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask ${hemi}_seed_mask.npy -f
done

python3 "$SCRIPTS/scil_surface.py" roi_00004.vtk \
    --vts_val 1.0 --save_vts_mask roi_00004_seed_mask.npy -f
python3 "$SCRIPTS/scil_surface.py" roi_00004.vtk \
    --vts_val 0.0 --save_vts_mask roi_00004_zero_mask.npy -f

# --- Step 4: concatenate masks ---
echo ""
echo "[4/6] Concatenating surface maps (scil_surface_map_concatenate.py)..."
python3 "$SCRIPTS/scil_surface_map_concatenate.py" \
    lh_seed_mask.npy rh_seed_mask.npy \
    --outer_surfaces_map lh_zero_mask.npy rh_zero_mask.npy \
    --inner_surfaces_map roi_00004_zero_mask.npy \
    --out_map seed_mask.npy -f

# --- Step 5: concatenate surfaces ---
echo ""
echo "[5/6] Concatenating surfaces (scil_surface_concatenate.py)..."
python3 "$SCRIPTS/scil_surface_concatenate.py" \
    lh_white_lps.vtk rh_white_lps.vtk \
    --outer_surfaces lh_pial_lps.vtk rh_pial_lps.vtk \
    --inner_surfaces roi_00004.vtk \
    --out_surface_id surfaces_id.npy \
    --out_surface_type_map surfaces_type.npy \
    --out_concatenated_surface surfaces.vtk -f

# --- Step 6: generate seed map and seeds ---
echo ""
echo "[6/6] Generating seeds (scil_surface_seed_map.py + scil_surface_seeds_from_map.py)..."
python3 "$SCRIPTS/scil_surface_seed_map.py" surfaces.vtk seeding_map.npy \
    --vts_mask seed_mask.npy \
    --triangle_area_weighting -f

python3 "$SCRIPTS/scil_surface_seeds_from_map.py" surfaces.vtk \
    seeding_map.npy $N_SEED seeds.npz \
    --random_number_generator 1 -f

echo ""
echo "============================================"
echo " All steps passed. Results in: $RESULTS"
ls -lh "$RESULTS"/*.npy "$RESULTS"/*.vtk "$RESULTS"/*.npz 2>/dev/null || true
echo "============================================"
