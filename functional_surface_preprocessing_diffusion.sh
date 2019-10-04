#!/bin/bash
#SBATCH --time=5-00:00:00 --mem=24gb
#


subj=${1}
out=${2}

SUBJECTS_DIR=${out}/T1Diff

# Prepare FSFAST analyses
cd ${out}

#Prepare FSFAST Analysis Directory
mkdir FunDiff/${subj}

# Determine BOLD run number
dcmunpack -src ./Funraw/${subj} -index-out FunDiff/${subj}/dcm.inddex.dat | grep -E 'series:' | sed 's/Found\ 1\ unique\ series: //' > FunDiff/${subj}/tmp

read -d '' -r -a temp < FunDiff/${subj}/tmp

# Create directory for subject
dcmunpack -src ./Funraw/${subj} -targ ./FunDiff/${subj} -run `echo $temp` bold nii f.nii

# Clean-up
rm FunDiff/${subj}/tmp
rm FunDiff/${subj}/dcm.inddex.dat

# Connect functional data to SUBJECTS_DIR
echo "$subj" > FunDiff/${subj}/subjectname

cd FunDiff

# Preprocess Functional Data
preproc-sess -s ${subj} -sdf ${out}/Fun/${subj}/slice_time_fmri.txt -fwhm 5 -surface self lhrh -per-run -fsd bold

# Create nuisance regressors
fcseed-sess -s ${subj} -cfg wm.config

fcseed-sess -s ${subj} -cfg vcsf.config

# Perform Regressions to leave residual hemispheres
selxavg3-sess -s ${subj} -s ${subj} -a lh.nuisance -no-con-ok

selxavg3-sess -s ${subj} -s ${subj} -a rh.nuisance -no-con-ok

