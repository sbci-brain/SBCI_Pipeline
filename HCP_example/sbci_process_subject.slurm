#!/bin/bash
#SBATCH -t 5-0:00:00 
#SBATCH -o sbci_%j.log
#SBATCH --mem-per-cpu=20gb

subj=${1}
out=${2}
scripts=${3}

subdir=${out}/${subj}

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /home/user/bashrc

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/home/user/project/sbci_config

# link the log file into the output folder (bash variables don't work in #SBATCH -o)
# important to keep "#SBATCH -o sbci_%j.log" in the options of this file
ln -f sbci_${SLURM_JOB_ID}.log ${subdir}/sbci_${1}.log

echo "Beginning preprocessing of subject $subj"

date

cd ${subdir}
source ${scripts}/sbci_step2_process_surfaces.sh
source ${scripts}/sbci_step3_structural.sh
source ${scripts}/sbci_step4_functional.sh
source ${scripts}/sbci_step5_atlas_connectivity.sh
cd -

date

echo "Done processing of subject $subj"

# remove the temporary log file
rm sbci_${SLURM_JOB_ID}.log
