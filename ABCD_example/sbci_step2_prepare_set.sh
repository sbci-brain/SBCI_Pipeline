#!/bin/bash

# code for SBCI  

# author:Zhengwu Zhang (based on set-nextflow)
# date: Aug. 2020

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

echo "Begin processing SET preparation: $(date)"

echo ${ROIS[@]}

cd dwi_pipeline

##########################
## prepare data for SET ##
##########################

mkdir -p set/preprocess

cp structure/t1_freesurfer/label/lh*a2009s.annot set/preprocess/
cp structure/t1_freesurfer/label/rh*a2009s.annot set/preprocess/

cp structure/t1_freesurfer/surf/lh.pial set/preprocess/
cp structure/t1_freesurfer/surf/rh.pial set/preprocess/

cp structure/t1_freesurfer/surf/lh.white set/preprocess/
cp structure/t1_freesurfer/surf/rh.white set/preprocess/
cp structure/t1_freesurfer/mri/wmparc.mgz set/preprocess/

cp structure/aparc.a2009s+aseg.nii.gz set/preprocess/

# convert volume 
# ET suggested to run these command lines (mri_convert) in the freesurfer folder;
# since mris_convert might need other files to conduct the transformation
mri_convert set/preprocess/wmparc.mgz set/preprocess/labels.nii.gz

mrconvert set/preprocess/labels.nii.gz -stride 1,2,3 set/preprocess/labels.nii.gz -force

# surface preprocessing
# from ET: run this in freesurfer folder
mris_convert --to-scanner set/preprocess/lh.pial set/preprocess/lh.pial.vtk
mris_convert --to-scanner set/preprocess/rh.pial set/preprocess/rh.pial.vtk
mris_convert --to-scanner set/preprocess/lh.white set/preprocess/lh.white.vtk
mris_convert --to-scanner set/preprocess/rh.white set/preprocess/rh.white.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_flip_surface.py set/preprocess/lh.pial.vtk set/preprocess/lh_pial_lps.vtk -x -y
scil_flip_surface.py set/preprocess/rh.pial.vtk set/preprocess/rh_pial_lps.vtk -x -y
scil_flip_surface.py set/preprocess/lh.white.vtk set/preprocess/lh_white_lps.vtk -x -y
scil_flip_surface.py set/preprocess/rh.white.vtk set/preprocess/rh_white_lps.vtk -x -y

#surface for surface labels; (check this, maybe use xl_white.vkt); confirmed with ET, it's okay to use either surfaces.
scil_surface.py set/preprocess/lh_white_lps.vtk --annot set/preprocess/lh.aparc.a2009s.annot --save_vts_label  set/preprocess/lh_labels.npy -f
scil_surface.py set/preprocess/rh_white_lps.vtk --annot set/preprocess/rh.aparc.a2009s.annot --save_vts_label  set/preprocess/rh_labels.npy -f

scil_surface.py set/preprocess/lh_white_lps.vtk --vts_val 0.0 --save_vts_mask  set/preprocess/lh_zero_mask.npy -f
scil_surface.py set/preprocess/rh_white_lps.vtk --vts_val 0.0 --save_vts_mask  set/preprocess/rh_zero_mask.npy -f

# Generate ROIs in VTK
ROI_SURFACES=""
ROI_FLOW_MASKS=""
ROI_INTERSECTIONS_MASKS=""
ROI_SEED_MASKS=""

for ROI in ${ROIS[*]}; do
  printf -v NAME "%05g" $ROI

  scil_surface_from_volume.py set/preprocess/labels.nii.gz \
                set/preprocess/roi_${NAME}.vtk \
                --index ${ROI} \
                --closing 2 \
                --opening 2 \
                --smooth 2 \
                --vox2vtk --fill --max_label -f

  # roi mask for ROI seeding
  # intersection is for starting or stopping streamlines;
  # intersection does not include subcortical surfaces

  # put 0 everywhere; don't apply flow to this ROI
  scil_surface.py set/preprocess/roi_${NAME}.vtk \
		--vts_val 0.0 \
		--save_vts_mask set/preprocess/${NAME}_flow_mask.npy -f

  # streamline can stop any part in this ROI
  scil_surface.py set/preprocess/roi_${NAME}.vtk \
		--vts_val 1.0 \
		--save_vts_mask set/preprocess/${NAME}_intersections_mask.npy -f
  
  # at each vertices check fa value and binarise 0 if < 0.15, 1 otherwise
  scil_surface_map_from_volume.py set/preprocess/roi_${NAME}.vtk \
		diffusion/dti/fa.nii.gz \
                set/preprocess/${NAME}_seed_mask.npy \
		--binarize --binarize_value 0.15 -f

  ROI_SURFACES="$ROI_SURFACES set/preprocess/roi_${NAME}.vtk"
  ROI_FLOW_MASKS="$ROI_FLOW_MASKS set/preprocess/${NAME}_flow_mask.npy"
  ROI_INTERSECTIONS_MASKS="$ROI_INTERSECTIONS_MASKS set/preprocess/${NAME}_intersections_mask.npy"
  ROI_SEED_MASKS="$ROI_SEED_MASKS set/preprocess/${NAME}_seed_mask.npy"
