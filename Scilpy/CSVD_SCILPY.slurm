#!/bin/bash 
#SBATCH -t 4-00:00:00 
#SBATCH -n 1 
#SBATCH -c 1 
#SBATCH -o path/to/csvd_analysis/DTI/Scilpy/subjectname/scilpy.log 
#SBATCH --mem-per-cpu=30gb 

echo "Sourcing .bashrc"
source /home/user/.bashrc

cd path/to/csvd_analysis/DTI/Scilpy

echo "Beginning preprocessing of subject subjectname"
source /home/user/abcd_dwi_preprocessing/csvd_step6_scilpyprep.sh subjectname /scratch/user/csvd_analysis 
source /home/user/abcd_dwi_preprocessing/step1_preparedata.sh
source /home/user/abcd_dwi_preprocessing/step2_t1_dwi_registration.sh
source /home/user/abcd_dwi_preprocessing/step3_t1_freesurfer.sh
source /home/user/abcd_dwi_preprocessing/step4_fodf_estimation.sh
source /home/user/abcd_dwi_preprocessing/step5_tractography.sh

echo "Done preprocessing of subject subjectname" 
