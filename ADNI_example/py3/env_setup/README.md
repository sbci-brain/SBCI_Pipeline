# Python 3 Environment Setup

This directory documents the environment required to run the Python 3 SBCI
scripts in `scripts/scripts_py3/` and the Python 3 ADNI workflow wrappers in
`ADNI_example/py3/wrappers/`.

The converted pipeline was developed and validated with Python 3.11. Python
3.11 is recommended because the supported versions of scilpy and trimeshpy
used by this repository are compatible with it.

The Conda environment used for Longleaf validation is named `sbci_py3`.

## Create the environment

From the repository root:

```bash
conda create -n sbci_py3 python=3.11 pip -y
conda activate sbci_py3

python -m pip install --upgrade pip setuptools wheel
python -m pip install -r ADNI_example/py3/requirements.txt
```

The Python requirements include:

- NumPy
- SciPy
- nibabel
- DIPY
- VTK
- trimeshpy
- scilpy 2.2 or newer
- h5py
- tqdm

The old Python 2 environment and scilpy 1.x commands are not compatible with
the Python 3 workflow. A source installation of scilpy is normally unnecessary
when `scilpy>=2.2.0` can be installed from PyPI.

## Verify Python packages

```bash
python - <<'PY'
import sys
import numpy
import scipy
import nibabel
import dipy
import vtk
import trimeshpy
import scilpy
import h5py
import tqdm

print("Python:", sys.version)
print("NumPy:", numpy.__version__)
print("SciPy:", scipy.__version__)
print("nibabel:", nibabel.__version__)
print("DIPY:", dipy.__version__)
print("VTK:", vtk.vtkVersion.GetVTKVersion())
print("scilpy:", getattr(scilpy, "__version__", "installed"))
print("Python package imports: OK")
PY

python -m pip check
```

## Record the exact tested environment

`requirements.txt` defines the supported minimum package versions, but it does
not lock every transitive dependency. To record the exact environment installed
on Longleaf, activate it and export it from the repository root:

```bash
source ~/.bashrc_sbci_py3
conda activate sbci_py3

conda env export --no-builds > ADNI_example/py3/env_setup/sbci_py3_environment.yml
conda list --explicit > ADNI_example/py3/env_setup/sbci_py3_explicit.txt
```

The YAML file is the more portable environment description. The explicit file
is useful for reproducing the environment on the same operating system and
Conda platform.

To recreate the portable environment later:

```bash
conda env create -f ADNI_example/py3/env_setup/sbci_py3_environment.yml
```

The ADNI shell scripts also call scilpy command-line programs. Confirm that
the commands used by the converted workflow are available:

```bash
command -v scil_surface_flip
command -v scil_surface_smooth
command -v scil_tracking_pft_maps
command -v scil_tractogram_convert
```

## SBCI environment variables

Before running a Python 3 step script, set the script and configuration paths:

```bash
export SBCI_PY3_SCRIPTS=/path/to/SBCI_Pipeline/scripts/scripts_py3
export SBCI_CONFIG=/path/to/SBCI_Pipeline/ADNI_example/sbci_config
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"
```

Then source the SBCI configuration:

```bash
source "${SBCI_CONFIG}"
```

The configuration must define the paths and variables expected by the original
SBCI workflow, including `SBCI_PATH`, `OUTPUT_PATH`, `RESOLUTION`, `BANDWIDTH`,
`N_RUNS`, and the ROI definitions.

## Longleaf activation

The submission script `process_sbci_py3.sh` sources
`~/.bashrc_sbci_py3`. The environment validated on UNC Longleaf uses the
following module stack and Conda initialization:

```bash
# SBCI Python 3 environment on UNC Longleaf
module purge
module load gcc/12.2.0
module load mrtrix3/3.0.3
module load freesurfer/6.0.0
module load ants/2.5.4
module load fsl/6.0.7
module load java/17.0.2
module load matlab/2021a
module load dcm2niix/1.0.20211006
module load pigz/2.8
module load git-lfs/3.6.1

module unload python
module load anaconda/2024.02
source /nas/longleaf/rhel9/apps/anaconda/2024.02/etc/profile.d/conda.sh

export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/bin:${PATH}"
export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/toolbox:${PATH}"
source /nas/longleaf/apps/freesurfer/6.0.0/freesurfer/SetUpFreeSurfer.sh

export ANTSPATH="/nas/longleaf/rhel9/apps/ants/2.5.4/bin/"
export PATH="${ANTSPATH}:${PATH}"

# Keep these only when the PSC preprocessing pipeline is also required.
export PATH="/path/to/PSC_Pipeline/scripts:${PATH}"
export PYTHONPATH="/path/to/PSC_Pipeline:${PYTHONPATH:-}"

# Point this at the Python 3 scripts in the checked-out repository.
export SBCI_PY3_ROOT="/path/to/SBCI_Pipeline"
export SBCI_PY3_SCRIPTS="${SBCI_PY3_ROOT}/scripts/scripts_py3"
export PYTHONPATH="${SBCI_PY3_SCRIPTS}:${PYTHONPATH:-}"

conda activate sbci_py3
```

The repository directory must match the actual Longleaf checkout. Older test
copies used a directory named `scripts`; the current layout uses
`scripts/scripts_py3`. Do not leave both paths configured, because that makes it easy
to run a stale script accidentally.

Test the setup before submitting jobs:

```bash
source ~/.bashrc_sbci_py3
echo "SBCI_PY3_SCRIPTS=${SBCI_PY3_SCRIPTS}"
test -d "${SBCI_PY3_SCRIPTS}" || echo "ERROR: Python 3 script directory is missing"
which python3
python3 --version
python3 -c 'import sys; print("Executable:", sys.executable)'
```

## External pipeline dependencies

The Conda environment only supplies the Python dependencies. The complete ADNI
pipeline still requires the same external software and reference data as the
original SBCI pipeline, including:

- FreeSurfer and its subject/reference data
- FSL where required by preprocessing
- the compiled concon `c3_main` executable
- Bash and SLURM for the provided Longleaf submission scripts
- the atlas, grid, and surface files referenced by `sbci_config`

These tools are not installed by `requirements.txt`; they must be loaded or
configured in the cluster environment as they were for the Python 2 pipeline.

## Running the converted ADNI workflow

After activating the environment and setting `SBCI_CONFIG`, run the Python 3
wrappers under `ADNI_example/py3/wrappers/`, for example:

```bash
bash ADNI_example/py3/wrappers/sbci_step4_process_surfaces_py3.sh
bash ADNI_example/py3/wrappers/sbci_step5_structural_py3.sh
bash ADNI_example/py3/wrappers/sbci_step6_functional_py3.sh
```

For batch submission on Longleaf, run:

```bash
bash ADNI_example/py3/process_sbci_py3.sh \
    SUBJECT_LIST SUBJECTS_DIR ADNI_example/py3/wrappers
```

## Validation status

The converted ADNI workflow was compared against the original Python 2
pipeline. Deterministic Steps 4-6 reproduce the Python 2 outputs exactly or
within floating-point precision. Step 3 tractography is stochastic and was
validated using streamline counts, endpoint distributions, connectivity
similarity, and downstream structural-connectivity comparisons.
