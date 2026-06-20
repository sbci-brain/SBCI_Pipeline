#!/bin/bash
# Python 3 / scilpy 2.x adaptation of ADNI_example/sbci_step2_prepare_set.sh
#
# Per-subject: prepares surfaces, ROIs, flow, and PFT maps for SET tractography.
#
# Reference: https://github.com/sbci-brain/SBCI_Pipeline/blob/master/ADNI_example/sbci_step2_prepare_set.sh
#
# Command mappings (Python 2 → Python 3):
#   python ${SCRIPT_PATH}/X.py                → python3 ${SBCI_PY3_SCRIPTS}/X.py
#   scil_surface.py                           → python3 ${SBCI_PY3_SCRIPTS}/scil_surface.py
#   scil_concatenate_surfaces.py              → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_concatenate.py
#   scil_concatenate_surfaces_map.py          → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py
#   scil_surface_flow.py                      → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_flow.py
#   scil_surface_seed_map.py                  → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_seed_map.py
#
# Confirmed scilpy 2.x renames (verified on Longleaf):
#   scil_flip_surface.py                              →  scil_surface_flip
#   scil_smooth_surface.py                            →  scil_surface_smooth
#   scil_compute_maps_for_particle_filter_tracking.py →  scil_tracking_pft_maps
#   scil_surface_from_volume.py                       →  NOT in scilpy 2.x → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_from_volume.py
#   scil_surface_map_from_volume.py                   →  NOT in scilpy 2.x → python3 ${SBCI_PY3_SCRIPTS}/scil_surface_map_from_volume.py
#
# Usage:
#   export SBCI_CONFIG=/path/to/sbci_config
#   export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
#   source ~/.bashrc_sbci_py3 && conda activate sbci_py3
#   cd /path/to/subject_dir
#   bash /path/to/SBCI_Pipeline/ADNI_example/py3/wrappers/sbci_step2_prepare_set_py3.sh

set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

echo "Begin processing SET preparation: $(date)"

echo "${ROIS[@]}"

cd dwi_pipeline

##########################
## prepare data for SET ##
##########################

mkdir -p set/preprocess

cp structure/t1_freesurfer/label/lh*a2009s.annot set/preprocess/
cp structure/t1_freesurfer/label/rh*a2009s.annot set/preprocess/

cp structure/t1_freesurfer/surf/lh.pial  set/preprocess/
cp structure/t1_freesurfer/surf/rh.pial  set/preprocess/
cp structure/t1_freesurfer/surf/lh.white set/preprocess/
cp structure/t1_freesurfer/surf/rh.white set/preprocess/
cp structure/t1_freesurfer/mri/wmparc.mgz set/preprocess/

cp structure/aparc.a2009s+aseg.nii.gz set/preprocess/

# convert volume
mri_convert set/preprocess/wmparc.mgz set/preprocess/labels.nii.gz

mrconvert set/preprocess/labels.nii.gz -stride 1,2,3 set/preprocess/labels.nii.gz -force

# surface preprocessing
mris_convert --to-scanner set/preprocess/lh.pial  set/preprocess/lh.pial.vtk
mris_convert --to-scanner set/preprocess/rh.pial  set/preprocess/rh.pial.vtk
mris_convert --to-scanner set/preprocess/lh.white set/preprocess/lh.white.vtk
mris_convert --to-scanner set/preprocess/rh.white set/preprocess/rh.white.vtk

# flip from RAS to LPS (required by SET)
# scilpy 2.x: scil_flip_surface.py → scil_surface_flip
scil_surface_flip set/preprocess/lh.pial.vtk  set/preprocess/lh_pial_lps.vtk  x y -f
scil_surface_flip set/preprocess/rh.pial.vtk  set/preprocess/rh_pial_lps.vtk  x y -f
scil_surface_flip set/preprocess/lh.white.vtk set/preprocess/lh_white_lps.vtk x y -f
scil_surface_flip set/preprocess/rh.white.vtk set/preprocess/rh_white_lps.vtk x y -f

# surface labels from annotation files
python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/lh_white_lps.vtk \
        --annot set/preprocess/lh.aparc.a2009s.annot \
        --save_vts_label set/preprocess/lh_labels.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/rh_white_lps.vtk \
        --annot set/preprocess/rh.aparc.a2009s.annot \
        --save_vts_label set/preprocess/rh_labels.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/lh_white_lps.vtk \
        --vts_val 0.0 --save_vts_mask set/preprocess/lh_zero_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/rh_white_lps.vtk \
        --vts_val 0.0 --save_vts_mask set/preprocess/rh_zero_mask.npy -f

# Generate ROIs in VTK
ROI_SURFACES=""
ROI_FLOW_MASKS=""
ROI_INTERSECTIONS_MASKS=""
ROI_SEED_MASKS=""

