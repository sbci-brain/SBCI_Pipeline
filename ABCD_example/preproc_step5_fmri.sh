#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

echo "Sourcing FREESURFER_HOME"
source ${FREESURFER_PATH}/SetUpFreeSurfer.sh

echo "Begin FSFast fMRI preprocessing: $(date)"
export SUBJECTS_DIR=$(pwd)/dwi_pipeline/structure

# convert everything to fsfast format
cd func

ls *_bold.nii.gz > ./fcruns

while read BOLDRUN; do
  NUMBER=${BOLDRUN#*run-}
  NUMBER=$(printf "%03d" ${NUMBER%_*})

  mkdir -p ../fsfast/bold/${NUMBER}
  cp ${BOLDRUN} ../fsfast/bold/${NUMBER}/f.nii.gz
  cp ${BOLDRUN%_*}*.tsv ../fsfast/bold/${NUMBER}/motion.tsv

  tail -n +2 ../fsfast/bold/${NUMBER}/motion.tsv > ../fsfast/bold/${NUMBER}/motion.dat
  cut -f2- ../fsfast/bold/${NUMBER}/motion.dat > ../fsfast/bold/${NUMBER}/tmp.dat
  tr '\t' ' ' < ../fsfast/bold/${NUMBER}/tmp.dat > ../fsfast/bold/${NUMBER}/motion.dat
  rm ../fsfast/bold/${NUMBER}/tmp.dat
done < ./fcruns

# perform fsfast processing
cd ../fsfast
echo t1_freesurfer > subjectname

# preprocess the BOLD time series for each run separately
preproc-sess -s . -surface fsaverage lhrh -per-run -fwhm 5 -fsd bold -mni305 -force

# configure the nuisance variables
fcseed-config -wm -fcname wm.dat -fsd bold -mean -cfg wm.config -force
fcseed-config -vcsf -fcname vcsf.dat -fsd bold -mean -cfg vcsf.config -force

fcseed-sess -s . -cfg wm.config -force
fcseed-sess -s . -cfg vcsf.config -force

###########################################################################################
# surface-based analysis registered to fsaverage, or volume-based mni305 for subcortical
# separate analysis for each run 
# skip the first 8 frames
# no task-based paradigm (resting-state)
# regress out ventricular cerebrospinal fluid (5PCs)
# regress out white matter (5PCs)
# regress out global waveform
# regress out motion
# detrend the signal (reduce drift using quadratic regression)
# output as BOLD signal
# TR value in seconds
# highpass filter cutoff in Hz (0.009)
# lowpass filter cutoff in Hz (0.08)
# no smoothing
# perform intensity normalisation
###########################################################################################

mkanalysis-sess -analysis fc.surface.lh \
    -surface fsaverage lh \
    -per-run \
    -nskip 8 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg motion.dat 6 \
    -nuisreg global.waveform.dat 1 \
    -polyfit 2 \
    -fsd bold \
    -TR 0.8 \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -fwhm 5 \
    -force

mkanalysis-sess -analysis fc.surface.rh \
    -surface fsaverage rh \
    -per-run \
    -nskip 8 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg motion.dat 6 \
    -nuisreg global.waveform.dat 1 \
    -polyfit 2 \
    -fsd bold \
    -TR 0.8 \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -fwhm 5 \
    -force

mkanalysis-sess -analysis fc.mni \
    -mni305 \
    -per-run \
    -nskip 8 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg motion.dat 6 \
    -nuisreg global.waveform.dat 1 \
    -polyfit 2 \
    -fsd bold \
    -TR 0.8 \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -fwhm 5 \
    -force

# regress out the nuisance variables for each run separately
selxavg3-sess -analysis fc.surface.lh -s . -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.surface.rh -s . -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.mni -s . -no-con-ok -run-wise -svres -force

cd ..

# find the separate runs and move the final BOLD timeseries' to their own folders
find ./fsfast/bold/ -regextype sed -regex ".*/[0-9]\+$" -type d -printf "%f\n" > ./fcruns

while read BOLDRUN; do
  mkdir -p fmri/bold/${BOLDRUN}
  cp ./fsfast/bold/fc.surface.lh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.surface.lh.nii.gz
  cp ./fsfast/bold/fc.surface.rh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.surface.rh.nii.gz
  cp ./fsfast/bold/fc.mni/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz ./fmri/bold/${BOLDRUN}/fc.mni.nii.gz
done < ./fcruns

echo "Finished FSFast fMRI preprocessing: $(date)"
