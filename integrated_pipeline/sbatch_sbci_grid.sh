#!/bin/bash
#SBATCH -t 1:00:00 
#SBATCH -o sbci_grid_%j.log
#SBATCH --mem-per-cpu=20gb

scripts=${1}

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /nas/longleaf/home/mrcole/.bashrc-sbci

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
echo "Sourcing SBCI config file"
source /pine/scr/m/r/mrcole/UKB/sbci_config

########################################

echo "Beginning SBCI processing of common grid."
date

echo "Running Step 1: $(date)"
source ${scripts}/sbci_step1_process_grid.sh

echo "Done processing grid for SBCI"
date

########################################
