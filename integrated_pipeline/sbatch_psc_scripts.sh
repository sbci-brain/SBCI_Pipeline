#!/bin/bash
#SBATCH -t 4-0:00:00 
#SBATCH -o psc_diffusion_%j.log
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
ln -f psc_diffusion_${SLURM_JOB_ID}.log ${subdir}/psc_diffusion_${1}.log
rootdir=$(pwd)

########################################

cd ${subdir}

echo "Beginning PSC processing of UKB subject ${subj}."
date

echo "Running Step 1: $(date)"
source ${scripts}/psc_step1_tractography.sh

echo "Done processing diffusion data using PSC."
date

########################################

# remove the temporary log file
rm ${rootdir}/psc_diffusion_${SLURM_JOB_ID}.log
