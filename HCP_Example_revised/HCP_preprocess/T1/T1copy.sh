#!/bin/bash

# Set the base directories
src_base_dir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCPDevelopDTIfMRI/imagingcollection01"
dst_base_dir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/HCP_Development"

# Get the first 5 subject directories
subject_dirs=($(ls -d ${src_base_dir}/*))

# Loop over each subject directory in the list
for subject_dir in "${subject_dirs[@]}"; do
    # Extract the subject ID
    subject_id=$(basename $subject_dir)

    # Define the source file paths
    src_file_nii="${subject_dir}/unprocessed/T1w_MPR_vNav_4e_e1e2_mean/${subject_id}_T1w_MPR_vNav_4e_e1e2_mean.nii.gz"
    src_file_json="${subject_dir}/unprocessed/T1w_MPR_vNav_4e_e1e2_mean/${subject_id}_T1w_MPR_vNav_4e_e1e2_mean.json"

    # Check if the source files exist
    if [ -e "$src_file_nii" ] && [ -e "$src_file_json" ]; then
        # Define the destination directory
        dst_dir="${dst_base_dir}/${subject_id}/T1"

        # Create the destination directory if it doesn't exist
        mkdir -p $dst_dir

        # Copy the files to the destination directory
        cp $src_file_nii $dst_dir/
        cp $src_file_json $dst_dir/

        echo "Copied ${src_file_nii} and ${src_file_json} to ${dst_dir}/"
    else
        echo "One or both files ${src_file_nii} or ${src_file_json} do not exist. Skipping ${subject_id}."
    fi
done

echo " subjects processed."
