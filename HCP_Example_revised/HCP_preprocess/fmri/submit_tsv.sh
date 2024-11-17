#!/bin/bash

# Define the base directory containing all subjects
BASE_DIR="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/HCP_Development"

# Automatically detect all subjects in the base directory
SUBJECTS=($(ls -d $BASE_DIR/sub-*/))

# Number of subjects to process per batch
BATCH_SIZE=5

# Total number of subjects detected
TOTAL_SUBJECTS=${#SUBJECTS[@]}

# Loop through subjects in batches and submit jobs
for (( i=0; i<TOTAL_SUBJECTS; i+=BATCH_SIZE )); do
    # Select the current batch of subjects
    BATCH_SUBJECTS=("${SUBJECTS[@]:i:BATCH_SIZE}")
    echo "Submitting batch starting with subject: $(basename "${BATCH_SUBJECTS[0]}")"

    # Create a temporary job script for the batch
    JOB_SCRIPT="job_${i}.sh"

    cat <<EOT > $JOB_SCRIPT
#!/bin/bash
#SBATCH --job-name=mcflirt_job_${i}       # Job name for the SLURM scheduler
#SBATCH --output=mcflirt_job_${i}_%j.out # File to store standard output
#SBATCH --error=mcflirt_job_${i}_%j.err  # File to store error messages
#SBATCH --time=5:00:00                   # Maximum runtime for the job
#SBATCH --cpus-per-task=2                # Number of CPUs allocated
#SBATCH --mem=8G                         # Memory allocation for the job

# Load the FSL module (adjust based on your environment)
module load fsl

# Execute the processing script with the current batch of subjects
/nas/longleaf/home/yifzhang/zhengwu/HCP/HCP_rfMRI_preprocessing/generate_tsv.sh ${BATCH_SUBJECTS[@]}
EOT

    # Submit the job script to the SLURM scheduler
    sbatch $JOB_SCRIPT

    # Optional: Delete the temporary job script after submission
    rm $JOB_SCRIPT
done
