#!/bin/bash

# This script:
# 1. prepares data for surface enhanced tractography (SET)
# 2. performs SET and combines with PFT tractography

# author: Martin Cole with thanks to Etienne St-Onge
# date: May 28, 2019

# TODO: add SRUN commands to appropriate tasks

##########################
## prepare data for SET ##
##########################
SRUN=srun

# intitial seed for RNG
RNG=0

# number of seeds to generate 
# for each hemisphere in 1000s
N_SEED=$1

# number of steps into the
# surface for surface flow
STEPS=$2

ID=${N_SEED}k_n${STEPS}

cd dwi_psc_connectome

mkdir set_${ID}
mkdir set_${ID}/preprocess

# convert freesurfer output to vtk
mris_convert --to-scanner structure/t1_freesurfer/surf/lh.pial set_${ID}/preprocess/lh.pial.vtk
mris_convert --to-scanner structure/t1_freesurfer/surf/rh.pial set_${ID}/preprocess/rh.pial.vtk
mris_convert --to-scanner structure/t1_freesurfer/surf/lh.white set_${ID}/preprocess/lh.white.vtk
mris_convert --to-scanner structure/t1_freesurfer/surf/rh.white set_${ID}/preprocess/rh.white.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_surface.py set_${ID}/preprocess/lh.pial.vtk --fx --fy --out_surface set_${ID}/preprocess/lh_pial_lps.vtk -f
scil_surface.py set_${ID}/preprocess/rh.pial.vtk --fx --fy --out_surface set_${ID}/preprocess/rh_pial_lps.vtk -f
scil_surface.py set_${ID}/preprocess/lh.white.vtk --fx --fy --out_surface set_${ID}/preprocess/lh_white_lps.vtk -f
scil_surface.py set_${ID}/preprocess/rh.white.vtk --fx --fy --out_surface set_${ID}/preprocess/rh_white_lps.vtk -f

# convert the parcellation file into nifti format
mri_convert structure/t1_freesurfer/mri/wmparc.mgz set_${ID}/preprocess/wmparc.nii.gz

###################################################################################
# create the brainstem and gray nuclei (inner) surfaces for tracts to flow through 
###################################################################################

# brainstem
scil_surface_from_volume.py set_${ID}/preprocess/wmparc.nii.gz \
        --out_surface set_${ID}/preprocess/brainstem.vtk --index 16 --opening 2 --smooth 2 --vox2vtk -f

## gray nuclei
scil_surface_from_volume.py set_${ID}/preprocess/wmparc.nii.gz \
        --out_surface set_${ID}/preprocess/gray_nuclei.vtk --index 9 10 11 12 13 17 18 27 48 49 50 51 52 53 54 59 \
        --opening 2  --smooth 2 --vox2vtk -f

#################
## perform SET ##
#################

mkdir set_${ID}/out_surf

# generate surface masks. removing the corpus callosum ensures that tracts are not cut short within that region.
scil_surface.py set_${ID}/preprocess/lh_white_lps.vtk -a structure/t1_freesurfer/label/lh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask --out_masked_vts set_${ID}/out_surf/lh_mask.npy -f
scil_surface.py set_${ID}/preprocess/rh_white_lps.vtk -a structure/t1_freesurfer/label/rh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask --out_masked_vts set_${ID}/out_surf/rh_mask.npy -f

# generate surface seeds (N_SEED per hemisphere). 
scil_surface_seeds.py set_${ID}/preprocess/lh_white_lps.vtk ${N_SEED}000 set_${ID}/out_surf/lh_seed_${N_SEED}k.npz \
        --vts_mask set_${ID}/out_surf/lh_mask.npy --random_number_generator ${RNG} --triangle_area_weighting -f
scil_surface_seeds.py set_${ID}/preprocess/rh_white_lps.vtk ${N_SEED}000 set_${ID}/out_surf/rh_seed_${N_SEED}k.npz \
        --vts_mask set_${ID}/out_surf/rh_mask.npy --random_number_generator ${RNG} --triangle_area_weighting -f

# smooth the white matter surface to help with surface flow generaration
scil_surface.py set_${ID}/preprocess/lh_white_lps.vtk --vts_mask set_${ID}/out_surf/lh_mask.npy \
        --smooth 2 --smooth_weight 2.0 --out_surface  set_${ID}/out_surf/lh_white_s2w2.vtk -f
scil_surface.py set_${ID}/preprocess/rh_white_lps.vtk --vts_mask set_${ID}/out_surf/rh_mask.npy \
        --smooth 2 --smooth_weight 2.0 --out_surface  set_${ID}/out_surf/rh_white_s2w2.vtk -f

##########################################################################################
# generate the surface flow: can set --nb_step 0 with --step_size 4 to see tractography 
# without surface flow. need to experiment to find good value of --nb_step for both young
# and old brains, likely somewhere between 50-100. --step_size is likely fine at 1, but 
# does affect speed of function - larger steps equal quicker run time.
##########################################################################################
scil_surface_flow.py set_${ID}/out_surf/lh_white_s2w2.vtk --vts_mask set_${ID}/out_surf/lh_mask.npy \
        --nb_step ${STEPS} --step_size 1 --out_surface set_${ID}/out_surf/lh_white_n${STEPS}s1.vtk \
        --out_tract set_${ID}/lh_flow_n${STEPS}s1.fib -f
