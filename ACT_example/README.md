# SBCI Pipeline

This folder includes all the necessary scripts.

The procudure includes following steps:

1. Minimal Preprocess
2. Preprocess
3. PSC process
4. SBCI process

This README is based on bluehive at University of Rochester. The environment could be adjusted based on your system. The scripts are designed for slurm workload mangement.


## Setup Environment
Install Anaconda, and create **two** virtual environments:
### 1. The conda env for minimal process
	pip install dcm2bids pydeface dcm2niix mrtrix3 qt ants
	source dt_install.sh

### 2. SBCI env
Follow the initial README file sbci env setup
		`cd ..`
		`source install.sh`
You should switch to this SBCI env after minimal process

## Minimal Preprocess
Since sbci pipeline requires minimal processed data, we use mrtrix3 to do minimal preprocess.
Note: make sure you are in minimal process env.
Before starting minimal preprocess, you need to config paths to the data.
Edit following in *convert.py*
```
ACT_PATH=path/to/Data
CONFIG_PATH=path/to/Data/bids/config.json
OUTPUT_BIDS=output/path/BIDS_format
session=session_num
```
Then start minimal preprocess by run:
	`python convert.py`

To further understand what happening here, please look at the [BATMAN tutorial](https://osf.io/fkyht/)

## SBCI Process
**Switch to the env for sbci.**

Create a process subjects list:
`python output_subj.py`
This will create a txt file(e.g. ACT.txt) of subjects names which need to be processed.

Set configurations
Edit this paths in sbci_config:
```
PSC_PATH=/path/to/PSC_Pipeline/
SBCI_PATH=/path/to/SBCI_Pipeline/
FREESURFER_PATH=/software/freesurfer/6.0.0/
OUTPUT_PATH=/path/to/output/SBCI_AVG
RESOLUTION=ico4 # we use iso4 in ACT
```

Note: **TR** in *preproc_step5_fmri.sh* may requires to be adjusted according to the analysis result.

Edit this in preprocess.sh:
```
IN=Subjects_List.txt
DATA=/path/to/Data
SCRIPTS=/home/ywang330/SBCI_Pipeline/ACT_example
# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export  SBCI_CONFIG=path/to/ACT_example/sbci_config
```

Edit this in proc_psc.sh
```
IN=Subjects_List.txt
OUT=/path/to/output/SBCI_AVG # same to OUTPUT_PATH in sbci_config
SCRIPTS=/home/ywang330/SBCI_Pipeline/ACT_example
# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export  SBCI_CONFIG=/home/ywang330/SBCI_Pipeline/ACT_example/sbci_config
```

Edit this in proc_sbci.sh (same with proc_psc.sh)
```
IN=Subjects_List.txt
OUT=/path/to/output/SBCI_AVG # same to OUTPUT_PATH in sbci_config
SCRIPTS=/home/ywang330/SBCI_Pipeline/ACT_example
# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export  SBCI_CONFIG=/home/ywang330/SBCI_Pipeline/ACT_example/sbci_config
```

### How to Run sbci scripts
After you completed all the configuration above. You can only run following commands one by one. 

Note: You cannot start next step until all the jobs of current steps finished.

```
# Step 1:
sbatch preprocess.sh
# Step 2:
sbatch process_psc.sh
# Step 3:
sbatch process_sbci.sh
```

**Now, you are all set!**

You can check bluehive instructions at https://info.circ.rochester.edu/
Followings are related slurm commands you may need:
```
# check job status
squeue -u USERNAME
# Cancel a job
scancel JOB_ID
# Cancel all the jobs of a User
scancel -u ywang330
```

