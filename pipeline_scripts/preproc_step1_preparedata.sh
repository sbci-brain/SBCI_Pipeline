#!/bin/bash
# module load dcm2niix
# module load pigz #Speeds up dcm2niix

# This code is validated by Zhengwu Zhang on May 13, 2019 for ABCD subjects
# Updated for CSVD by Kyle Murray
# Updated for SBCI by Martin Cole

# flip T1
cd anat
mrconvert T1.nii.gz -stride 1,2,3 T1.nii.gz -force
cd ..

# flip dMRI
cd dwi
mrconvert dwi.nii.gz -stride 1,2,3,4 dwi_all.nii.gz -force
scil_convert_gradient_fsl_to_mrtrix.py *.bval *.bvec encoding.b  -f
scil_flip_grad.py --mrtrix encoding.b encoding_x.b x -f
scil_convert_gradient_mrtrix_to_fsl.py encoding_x.b flip_x.bval flip_x.bvec -f 
cd ..

# move final files to one folder
mkdir dwi_sbci_connectome
cd dwi_sbci_connectome

mv ../anat/T1.nii.gz t1.nii.gz
mv ../dwi/flip_x.bval flip_x.bval
mv ../dwi/flip_x.bvec flip_x.bvec
mv ../dwi/dwi_all.nii.gz data.nii.gz
 


