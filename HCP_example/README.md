# Running a sample subject from HCP on Bluehive / BHWard

## Setup sbci_config

Edit lines 9-10 in sbci_config to point to the scripts and concon folder in this repository:

    SCRIPT_PATH=/home/user/SBCI/scripts
    CONCON_PATH=/home/user/SBCI/concon
    
Edit lines 42-43 to point to the working directory:

    REFDIR=/home/user/project/subjects_dir/reference_subject/dwi_sbci_connectome/structure/fsaverage
    AVGDIR=/home/user/project/subjects_dir/SBCI_AVG
    
Where `reference_subject` is the name of the test HCP subject (in this case 103818). Do not change anything line 42 to the right of `reference_subject` and 
there is no need to change `SBCI_AVG` in line 43.

Feel free to edit any other lines (like resolution or parcellations) you want so that you can get the feel of the available settings.

## Setup .slurm files

Each of the three .slurm files will have some combination of the following lines:

    # CHANGE LOCATION TO YOUR SOURCE FILE
    echo "Sourcing .bashrc"
    source /home/user/bashrc

    # CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
    export SBCI_CONFIG=/home/user/project/sbci_config

    # CHANGE LOCATION TO FREESURFER WITH PERSONAL LICENSE
    fsdir=/software/freesurfer/6.0.0/freesurfer/

Make the appropriate changes to 

1. Point to your .bashrc file that sets up your Python environment with Scilpy installed and anything else required. A sample 
.bashrc file can be found in the root directory of this repository. 
2. Point to your modified sbci_config files
3. Point to your local installation of Freesurfer with your personal license (required for functional commands)

You may also wish to make changes to the `#SBATCH` options to configure a certain partition to run on, for example. You may also wish to change the 
line 24 in `HCP_sbci_preproc.slurm` to reflect the same changes:

    # CHANGE SBATCH OPTIONS FOR SET AND FSFAST
    options='-t 5-00:00:00 --mem-per-cpu=20gb'

## Fetch sample data

Source the `fetch_data.sh` scripts in your project directory/working directory. This will create a new directory called `raw_data` filled with sample 
unprocessed data for a single subject from HCP. You will need the [Amazon Web Services](https://docs.aws.amazon.com/cli/latest/reference/) (AWS) client 
installed on your computer, which can be done by running `conda install awscli'.

## Process the subject

The following assumes you have already installed Scilpy and SET.

### Part 1. Preprocessing

The `HCP_sbci_preproc.slurm` file will copy/format the unprocessed data into a subject directory, then perform all the fMRI and Diffusion preprocessing 
using Freesurfer and FSfast. Run it using `sbatch` and changing the input options as required (subjects_dir will be created by the script).

    sbatch HCH_sbci_preproc.slurm 103818 /path/to/subjects_dir /path/to/raw_data /path/to/pipeline_scripts

This will take some time, depending on your machine. When it is finished, you may wish to check the log files to look for any errors.

|File                 |Description                                                  |
|---------------------|-------------------------------------------------------------|
|preproc_scilpy_#.log |All results from the diffusion preprocessing for subject #   |
|preproc_fsfast_#.log |All results from the functional preprocessing for subject #  |
|preproc_set_#_#.log  |All the SET tracking results for run # and subject #         |

If you have more than one subject, you would run this .slurm script once for each one.

### Part 2. Processing the downsampled grid

The `sbci_process_grid.slurm` file will create the mapping from full freesurfer mesh resolution to a resolution of your choosing in the `sbci_config` 
file (default is a 99% reduction in the number of vertices). Several parcellations are also calculated to aid in visualisation and comparison of the
resulting atlas-free connectomes. Run it using `sbatch1 and changing the input options as required.

    sbatch sbci_process_grid.slurm /path/to/subjects_dir /path/to/pipeline_scripts

This will run relatively quickly and only needs to be run once unless you wish to change parcellations or resolution. When it is finished, 
you may wish to check the log file (`sbci_grid.log` located in the `AVGDIR` as defined in `sbci_config`) to look for any errors.

### Part 3. Processing the subject(s)

The `sbci_process_subject.slurm` file will perform SBCI on the selected subject. Run it using `sbatch` and changing the input options as required.

    sbatch sbci_process_subject.slurm 103818 /path/to/subjects_dir /path/to/pipeline_scripts

This will should be done within a few hours, depending on your machine. When it is finished, you may wish to check the log file (`sbci_#.log`) to look for
any errors. The results will be in `/path/to/subjects_dir/subject_id/dwi_sbci_connectome/SBCI` as .mat files. The sample scripts in the matlab folder of
this repository will show you one way to collect the results of multiple subjects in easy to analyse tensors.


