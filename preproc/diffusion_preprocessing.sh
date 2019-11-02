#!/bin/bash
#SBATCH --time=5-00:00:00 --mem=24gb --partition=gpu --gres=gpu:1
#
# Created by Kyle Murray
#
# Preprocess DTI data on HPC
# This script works for AP_b1000, AP_b2000, and two PA voumes
#

module load fsl/6.0.0/b1

subj=${1}
out=${2}

cd ${out}

# Set up TOPUP
di=DTI/data/${subj}
dp=DTI/preproc/${subj}

# Combine all APs into one dwidata file
fslmerge -t ${dp}/dwidata ${di}/dti_AP1000.nii ${di}/dti_AP2000.nii

# Combine bvals and bvecs
read -d '' -r -a bval1 < ${di}/dti_AP1000.bval
read -d '' -r -a bval2 < ${di}/dti_AP2000.bval
echo ${bval1[@]} ${bval2[@]} > ${dp}/bvals

read -d '' -r -a bvec1 < ${di}/dti_AP1000.bvec
read -d '' -r -a bvec2 < ${di}/dti_AP2000.bvec
echo ${bvec1[@]:0:${#bval1[@]}} ${bvec2[@]:0:${#bval1[@]}} > ${dp}/bvecs
echo ${bvec1[@]:${#bval1[@]}:${#bval1[@]}} ${bvec2[@]:${#bval1[@]}:${#bval1[@]}} >> ${dp}/bvecs
echo ${bvec1[@]:$(( ${#bval1[@]} + ${#bval1[@]} )):${#bval1[@]}} ${bvec2[@]:$(( ${#bval1[@]} + ${#bval1[@]} )):${#bval1[@]}} >> ${dp}/bvecs

# Create index.txt file for later use
indx=""
for ((i=1; i<=$(( ${#bval1[@]} + ${#bval1[@]} )); i+=1));
do
    indx="$indx 1"
done
echo $indx > ${dp}/index.txt

# Create all_my_b0_images.nii
fslroi ${di}/dti_AP1000.nii ${dp}/nodif_1000 0 2
fslroi ${di}/dti_AP2000.nii ${dp}/nodif_2000 0 2
fslmerge -t ${dp}/AP_b0 ${dp}/nodif_1000 ${dp}/nodif_2000
fslmerge -t ${dp}/AP_PA_b0 ${dp}/AP_b0 ${di}/dti_PA

# Create acqparams file
#CSVD EPI factor = 172
#CSVD Echo Spacing = 0.66 ms
echo "0 -1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 -1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 -1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 -1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 1 0 0.11352" >> ${dp}/acqparams.txt
echo "0 1 0 0.11352" >> ${dp}/acqparams.txt
cd ${dp}

# Run TOPUP
topup \
    --imain=AP_PA_b0 \
    --datain=acqparams.txt \
    --config=b02b0.cnf \
    --out=topup_AP_PA_b0 \
    --iout=topup_AP_PA_b0_iout \
    --fout=topup_AP_PA_b0_fout

# Prepare EDDY
# Generate brain mask using the corrected b0 volumes
fslmaths topup_AP_PA_b0_iout -Tmean hifi_nodif
# Brain extract the averaged b0
bet hifi_nodif hifi_nodif_brain -m -f 0.2

# Run EDDY
eddy_cuda \
    --imain=dwidata \
    --mask=hifi_nodif_brain_mask \
    --index=index.txt \
    --acqp=acqparams.txt \
    --bvecs=bvecs \
    --bvals=bvals \
    --fwhm=0 \
    --topup=topup_AP_PA_b0 \
    --flm=quadratic \
    --out=eddy_unwarped_images \
    --data_is_shelled

# Run dtifit
dtifit \
    --data=eddy_unwarped_images \
    --mask=hifi_nodif_brain_mask \
    --bvecs=bvecs \
    --bvals=bvals \
    --out=dti

