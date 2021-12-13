#!/bin/bash
#SBATCH -t 4-0:00:00 
#SBATCH -o preproc_diffusion_%j.log
#SBATCH --mem-per-cpu=20gb

subj=${1}
out=${2}
scripts=${3}

subdir=${out}/${subj}

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /nas/longleaf/home/mrcole/.bashrc-sbci

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
echo "Sourcing SBCI config file"
source /pine/scr/m/r/mrcole/UKB/sbci_config

# link the log file into the output folder (bash variables don't work in #SBATCH -o)
# important to keep "#SBATCH -o preproc_diffusion_%j.log" in the options of this file
ln -f preproc_diffusion_${SLURM_JOB_ID}.log ${subdir}/preproc_diffusion_${1}.log
rootdir=$(pwd)

########################################

mkdir -p ${subdir}
cd ${subdir}

echo "Beginning diffusion processing of UKB subject ${subj}."
date

echo "Running Step 1: $(date)"
source ${scripts}/preproc_step1_preparedata.sh
echo "Running Step 2: $(date)"
source ${scripts}/preproc_step2_t1_dwi_registration.sh
echo "Running Step 3: $(date)"
source ${scripts}/preproc_step3_t1_freesurfer.sh
echo "Running Step 4: $(date)"
source ${scripts}/preproc_step4_fodf_estimation.sh

echo "Done processing diffusion data."
date

########################################

# remove the temporary log file
rm ${rootdir}/preproc_diffusion_${SLURM_JOB_ID}.log
