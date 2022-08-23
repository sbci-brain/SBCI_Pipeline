#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

# fiber tracking
cd dwi_pipeline
mkdir psc_streamlines

cd structure

# compute pft maps
scil_compute_maps_for_particle_filter_tracking.py map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz -t 0.05 --interface interface_005.nii.gz -f

# dilation
seeding_map_dilation.py interface_005.nii.gz map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz --output_interface interface.nii.gz -t 0.05
scil_count_non_zero_voxels.py interface.nii.gz -o interface_count.txt
mv interface.nii.gz seeding_mask.nii.gz

cd ..

# streamline tracking - faster version
scil_compute_pft_dipy.py diffusion/fodf/fodf.nii.gz \
            structure/seeding_mask.nii.gz \
            structure/map_include.nii.gz \
            structure/map_exclude.nii.gz \
            psc_streamlines/full_interface_prob_pft.trk \
            --algo 'prob' --npv 20 --step 0.2 --theta 20 \
            --sfthres 0.1 --sfthres_init 0.5 \
            --min_length 20 --max_length 250 \
            --particles 15 --back 2 \
            --forward 1 --compress 0.2 -f

# remove invalid streamlines
scil_remove_invalid_coordinates_from_streamlines.py --gnc --fnc \
            psc_streamlines/full_interface_prob_pft.trk \
            structure/t1_warped.nii.gz \
            psc_streamlines/full_interface_prob_pft_invcoord.trk -f


########################### connectivity ###########################
# get connectivity matrix
mkdir -p psc_connectome
cd psc_connectome

###### extract the streamline connectivity matrix for both cortical and subcortical 

# Desikan atlas
# extract connectivity matrices, get the dilation of images for Desikan
extraction_sccm_withfeatures_cortical.py ../psc_streamlines/full_interface_prob_pft_invcoord.trk \
            ../diffusion/dti/fa.nii.gz \
            ../diffusion/dti/md.nii.gz \
            ../structure/wmparc_warped_label.nii.gz \
            ${PSC_PATH}/connectome/Desikan_ROI.txt \
            ${PSC_PATH}/connectome/FreeSurferColorLUT.txt \
            ${DATASET_NAME} 20 240 1 2 0.6 desikan

extraction_sccm_withfeatures_subcortical.py ../psc_streamlines/full_interface_prob_pft_invcoord.trk \
            ../diffusion/dti/fa.nii.gz \
            ../diffusion/dti/md.nii.gz \
            ../structure/wmparc_warped_label.nii.gz \
            desikan_dilated_labels.nii.gz \
            ${PSC_PATH}/connectome/Subcortical_ROI.txt \
            ${PSC_PATH}/connectome/FreeSurferColorLUT.txt \
            ${DATASET_NAME} 20 240 0.6 desikan


# Destreoux
extraction_sccm_withfeatures_cortical.py ../psc_streamlines/full_interface_prob_pft_invcoord.trk \
            ../diffusion/dti/fa.nii.gz \
            ../diffusion/dti/md.nii.gz \
            ../structure/aparc.a2009s+aseg_warped_label.nii.gz \
            ${PSC_PATH}/connectome/Destrieux_ROI.txt \
            ${PSC_PATH}/connectome/FreeSurferColorLUT.txt \
            ${DATASET_NAME} 20 240 1 2 0.6 destrieux

extraction_sccm_withfeatures_subcortical.py ../psc_streamlines/full_interface_prob_pft_invcoord.trk \
            ../diffusion/dti/fa.nii.gz \
            ../diffusion/dti/md.nii.gz \
            ../structure/aparc.a2009s+aseg_warped_label.nii.gz \
            destrieux_dilated_labels.nii.gz \
            ${PSC_PATH}/connectome/Subcortical_ROI.txt \
            ${PSC_PATH}/connectome/FreeSurferColorLUT.txt \
            ${DATASET_NAME} 20 240 0.6 destrieux

cd ..

#remove files that we don't want to keep
rm psc_streamlines/full_interface_prob_pft.trk

cd ..
