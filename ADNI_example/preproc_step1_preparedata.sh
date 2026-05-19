#!/bin/bash

echo "Begin preparing data: $(date)"

# reorient T1 to standard MRtrix stride
cd anat
mrconvert *_T1w.nii* -stride 1,2,3 t1.nii.gz -force
cd ..

# reorient eddy-corrected DWI and convert/flip gradients
# Inputs from adni_dwi_eddy_correction.sh:
#   eddy_corrected_data.nii.gz            — motion + eddy + B0 corrected
#   eddy_corrected_data.eddy_rotated_bvecs — bvecs rotated by eddy for head motion
#   ap_dwi.bval                           — b-values
cd dwi
mrconvert eddy_corrected_data.nii.gz -stride 1,2,3,4 flipped_data.nii.gz -force
scil_convert_gradient_fsl_to_mrtrix.py ap_dwi.bval eddy_corrected_data.eddy_rotated_bvecs encoding.b -f
scil_flip_grad.py --mrtrix encoding.b encoding_x.b x -f
scil_convert_gradient_mrtrix_to_fsl.py encoding_x.b flip_x.bval flip_x.bvec -f
cd ..

# assemble dwi_pipeline/
mkdir -p dwi_pipeline
cd dwi_pipeline

mv ../anat/t1.nii.gz t1.nii.gz
mv ../dwi/flip_x.bval flip_x.bval
mv ../dwi/flip_x.bvec flip_x.bvec
mv ../dwi/flipped_data.nii.gz data.nii.gz

echo "Finished preparing data: $(date)"
