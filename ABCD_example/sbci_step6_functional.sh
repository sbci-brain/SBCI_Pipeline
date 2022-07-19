#!/bin/bash

source ${SBCI_CONFIG}

if [ -z ${REFDIR+x} ]; then 
    REFDIR=${SBCI_PATH}/data/fsaverage
fi

if [ -z ${SCRIPT_PATH+x} ]; then 
    SCRIPT_PATH=${SBCI_PATH}/scripts
fi

##########################################################
# CALCULATE FUNCTIONAL BOLD TIME SERIES AND CONNECTIVITY #
##########################################################

# If the subject has multiple BOLD runs, calculate FC for each of them (it is 
# possible to concatenate BOLD time series instead of treating them individually)
find ./fmri/bold/ -regextype sed -regex ".*/[0-9]\+$" -type d -print0 > ./dwi_pipeline/sbci_connectome/fcruns 

TS_LIST=""

run=1

while IFS= read -r -d '' FCDIR; do

  FCOUTPUTDIR=./dwi_pipeline/sbci_connectome/RUN$(printf '%03d' $run)

  mkdir -p ${FCOUTPUTDIR}

  # Step1) Convert BOLD timeseries into SBCI format
  python ${SCRIPT_PATH}/convert_fsfast_timeseries.py \
         --lh_time_series ${FCDIR}/fc.surface.lh.nii.gz \
         --rh_time_series ${FCDIR}/fc.surface.rh.nii.gz \
         --sub_time_series ${FCDIR}/fc.mni.nii.gz \
         --aparc ${REFDIR}/mri.2mm/aseg.mgz \
         --sub_rois ${ROIS[*]} \
         --output ${FCOUTPUTDIR}/fc_ts.npz -f

  run=$((run + 1))
  
  TS_LIST="${TS_LIST} ${FCOUTPUTDIR}/fc_ts.npz"

done < ./dwi_pipeline/sbci_connectome/fcruns

# Step2) Join all the runs into a single timeseries
python ${SCRIPT_PATH}/concatenate_timeseries.py \
       --time_series ${TS_LIST} \
       --output ./dwi_pipeline/sbci_connectome/fc_ts.npz -f

# Step3) Calculate FC matrix at the given resolution in template space
python ${SCRIPT_PATH}/calculate_fc.py \
       --time_series ./dwi_pipeline/sbci_connectome/fc_ts.npz \
       --mesh ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz \
       --output ./dwi_pipeline/sbci_connectome/fc_avg_${RESOLUTION}.mat --ts -f

