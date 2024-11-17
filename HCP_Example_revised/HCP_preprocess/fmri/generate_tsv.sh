#!/bin/bash

# Define the base directory containing all subjects
BASE_DIR="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/HCP_Development"

# Use the provided subject list as arguments if available; otherwise, detect all subjects in the directory
if [ "$#" -gt 0 ]; then
    SUBJECTS=("$@")
else
    SUBJECTS=($(ls -d $BASE_DIR/sub-*/))
fi

# Loop through each subject for processing
for SUBJECT_PATH in "${SUBJECTS[@]}"; do
    # Extract the subject ID from the folder path
    SUBJECT=$(basename "$SUBJECT_PATH" | sed 's:/*$::')
    echo "Processing $SUBJECT..."

    # Define the input and output file paths
    INPUT_FILE="$BASE_DIR/$SUBJECT/ses-V1_MR/func/${SUBJECT}_ses-V1_MR_task-rest_bold.nii.gz"
    OUTPUT_PREFIX="$BASE_DIR/$SUBJECT/ses-V1_MR/func/${SUBJECT}_ses-V1_MR_run-001_task-rest_bold"

    # Check if the input file exists
    if [ ! -f "$INPUT_FILE" ]; then
        echo "Input file not found for $SUBJECT. Skipping."
        continue
    fi

    # Run mcflirt to generate motion-corrected output files without creating new directories
    mcflirt -in "$INPUT_FILE" -out "$OUTPUT_PREFIX" -plots

    # Define the motion parameter file path
    MOTION_PAR_FILE="${OUTPUT_PREFIX}.par"
    MOTION_TSV_FILE="$BASE_DIR/$SUBJECT/ses-V1_MR/func/${SUBJECT}_ses-V1_MR_run-001_task-rest_motion.tsv"

    # Check if the motion parameter file exists
    if [ -f "$MOTION_PAR_FILE" ]; then
        # Use awk to generate a TSV file with headers
        awk 'BEGIN{print "t_indx\trot_z\trot_x\trot_y\ttrans_z\ttrans_x\ttrans_y"} {print NR-1 "\t" $1 "\t" $2 "\t" $3 "\t" $4 "\t" $5 "\t" $6}' "$MOTION_PAR_FILE" > "$MOTION_TSV_FILE"
        echo "Generated $MOTION_TSV_FILE"
    else
        echo "Motion parameter file not found for $SUBJECT. Skipping."
    fi

    # **Optional: Add file deletion code here**
    # Delete the .par file
    if [ -f "$MOTION_PAR_FILE" ]; then
        rm "$MOTION_PAR_FILE"
        echo "Deleted $MOTION_PAR_FILE"
    fi

    # Delete the original input .nii.gz file
    if [ -f "$INPUT_FILE" ]; then
        rm "$INPUT_FILE"
        echo "Deleted $INPUT_FILE"
    fi

    echo "Finished processing $SUBJECT."
done
