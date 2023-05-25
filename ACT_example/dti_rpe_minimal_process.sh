#!/bin/bash
#SBATCH -t 3-3:00:00 
#SBATCH --mem-per-cpu=32gb

# Written by Andrew Jahn, University of Michigan, 02.25.2019
# Updated 07.10.2020 to incorporate changes from MRtrix version 3.0.1
# Based on Marlene Tahedl's BATMAN tutorial (http://www.miccai.org/edu/finalists/BATMAN_trimmed_tutorial.pdf)
# The main difference between this script and the other one in this repository, is that this script assumes that your diffusion images were acquired with AP phase encoding
# Thanks to John Plass and Bennet Fauber for useful comments
# Adapted by Mia Anthony, March 2023

# USAGE
# $(basename $0) [Raw Diffusion] [RevPhaseImage] [AP bvec] [AP bval] [PA bvec] [PA bval] [Anatomical]

# Arguments: 
# 		1) The raw diffusion image;
# 		2) The image acquired with the reverse phase-encoding direction;
# 		3) The bvec file for the data acquired in the AP direction;
# 		4) The bval file for the data acquired in the AP direction;
# 		5) The bvec file for the data acquired in the PA direction;
# 		6) The bval file for the data acquired in the PA direction;
#       7) The anatomical image"

RAW_DWI=$1 # raw diffusion image /dwi/sub-0105_ses-01_dwi.nii.gz
REV_PHASE=$2 # image acquired with the reverse phase-encoding direction
# fmap/sub-0105_ses-01_dir-PA_dwi.nii.gz
AP_BVEC=$3 # bvec file for AP dwi/bvec
AP_BVAL=$4 # bval file for AP dwi/bval
PA_BVEC=$5 # bvec file for PA not use
PA_BVAL=$6 # bval file for PA not use
ANAT=$7 # T1 anatomical
BIDS_PATH=$8 # BIDS path
########################### STEP 0 ###################################
#	              TO-DO before preprocessing (only once)          	 #
######################################################################
cd $BIDS_PATH
# Create QC folder and assign the path to a variable named 'QC_DIR'
QC_DIR=${BIDS_PATH}/QC/

export QT_QPA_PLATFORM=offscreen
export XDG_RUNTIME_DIR=${BIDS_PATH}/run
export RUNLEVEL=3

# export TMP_DIR=${BIDS_PATH}/tmp

# Create the following folders in the QC dir to save QC images 
# /residual 
# /corrupt
# /mask
# /fod_voxels
# /fod_overlay 
# /tissue_align 
# /gm_wm 
# mkdir -p $QC_DIR/residual $QC_DIR/corrupt $QC_DIR/mask $QC_DIR/fod_voxels $QC_DIR/fod_overlay $QC_DIR/tissue_align $QC_DIR/gm_wm

########################### STEP 1 ###################################
#	            Convert data to .mif format and denoise	   	         #
######################################################################

# Convert .nii to .mif format
mrconvert $RAW_DWI raw_dwi.mif -fslgrad $AP_BVEC $AP_BVAL

# Denoise dwi
dwidenoise raw_dwi.mif dwi_den.mif -noise noise.mif

# Calculate residual to check whether any region is disproportionately affected by noise.
mrcalc raw_dwi.mif dwi_den.mif  -subtract noise_residual.mif

# ---------------------- QC steps  ---------------------- #
# Everything within the grey and white matter should be relatively uniform and blurry. If any clear anatomical landmarks are visible in the residual image, those parts of the brain have been corrupted by noise - increase the extent of the denoising filter from 5 (default) to a larger number, e.g. 7.
# mkdir $QC_DIR/residual 
# mrview noise_residual.mif -capture.folder $QC_DIR/residual -capture.prefix $SBJ -capture.grab

# dwidenoise raw_dwi.mif dwi_den.mif  -extent 7 -noise noise_7extent.nii.gz

# Determine whether Gibbs denoising is needed. Check diffusion data for ringing artifacts before and after to determine whether Gibbs denoising improved the data. If the data looks worse or the same, then skip Gibbs denoising.
# mrdegibbs raw_dwi.mif dwi_den.mif
mrdegibbs raw_dwi.mif dwi_den.mif -force

# mrview raw_dwi.mif dwi_den.mif -capture.folder $QC_DIR/gibbs -capture.prefix $SBJ -capture.grab

##### Check for gibbs ringing before continuing to process

# -------------------------------------------------------- #

