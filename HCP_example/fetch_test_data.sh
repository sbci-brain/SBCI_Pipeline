# Downloads unprocessed data from the HCP for a sample subject

# Directory structure:
# ./raw_data/Functional/SUBJECT/unprocessed/*
# ./raw_data/Diffusion/SUBJECT/T1w/*

# the subject to download
SUBJECT=103818

mkdir -p raw_data/Functional
mkdir -p raw_data/Diffusion

########################
#### DIFFUSION DATA ####
########################
cd raw_data/Diffusion/ 

mkdir -p ${SUBJECT}/T1w/Diffusion
cd ${SUBJECT}

aws s3 cp --recursive s3://hcp-openaccess/HCP_1200/${SUBJECT}/T1w/Diffusion ./T1w/Diffusion/
aws s3 cp s3://hcp-openaccess/HCP_1200/${SUBJECT}/T1w/T1w_acpc_dc_restore_1.25.nii.gz ./T1w/

#########################
#### FUNCTIONAL DATA ####
#########################
cd ../../Functional

mkdir -p ${SUBJECT}/unprocessed/3T/rfMRI_REST1_LR
mkdir -p ${SUBJECT}/unprocessed/3T/rfMRI_REST1_RL
mkdir -p ${SUBJECT}/unprocessed/3T/rfMRI_REST2_LR
mkdir -p ${SUBJECT}/unprocessed/3T/rfMRI_REST2_RL

cd ${SUBJECT}/unprocessed/3T

aws s3 cp s3://hcp-openaccess/HCP_1200/${SUBJECT}/unprocessed/3T/rfMRI_REST1_LR/103818_3T_rfMRI_REST1_LR.nii.gz ./rfMRI_REST1_LR/
aws s3 cp s3://hcp-openaccess/HCP_1200/${SUBJECT}/unprocessed/3T/rfMRI_REST1_RL/103818_3T_rfMRI_REST1_RL.nii.gz ./rfMRI_REST1_RL/
aws s3 cp s3://hcp-openaccess/HCP_1200/${SUBJECT}/unprocessed/3T/rfMRI_REST2_LR/103818_3T_rfMRI_REST2_LR.nii.gz ./rfMRI_REST2_LR/
aws s3 cp s3://hcp-openaccess/HCP_1200/${SUBJECT}/unprocessed/3T/rfMRI_REST2_RL/103818_3T_rfMRI_REST2_RL.nii.gz ./rfMRI_REST2_RL/

# return to the initial folder
cd ../../../../../
