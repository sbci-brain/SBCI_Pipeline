#!/bin/bash

IN=${1}
OUT=${2}
SCRIPTS=${3}

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /nas/longleaf/home/yifzhang/.bashrc_sbci

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/nas/longleaf/home/yifzhang/zhengwu/SBCI_Pipeline/HCP_example_finial/sbci_config

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS=""

echo "Sourcing SBCI config file"
source $SBCI_CONFIG

echo $(which python)

# helper function to return job id
function sb() {
   result="$(sbatch "$@")"
   
   if [[ "$result" =~ Submitted\ batch\ job\ ([0-9]+) ]]; then
     echo "${BASH_REMATCH[1]}"
   fi 
}

# create a unique job name prefix
JID=$(uuidgen | tr '-' ' ' | awk {'print $1}')

# get all subject names
mapfile -t subjects < ${IN}

# make sure there are subjects
if [[ ${#subjects[@]} -eq 0 ]]; then
    echo "no subjects found in ${IN}"
    exit 1
fi

echo "Processing ${#subjects[@]} subject(s): ${JID}"

ROOT=$(pwd)

for i in $(seq 1 ${#subjects[@]}); do
    if [ -d "${OUT}/${subjects[$idx]}" ]; then
        idx=$((i - 1))

        cd ${OUT}/${subjects[$idx]}

        echo "Placing subject ${subjects[$idx]} in queue"
        STEP1=$(sb $OPTIONS --time=48:00:00 --mem=24g --job-name=$JID.step1 \
            --export=ALL,SBCI_CONFIG \
            --output=psc_step1_tractography.log ${SCRIPTS}/psc_step1_tractography.sh)
    else
        echo "ERROR: Subject not found: ${subjects[$idx]}" 
    fi

    cd ${ROOT}
done

# /nas/longleaf/home/yifzhang/zhengwu/SBCI_Pipeline/HCP_example_finial/process_psc.sh /overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/test_data/subject_list /overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/test_data /nas/longleaf/home/yifzhang/zhengwu/SBCI_Pipeline/HCP_example_finial