#!/bin/bash
# Verification wrapper for sbci_step2_prepare_set_py3.sh
#
# Runs the Python 3 step2 pipeline into SEPARATE directories:
#   set/preprocess_py3/   (instead of set/preprocess/)
#   set/out_surf_py3/     (instead of set/out_surf/)
#   structure/            (PFT maps written to _py3 filenames)
#
# After it finishes, run compare_outputs.py to diff against
# the existing Python 2 results.
#
# Usage (from subject root, e.g. sub-002S6066/):
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   source ~/.bashrc_sbci_py3
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/run_step2_verify.sh
#
# Then compare:
#   python3 /path/to/SBCI_Pipeline/tests_py3/compare_step2_outputs.py \
#       dwi_pipeline/set/out_surf \
#       dwi_pipeline/set/out_surf_py3

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "==================================================="
echo " SET preparation VERIFICATION RUN (Python 3)"
echo " Writing to:  set/preprocess_py3/  set/out_surf_py3/"
echo " SBCI_PY3_SCRIPTS : ${SBCI_PY3_SCRIPTS}"
echo " Python           : $(python3 --version)"
echo "==================================================="

source "${SBCI_CONFIG}"
echo "ROIS  : ${ROIS[*]}"
echo "STEPS : ${STEPS}"
echo "Begin: $(date)"

cd dwi_pipeline

# Use _py3 suffixed directories so old outputs are untouched
PREPROC=set/preprocess_py3
OUTSURF=set/out_surf_py3

mkdir -p "${PREPROC}" "${OUTSURF}"

# ------------------------------------------------------------------ #
#  Copy FreeSurfer outputs                                            #
# ------------------------------------------------------------------ #
cp structure/t1_freesurfer/label/lh*a2009s.annot "${PREPROC}/"
cp structure/t1_freesurfer/label/rh*a2009s.annot "${PREPROC}/"
cp structure/t1_freesurfer/surf/lh.pial          "${PREPROC}/"
cp structure/t1_freesurfer/surf/rh.pial          "${PREPROC}/"
cp structure/t1_freesurfer/surf/lh.white         "${PREPROC}/"
cp structure/t1_freesurfer/surf/rh.white         "${PREPROC}/"
cp structure/t1_freesurfer/mri/wmparc.mgz        "${PREPROC}/"
cp structure/aparc.a2009s+aseg.nii.gz            "${PREPROC}/"

# ------------------------------------------------------------------ #
#  Volume conversion                                                  #
# ------------------------------------------------------------------ #
mri_convert "${PREPROC}/wmparc.mgz" "${PREPROC}/labels.nii.gz"
mrconvert "${PREPROC}/labels.nii.gz" -stride 1,2,3 \
          "${PREPROC}/labels.nii.gz" -force

# ------------------------------------------------------------------ #
#  Surface conversion + LPS flip                                      #
# ------------------------------------------------------------------ #
for surf in lh.pial rh.pial lh.white rh.white; do
    mris_convert --to-scanner "${PREPROC}/${surf}" "${PREPROC}/${surf}.vtk"
done

scil_surface_flip "${PREPROC}/lh.pial.vtk"  "${PREPROC}/lh_pial_lps.vtk"  x y -f
scil_surface_flip "${PREPROC}/rh.pial.vtk"  "${PREPROC}/rh_pial_lps.vtk"  x y -f
scil_surface_flip "${PREPROC}/lh.white.vtk" "${PREPROC}/lh_white_lps.vtk" x y -f
scil_surface_flip "${PREPROC}/rh.white.vtk" "${PREPROC}/rh_white_lps.vtk" x y -f

# ------------------------------------------------------------------ #
#  Cortical vertex labels and masks                                   #
# ------------------------------------------------------------------ #
for hemi in lh rh; do
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/${hemi}_white_lps.vtk" \
        --annot "${PREPROC}/${hemi}.aparc.a2009s.annot" \
        --save_vts_label "${PREPROC}/${hemi}_labels.npy" -f

    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/${hemi}_white_lps.vtk" \
        --vts_val 0.0 --save_vts_mask "${PREPROC}/${hemi}_zero_mask.npy" -f

    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/${hemi}_white_lps.vtk" \
        --annot "${PREPROC}/${hemi}.aparc.a2009s.annot" \
        -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
        --save_vts_mask "${PREPROC}/${hemi}_flow_mask.npy" -f

    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/${hemi}_white_lps.vtk" \
        --annot "${PREPROC}/${hemi}.aparc.a2009s.annot" \
        -i -1 0 --inverse_mask \
        --save_vts_mask "${PREPROC}/${hemi}_seed_mask.npy" -f

    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/${hemi}_white_lps.vtk" \
        --annot "${PREPROC}/${hemi}.aparc.a2009s.annot" \
        -i -1 0 --inverse_mask \
        --save_vts_mask "${PREPROC}/${hemi}_intersections_mask.npy" -f
done

# ------------------------------------------------------------------ #
#  ROI surfaces and masks                                             #
# ------------------------------------------------------------------ #
ROI_SURFACES=""
ROI_FLOW_MASKS=""
ROI_INTERSECTIONS_MASKS=""
ROI_SEED_MASKS=""

