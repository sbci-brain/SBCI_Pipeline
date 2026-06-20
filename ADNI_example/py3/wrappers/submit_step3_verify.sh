#!/bin/bash
#SBATCH --job-name=sbci_step3_verify
#SBATCH --time=12:00:00
#SBATCH --mem=32g
#SBATCH --cpus-per-task=1
#SBATCH --output=%x_%j.log
#SBATCH --mail-type=END,FAIL

# ------------------------------------------------------------------ #
#  SBCI Step 3 Verification Run — Python 3                           #
#  Runs all N_RUNS tractography passes into set/streamline_py3/      #
#  Submit from the subject root (e.g. sub-002S6066/):                #
#    sbatch ADNI_example/py3/wrappers/submit_step3_verify.sh
# ------------------------------------------------------------------ #

set -euo pipefail

# activate the Python 3 scilpy environment first so SBCI_PATH is available
# ~/.bashrc_sbci_py3 sources FreeSurfer / conda / module commands that can
# return non-zero or reference unset variables — relax all strict flags for
# the duration of the source, then restore them.
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
echo ""

bash "${WRAPPER_DIR}/run_step3_verify.sh"

echo ""
echo "Job ${SLURM_JOB_ID} finished: $(date)"