# Extract the b0 images in the AP direction. For the PA_BVEC and PA_BVAL files, they should be in the follwing format (assuming you extract only one volume):
# PA_BVEC: 0 0 0
# PA_BVAL: 0
dwiextract dwi_den.mif - -bzero | mrmath - mean mean_b0_AP.mif -axis 3

# Average b0s for AP direction to calculate mean intensity 
mrconvert $REV_PHASE PA.mif # If the PA map contains only 1 image, add the option "-coord 3 0"

# Average b0s for PA direction 
# mrconvert PA.mif -fslgrad $PA_BVEC $PA_BVAL - | mrmath - mean mean_b0_PA.mif -axis 3
mrconvert PA.mif - | mrmath - mean mean_b0_PA.mif -axis 3

# Concatenate the b0 images from AP and PA directions to create a paired b0 image
mrcat mean_b0_AP.mif mean_b0_PA.mif -axis 3 b0_pair.mif

# Run dwipreproc (wrapper for eddy and topup). *CHANGE READOUT TIME based on TotalReadoutTime in the AP/PA JSON file*
# CogTE = 0.0476
readout_time=0.0476
dwifslpreproc dwi_den.mif dwi_den_preproc.mif -nocleanup -pe_dir AP -rpe_pair -se_epi b0_pair.mif -readout_time $readout_time -align_seepi # -align_seepi ensures that the first volume in the series provided to topup is also the first volume in the series provided to eddy to make sure the volumes are aligned.


# Bias field correction. Needs ANTs to be installed in order to use the "ants" option
dwibiascorrect ants dwi_den_preproc.mif dwi_den_preproc_unbiased.mif -bias bias.mif

# Create whole brain mask from bias corrected data - mask should be tight
dwi2mask dwi_den_preproc_unbiased.mif mask.mif

# create new bvecs and bvals files for the preprocessed data
mrinfo dwi_den_preproc_unbiased.mif -export_grad_fsl dwi/bvecs dwi/bvals

mrconvert dwi_den_preproc_unbiased.mif dwi/dwi.nii.gz

# ########################### STEP 2 ###################################
# #             Basis function for each tissue type                    #
# ######################################################################

# # Create a basis function from the subject's DWI data to estimate response function for spherical deconvolution. The "dhollander" function is best used for multi-shell acquisitions; it will estimate different basis functions for each tissue type. For single-shell acquisition, use the "tournier" function instead

# # -------------- Type of shell-acquisition  -------------- #
# ### SINGLE-SHELL (single b-value) 
# # dwi2response tournier dwi_den_preproc_unbiased.mif response_wm.txt response_gm.txt response_csf.txt -voxels voxels.mif
# dwi2response tournier dwi_den_preproc_unbiased.mif response_wm.txt -voxels voxels.mif

# # move files into QC folder 
# # mv response_wm.txt response_gm.txt response_csf.txt $QC_DIR/response/$SBJ

# # Estimate fibre orientation distributions (FOD) from diffusion data using spherical deconvolution, using the basis functions estimated above
# # dwi2fod csd dwi.mif response_wm.txt wmfod.mif
# dwi2fod csd dwi_den_preproc_unbiased.mif response_wm.txt wmfod.mif
# # -------------------------------------------------------- #

# ### MULTI-SHELL (more than 1 b-value)
# # dwi2response dhollander dwi_den_preproc_unbiased.mif response_wm.txt response_gm.txt response_csf.txt-voxels voxels.mif

# # Estimate fibre orientation distributions from diffusion data using spherical deconvolution, using the basis functions estimated above
# # dwi2fod msmt_csd dwi_den_preproc_unbiased.mif -mask mask.mif response_wm.txt wmfod.mif response_gm.txt gmfod.mif response_csf.txt csffod.mif
# # -------------------------------------------------------- #

# # Create an image of the FODs overlaid onto the estimated tissues (Blue=WM; Green=GM; Red=CSF)
# # mrconvert -coord 3 0 wmfod.mif - | mrcat csffod.mif gmfod.mif - vf.mif

# # Normalize the FODs to enable comparison between subjects
# # mtnormalise wmfod.mif wmfod_norm.mif gmfod.mif gmfod_norm.mif csffod.mif csffod_norm.mif -mask mask.mif
# mtnormalise wmfod.mif wmfod_norm.mif -mask mask.mif

# ########################### STEP 3 ###################################
# #            Create a GM/WM boundary for seed analysis               #
# ######################################################################

# # Convert the anatomical image to .mif format, and then extract all five tissue catagories (1=GM; 2=Subcortical GM; 3=WM; 4=CSF; 5=Pathological tissue)
# mrconvert $ANAT anat.mif

