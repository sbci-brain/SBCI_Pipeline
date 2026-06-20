#!/bin/bash
#SBATCH --job-name=sbci_py3_test
#SBATCH --output=tests/test_scripts_%j.log
#SBATCH --time=00:15:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SBCI_ENV_FILE:-${HOME}/.bashrc_sbci_py3}"

if [[ ! -f "${ENV_FILE}" ]]; then
    echo "ERROR: Environment file not found: ${ENV_FILE}" >&2
    echo "Set SBCI_ENV_FILE to the environment setup file for this system." >&2
    exit 1
fi

source "${ENV_FILE}"
bash "${SCRIPT_DIR}/test_scripts.sh"
