#!/bin/bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 SUBJECT_LIST SUBJECTS_DIR WRAPPER_DIR" >&2
    exit 2
fi

IN=$1
OUT=$2
SCRIPTS=$3

# CHANGE LOCATION TO YOUR SOURCE FILE
ENV_FILE="${SBCI_ENV_FILE:-${HOME}/.bashrc_sbci_py3}"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: Environment file not found: ${ENV_FILE}" >&2
    echo "Set SBCI_ENV_FILE to the environment setup file for this system." >&2
    exit 1
fi
echo "Sourcing ${ENV_FILE}"
source "${ENV_FILE}"

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
export SBCI_CONFIG="${SBCI_CONFIG:-${REPO_ROOT}/ADNI_example/sbci_config}"
export SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

# CHANGE FOR SPECIFIC SBATCH OPTIONS
OPTIONS=""

echo "Sourcing SBCI config file"
source "${SBCI_CONFIG}"

echo $(which python3)

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
mapfile -t subjects < "${IN}"

# make sure there are subjects
if [[ ${#subjects[@]} -eq 0 ]]; then
    echo "no subjects found in ${IN}"
    exit 1
fi

echo "Processing ${#subjects[@]} subject(s)"

echo "Beginning processing of SBCI grid: $(date)"
mkdir -p ${OUTPUT_PATH}

STEP1=$(sb ${OPTIONS} --time=4:00:00 --mem=4g --job-name=$JID.step1 \
    --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
    --output=${OUTPUT_PATH}/sbci_step1_process_grid.log ${SCRIPTS}/sbci_step1_process_grid_py3.sh)

sleep 0.01

ROOT=$(pwd)

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))

    if [ -d "${OUT}/${subjects[$idx]}" ]; then
        cd ${OUT}/${subjects[$idx]}

        echo "Placing subject ${subjects[$idx]} in queue"
        STEP2=$(sb ${OPTIONS} --time=20:00:00 --mem=20g --job-name=$JID.step2.${subjects[$idx]} \
            --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
            --output=sbci_step2_prepare_set.log \
            --dependency=afterok:${STEP1} ${SCRIPTS}/sbci_step2_prepare_set_py3.sh)

        STEP3=()
        for ((RUN = 1; RUN <= N_RUNS; RUN++)); do
            STEP3+=($(sb ${OPTIONS} --time=40:00:00 --mem=20g --job-name=$JID.step3-4.${subjects[$idx]} \
                --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
                --output=sbci_step3_set_${RUN}.log \
                --dependency=afterok:${STEP2} ${SCRIPTS}/sbci_step3_run_set_py3.sh $RUN))

        done

        STEP4=$(sb ${OPTIONS} --time=4:00:00 --mem=4g --job-name=$JID.step3-4.${subjects[$idx]} \
            --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
            --output=sbci_step4_process_surfaces.log \
            --dependency=singleton ${SCRIPTS}/sbci_step4_process_surfaces_py3.sh)

        STEP5=$(sb ${OPTIONS} --time=20:00:00 --mem=20g --job-name=$JID.step5.${subjects[$idx]} \
            --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
            --output=sbci_step5_structural.log \
            --dependency=afterok:${STEP4} ${SCRIPTS}/sbci_step5_structural_py3.sh)

        STEP6=$(sb ${OPTIONS} --time=10:00:00 --mem=20g --job-name=$JID.step6.${subjects[$idx]} \
            --export=ALL,SBCI_CONFIG,SBCI_PY3_SCRIPTS \
            --output=sbci_step6_functional.log \
            --dependency=afterok:${STEP1} ${SCRIPTS}/sbci_step6_functional_py3.sh)
    else
        echo "ERROR: Subject not found: ${subjects[$idx]}"
    fi

    cd ${ROOT}
done
