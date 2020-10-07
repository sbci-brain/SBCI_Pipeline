# This script is for two things:
# 1. segment t1 image
# 2. reconstruct fodf for tracking

# author: Zhengwu Zhang
# date: Mar. 23, 2017

# Updated  for SBCI by Martin Cole

#########################################################  
####### t1 preprocessing - get ready for tracking #######
######################################################### 

cd structure

# segment
fast -t 1 -n 3 -H 0.1 -I 4 -l 20.0 -g -o t1_brain.nii.gz t1_warped.nii.gz
mv t1_brain_seg_2.nii.gz mask_wm.nii.gz
mv t1_brain_seg_1.nii.gz mask_gm.nii.gz
mv t1_brain_seg_0.nii.gz mask_csf.nii.gz
mv t1_brain_pve_2.nii.gz map_wm.nii.gz
mv t1_brain_pve_1.nii.gz map_gm.nii.gz
mv t1_brain_pve_0.nii.gz map_csf.nii.gz

# compute pft maps
scil_compute_maps_for_particle_filter_tracking.py map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz --interface interface.nii.gz -f

cd ..

##########################################################  
####### dwi preprocessing - get ready for tracking #######
########################################################## 

# processe dMRI image
cd diffusion

# compute FRF
scil_compute_ssst_frf.py dwi_fodf.nii.gz fodf.bval fodf.bvec frf.txt \
	--mask b0_mask_resampled.nii.gz \
        --fa 0.7 --min_fa 0.5 --min_nvox 300 --roi_radius 20

# compute fodf and fodf metrics
mkdir fodf

scil_compute_fodf.py dwi_fodf.nii.gz fodf.bval fodf.bvec frf.txt --sh_order 8 \
 --force_b0_threshold --mask b0_mask_resampled.nii.gz \
 --fodf fodf/fodf.nii.gz --peaks fodf/peaks.nii.gz \
 --peak_indices fodf/peak_indices.nii.gz --processes 1

scil_compute_fodf_max_in_ventricles.py fodf/fodf.nii.gz dti/fa.nii.gz dti/md.nii.gz \
        --max_value_output fodf/ventricles_fodf_max_value.txt -f

a_threshold=$(echo 2*$(cat fodf/ventricles_fodf_max_value.txt)|bc)

scil_compute_fodf_metrics.py fodf/fodf.nii.gz ${a_threshold} \
        --mask b0_mask_resampled.nii.gz --afd fodf/afd_max.nii.gz \
        --afd_total fodf/afd_total.nii.gz --afd_sum fodf/afd_sum.nii.gz \
        --nufo fodf/nufo.nii.gz -f

# get out the folder
cd ..

