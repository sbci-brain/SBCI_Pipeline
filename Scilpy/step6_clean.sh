#!/bin/bash
#step 6 clean unnecessary files
#don't run this step until you confirm all steps are done successfully 

cd dwi_psc_connectome

#diffusion
cd diffusion

rm data.nii.gz
rm dwi_n4.nii.gz
rm dwi_bet.nii.gz
rm dwi_cropped.nii.gz
rm dwi_resample_clipped.nii.gz
rm dwi_resample.nii.gz
rm dwi_normalized.nii.gz
rm dwi_fodf.nii.gz
rm dwi_dti.nii.gz
cd ..


cd structure
rm bias_field_t1.nii.gz
cd ..

cd ..
rm -r dwi
cd ..

#now each subject takes about 3 Gb space
