#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

echo "Begin processing SBCI grid: $(date)"
mkdir -p ${OUTPUT_PATH}

if [ -z ${REFDIR+x} ]; then 
    REFDIR=${SBCI_PATH}/integrated_pipeline/fsaverage
fi

if [ -z ${SCRIPT_PATH+x} ]; then 
    SCRIPT_PATH=${SBCI_PATH}/scripts
fi

# convert freesurfer surfaces to vtk format
mris_convert ${REFDIR}/surf/lh.white_avg ${OUTPUT_PATH}/lh_white_avg.vtk
mris_convert ${REFDIR}/surf/rh.white_avg ${OUTPUT_PATH}/rh_white_avg.vtk
mris_convert ${REFDIR}/surf/lh.sphere.reg.avg ${OUTPUT_PATH}/lh_sphere_avg.vtk
mris_convert ${REFDIR}/surf/rh.sphere.reg.avg ${OUTPUT_PATH}/rh_sphere_avg.vtk
mris_convert ${REFDIR}/surf/lh.inflated_avg ${OUTPUT_PATH}/lh_inflated_avg.vtk
mris_convert ${REFDIR}/surf/rh.inflated_avg ${OUTPUT_PATH}/rh_inflated_avg.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_flip_surface.py ${OUTPUT_PATH}/lh_sphere_avg.vtk ${OUTPUT_PATH}/lh_sphere_avg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUT_PATH}/rh_sphere_avg.vtk ${OUTPUT_PATH}/rh_sphere_avg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUT_PATH}/lh_white_avg.vtk ${OUTPUT_PATH}/lh_white_avg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUT_PATH}/rh_white_avg.vtk ${OUTPUT_PATH}/rh_white_avg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUT_PATH}/lh_inflated_avg.vtk ${OUTPUT_PATH}/lh_inflated_avg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUT_PATH}/rh_inflated_avg.vtk ${OUTPUT_PATH}/rh_inflated_avg_lps.vtk -x -y -f

## Step1) Sample from the white matter mesh to the required resolution
python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${OUTPUT_PATH}/lh_white_avg_lps.vtk \
       --output ${OUTPUT_PATH}/lh_white_avg_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${OUTPUT_PATH}/rh_white_avg_lps.vtk \
       --output ${OUTPUT_PATH}/rh_white_avg_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

# Step2) Downsample the white sphere mesh to the required resolution
python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${OUTPUT_PATH}/lh_sphere_avg_lps.vtk \
       --points ${OUTPUT_PATH}/lh_white_avg_ids_${RESOLUTION}.npz \
       --output ${OUTPUT_PATH}/lh_sphere_avg_${RESOLUTION}.vtk -f

python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${OUTPUT_PATH}/rh_sphere_avg_lps.vtk \
       --points ${OUTPUT_PATH}/rh_white_avg_ids_${RESOLUTION}.npz \
       --output ${OUTPUT_PATH}/rh_sphere_avg_${RESOLUTION}.vtk -f

# Step3) Generate a discrete mapping from the full resolution mesh to the downsampled mesh
python ${SCRIPT_PATH}/map_surfaces.py \
       --lh_surface_hi ${OUTPUT_PATH}/lh_sphere_avg_lps.vtk \
       --lh_surface_lo ${OUTPUT_PATH}/lh_sphere_avg_${RESOLUTION}.vtk \
       --rh_surface_hi ${OUTPUT_PATH}/rh_sphere_avg_lps.vtk \
       --rh_surface_lo ${OUTPUT_PATH}/rh_sphere_avg_${RESOLUTION}.vtk \
       --matlab_output ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.mat \
       --output ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz -f

# Step4) Generate meshes for visualisation
python ${SCRIPT_PATH}/downsample_mesh.py \
       --lh_surface ${OUTPUT_PATH}/lh_white_avg_lps.vtk \
       --rh_surface ${OUTPUT_PATH}/rh_white_avg_lps.vtk \
       --mesh ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz \
       --suffix _${RESOLUTION} -f

