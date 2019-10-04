#fiber tracking
SRUN=srun
DatasetNAME=csvd

#set PSC path 
#### change to your own path
export PSC_PATH=path/to/PSC_Pipeline


mkdir streamlines
#streamline tracking - faster version
scil_compute_pft_dipy.py diffusion/fodf/fodf.nii.gz structure/seeding_mask.nii.gz structure/map_include.nii.gz structure/map_exclude.nii.gz\
            streamlines/full_interface_prob_pft.trk --algo 'prob'\
            --npv 20 --step 0.2 --theta 20\
            --sfthres 0.1 --sfthres_init 0.5\
            --min_length 20 --max_length 250\
            --particles 15 --back 2\
            --forward 1 -f \
            --compress 0.2

# remove invalid streamlines
scil_remove_invalid_coordinates_from_streamlines.py --gnc --fnc \
streamlines/full_interface_prob_pft.trk structure/t1_warped.nii.gz streamlines/full_interface_prob_pft_invcoord.trk -f


########################### connectivity ###########################
# get connectivity matrix
mkdir connectome
cd connectome

###### extract the streamline connectivity matrix for both cortical and subcortical 

#desikan atlas
# extract connectivity matrices, get the dilation of images for Desikan
$SRUN extraction_sccm_withfeatures_cortical.py ../streamlines/full_interface_prob_pft_invcoord.trk ../diffusion/dti/fa.nii.gz ../diffusion/dti/md.nii.gz ../structure/wmparc_warped_label.nii.gz $PSC_PATH/connectome/Desikan_ROI.txt $PSC_PATH/connectome/FreeSurferColorLUT.txt $DatasetNAME 20 240 1 2 0.6 desikan
$SRUN extraction_sccm_withfeatures_subcortical.py ../streamlines/full_interface_prob_pft_invcoord.trk ../diffusion/dti/fa.nii.gz ../diffusion/dti/md.nii.gz ../structure/wmparc_warped_label.nii.gz desikan_dilated_labels.nii.gz  $PSC_PATH/connectome/Subcortical_ROI.txt $PSC_PATH/connectome/FreeSurferColorLUT.txt $DatasetNAME 20 240 0.6 desikan


# Destreoux
$SRUN extraction_sccm_withfeatures_cortical.py ../streamlines/full_interface_prob_pft_invcoord.trk ../diffusion/dti/fa.nii.gz ../diffusion/dti/md.nii.gz ../structure/aparc.a2009s+aseg_warped_label.nii.gz $PSC_PATH/connectome/Destrieux_ROI.txt $PSC_PATH/connectome/FreeSurferColorLUT.txt $DatasetNAME 20 240 1 2 0.6 destrieux
$SRUN extraction_sccm_withfeatures_subcortical.py ../streamlines/full_interface_prob_pft_invcoord.trk ../diffusion/dti/fa.nii.gz ../diffusion/dti/md.nii.gz ../structure/aparc.a2009s+aseg_warped_label.nii.gz destrieux_dilated_labels.nii.gz  $PSC_PATH/connectome/Subcortical_ROI.txt $PSC_PATH/connectome/FreeSurferColorLUT.txt $DatasetNAME 20 240 0.6 destrieux

cd ..

#remove files that we don't want to keep
rm streamlines/full_interface_prob_pft.trk

cd ..
cd ..

#rm HCP_destrieux_partbrain_subcort_cm_processed_sfa_100.mat
#rm HCP_destrieux_partbrain_cm_processed_smd_100.mat
#rm HCP_destrieux_partbrain_subcort_cm_streamlines.mat

#rm HCP_desikan_partbrain_subcort_cm_processed_sfa_100.mat
#rm HCP_desikan_partbrain_cm_processed_smd_100.mat]
#rm HCP_desikan_partbrain_subcort_cm_streamlines.mat

