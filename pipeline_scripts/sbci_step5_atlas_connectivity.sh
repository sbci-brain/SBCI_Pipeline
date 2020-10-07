#!/bin/bash

source ${SBCI_CONFIG}

idx=0

for PARCELLATION in ${ATLAS_PARCELLATIONS[*]}; do

  echo Calculating Atlas: ${PARCELLATION}

  # Step1) Calculate continuous SC at atlas level
  python ${SCRIPT_PATH}/calculate_continuous_sc.py \
         --sc_matrix ${OUTPUTDIR}/smoothed_sc_avg_${BANDWIDTH}_${RESOLUTION}.npz \
         --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
         --atlas ${AVGDIR}/${PARCELLATION}_avg_roi_${RESOLUTION}.npz \
         --mask_indices ${ATLAS_ROI_MASKS[$idx]} \
         --output ${OUTPUTDIR}/${PARCELLATION}_csc.mat -f
  
  run=1

  while IFS= read -r -d '' FCDIR; do

    FCOUTPUTDIR=${OUTPUTDIR}/RUN$(printf '%03d' $run)

    # Step2) Calculate continuous FC (wm, motion, vcsf, gsl, confounders)
    python ${SCRIPT_PATH}/calculate_approx_continuous_fc.py \
           --time_series ${FCOUTPUTDIR}/fc_ts_partial.npz \
           --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
           --atlas ${AVGDIR}/${PARCELLATION}_avg_roi_${RESOLUTION}.npz \
           --mask_indices ${ATLAS_ROI_MASKS[$idx]} \
           --output ${FCOUTPUTDIR}/${PARCELLATION}_cfc.mat -f

    run=$((run + 1))

  done < ${OUTPUTDIR}/fcruns

  idx=$((idx + 1))

done
