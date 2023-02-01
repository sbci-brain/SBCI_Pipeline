#!/bin/bash
#SBATCH -t 5-0:00:00 
#SBATCH -o preproc_scilpy_%j.log
#SBATCH --mem-per-cpu=256gb
#SBATCH --output /home/ywang330/SBCI_Pipeline/HCP_integrated/sbatch_message.txt

OUT=/scratch/tbaran2_lab/sbci_integrated/subjects_dir
SCRIPTS=/home/ywang330/SBCI_Pipeline/integrated_pipeline

subj=103818

ROOTDIR=$(pwd)

# CHANGE LOCATION TO YOUR SOURCE FILE
# echo "Sourcing .bashrc"
# source /home/mcole22/.bashrc-set

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/home/ywang330/SBCI_Pipeline/HCP_integrated/sbci_config

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS='-t 5-00:00:00 --mem-per-cpu=256gb'

echo "Sourcing SBCI config file"
source $SBCI_CONFIG

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
    
    
# example slurm parameters
# #SBATCH -J job_name                # job name
# #SBATCH -a 0-39                    # job array size, starting at 0
# #SBATCH -c 8                       # cpus per task (slurm "cores")
# #SBATCH -N 1                       # number of nodes (usually 1)
# #SBATCH --ntasks=1                 # parallel ntasks per node
# #SBATCH --mem-per-cpu=24G          # memory per core (GB)
# #SBATCH -t 06:00:00                # job time ([d-]:hh:mm:ss)
    
for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))
    cd ${OUT}/${subjects[$idx]}
    
    echo "Placing subject ${subjects[$idx]} in queue"
    echo "Beginning processing of SBCI grid: $(date)"
    
    STEP1=$(sb ${OPTIONS} \
        --time=40:00:00 \
        --mem=256g \
        --job-name=$JID.step1 \
        --export=ALL,SBCI_CONFIG \
    --output=sbci_step1_process_grid.log ${SCRIPTS}/sbci_step1_process_grid.sh)
    
    STEP2=$(sb ${OPTIONS} \
        --time=40:00:00 \
        --mem=256g \
        --job-name=$JID.step2.${subjects[$idx]} \
        --export=ALL,SBCI_CONFIG \
        --output=sbci_step2_prepare_set.log \
    --dependency=afterok:${STEP1} ${SCRIPTS}/sbci_step2_prepare_set.sh)

    STEP3=()
    for ((RUN = 1; RUN <= N_RUNS; RUN++)); do 
        STEP3+=$(sb ${OPTIONS} \
            --time=40:00:00 \
            --mem=256g \
            --job-name=$JID.step3-4.${subjects[$idx]} \
            --export=ALL,SBCI_CONFIG \
            --output=sbci_step3_set_${RUN}.log \
        --dependency=afterok:${STEP2} ${SCRIPTS}/sbci_step3_run_set.sh $RUN)
    done
    
    STEP4=$(sb ${OPTIONS} \
        --time=40:00:00 \
        --mem=256g \
        --job-name=$JID.step3-4.${subjects[$idx]} \
        --export=ALL,SBCI_CONFIG \
        --output=sbci_step4_process_surfaces.log \
    --dependency=singleton ${SCRIPTS}/sbci_step4_process_surfaces.sh)
    
    STEP5=$(sb ${OPTIONS} \
        --time=40:00:00 \
        --mem=256g \
        --job-name=$JID.step5.${subjects[$idx]} \
        --export=ALL,SBCI_CONFIG \
        --output=sbci_step5_structural.log \
    --dependency=afterok:${STEP4} ${SCRIPTS}/sbci_step5_structural.sh)
    
    STEP6=$(sb ${OPTIONS} \
        --time=40:00:00 \
        --mem=256g \
        --job-name=$JID.step6.${subjects[$idx]} \
        --export=ALL,SBCI_CONFIG \
        --output=sbci_step6_functional.log \
        --dependency=afterok:${STEP1} ${SCRIPTS}/sbci_step6_functional.sh)
    
    cd ${ROOTDIR}
done