done


# surf mask for masks_for_concatenate for surface flow
# some ROIs [6 7 8 9 10 35 42 67] were removed 
scil_surface.py set/preprocess/lh.white.vtk --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
        --save_vts_mask set/preprocess/lh_flow_mask.npy -f

scil_surface.py set/preprocess/rh.white.vtk --annot set/preprocess/rh.aparc.a2009s.annot \
        -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
        --save_vts_mask set/preprocess/rh_flow_mask.npy -f

scil_surface.py set/preprocess/lh.white.vtk --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/lh_seed_mask.npy -f

scil_surface.py set/preprocess/rh.white.vtk --annot set/preprocess/rh.aparc.a2009s.annot\
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/rh_seed_mask.npy -f

scil_surface.py set/preprocess/lh.white.vtk --annot set/preprocess/lh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/lh_intersections_mask.npy -f

scil_surface.py set/preprocess/rh.white.vtk --annot set/preprocess/rh.aparc.a2009s.annot \
        -i -1 0 --inverse_mask \
        --save_vts_mask set/preprocess/rh_intersections_mask.npy -f

mkdir set/out_surf

# concatenate surface
# order is important for inner surfaces for connectivity 
# lh_white... is called base surface
scil_concatenate_surfaces.py set/preprocess/lh_white_lps.vtk set/preprocess/rh_white_lps.vtk \
        --outer_surfaces set/preprocess/lh_pial_lps.vtk set/preprocess/rh_pial_lps.vtk \
        --inner_surfaces ${ROI_SURFACES} \
        --out_surface_id set/preprocess/surfaces_id.npy \
        --out_surface_type_map set/preprocess/surfaces_type.npy \
        --out_concatenated_surface set/out_surf/surfaces.vtk -f

#concatenate mask
scil_concatenate_surfaces_map.py set/preprocess/lh_flow_mask.npy set/preprocess/rh_flow_mask.npy \
        --outer_surfaces_map set/preprocess/lh_zero_mask.npy set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_FLOW_MASKS} \
        --out_map set/out_surf/flow_mask.npy -f

scil_concatenate_surfaces_map.py set/preprocess/lh_seed_mask.npy set/preprocess/rh_seed_mask.npy \
        --outer_surfaces_map set/preprocess/lh_zero_mask.npy set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_SEED_MASKS} \
        --out_map set/out_surf/seed_mask.npy -f

scil_concatenate_surfaces_map.py set/preprocess/lh_intersections_mask.npy set/preprocess/rh_intersections_mask.npy \
        --outer_surfaces_map set/preprocess/lh_intersections_mask.npy set/preprocess/rh_intersections_mask.npy \
        --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
        --out_map set/out_surf/intersections_mask.npy -f

# visulize surface and mask;
#scil_visualize_set_output.py set/out_surf/surfaces.vtk --surfaces_id set/preprocess/surfaces_id.npy --indices 1 2
#scil_decatenate_surfaces  -- for decatenating surfaces

# concatenate label for connectivity
scil_concatenate_surfaces_map.py set/preprocess/lh_labels.npy set/preprocess/rh_labels.npy \
        --outer_surfaces_map set/preprocess/lh_zero_mask.npy set/preprocess/rh_zero_mask.npy \
        --inner_surfaces_map ${ROI_INTERSECTIONS_MASKS} \
        --out_map set/out_surf/unique_id.npy \
        --unique_id \
        --out_id_map set/out_surf/unique_id.txt \
        --indices_to_remove -1 0 -f

# transform surfaces and ROIs
# for HCP we don't need to do this

# Surface_Flow 
scil_smooth_surface.py set/out_surf/surfaces.vtk set/out_surf/smoothed.vtk \
            --vts_mask set/out_surf/flow_mask.npy \
            --nb_steps 2 \
            --step_size 2.0 -f

# can be 75 for HCP, maybe 100 for low resolution data
scil_surface_flow.py set/out_surf/smoothed.vtk set/out_surf/flow_${STEPS}_1.vtk \
            --vts_mask set/out_surf/flow_mask.npy \
            --nb_step ${STEPS} \
            --step_size 1.0 \
            --gaussian_threshold 0.2 \
            --angle_threshold 2 \
            --out_flow set/out_surf/flow_${STEPS}_1.hdf5 -f

# Surface_Seeding_Map
# flow_${STEPS}_1 or surfaces can be used; the output is set/out_surf/seeding_map_0.npy; 
# weighting based on triangle area
scil_surface_seed_map.py set/out_surf/surfaces.vtk set/out_surf/seeding_map_0.npy \
        --vts_mask set/out_surf/seed_mask.npy \
        --triangle_area_weighting -f

cd ..

echo "Finished processing SET preparation: $(date)"
