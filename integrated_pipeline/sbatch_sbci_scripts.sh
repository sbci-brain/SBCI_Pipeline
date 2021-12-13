#!/bin/bash
#SBATCH -t 4-0:00:00 
#SBATCH -o sbci_diffusion_%j.log
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
ln -f sbci_diffusion_${SLURM_JOB_ID}.log ${subdir}/sbci_diffusion_${1}.log
rootdir=$(pwd)

########################################

cd ${subdir}

echo "Beginning SBCI processing of UKB subject ${subj}."
date

echo "Running Step 2: $(date)"
source ${scripts}/sbci_step2_prepare_set.sh

echo "Starting parallel tracking jobs for SET: $(date)"

# run SET tracking in parallel N_RUN times (sourced from SBCI_CONFIG)
for ((RUN = 1; RUN <= N_RUNS; RUN++)); do
  sbatch --wait -o ${subdir}/preproc_set_${RUN}_${subj}.log \
          -t 2-0:00:00 --mem-per-cpu=20gb \
  	  ${scripts}/sbci_step3_run_set.sh $RUN &
done

# wait for SET to finish processing before moving on
wait

echo "Running Step 3: $(date)"
#source ${scripts}/sbci_step4_process_surfaces.sh
#echo "Running Step 4: $(date)"
#source ${scripts}/sbci_step5_structural.sh

echo "Done processing diffusion data using SBCI"
date

########################################

# remove the temporary log file
rm ${rootdir}/sbci_diffusion_${SLURM_JOB_ID}.log