scil_surface_flow.py set_${ID}/out_surf/rh_white_s2w2.vtk --vts_mask set_${ID}/out_surf/rh_mask.npy \
        --nb_step ${STEPS} --step_size 1 --out_surface set_${ID}/out_surf/rh_white_n${STEPS}s1.vtk \
        --out_tract set_${ID}/rh_flow_n${STEPS}s1.fib -f

# pft tracking from surface (left hemisphere)
scil_surface_pft_dipy.py diffusion/fodf/fodf.nii.gz \
        structure/map_include.nii.gz \
        structure/map_exclude.nii.gz \
        set_${ID}/out_surf/lh_white_n${STEPS}s1.vtk \
        set_${ID}/out_surf/lh_seed_${N_SEED}k.npz \
        set_${ID}/lh_${N_SEED}k.trk \
        --algo 'prob' \
        --step 0.2 --theta 20 \
        --sfthres 0.1 \
        --max_length 250 \
        --particles 15 --back 2 \
        --forward 1 -f \
        --compress 0.2

# pft tracking from surface (right hemisphere)
scil_surface_pft_dipy.py diffusion/fodf/fodf.nii.gz \
        structure/map_include.nii.gz \
        structure/map_exclude.nii.gz \
        set_${ID}/out_surf/rh_white_n${STEPS}s1.vtk \
        set_${ID}/out_surf/rh_seed_${N_SEED}k.npz \
        set_${ID}/rh_${N_SEED}k.trk \
        --algo 'prob' \
        --step 0.2 --theta 20 \
        --sfthres 0.1 \
        --max_length 250 \
        --particles 15 --back 2 \
        --forward 1 -f \
        --compress 0.2

# convert .trk to .fib and compute intersections
scil_convert_tractogram.py set_${ID}/lh_${N_SEED}k.trk set_${ID}/lh_${N_SEED}k.fib -f
scil_convert_tractogram.py set_${ID}/rh_${N_SEED}k.trk set_${ID}/rh_${N_SEED}k.fib -f

scil_surface_tractogram_filtering.py set_${ID}/lh_${N_SEED}k.fib set_${ID}/rh_${N_SEED}k.fib \
        --surfaces set_${ID}/out_surf/lh_white_n${STEPS}s1.vtk set_${ID}/out_surf/rh_white_n${STEPS}s1.vtk \
        --surfaces_masks set_${ID}/out_surf/lh_mask.npy set_${ID}/out_surf/rh_mask.npy \
        --outer_surfaces set_${ID}/preprocess/lh_pial_lps.vtk set_${ID}/preprocess/rh_pial_lps.vtk \
        --outer_masks set_${ID}/out_surf/lh_mask.npy set_${ID}/out_surf/rh_mask.npy \
        --inner_surfaces set_${ID}/preprocess/gray_nuclei.vtk set_${ID}/preprocess/brainstem.vtk \
        --output_intersections_info set_${ID}/intersections_info_pft_${N_SEED}000.txt \
        --output_intersections set_${ID}/intersections_pft_${N_SEED}k.npz \
        --only_endpoints --output_tractogram set_${ID}/cut_pft_${N_SEED}k.fib -f

# combine streamlines with flow
rm -f set_${ID}/set_pft_${N_SEED}k_n${STEPS}s1.fib

scil_surface_combine_flow.py set_${ID}/intersections_pft_${N_SEED}k.npz set_${ID}/cut_pft_${N_SEED}k.fib \
        set_${ID}/set_pft_${N_SEED}k_n${STEPS}s1.fib set_${ID}/lh_flow_n${STEPS}s1.fib set_${ID}/rh_flow_n${STEPS}s1.fib \
        --surfaces set_${ID}/out_surf/lh_white_n${STEPS}s1.vtk set_${ID}/out_surf/rh_white_n${STEPS}s1.vtk 

#######################
## quality assurance ##
#######################

# using MI-Brain, check that:
# 1. *_pial.vtk, *_white.vtk, brainstem.vtk, gray_nuclei.vtk are aligned with original t1.nii.gz

# visualise masked sufaces, checking that the corpus collosum is in black:
# 1. scil_surface.py set/preprocess/lh_white_lps.vtk --vts_mask set/out_surf/lh_mask.npy -v
# 2. scil_surface.py set/preprocess/rh_white_lps.vtk --vts_mask set/out_surf/rh_mask.npy -v

# visualise seeds, checking the surface orientation:
# 1. scil_visualize_surface_seeds.py set/preprocess/lh_white_lps.vtk set/out_surf/lh_seed_${N_SEED}k.npz -n 1
# 2. scil_visualize_surface_seeds.py set/preprocess/rh_white_lps.vtk set/out_surf/rh_seed_${N_SEED}k.npz -n 1

# using MI-Brain, check that *_flow_n10s1.fib goes from *_white_s2w2.vtk to *_white_n10s1.vtk

# visualise intersections:
# scil_visualize_surface_intersections.py set/intersections_pft_${N_SEED}k.npz \
#        set/out_surf/lh_white_n10s1.vtk set/out_surf/rh_white_n10s1.vtk

# using MI-Brain, check that cut_pft_${N_SEED}k.fib goes from *_white_s2w2.vtk to *_white_n10s1.vtk
