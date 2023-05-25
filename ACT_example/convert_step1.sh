#!/bin/bash
#SBATCH -t 0-1:00:00 
#SBATCH --mem-per-cpu=10gb

dicom_dir_path=${1}
screen_id=${2}
session=${3}
CONFIG_PATH=${4}
OUTPUT_BIDS_PATH=${5}

source sbci_config
. ${FSLDIR}/etc/fslconf/fsl.sh

dcm2bids -d $dicom_dir_path -p ${screen_id} -s $session -c $CONFIG_PATH -o $OUTPUT_BIDS_PATH

# not necessary for this example
# pydeface ${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/anat/sub-${screen_id}_ses-${session}_T1w.nii.gz

RAW_DWI=${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/dwi/sub-${screen_id}_ses-${session}_dwi.nii.gz
REV_PHASE=${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/fmap/sub-${screen_id}_ses-${session}_dir-PA_dwi.nii.gz
AP_BVEC=${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/dwi/sub-${screen_id}_ses-${session}_dwi.bvec
AP_BVAL=${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/dwi/sub-${screen_id}_ses-${session}_dwi.bval
PA_BVEC=0
PA_BVAL=0
ANAT=${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}/anat/sub-${screen_id}_ses-${session}_T1w.nii.gz
sbatch dti_rpe_minimal_process.sh ${RAW_DWI} ${REV_PHASE} ${AP_BVEC} ${AP_BVAL} ${PA_BVEC} ${PA_BVAL} ${ANAT} ${OUTPUT_BIDS_PATH}/sub-${screen_id}/ses-${session}