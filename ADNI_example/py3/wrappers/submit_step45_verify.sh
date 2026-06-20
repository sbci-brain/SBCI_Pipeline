#!/bin/bash
#SBATCH --job-name=sbci_step45_py3
#SBATCH --time=04:00:00
#SBATCH --mem=32g
#SBATCH --cpus-per-task=4
#SBATCH --output=%x_%j.log
#SBATCH --mail-type=END,FAIL
#
# SBCI Steps 4 + 5 Verification Run — Python 3
# Runs step 4 (surface processing) followed by step 5 (structural SC)
# and writes outputs to sbci_connectome_py3/ for side-by-side comparison.
#
# Submit from the subject root (e.g. sub-002S6066/):
#   sbatch ADNI_example/py3/wrappers/submit_step45_verify.sh

set -euo pipefail

set +euo pipefail
ENV_FILE="${SBCI_ENV_FILE:-${HOME}/.bashrc_sbci_py3}"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: Environment file not found: ${ENV_FILE}" >&2
    echo "Set SBCI_ENV_FILE to the environment setup file for this system." >&2
    exit 1
fi
source "${ENV_FILE}"
set -euo pipefail

WRAPPER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${WRAPPER_DIR}/../../.." && pwd)"
SBCI_CONFIG="${SBCI_CONFIG:-${REPO_ROOT}/ADNI_example/sbci_config}"
SBCI_PY3_SCRIPTS="${SBCI_PY3_SCRIPTS:-${REPO_ROOT}/scripts/scripts_py3}"
export SBCI_CONFIG SBCI_PY3_SCRIPTS

echo "Job ${SLURM_JOB_ID} started: $(date)"
echo "Host: $(hostname)"
echo "Dir:  $(pwd)"
echo "SBCI_CONFIG:      ${SBCI_CONFIG}"
echo "SBCI_PY3_SCRIPTS: ${SBCI_PY3_SCRIPTS}"
echo "Python:           $(python3 --version)"

# ------------------------------------------------------------------ #
#  Step 4: process surfaces                                           #
# ------------------------------------------------------------------ #
echo ""
echo "########## STEP 4 ##########"
bash "${WRAPPER_DIR}/run_step4_verify.sh"

# ------------------------------------------------------------------ #
#  Step 5: structural connectivity                                    #
# ------------------------------------------------------------------ #
echo ""
echo "########## STEP 5 ##########"
bash "${WRAPPER_DIR}/run_step5_verify.sh"

echo ""
echo "Job ${SLURM_JOB_ID} finished: $(date)"
