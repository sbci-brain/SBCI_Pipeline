#!/bin/bash

#SBATCH -N 1
#SBATCH -n 1
#SBATCH -p general
#SBATCH -t 24:00:00
#SBATCH --mem=24g
#SBATCH --output=dwicat_process-%x_%j.log

module load fsl/6.0.6

baseDir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/missing_data/Devel_func"
startIndex=$1
endIndex=$2

subjectIDs=$(ls $baseDir | sed -n "${startIndex},${endIndex}p")

for subjectID in $subjectIDs
do
  apDir="${baseDir}/${subjectID}/unprocessed/rfMRI_REST1a_AP"
  paDir="${baseDir}/${subjectID}/unprocessed/rfMRI_REST1a_PA"
  outputDir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/missing_data/Devel_func/${subjectID}/fmri"

  json_file_AP="${apDir}/${subjectID}_SpinEchoFieldMap2_AP.json"
  json_file_PA="${paDir}/${subjectID}_SpinEchoFieldMap2_PA.json"
  file_AP="${apDir}/${subjectID}_SpinEchoFieldMap2_AP.nii.gz"
  file_PA="${paDir}/${subjectID}_SpinEchoFieldMap2_PA.nii.gz"

# Check if all necessary files exist, if not, skip to the next subject
  if [ ! -f "$json_file_AP" ] || [ ! -f "$json_file_PA" ] || [ ! -f "$file_AP" ] || [ ! -f "$file_PA" ]; then
    echo "Required files not found for subject ${subjectID}. Skipping..."
    continue
  fi

 if [ -f "${outputDir}/${subjectID}_rfMRI_REST1_PA_AP_corr.nii.gz" ]; then
    echo "Correction output already exists for ${subjectID}. Skipping subject..."
    continue
 fi
  mkdir -p $outputDir

  AP_readout=$(grep -m 1 "TotalReadoutTime" ${json_file_AP} | sed 's/"TotalReadoutTime": //' | sed 's/,//')
  PA_readout=$(grep -m 1 "TotalReadoutTime" ${json_file_PA} | sed 's/"TotalReadoutTime": //' | sed 's/,//')

  echo "Processing ${subjectID}: Creating acqparams.txt..."
  PA=$(fslval $file_PA dim4)
  AP=$(fslval $file_AP dim4)
  rm -rf $outputDir/acqparams.txt

  i=0
  while [ $i -lt ${PA} ]; do
      echo "0 1 0 ${PA_readout}" >> $outputDir/acqparams.txt
      i=$(( $i + 1 ))
  done

  i=0
  while [ $i -lt ${AP} ]; do
      echo "0 -1 0 ${AP_readout}" >> $outputDir/acqparams.txt
      i=$(( $i + 1 ))
  done

  echo "Merging PA and AP images into a single 4D file..."
  fslmerge -t ${outputDir}/${subjectID}_SpinEchoFieldMap1_PA_AP.nii.gz \
           $file_PA \
           $file_AP

 if [ ! -f "${outputDir}/my_output_fieldcoef.nii.gz" ]; then
    echo "Running TOPUP to estimate distortion fields..."
    topup --imain=${outputDir}/${subjectID}_SpinEchoFieldMap1_PA_AP.nii.gz \
          --datain=${outputDir}/acqparams.txt \
          --config=b02b0.cnf \
          --out=${outputDir}/my_output
 else
    echo "TOPUP results already exist for ${subjectID}. Skipping TOPUP..."
 fi


  echo "Applying TOPUP correction to PA and AP images..."
  applytopup --imain=${paDir}/${subjectID}_rfMRI_REST1_PA.nii.gz,${apDir}/${subjectID}_rfMRI_REST1_AP.nii.gz \
             --inindex=1,2 \
             --datain=${outputDir}/acqparams.txt \
             --topup=${outputDir}/my_output \
             --out=${outputDir}/${subjectID}_rfMRI_REST1_PA_AP_corr.nii.gz \
             --verbose

  echo "TOPUP correction completed for subject ${subjectID}. Results stored in ${outputDir}."

done
