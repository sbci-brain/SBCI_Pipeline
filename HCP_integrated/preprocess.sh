#!/bin/bash
#SBATCH -t 5-0:00:00 
#SBATCH -o preproc_scilpy_%j.log
#SBATCH --mem-per-cpu=256gb
#SBATCH --output /home/ywang330/SBCI_Pipeline/HCP_integrated/sbatch_message.txt

OUT=/scratch/tbaran2_lab/sbci_integrated/subjects_dir
SCRIPTS=/home/ywang330/SBCI_Pipeline/integrated_pipeline

subj=103818 
out=/scratch/tbaran2_lab/sbci_integrated/subjects_dir
data=/scratch/ywang330/raw_data

diffdata=${data}/Diffusion
funcdata=${data}/Functional

mkdir -p ${out}/${subj}/anat
mkdir -p ${out}/${subj}/dwi

mkdir -p ${out}/${subj}/fsfast/t1_freesurfer/bold/001
mkdir -p ${out}/${subj}/fsfast/t1_freesurfer/bold/002
mkdir -p ${out}/${subj}/fsfast/t1_freesurfer/bold/003
mkdir -p ${out}/${subj}/fsfast/t1_freesurfer/bold/004

subdir=${out}/${subj}

# copy T1w data to output folder
cp ${diffdata}/${subj}/T1w/T1w_acpc_dc_restore_1.25.nii.gz ${subdir}/anat/${subj}_T1w.nii.gz

# copy eddy-corrected DWI data to output folder
cp ${diffdata}/${subj}/T1w/Diffusion/bvals ${subdir}/dwi/${subj}_dwi.bval
cp ${diffdata}/${subj}/T1w/Diffusion/bvecs ${subdir}/dwi/${subj}_dwi.bvec
cp ${diffdata}/${subj}/T1w/Diffusion/data.nii.gz ${subdir}/dwi/${subj}_dwi.nii.gz

# copy RAW fMRI data to output folder
cp ${funcdata}/${subj}/unprocessed/3T/rfMRI_REST1_LR/${subj}_3T_rfMRI_REST1_LR.nii.gz ${subdir}/fsfast/t1_freesurfer/bold/001/f.nii.gz
cp ${funcdata}/${subj}/unprocessed/3T/rfMRI_REST1_RL/${subj}_3T_rfMRI_REST1_RL.nii.gz ${subdir}/fsfast/t1_freesurfer/bold/002/f.nii.gz
cp ${funcdata}/${subj}/unprocessed/3T/rfMRI_REST2_LR/${subj}_3T_rfMRI_REST2_LR.nii.gz ${subdir}/fsfast/t1_freesurfer/bold/003/f.nii.gz
cp ${funcdata}/${subj}/unprocessed/3T/rfMRI_REST2_RL/${subj}_3T_rfMRI_REST2_RL.nii.gz ${subdir}/fsfast/t1_freesurfer/bold/004/f.nii.gz

echo "t1_freesurfer" > ${subdir}/fsfast/t1_freesurfer/subjectname
    
ROOTDIR=$(pwd)


# CHANGE LOCATION TO YOUR SOURCE FILE
# echo "Sourcing .bashrc"
# source /home/manthon6/.bashrc_sbci

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/home/ywang330/SBCI_Pipeline/HCP_integrated/sbci_config

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS='-t 5-00:00:00 --mem-per-cpu=256gb'

echo "Sourcing SBCI config file"
source $SBCI_CONFIG

. ${FSLDIR}/etc/fslconf/fsl.sh

# helper function to return job id
function sb() {
   result="$(sbatch "$@")"

   if [[ "$result" =~ Submitted\ batch\ job\ ([0-9]+) ]]; then
     echo "${BASH_REMATCH[1]}"
   fi
}

# create a unique job name prefix
JID=$(uuidgen | tr '-' ' ' | awk {'print $1}')

subjects=103818

echo "Processing ${#subjects[@]} subject(s): ${JID}"

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))
    cd ${OUT}/${subjects[$idx]}

    echo "Placing subject ${subjects[$idx]}"

    # create dwi_pipeline folder for diffusion output
    mkdir -p dwi_pipeline

    STEP1=$(sb $OPTIONS \
        --time=00:05:00 \
        --mem=20g \
        --job-name=$JID.${subjects[$idx]}.${j}.preproc.step1 \
        --export=ALL,SBCI_CONFIG \
        --output=preproc_step1_preparedata.log ${SCRIPTS}/preproc_step1_preparedata.sh)
    echo "submit step1"

    cd dwi_pipeline

    # register T1 and diffusion data in the same space
    STEP2=$(sb $OPTIONS \
        --time=4-0:00:00 \
        -c 8 \
        --mem=256g \
        --job-name=$JID.${subjects[$idx]}.${j}.preproc.step2 \
        --export=ALL,SBCI_CONFIG \
        --output=preproc_step2_t1_dwi_registration.log \
        --dependency=afterok:${STEP1} ${SCRIPTS}/preproc_step2_t1_dwi_registration.sh)
    echo "afterok:${STEP1} ${SCRIPTS}"
    echo "submit step2"

    # preprocess T1 strucural 
    STEP3=$(sb $OPTIONS \
        --time=4-0:00:00 \
        --mem=256g \
        --job-name=$JID.${subjects[$idx]}.${j}.preproc.step3 \
        --export=ALL,SBCI_CONFIG \
        --output=preproc_step3_t1_freesurfer.log \
        --dependency=afterok:${STEP2} ${SCRIPTS}/preproc_step3_t1_freesurfer.sh)
    echo "submit step3"

    # get fiber orientation distribution function (FODF)
    STEP4=$(sb $OPTIONS \
        --time=4-0:00:00 \
        --mem=256g \
        --job-name=$JID.${subjects[$idx]}.${j}.preproc.step4 \
        --export=ALL,SBCI_CONFIG \
        --output=preproc_step4_fodf_estimation.log \
        --dependency=afterok:${STEP3} ${SCRIPTS}/preproc_step4_fodf_estimation.sh)
    echo "submit step4"

    cd ..
    STEP5=$(sb $OPTIONS --time=4-0:00:00 --mem=10g --job-name=$JID.${subjects[$idx]}.preproc.step5 \
            --export=ALL,SBCI_CONFIG \
            --output=preproc_step5_fmri.log \
            --dependency=afterok:${STEP3} ${SCRIPTS}/preproc_step5_fmri.sh)
    echo "submit step5"
    cd ${ROOTDIR} 
    # preprocess functional data
done


echo "done"