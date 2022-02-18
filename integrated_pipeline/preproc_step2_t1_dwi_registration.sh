#!/bin/bash

# this script is for two things:
# 1. prepare data for tractography
# 2. register t1 to diffusion (d0 and fa) space

# Author: Zhengwu Zhang
# Date: Oct. 23, 2018

# Updated for CSVD by Kyle Murray
# Updated for SBCI by Martin Cole

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

if [ -z ${TEMPLATEDIR+x} ]; then 
    TEMPLATEDIR=${SBCI_PATH}/integrated_pipeline/mni_152_sym_09c
fi

echo "Begin T1-DWI registration preprocessing: $(date)"

# folder for t1 preprocessing
mkdir structure/

#results for diffusion analysis
mkdir diffusion/

mv data.nii.gz diffusion/data.nii.gz
mv flip_x.bvec diffusion/flip_x.bvec
mv flip_x.bval diffusion/flip_x.bval

#####################################  
######## dMRI preprocessing #########
##################################### 

# extract b0 from dwi
scil_extract_b0.py diffusion/data.nii.gz \
	diffusion/flip_x.bval \
	diffusion/flip_x.bvec \
	diffusion/b0.nii.gz \
	--mean --b0_thr 10

# bet dwi
bet diffusion/b0.nii.gz diffusion/b0_bet.nii.gz -m -R -f 0.10

mrcalc diffusion/data.nii.gz diffusion/b0_bet_mask.nii.gz \
	 -mult diffusion/dwi_bet.nii.gz -quiet -force

# N4_DWI
N4BiasFieldCorrection -i diffusion/b0_bet.nii.gz \
        -o [diffusion/b0_n4.nii.gz, diffusion/bias_field_b0.nii.gz] \
        -c [300x150x75x50, 1e-6] -v 1

scil_apply_bias_field_on_dwi.py diffusion/dwi_bet.nii.gz diffusion/bias_field_b0.nii.gz \
        diffusion/dwi_n4.nii.gz --mask diffusion/b0_bet_mask.nii.gz -f

# crop dwi
scil_crop_volume.py diffusion/dwi_n4.nii.gz diffusion/dwi_cropped.nii.gz \
        --output_bbox diffusion/dwi_boundingBox.pkl -f

scil_crop_volume.py diffusion/b0_bet.nii.gz diffusion/b0_cropped.nii.gz \
        --input_bbox diffusion/dwi_boundingBox.pkl -f

scil_crop_volume.py diffusion/b0_bet_mask.nii.gz diffusion/b0_mask_cropped.nii.gz \
        --input_bbox diffusion/dwi_boundingBox.pkl -f

# dwi normalization
dwinormalise individual \
        diffusion/dwi_cropped.nii.gz \
        diffusion/b0_cropped.nii.gz \
        diffusion/dwi_normalized.nii.gz \
        -fslgrad diffusion/flip_x.bvec diffusion/flip_x.bval -force

# resample the dti image into 1x1x1
scil_resample_volume.py diffusion/dwi_normalized.nii.gz \
	diffusion/dwi_resample.nii.gz \
	--resolution 1 --interp "cubic" -f

fslmaths diffusion/dwi_resample.nii.gz -thr 0 diffusion/dwi_resample_clipped.nii.gz

scil_resample_volume.py diffusion/b0_mask_cropped.nii.gz \
	diffusion/mask_resample.nii.gz \
        --ref diffusion/dwi_resample.nii.gz \
        --enforce_dimensions \
        --interp nn -f

mrcalc diffusion/dwi_resample_clipped.nii.gz \
	diffusion/mask_resample.nii.gz \
        -mult diffusion/dwi_resampled.nii.gz -quiet

# resample b0
scil_extract_b0.py diffusion/dwi_resampled.nii.gz \
	diffusion/flip_x.bval \
	diffusion/flip_x.bvec \
	diffusion/b0_resampled.nii.gz \
	--mean --b0_thr 10

mrthreshold diffusion/b0_resampled.nii.gz diffusion/b0_mask_resampled.nii.gz --abs 0.00001


################################################################### 
######################## t1 preprocessing #########################
################################################################### 

# denoise and bias field correction for t1 image 
scil_run_nlmeans.py ../../t1.nii.gz structure/t1_denoised.nii.gz 1 --noise_est basic -f

N4BiasFieldCorrection -i structure/t1_denoised.nii.gz \
        -o [structure/t1_n4.nii.gz, structure/bias_field_t1.nii.gz] \
        -c [300x150x75x50, 1e-6] -v 1

# bet t1
antsBrainExtraction.sh -d 3 -a structure/t1_n4.nii.gz -e ${TEMPLATEDIR}/t1/t1_template.nii.gz \
        -o bet/ -m ${TEMPLATEDIR}/t1/t1_brain_probability_map.nii.gz -u 0

mrcalc structure/t1_n4.nii.gz bet/BrainExtractionMask.nii.gz -mult structure/t1_bet.nii.gz -force

