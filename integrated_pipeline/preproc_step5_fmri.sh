#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

echo "Sourcing FREESURFER_HOME"
source ${FREESURFER_PATH}/SetUpFreeSurfer.sh

echo "Begin FSFast fMRI preprocessing: $(date)"
export SUBJECTS_DIR=$(pwd)/dwi_pipeline/structure

cd fsfast
echo t1_freesurfer > subjectname

SUBJECT_ID=t1_freesurfer

# preprocess the BOLD time series for each run separately
preproc-sess -s ${SUBJECT_ID} -fwhm 5 -stc siemens -surface fsaverage lhrh -per-run -fsd bold -mni305 -force

# configure the nuisance variables
fcseed-config -wm -fcname wm.dat -fsd bold -mean -cfg wm.config -force
fcseed-config -vcsf -fcname vcsf.dat -fsd bold -mean -cfg vcsf.config -force

fcseed-sess -s ${SUBJECT_ID} -cfg wm.config -force
fcseed-sess -s ${SUBJECT_ID} -cfg vcsf.config -force

###########################################################################################
# surface-based analysis registered to fsaverage, or volume-based mni305 for subcortical
# separate analysis for each run 
# smoothing to 5mm FWHM
# no task-based paradigm (resting-state)
# regress out ventricular cerebrospinal fluid (5PCs)
# regress out white matter (5PCs)
# regress out global waveform
# regress out motion
# detrend the signal (reduce drift using linear regression)
# output as BOLD signal
# TR value in seconds
# apply slice timing correction (other options: up, down, odd, even)
# highpass filter cutoff in Hz (0.009)
# lowpass filter cutoff in Hz (0.08)
# perform intensity normalisation
###########################################################################################

mkanalysis-sess -analysis fc.surface.lh \
    -surface fsaverage lh \
    -per-run \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 1 \
    -fsd bold \
    -TR 2.5 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force

mkanalysis-sess -analysis fc.surface.rh \
    -surface fsaverage rh \
    -per-run \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 1 \
    -fsd bold \
    -TR 2.5 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force 

mkanalysis-sess -analysis fc.mni \
    -mni305 \
    -per-run \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 1 \
    -fsd bold \
    -TR 2.5 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force

# regress out the nuisance variables for each run separately
selxavg3-sess -analysis fc.surface.lh -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.surface.rh -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.mni -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force

# find the separate runs and move the final BOLD timeseries' to their own folders
cd ..

find ./fsfast/bold/ -regextype sed -regex ".*/[0-9]\+$" -type d -printf "%f\n" > ./fcruns

while read BOLDRUN; do
  mkdir -p fmri/bold/${BOLDRUN}
  mv ./fsfast/bold/fc.surface.lh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.surface.lh.nii.gz
  mv ./fsfast/bold/fc.surface.rh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.surface.rh.nii.gz
  mv ./fsfast/bold/fc.mni/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.mni.nii.gz
done < ./fcruns

echo "Finished FSFast fMRI preprocessing: $(date)"
