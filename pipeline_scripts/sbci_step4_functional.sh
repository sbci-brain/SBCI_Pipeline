#!/bin/bash

source ${SBCI_CONFIG}

####################################################################
# CALCULATE RESIDIUAL FUNCTIONAL BOLD TIME SERIES AND CONNECTIVITY #
####################################################################

# If the subject has multiple BOLD runs, calculate FC for each of them (it is 
# possible to concatenate BOLD time series instead of treating them individually)
find ./fsfast/t1_freesurfer/bold/ -regextype sed -regex ".*/[0-9][0-9][0-9]" -type d -print0 > ${OUTPUTDIR}/fcruns 

run=1

while IFS= read -r -d '' FCDIR; do

  FCOUTPUTDIR=${OUTPUTDIR}/RUN$(printf '%03d' $run)

  mkdir -p ${FCOUTPUTDIR}

  # Step1) Calculate FC residual time series (wm, motion, vcsf, gsl)
  python ${SCRIPT_PATH}/calculate_residual_timeseries.py \
         --lh_time_series ${FCDIR}/fmcpr.sm5.fsaverage.lh.nii.gz \
         --rh_time_series ${FCDIR}/fmcpr.sm5.fsaverage.rh.nii.gz \
         --motion ${FCDIR}/fmcpr.mcdat \
         --wm ${FCDIR}/wm.dat \
         --vcsf ${FCDIR}/vcsf.dat \
         --gsl ${FCDIR}/global.waveform.dat \
         --output ${FCOUTPUTDIR}/fc_ts_partial.npz -f

  # Step2) Register the BOLD time series to template space
  #############################################################################
  ## Assuming bold series is already in template space through fs fast,      ##
  ## otherwise uncomment below and change input and output names accordingly ##
  #############################################################################
  #python ${SCRIPT_PATH}/group/register_fc.py \
  #       --lh_surface ${OUTPUTDIR}/lh_sphere_reg_lps_norm.vtk \
  #       --lh_average ${AVGDIR}/lh_sphere_avg_norm.vtk \
  #       --rh_surface ${OUTPUTDIR}/rh_sphere_reg_lps_norm.vtk \
  #       --rh_average ${AVGDIR}/rh_sphere_avg_norm.vtk \
  #       --time_series ${FCOUTPUTDIR}/fc_ts_partial.npz \
  #       --output ${FCOUTPUTDIR}/registered_fc_ts_partial.npz -f

  # Step3) Calculate FC matrix at the given resolution in template space
  python ${SCRIPT_PATH}/calculate_fc.py \
         --time_series ${FCOUTPUTDIR}/fc_ts_partial.npz \
         --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
         --output ${FCOUTPUTDIR}/fc_partial_avg_${RESOLUTION}.mat -f

  run=$((run + 1))

done < ${OUTPUTDIR}/fcruns

