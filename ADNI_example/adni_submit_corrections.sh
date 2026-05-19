#!/bin/bash

# Submit one DWI eddy correction job per subject, then one fMRI correction job
# per subject that depends on the DWI job completing successfully.
#
# Usage: ./adni_submit_corrections.sh <subject_list> [scripts_dir]
#
#   subject_list  — plain text file, one BIDS subject ID per line
#                   (use subjects_anat_dwi_func.txt from adni_scan_subjects.sh)
#   scripts_dir   — path to ADNI_example scripts (default: directory of this script)
#
# Example:
#   ./adni_submit_corrections.sh subjects_anat_dwi_func.txt \
#       /nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
#
# Each subject gets two SLURM jobs:
#   1. adni_dwi_eddy_correction.sh <subj>   — topup + synb0 (CPU, general partition)
#      └─ internally submits eddy_cuda       — GPU job, submitted from within job 1
#   2. adni_fmri_correction.sh <subj>       — fugue B0 correction (CPU, afterok job 1)
#
# Logs are written to each subject's output folder:
#   <BIDS_ROOT>/<subj>/dwi/adni_dwi_eddy-<jobid>.log
#   <BIDS_ROOT>/<subj>/fmri/adni_fmri_corr-<jobid>.log

IN="${1}"
SCRIPTS="${2:-$(dirname "$(realpath "$0")")}"
OUTPUT_BASE="/overflow/zzhanglab/ADNI/ADNI-bids"

if [ -z "$IN" ]; then
    echo "Usage: $0 <subject_list> [scripts_dir]"
    exit 1
fi

if [ ! -f "$IN" ]; then
    echo "ERROR: Subject list not found: $IN"
    exit 1
fi

mapfile -t subjects < "$IN"
if [[ ${#subjects[@]} -eq 0 ]]; then
    echo "No subjects found in $IN"
    exit 1
fi

echo "Submitting correction jobs for ${#subjects[@]} subjects"
echo "Scripts: ${SCRIPTS}"
echo ""
printf "%-32s  %-12s  %-12s\n" "Subject" "DWI job" "fMRI job"
printf "%-32s  %-12s  %-12s\n" "--------------------------------" "-------" "--------"

for SUBJ in "${subjects[@]}"; do
    # Pre-create output directories so log files have a valid path
    DWI_OUT="${OUTPUT_BASE}/${SUBJ}/dwi"
    FMRI_OUT="${OUTPUT_BASE}/${SUBJ}/fmri"
    mkdir -p "$DWI_OUT" "$FMRI_OUT"

    # Submit DWI job
    DWI_JOB=$(sbatch \
        --job-name="dwi_${SUBJ}" \
        --output="${DWI_OUT}/adni_dwi_eddy-%j.log" \
        "${SCRIPTS}/adni_dwi_eddy_correction.sh" "$SUBJ" \
        | awk '{print $NF}')

    if [ -z "$DWI_JOB" ]; then
        printf "%-32s  %-12s  %-12s\n" "$SUBJ" "FAILED" "not submitted"
        continue
    fi

    # Submit fMRI job, runs only after DWI job succeeds
    FMRI_JOB=$(sbatch \
        --job-name="fmri_${SUBJ}" \
        --dependency=afterok:${DWI_JOB} \
        --output="${FMRI_OUT}/adni_fmri_corr-%j.log" \
        "${SCRIPTS}/adni_fmri_correction.sh" "$SUBJ" \
        | awk '{print $NF}')

    printf "%-32s  %-12s  %-12s\n" "$SUBJ" "$DWI_JOB" "${FMRI_JOB:-FAILED}"
done

echo ""
echo "Monitor progress:  squeue -u \$USER"
echo "Check a DWI log:   cat ${OUTPUT_BASE}/<subj>/dwi/adni_dwi_eddy-<jobid>.log"
echo "Check fMRI log:    cat ${OUTPUT_BASE}/<subj>/fmri/adni_fmri_corr-<jobid>.log"