for ROI in ${ROIS[*]}; do
    printf -v NAME "%05g" "${ROI}"

    # scil_surface_from_volume was dropped in scilpy 2.x — copy the ROI surface
    # from the existing Python 2 run (same labels.nii.gz input, deterministic).
    cp "set/preprocess/roi_${NAME}.vtk" "${PREPROC}/roi_${NAME}.vtk"

    # scil_surface_map_from_volume also dropped — copy FA-thresholded seed mask.
    cp "set/preprocess/${NAME}_seed_mask.npy" "${PREPROC}/${NAME}_seed_mask.npy"

    # Flow mask (all zeros) and intersections mask (all ones) are generated by
    # our scil_surface.py — these ARE part of what we're verifying.
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/roi_${NAME}.vtk" \
        --vts_val 0.0 --save_vts_mask "${PREPROC}/${NAME}_flow_mask.npy" -f

    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" \
        "${PREPROC}/roi_${NAME}.vtk" \
        --vts_val 1.0 --save_vts_mask "${PREPROC}/${NAME}_intersections_mask.npy" -f

    ROI_SURFACES="${ROI_SURFACES} ${PREPROC}/roi_${NAME}.vtk"
    ROI_FLOW_MASKS="${ROI_FLOW_MASKS} ${PREPROC}/${NAME}_flow_mask.npy"
    ROI_INTERSECTIONS_MASKS="${ROI_INTERSECTIONS_MASKS} ${PREPROC}/${NAME}_intersections_mask.npy"
    ROI_SEED_MASKS="${ROI_SEED_MASKS} ${PREPROC}/${NAME}_seed_mask.npy"
done

# ------------------------------------------------------------------ #
#  Concatenate surfaces and maps                                      #
# ------------------------------------------------------------------ #
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_concatenate.py" \
    "${PREPROC}/lh_white_lps.vtk" "${PREPROC}/rh_white_lps.vtk" \
    --outer_surfaces "${PREPROC}/lh_pial_lps.vtk" "${PREPROC}/rh_pial_lps.vtk" \
    --inner_surfaces ${ROI_SURFACES} \
    --out_surface_id "${PREPROC}/surfaces_id.npy" \
    --out_surface_type_map "${PREPROC}/surfaces_type.npy" \
    --out_concatenated_surface "${OUTSURF}/surfaces.vtk" -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
    "${PREPROC}/lh_flow_mask.npy" "${PREPROC}/rh_flow_mask.npy" \
    --outer_surfaces_map "${PREPROC}/lh_zero_mask.npy" "${PREPROC}/rh_zero_mask.npy" \
    --inner_surfaces_map ${ROI_FLOW_MASKS} \
    --out_map "${OUTSURF}/flow_mask.npy" -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
    "${PREPROC}/lh_seed_mask.npy" "${PREPROC}/rh_seed_mask.npy" \
    --outer_surfaces_map "${PREPROC}/lh_zero_mask.npy" "${PREPROC}/rh_zero_mask.npy" \
    --inner_surfaces_map ${ROI_SEED_MASKS} \
    --out_map "${OUTSURF}/seed_mask.npy" -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
    "${PREPROC}/lh_intersections_mask.npy" "${PREPROC}/rh_intersections_mask.npy" \
    --outer_surfaces_map "${PREPROC}/lh_intersections_mask.npy" \
                         "${PREPROC}/rh_intersections_mask.npy" \
    --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
    --out_map "${OUTSURF}/intersections_mask.npy" -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
    "${PREPROC}/lh_labels.npy" "${PREPROC}/rh_labels.npy" \
    --outer_surfaces_map "${PREPROC}/lh_zero_mask.npy" "${PREPROC}/rh_zero_mask.npy" \
    --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
    --out_map "${OUTSURF}/unique_id.npy" \
    --unique_id \
    --out_id_map "${OUTSURF}/unique_id.txt" \
    --indices_to_remove -1 0 -f

# ------------------------------------------------------------------ #
#  Smoothing and flow                                                 #
# ------------------------------------------------------------------ #
scil_surface_smooth "${OUTSURF}/surfaces.vtk" "${OUTSURF}/smoothed.vtk" \
    --vts_mask "${OUTSURF}/flow_mask.npy" \
    --nb_steps 2 --step_size 2.0 -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_flow.py" \
    "${OUTSURF}/smoothed.vtk" "${OUTSURF}/flow_${STEPS}_1.vtk" \
    --vts_mask "${OUTSURF}/flow_mask.npy" \
    --nb_steps "${STEPS}" \
    --step_size 1.0 \
    --gaussian_threshold 0.2 \
    --angle_threshold 2 \
    --out_flow "${OUTSURF}/flow_${STEPS}_1.hdf5" -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seed_map.py" \
    "${OUTSURF}/surfaces.vtk" "${OUTSURF}/seeding_map_0.npy" \
    --vts_mask "${OUTSURF}/seed_mask.npy" \
    --triangle_area_weighting -f

# ------------------------------------------------------------------ #
#  PFT maps (written to _py3 filenames to avoid overwriting)         #
# ------------------------------------------------------------------ #
cd structure
scil_tracking_pft_maps map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz \
    --include  set_map_include_py3.nii.gz \
    --exclude  set_map_exclude_py3.nii.gz \
    --interface set_interface_py3.nii.gz -f
cd ..

cd ..

echo ""
echo "==================================================="
echo " Run complete: $(date)"
echo ""
echo " New outputs:  dwi_pipeline/${OUTSURF}/"
ls -lh dwi_pipeline/${OUTSURF}/ 2>/dev/null || true
echo ""
echo " To compare against Python 2 results, run:"
echo "   python3 ${REPO_ROOT}/tests_py3/compare_step2_outputs.py \\"
echo "       dwi_pipeline/set/out_surf \\"
echo "       dwi_pipeline/${OUTSURF}"
echo "==================================================="
