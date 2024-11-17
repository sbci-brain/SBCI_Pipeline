#!/bin/bash

BASE_DIR="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/missing_data/Develop_dwi"

for subject_path in ${BASE_DIR}/*_V1_MR; do

    subject=$(basename $subject_path | cut -d'_' -f1)

    bids_subject_dir="${BASE_DIR}/sub-${subject}"
    bids_session_dir="${bids_subject_dir}/ses-V1_MR"
    
    mkdir -p "$bids_session_dir/anat" "$bids_session_dir/dwi" "$bids_session_dir/func"

    if [ -d "${subject_path}/dwi" ]; then
        echo "Processing DWI for $subject..."

        dwi_file="${subject_path}/dwi/eddy_corrected_data.nii.gz"
        if [ -f "$dwi_file" ]; then
            mv "$dwi_file" "${bids_session_dir}/dwi/sub-${subject}_ses-V1_MR_dwi.nii.gz"
        fi

        bvec_file="${subject_path}/dwi/eddy_corrected_data.eddy_rotated_bvecs"
        if [ -f "$bvec_file" ];then
            mv "$bvec_file" "${bids_session_dir}/dwi/sub-${subject}_ses-V1_MR_dwi.bvec"
        fi

        bval_file="${subject_path}/dwi/merged.bval"
        if [ -f "$bval_file" ]; then
            mv "$bval_file" "${bids_session_dir}/dwi/sub-${subject}_ses-V1_MR_dwi.bval"
        fi
    else
        echo "No DWI data for $subject"
    fi

    if [ -d "${subject_path}/fmri" ]; then
        echo "Processing fMRI for $subject..."

        fmri_file="${subject_path}/fmri/${subject}_V1_MR_rfMRI_REST1_PA_AP_corr.nii.gz"
        if [ -f "$fmri_file" ];then
            mv "$fmri_file" "${bids_session_dir}/func/sub-${subject}_ses-V1_MR_task-rest_bold.nii.gz"
        fi
    else
        echo "No fMRI data for $subject"
    fi

    if [ -d "${subject_path}/T1" ]; then
        echo "Processing T1 (anat) for $subject..."

        t1_file="${subject_path}/T1/${subject}_V1_MR_T1w_MPR_vNav_4e_e1e2_mean.nii.gz"
        t1_json="${subject_path}/T1/${subject}_V1_MR_T1w_MPR_vNav_4e_e1e2_mean.json"
        
        if [ -f "$t1_file" ];then
            mv "$t1_file" "${bids_session_dir}/anat/sub-${subject}_ses-V1_MR_T1w.nii.gz"
        fi

        if [ -f "$t1_json" ];then
            mv "$t1_json" "${bids_session_dir}/anat/sub-${subject}_ses-V1_MR_T1w.json"
        fi
    else
        echo "No T1 data for $subject"
    fi

    echo "Cleaning up unnecessary files and directories for $subject..."
    rm -rf "${subject_path}/T1"
    rm -rf "${subject_path}/fmri"
    rm -rf "${subject_path}/dwi"
    rm -rf "${subject_path}"

    echo "Completed processing for $subject."
done

echo "BIDS conversion completed for all subjects."
