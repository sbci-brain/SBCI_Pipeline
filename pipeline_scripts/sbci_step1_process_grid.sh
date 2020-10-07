#!/bin/bash

# load global options
source ${SBCI_CONFIG}

mkdir -p ${AVGDIR}

# convert freesurfer surfaces to vtk format
mris_convert ${REFDIR}/surf/lh.white_avg ${AVGDIR}/lh_white_avg.vtk
mris_convert ${REFDIR}/surf/rh.white_avg ${AVGDIR}/rh_white_avg.vtk
mris_convert ${REFDIR}/surf/lh.sphere.reg.avg ${AVGDIR}/lh_sphere_avg.vtk
mris_convert ${REFDIR}/surf/rh.sphere.reg.avg ${AVGDIR}/rh_sphere_avg.vtk
mris_convert ${REFDIR}/surf/lh.inflated_avg ${AVGDIR}/lh_inflated_avg.vtk
mris_convert ${REFDIR}/surf/rh.inflated_avg ${AVGDIR}/rh_inflated_avg.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_flip_surface.py ${AVGDIR}/lh_sphere_avg.vtk ${AVGDIR}/lh_sphere_avg_lps.vtk -x -y -f
scil_flip_surface.py ${AVGDIR}/rh_sphere_avg.vtk ${AVGDIR}/rh_sphere_avg_lps.vtk -x -y -f
scil_flip_surface.py ${AVGDIR}/lh_white_avg.vtk ${AVGDIR}/lh_white_avg_lps.vtk -x -y -f
scil_flip_surface.py ${AVGDIR}/rh_white_avg.vtk ${AVGDIR}/rh_white_avg_lps.vtk -x -y -f
scil_flip_surface.py ${AVGDIR}/lh_inflated_avg.vtk ${AVGDIR}/lh_inflated_avg_lps.vtk -x -y -f
scil_flip_surface.py ${AVGDIR}/rh_inflated_avg.vtk ${AVGDIR}/rh_inflated_avg_lps.vtk -x -y -f

# Step1) Sample from the white matter mesh to the required resolution
python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${AVGDIR}/lh_white_avg_lps.vtk \
       --output ${AVGDIR}/lh_white_avg_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${AVGDIR}/rh_white_avg_lps.vtk \
       --output ${AVGDIR}/rh_white_avg_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

# Step2) Downsample the white sphere mesh to the required resolution
python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${AVGDIR}/lh_sphere_avg_lps.vtk \
       --points ${AVGDIR}/lh_white_avg_ids_${RESOLUTION}.npz \
       --output ${AVGDIR}/lh_sphere_avg_${RESOLUTION}.vtk -f

python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${AVGDIR}/rh_sphere_avg_lps.vtk \
       --points ${AVGDIR}/rh_white_avg_ids_${RESOLUTION}.npz \
       --output ${AVGDIR}/rh_sphere_avg_${RESOLUTION}.vtk -f

# Step3) Generate a discrete mapping from the full resolution mesh to the downsampled mesh
python ${SCRIPT_PATH}/map_surfaces.py \
       --lh_surface_hi ${AVGDIR}/lh_sphere_avg_lps.vtk \
       --lh_surface_lo ${AVGDIR}/lh_sphere_avg_${RESOLUTION}.vtk \
       --rh_surface_hi ${AVGDIR}/rh_sphere_avg_lps.vtk \
       --rh_surface_lo ${AVGDIR}/rh_sphere_avg_${RESOLUTION}.vtk \
       --output ${AVGDIR}/mapping_avg_${RESOLUTION}.npz -f

# Step4) Generate meshes for visualisation
python ${SCRIPT_PATH}/downsample_mesh.py \
       --lh_surface ${AVGDIR}/lh_white_avg_lps.vtk \
       --rh_surface ${AVGDIR}/rh_white_avg_lps.vtk \
       --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
       --suffix _${RESOLUTION} -f

python ${SCRIPT_PATH}/downsample_mesh.py \
       --lh_surface ${AVGDIR}/lh_inflated_avg_lps.vtk \
       --rh_surface ${AVGDIR}/rh_inflated_avg_lps.vtk \
       --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
       --suffix _${RESOLUTION} -f

# Step4) Generate the grid to be used in concon
python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${AVGDIR}/lh_sphere_avg_${RESOLUTION}.vtk \
       --output ${AVGDIR}/tmp_lh_grid.m -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${AVGDIR}/rh_sphere_avg_${RESOLUTION}.vtk \
       --output ${AVGDIR}/tmp_rh_grid.m -f

python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${AVGDIR}/tmp_lh_grid.m --output ${AVGDIR}/lh_grid_avg_${RESOLUTION}.m -f
python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${AVGDIR}/tmp_rh_grid.m --output ${AVGDIR}/rh_grid_avg_${RESOLUTION}.m -f
python ${SCRIPT_PATH}/normalise_vtk.py --surface ${AVGDIR}/lh_sphere_avg_${RESOLUTION}.vtk --output ${AVGDIR}/lh_grid_avg_${RESOLUTION}.vtk -f
python ${SCRIPT_PATH}/normalise_vtk.py --surface ${AVGDIR}/rh_sphere_avg_${RESOLUTION}.vtk --output ${AVGDIR}/rh_grid_avg_${RESOLUTION}.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${AVGDIR}/lh_sphere_avg_lps.vtk \
       --output ${AVGDIR}/lh_sphere_avg_norm.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${AVGDIR}/rh_sphere_avg_lps.vtk \
       --output ${AVGDIR}/rh_sphere_avg_norm.vtk -f

rm ${AVGDIR}/tmp_lh_grid.m
rm ${AVGDIR}/tmp_rh_grid.m

#######################################
# LOOP THROUGH SELECTED PARCELLATIONS #
#######################################

for PARCELLATION in ${GROUP_PARCELLATIONS[*]}; do

  echo Processing Parcellation: ${PARCELLATION}
      
  # Step5) Calculate atlas' for the downsampled mesh
  python ${SCRIPT_PATH}/group_roi_vertices.py \
         --lh_annot ${REFDIR}/label/lh.${PARCELLATION}.annot \
         --rh_annot ${REFDIR}/label/rh.${PARCELLATION}.annot \
         --mesh ${AVGDIR}/mapping_avg_${RESOLUTION}.npz \
         --output ${AVGDIR}/${PARCELLATION}_avg_roi_${RESOLUTION}.npz \
         --matlab ${AVGDIR}/${PARCELLATION}_avg_roi_${RESOLUTION}.mat -f
  
  # Step6) Calculate mapping for the atlas of choice
  python ${SCRIPT_PATH}/calculate_roi_mapping.py \
         --lh_annot ${REFDIR}/label/lh.${PARCELLATION}.annot \
         --rh_annot ${REFDIR}/label/rh.${PARCELLATION}.annot \
         --output ${AVGDIR}/mapping_avg_${PARCELLATION}.npz -f
  
  # Step7) Calculate ordering for the downsampled mesh
  python ${SCRIPT_PATH}/group_roi_vertices.py \
         --lh_annot ${REFDIR}/label/lh.${PARCELLATION}.annot \
         --rh_annot ${REFDIR}/label/rh.${PARCELLATION}.annot \
         --mesh ${AVGDIR}/mapping_avg_${PARCELLATION}.npz \
         --output ${AVGDIR}/${PARCELLATION}_avg_roi.npz \
         --matlab ${AVGDIR}/${PARCELLATION}_avg_roi.mat -f

done
