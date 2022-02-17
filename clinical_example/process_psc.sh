#!/bin/bash

# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /home/mcole22/.bashrc-set

module load mrtrix3/b3

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/scratch/dmi/zzhang87_lab/mcole22/SMS/sbci_config

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS="-p dmi --qos abcd"

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

# get all subject names
mapfile -t subjects < $1

# make sure there are subjects
if [[ ${#subjects[@]} -eq 0 ]]; then
    echo "no subjects found in ${1}"
    exit 1
fi

echo "Processing ${#subjects[@]} subject(s): ${JID}"

OUT=${2}
SCRIPTS=${3}

declare -a phases=("S1P1" "S3P1" "S3P2" "S6P1" "S6P2")

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))

    for j in ${phases[@]}; do

        if [ ! -d "${OUT}/${subjects[$idx]}/${j}" ]; then
            echo "Skipping missing subject/phase: ${OUT}/${subjects[$idx]}/${j}"
            continue
        fi

        cd ${OUT}/${subjects[$idx]}/${j}

        echo "Placing subject ${subjects[$idx]}, sequence ${j} in queue"
        STEP1=$(sb $OPTIONS --time=48:00:00 --mem=15g --job-name=$JID.step1 \
            --export=ALL,SBCI_CONFIG \
            --output=psc_step1_tractography.log ${SCRIPTS}/psc_step1_tractography.sh)

        cd -
    done
done

