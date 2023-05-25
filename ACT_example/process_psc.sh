#!/bin/bash
#SBATCH -t 0-1:00:00 
#SBATCH --mem-per-cpu=10gb

IN=ACT.txt
OUT=/scratch/tbaran2_lab/ACT_BIDS/SBCI_AVG
SCRIPTS=/home/ywang330/SBCI_Pipeline/ACT_example

# CHANGE LOCATION TO YOUR SOURCE FILE

module load mrtrix3/b3

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/home/ywang330/SBCI_Pipeline/ACT_example/sbci_config

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS=""

echo "Sourcing SBCI config file"
source $SBCI_CONFIG


. ${FSLDIR}/etc/fslconf/fsl.sh

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

echo "Processing ${#subjects[@]} subject(s): ${JID}"

rootdir=$(pwd)

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))
    cd ${OUT}/${subjects[$idx]}

    echo "Placing subject ${subjects[$idx]} in queue"

    STEP1=$(sb $OPTIONS --time=48:00:00 --mem=15g --job-name=$JID.step1 \
        --export=ALL,SBCI_CONFIG \
        --output=psc_step1_tractography.log\
        ${SCRIPTS}/psc_step1_tractography.sh)

    cd ${rootdir}
done
