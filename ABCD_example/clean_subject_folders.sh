#!/bin/bash

IN=${1}
OUT=${2}
SCRIPTS=${3}

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

echo "Clearing folders for ${#subjects[@]} subject(s): ${JID}"

ROOT=$(pwd)

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))

    if [ -d "${OUT}/${subjects[$idx]}" ]; then
        cd ${OUT}/${subjects[$idx]}

        echo "Placing subject ${subjects[$idx]} in queue"
        STEP1=$(sb --time=1:00:00 --mem=2g --job-name=$JID.clean \
            --output=postproc_clean_folders.log ${SCRIPTS}/postproc_clean_folders.sh)
    else
        echo "ERROR: Subject not found: ${subjects[$idx]}" 
    fi

    cd ${ROOT}
done
