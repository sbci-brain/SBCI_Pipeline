#!/bin/bash
#module load dcm2niix
#module load pigz #Speeds up dcm2niix

#This code is validated by Zhengwu Zhang on May 13, 2019 for ABCD subjects
# Updated for CSVD by Kyle Murray

cd anat
mrconvert T1.nii -stride 1,2,3 T1.nii.gz -force
cd ..

cd dwi
mrconvert dwi.nii.gz -stride 1,2,3,4 dwi_all.nii.gz -force
scil_convert_gradient_fsl_to_mrtrix.py *.bval *.bvec encoding.b  -f
scil_flip_grad.py --mrtrix encoding.b encoding_x.b x -f
scil_convert_gradient_mrtrix_to_fsl.py encoding_x.b bvals bvecs -f 
cd ..



mkdir dwi_psc_connectome
cd dwi_psc_connectome
 
#move final files to one folder
mv ../anat/T1.nii.gz t1.nii.gz
mv ../dwi/bvals bvals
mv ../dwi/bvecs bvecs
mv ../dwi/dwi_all.nii.gz data.nii.gz
 