for ROI in "${ROIS[@]}"; do
    printf -v NAME "%05g" "${ROI}"

    # scil_surface_from_volume is NOT in scilpy 2.x — using SBCI custom Python 3 port
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface_from_volume.py" set/preprocess/labels.nii.gz \
            set/preprocess/roi_${NAME}.vtk \
            --index "${ROI}" \
            --closing 2 \
            --opening 2 \
            --smooth 2 \
            --vox2vtk --fill --max_label -f

    # put 0 everywhere; don't apply flow to this ROI
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/roi_${NAME}.vtk \
            --vts_val 0.0 \
            --save_vts_mask set/preprocess/${NAME}_flow_mask.npy -f

    # seeding mask: no seeding on cerebellum or brainstem
    if [[ ${ROI} == 8 ]] || [[ ${ROI} == 47 ]] || [[ ${ROI} == 16 ]]; then
        python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/roi_${NAME}.vtk \
                --vts_val 0.0 \
                --save_vts_mask set/preprocess/${NAME}_seed_mask.npy -f
    else
        # scil_surface_map_from_volume is NOT in scilpy 2.x — using SBCI custom Python 3 port
        python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_from_volume.py" set/preprocess/roi_${NAME}.vtk \
                diffusion/dti/fa.nii.gz \
                set/preprocess/${NAME}_seed_mask.npy \
                --binarize --binarize_value 0.15 -f
    fi

    # streamline can stop at any point within this ROI
    python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/roi_${NAME}.vtk \
            --vts_val 1.0 \
            --save_vts_mask set/preprocess/${NAME}_intersections_mask.npy -f

    ROI_SURFACES="${ROI_SURFACES} set/preprocess/roi_${NAME}.vtk"
    ROI_FLOW_MASKS="${ROI_FLOW_MASKS} set/preprocess/${NAME}_flow_mask.npy"
    ROI_INTERSECTIONS_MASKS="${ROI_INTERSECTIONS_MASKS} set/preprocess/${NAME}_intersections_mask.npy"
    ROI_SEED_MASKS="${ROI_SEED_MASKS} set/preprocess/${NAME}_seed_mask.npy"
done

# flow masks for cortical surfaces (exclude certain labels)
python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/lh_white_lps.vtk \
        --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
        --save_vts_mask set/preprocess/lh_flow_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/rh_white_lps.vtk \
        --annot set/preprocess/rh.aparc.a2009s.annot \
        -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
        --save_vts_mask set/preprocess/rh_flow_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/lh_white_lps.vtk \
        --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/lh_seed_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/rh_white_lps.vtk \
        --annot set/preprocess/rh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/rh_seed_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/lh_white_lps.vtk \
        --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/lh_intersections_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface.py" set/preprocess/rh_white_lps.vtk \
        --annot set/preprocess/rh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/rh_intersections_mask.npy -f

mkdir -p set/out_surf

# concatenate surface
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_concatenate.py" \
        set/preprocess/lh_white_lps.vtk \
        set/preprocess/rh_white_lps.vtk \
        --outer_surfaces \
            set/preprocess/lh_pial_lps.vtk \
            set/preprocess/rh_pial_lps.vtk \
        --inner_surfaces ${ROI_SURFACES} \
        --out_surface_id set/preprocess/surfaces_id.npy \
        --out_surface_type_map set/preprocess/surfaces_type.npy \
        --out_concatenated_surface set/out_surf/surfaces.vtk -f

# concatenate masks
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
        set/preprocess/lh_flow_mask.npy \
        set/preprocess/rh_flow_mask.npy \
        --outer_surfaces_map \
            set/preprocess/lh_zero_mask.npy \
            set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_FLOW_MASKS} \
        --out_map set/out_surf/flow_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
        set/preprocess/lh_seed_mask.npy \
        set/preprocess/rh_seed_mask.npy \
        --outer_surfaces_map \
            set/preprocess/lh_zero_mask.npy \
            set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_SEED_MASKS} \
        --out_map set/out_surf/seed_mask.npy -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
        set/preprocess/lh_intersections_mask.npy \
        set/preprocess/rh_intersections_mask.npy \
        --outer_surfaces_map \
            set/preprocess/lh_intersections_mask.npy \
            set/preprocess/rh_intersections_mask.npy \
        --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
        --out_map set/out_surf/intersections_mask.npy -f

# concatenate label for connectivity
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_map_concatenate.py" \
        set/preprocess/lh_labels.npy \
        set/preprocess/rh_labels.npy \
        --outer_surfaces_map \
            set/preprocess/lh_zero_mask.npy \
            set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
        --out_map set/out_surf/unique_id.npy \
        --unique_id \
        --out_id_map set/out_surf/unique_id.txt \
        --indices_to_remove -1 0 -f

# Surface_Flow
# scilpy 2.x: scil_smooth_surface.py → scil_surface_smooth
scil_surface_smooth set/out_surf/surfaces.vtk set/out_surf/smoothed.vtk \
        --vts_mask set/out_surf/flow_mask.npy \
        --nb_steps 2 \
        --step_size 2.0 -f

python3 "${SBCI_PY3_SCRIPTS}/scil_surface_flow.py" \
        set/out_surf/smoothed.vtk set/out_surf/flow_${STEPS}_1.vtk \
        --vts_mask set/out_surf/flow_mask.npy \
        --nb_step "${STEPS}" \
        --step_size 1.0 \
        --gaussian_threshold 0.2 \
        --angle_threshold 2 \
        --out_flow set/out_surf/flow_${STEPS}_1.hdf5 -f

# Surface_Seeding_Map
python3 "${SBCI_PY3_SCRIPTS}/scil_surface_seed_map.py" \
        set/out_surf/surfaces.vtk \
        set/out_surf/seeding_map_0.npy \
        --vts_mask set/out_surf/seed_mask.npy \
        --triangle_area_weighting -f

cd structure

# compute pft maps
# scilpy 2.x: scil_compute_maps_for_particle_filter_tracking.py → scil_tracking_pft_maps
scil_tracking_pft_maps \
        map_wm.nii.gz \
        map_gm.nii.gz \
        map_csf.nii.gz \
        --include set_map_include.nii.gz \
        --exclude set_map_exclude.nii.gz \
        --interface set_interface.nii.gz -f

cd ..
cd ..

echo "Finished processing SET preparation: $(date)"