# # Segment the anatomical image into the tissue types
# 5ttgen fsl anat.mif 5tt_nocoreg.mif

# # Average the b0 images
# dwiextract dwi_den_preproc_unbiased.mif - -bzero | mrmath - mean mean_b0_processed.mif -axis 3

# # Convert b0 average and 5tt image to NIFTI for co-registration
# mrconvert mean_b0_processed.mif mean_b0_processed.nii.gz
# mrconvert 5tt_nocoreg.mif 5tt_nocoreg.nii.gz

# # Extract the first volume (gray matter) of the 5tt dataset
# fslroi 5tt_nocoreg.nii.gz 5tt_vol0.nii.gz 0 1

# # Use fsl to create a transformation matrix for co-registration between the tissue map and the b0 images 
# flirt -in mean_b0_processed.nii.gz -ref 5tt_vol0.nii.gz -interp nearestneighbour -dof 6 -omat diff2struct_fsl.mat

# # Convert back to format that mrtrix can read
# transformconvert diff2struct_fsl.mat mean_b0_processed.nii.gz 5tt_nocoreg.nii.gz flirt_import diff2struct_mrtrix.txt 

# # Co-register the anatomical image to the diffusion image
# mrtransform 5tt_nocoreg.mif -linear diff2struct_mrtrix.txt -inverse 5tt_coreg.mif

# # Create a seed region along the GM/WM boundary
# 5tt2gmwmi 5tt_coreg.mif gmwmSeed_coreg.mif


# ########################### STEP 4 ###################################
# #                                QC                                 #
# ######################################################################

# # --------------------------- QC for Step 1 --------------------------
# # View original diffusion data overlaid on top of the eddy-corrected data and colored in red
# # mrview dwi_den_preproc.mif -overlay.load raw_dwi.mif

# ### Corrupt slices 
# # dwi_post_eddy.eddy_outlier_map indicates whether a slice is an outlier (1) or not (0), because of too much motion, eddy currents, or something else.
# cd dwifslpreproc-tmp-*

# # Calculate the total number of slices by multiplying the number of slices for a single volume by the total number of volumes in the dataset.
# totalSlices=`mrinfo dwi.mif | grep Dimensions | awk '{print $6 * $8}'`

# # The total number of 1�s in the outlier map is then calculated, and the percentage of outlier slices is generated by dividing the number of outlier slices by the total number of slices. If this number is greater than 10 - i.e., if more than 10 percent of the slices are flagged as outliers - you should consider removing the subject from further analyses.
# totalOutliers=`awk '{ for(i=1;i<=NF;i++)sum+=$i } END { print sum }' dwi_post_eddy.eddy_outlier_map`

# echo "scale=5; ($totalOutliers / $totalSlices * 100)/1" | bc | tee ${SBJ}_percentageOutliers.txt 

# mv ${SBJ}_percentageOutliers.txt $QC_DIR/corrupt

# cd ..

# # --------------------------- QC for Step 2 --------------------------
# ### Brain mask 
# # mrview mask.mif -capture.folder $QC_DIR/mask -capture.prefix $SBJ -capture.grab

# ### Basis function
# # View the response functions for each tissue type (response_*.txt files in the QC folder). The WM function should flatten out at higher b-values, while the other tissues should remain spherical

# ### FOD estimation 
# # View the voxels used for FOD estimation (Blue=WM; Green=GM; Red=CSF)"
# # mrview dwi_den_preproc_unbiased.mif -overlay.load voxels.mif -capture.folder $QC_DIR/fod_voxels -capture.prefix $SBJ -capture.grab

# # Views the FODs overlaid on the tissue types (Blue=WM; Green=GM; Red=CSF)
# # mrview vf.mif -odf.load_sh wmfod.mif -capture.folder $QC_DIR/fod_overlay -capture.prefix $SBJ -capture.grab


# # --------------------------- QC for Step 3 --------------------------
# # Check alignment of the 5 tissue types before and after alignment (new alignment in red, old alignment in blue)
# # mrview dwi_den_preproc_unbiased.mif -overlay.load 5tt_nocoreg.mif -overlay.colourmap 2 -overlay.load 5tt_coreg.mif -overlay.colourmap 1 -capture.folder $QC_DIR/tissue_align -capture.prefix $SBJ -capture.grab

# # Check the seed region (should match up along the GM/WM boundary)
# # mrview dwi_den_preproc_unbiased.mif -overlay.load gmwmSeed_coreg.mif -capture.folder $QC_DIR/gm_wm -capture.prefix $SBJ -capture.grab
