#!/bin/bash

# Prepares CSVD DTI data for Scilpy PSC pipeline

subj=${1}
out=${2}

cd ${out}

subdir=${out}/DTI/Scilpy/${subj}

mkdir ${subdir}/anat
cp T1/${subj}/t1.nii ${subdir}/anat/T1.nii

mkdir ${subdir}/dwi
cp DTI/preproc/${subj}/bvals ${subdir}/dwi/${subj}.bval
cp DTI/preproc/${subj}/eddy_unwarped_images.eddy_rotated_bvecs ${subdir}/dwi/${subj}.bvec
cp DTI/preproc/${subj}/eddy_unwarped_images.nii.gz ${subdir}/dwi/dwi.nii.gz

cd ${subdir}