python ${SCRIPT_PATH}/downsample_mesh.py \
       --lh_surface ${OUTPUT_PATH}/lh_inflated_avg_lps.vtk \
       --rh_surface ${OUTPUT_PATH}/rh_inflated_avg_lps.vtk \
       --mesh ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz \
       --suffix _${RESOLUTION} -f

# Step4) Generate the grid to be used in concon
python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUT_PATH}/lh_sphere_avg_${RESOLUTION}.vtk \
       --output ${OUTPUT_PATH}/tmp_lh_grid.m -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUT_PATH}/rh_sphere_avg_${RESOLUTION}.vtk \
       --output ${OUTPUT_PATH}/tmp_rh_grid.m -f

python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUT_PATH}/tmp_lh_grid.m --output ${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.m -f
python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUT_PATH}/tmp_rh_grid.m --output ${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.m -f
python ${SCRIPT_PATH}/normalise_vtk.py --surface ${OUTPUT_PATH}/lh_sphere_avg_${RESOLUTION}.vtk --output ${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.vtk -f
python ${SCRIPT_PATH}/normalise_vtk.py --surface ${OUTPUT_PATH}/rh_sphere_avg_${RESOLUTION}.vtk --output ${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${OUTPUT_PATH}/lh_sphere_avg_lps.vtk \
       --output ${OUTPUT_PATH}/lh_sphere_avg_norm.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${OUTPUT_PATH}/rh_sphere_avg_lps.vtk \
       --output ${OUTPUT_PATH}/rh_sphere_avg_norm.vtk -f

rm ${OUTPUT_PATH}/tmp_lh_grid.m
rm ${OUTPUT_PATH}/tmp_rh_grid.m

# Step5) Generate coordinates and adjacency matrix files for grid
python ${SCRIPT_PATH}/get_coords.py --lh_surface ${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.vtk --rh_surface ${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.vtk --output ${OUTPUT_PATH}/grid_coords_${RESOLUTION}.mat -f
python ${SCRIPT_PATH}/get_coords.py --lh_surface ${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.vtk --rh_surface ${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.vtk --output ${OUTPUT_PATH}/grid_coords_${RESOLUTION}.npz -f
python ${SCRIPT_PATH}/get_adjacency_matrix.py --lh_surface ${OUTPUT_PATH}/lh_grid_avg_${RESOLUTION}.vtk --rh_surface ${OUTPUT_PATH}/rh_grid_avg_${RESOLUTION}.vtk --output ${OUTPUT_PATH}/adjacency_${RESOLUTION}.mat -f

########################################
# LOOP THROUGH AVAILABLE PARCELLATIONS #
########################################

GROUP_PARCELLATIONS=($(ls ${REFDIR}/label/lh.*.annot))

for PARCELLATION_FILE in ${GROUP_PARCELLATIONS[*]}; do

  PARCELLATION=${PARCELLATION_FILE##*lh.}
  PARCELLATION=${PARCELLATION%*.annot}

  if [ -f "${REFDIR}/label/rh.${PARCELLATION}.annot" ]; then

    echo Processing Parcellation: ${PARCELLATION}
        
    # Step6) Calculate atlas' for the downsampled mesh
    python ${SCRIPT_PATH}/group_roi_vertices.py \
           --lh_annot ${REFDIR}/label/lh.${PARCELLATION}.annot \
           --rh_annot ${REFDIR}/label/rh.${PARCELLATION}.annot \
           --mesh ${OUTPUT_PATH}/mapping_avg_${RESOLUTION}.npz \
           --output ${OUTPUT_PATH}/${PARCELLATION}_avg_roi_${RESOLUTION}.npz \
           --matlab ${OUTPUT_PATH}/${PARCELLATION}_avg_roi_${RESOLUTION}.mat -f

  fi
done

echo "Finished processing SBCI grid: $(date)"
