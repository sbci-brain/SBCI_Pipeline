#!/bin/bash

echo "Begin preparing data: $(date)"

# flip T1
cd anat
mrconvert *_T1w.nii.gz -stride 1,2,3 t1.nii.gz -force
cd ..

# flip dMRI
cd dwi
mrconvert *_dwi.nii.gz -stride 1,2,3,4 flipped_data.nii.gz -force
scil_convert_gradient_fsl_to_mrtrix.py *_dwi.bval *_dwi.bvec encoding.b  -f
scil_flip_grad.py --mrtrix encoding.b encoding_x.b x -f
scil_convert_gradient_mrtrix_to_fsl.py encoding_x.b flip_x.bval flip_x.bvec -f 
cd..

# move final files to one folder
mkdir dwi_pipeline
cd dwi_pipeline

mv ../anat/t1.nii.gz t1.nii.gz
mv ../dwi/flip_x.bval flip_x.bval
mv ../dwi/flip_x.bvec flip_x.bvec
mv ../dwi/flipped_data.nii.gz data.nii.gz

echo "Finished preparing data: $(date)"