mv bet/BrainExtractionMask.nii.gz structure/t1_bet_mask.nii.gz

# crop t1
scil_crop_volume.py structure/t1_bet.nii.gz structure/t1_bet_cropped.nii.gz \
        --output_bbox structure/t1_boundingBox.pkl -f

scil_crop_volume.py structure/t1_bet_mask.nii.gz structure/t1_bet_mask_cropped.nii.gz \
        --input_bbox structure/t1_boundingBox.pkl -f


######################################################################  
########### dwi preprocessing - get ready for tracking ###############
###################################################################### 

# b-values  for ukbiobank data include 0, 1000, 2000
# b-values  for abcd data include 0, 500, 1000, 2000 
# b-values  for bis data include 0, 1000, 2000

# extract data for dti
scil_extract_dwi_shell.py diffusion/dwi_resampled.nii.gz \
        diffusion/flip_x.bval diffusion/flip_x.bvec ${DTI_BVALS[*]} diffusion/dwi_dti.nii.gz \
        diffusion/dti.bval diffusion/dti.bvec -t 20 -f

# extract data for fodf
scil_extract_dwi_shell.py diffusion/dwi_resampled.nii.gz \
        diffusion/flip_x.bval diffusion/flip_x.bvec ${FODF_BVALS[*]} diffusion/dwi_fodf.nii.gz \
        diffusion/fodf.bval diffusion/fodf.bvec -t 20 -f

mkdir diffusion/dti

# compute dti metrics
scil_compute_dti_metrics.py diffusion/dwi_dti.nii.gz diffusion/dti.bval diffusion/dti.bvec \
	--mask diffusion/b0_mask_resampled.nii.gz \
        --not_all \
        --ad diffusion/dti/ad.nii.gz --evecs diffusion/dti/evecs.nii.gz \
        --evals diffusion/dti/evals.nii.gz --fa diffusion/dti/fa.nii.gz \
        --ga diffusion/dti/ga.nii.gz --rgb diffusion/dti/rgb.nii.gz \
        --md diffusion/dti/md.nii.gz --mode diffusion/dti/mode.nii.gz \
        --norm diffusion/dti/norm.nii.gz --rd diffusion/dti/rd.nii.gz \
        --tensor diffusion/dti/tensor.nii.gz \
        --non-physical diffusion/dti/nonphysical.nii.gz \
        --pulsation diffusion/dti/pulsation.nii.gz -f

################################################
####### registration between dti and t1 ########
################################################

# registration between t1 and diffusion imaging data can use multiple threads
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1

$SRUN antsRegistration --dimensionality 3 --float 0\
        --output [output,outputWarped.nii.gz,outputInverseWarped.nii.gz]\
        --interpolation Linear --use-histogram-matching 0\
        --winsorize-image-intensities [0.005,0.995]\
        --initial-moving-transform [diffusion/b0_resampled.nii.gz,structure/t1_bet_cropped.nii.gz,1]\
        --transform Rigid['0.2']\
        --metric MI[diffusion/b0_resampled.nii.gz,structure/t1_bet_cropped.nii.gz,1,32,Regular,0.25]\
        --convergence [500x250x125x50,1e-6,10] --shrink-factors 8x4x2x1\
        --smoothing-sigmas 3x2x1x0\
        --transform Affine['0.2']\
        --metric MI[diffusion/b0_resampled.nii.gz,structure/t1_bet_cropped.nii.gz,1,32,Regular,0.25]\
        --convergence [500x250x125x50,1e-6,10] --shrink-factors 8x4x2x1\
        --smoothing-sigmas 3x2x1x0\
        --transform SyN[0.1,3,0]\
        --metric MI[diffusion/b0_resampled.nii.gz,structure/t1_bet_cropped.nii.gz,1,32]\
        --metric CC[diffusion/dti/fa.nii.gz,structure/t1_bet_cropped.nii.gz,1,4]\
        --convergence [50x25x10,1e-6,10] --shrink-factors 4x2x1\
        --smoothing-sigmas 3x2x1


mv outputWarped.nii.gz structure/t1_warped.nii.gz
mv output0GenericAffine.mat structure/output0GenericAffine.mat
mv output1InverseWarp.nii.gz structure/output1InverseWarp.nii.gz
mv output1Warp.nii.gz structure/output1Warp.nii.gz

antsApplyTransforms -d 3 -i structure/t1_bet_mask_cropped.nii.gz -r structure/t1_warped.nii.gz \
        -o structure/t1_mask_warped.nii.gz -n NearestNeighbor \
        -t structure/output1Warp.nii.gz structure/output0GenericAffine.mat

# for freesurfer
antsApplyTransforms -d 3 -i structure/t1_n4.nii.gz -r structure/t1_n4.nii.gz \
        -o structure/t1_wholebrain_warped.nii.gz -n Linear \
        -t structure/output1Warp.nii.gz structure/output0GenericAffine.mat

echo "Finished T1-DWI registration preprocessing: $(date)"
