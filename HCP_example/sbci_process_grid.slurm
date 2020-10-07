#!/bin/bash
#SBATCH -t 5-0:00:00 
#SBATCH -o sbci_grid_%j.log
#SBATCH --mem-per-cpu=15gb

out=${1}
scripts=${2}

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /home/user/bashrc

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/home/user/project/sbci_config

# link the log file into the output folder (bash variables don't work in #SBATCH -o)
# important to keep "#SBATCH -o sbci_grid_%j.log" in the options of this file
ln -f sbci_grid_${SLURM_JOB_ID}.log ${out}/sbci_grid.log

echo "Beginning preprocessing template space grid" 

date 

source ${scripts}/sbci_step1_process_grid.sh

date 

echo "Done processing of template space grid" 

# remove the temporary log file
rm sbci_grid_${SLURM_JOB_ID}.log
