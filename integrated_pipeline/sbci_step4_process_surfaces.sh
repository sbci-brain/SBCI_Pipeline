#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

OUTPUTDIR=dwi_pipeline/sbci_connectome
SCDIR=dwi_pipeline/structure/t1_freesurfer

echo "Begin processing SBCI surfaces: $(date)"
mkdir -p ${OUTPUTDIR}

# create .vtk meshes
mris_convert ${SCDIR}/surf/lh.sphere ${OUTPUTDIR}/lh_sphere.vtk
mris_convert ${SCDIR}/surf/rh.sphere ${OUTPUTDIR}/rh_sphere.vtk
mris_convert ${SCDIR}/surf/lh.white ${OUTPUTDIR}/lh_white.vtk
mris_convert ${SCDIR}/surf/rh.white ${OUTPUTDIR}/rh_white.vtk
mris_convert ${SCDIR}/surf/lh.inflated ${OUTPUTDIR}/lh_inflated.vtk
mris_convert ${SCDIR}/surf/rh.inflated ${OUTPUTDIR}/rh_inflated.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_flip_surface.py ${OUTPUTDIR}/lh_sphere.vtk ${OUTPUTDIR}/lh_sphere_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/rh_sphere.vtk ${OUTPUTDIR}/rh_sphere_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/lh_white.vtk ${OUTPUTDIR}/lh_white_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/rh_white.vtk ${OUTPUTDIR}/rh_white_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/lh_inflated.vtk ${OUTPUTDIR}/lh_inflated_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/rh_inflated.vtk ${OUTPUTDIR}/rh_inflated_lps.vtk -x -y -f

mris_convert ${SCDIR}/surf/lh.sphere.reg ${OUTPUTDIR}/lh_sphere_reg.vtk
mris_convert ${SCDIR}/surf/rh.sphere.reg ${OUTPUTDIR}/rh_sphere_reg.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_flip_surface.py ${OUTPUTDIR}/lh_sphere_reg.vtk ${OUTPUTDIR}/lh_sphere_reg_lps.vtk -x -y -f
scil_flip_surface.py ${OUTPUTDIR}/rh_sphere_reg.vtk ${OUTPUTDIR}/rh_sphere_reg_lps.vtk -x -y -f

# normalize spherical meshes to have radius 1
python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${OUTPUTDIR}/lh_sphere_reg_lps.vtk \
       --output ${OUTPUTDIR}/lh_sphere_reg_lps_norm.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${OUTPUTDIR}/rh_sphere_reg_lps.vtk \
       --output ${OUTPUTDIR}/rh_sphere_reg_lps_norm.vtk -f

python ${SCRIPT_PATH}/get_coords.py --lh_surface ${OUTPUTDIR}/lh_sphere_reg_lps_norm.vtk --rh_surface ${OUTPUTDIR}/rh_sphere_reg_lps_norm.vtk --output ${OUTPUTDIR}/subject_coords.npz -f

# Step1) Sample from the white matter mesh to the required resolution
python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${OUTPUTDIR}/lh_white_lps.vtk \
       --output ${OUTPUTDIR}/lh_white_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

python ${SCRIPT_PATH}/sample_surface.py \
       --surface ${OUTPUTDIR}/rh_white_lps.vtk \
       --output ${OUTPUTDIR}/rh_white_ids_${RESOLUTION}.npz \
       --reduction ${RESOLUTION} -f

# Step2) Downsample the white sphere mesh to the required resolution
python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${OUTPUTDIR}/lh_sphere_lps.vtk \
       --points ${OUTPUTDIR}/lh_white_ids_${RESOLUTION}.npz \
       --output ${OUTPUTDIR}/lh_sphere_${RESOLUTION}.vtk -f

python ${SCRIPT_PATH}/generate_sphere.py \
       --surface ${OUTPUTDIR}/rh_sphere_lps.vtk \
       --points ${OUTPUTDIR}/rh_white_ids_${RESOLUTION}.npz \
       --output ${OUTPUTDIR}/rh_sphere_${RESOLUTION}.vtk -f

# Step3) Generate a discrete mapping from the full resolution mesh to the downsampled mesh
python ${SCRIPT_PATH}/map_surfaces.py \
       --lh_surface_hi ${OUTPUTDIR}/lh_sphere_lps.vtk \
       --lh_surface_lo ${OUTPUTDIR}/lh_sphere_${RESOLUTION}.vtk \
       --rh_surface_hi ${OUTPUTDIR}/rh_sphere_lps.vtk \
       --rh_surface_lo ${OUTPUTDIR}/rh_sphere_${RESOLUTION}.vtk \
       --output ${OUTPUTDIR}/mapping_${RESOLUTION}.npz -f

# Step4) Genereate a white matter mesh for visualisation
python ${SCRIPT_PATH}/downsample_mesh.py \
       --lh_surface ${OUTPUTDIR}/lh_white_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_white_lps.vtk \
       --mesh ${OUTPUTDIR}/mapping_${RESOLUTION}.npz \
       --suffix _${RESOLUTION} -f

# Step5) Validate downsampled mesh
python ${SCRIPT_PATH}/mesh_validation.py \
       --lh_surface_hi ${OUTPUTDIR}/lh_white_lps.vtk \
       --lh_surface_lo ${OUTPUTDIR}/lh_white_lps_${RESOLUTION}.vtk \
       --rh_surface_hi ${OUTPUTDIR}/rh_white_lps.vtk \
       --rh_surface_lo ${OUTPUTDIR}/rh_white_lps_${RESOLUTION}.vtk \
       --output ${OUTPUTDIR}/white_validation_${RESOLUTION}.npz -f

python ${SCRIPT_PATH}/mesh_validation.py \
       --lh_surface_hi ${OUTPUTDIR}/lh_sphere_lps.vtk \
       --lh_surface_lo ${OUTPUTDIR}/lh_sphere_${RESOLUTION}.vtk \
       --rh_surface_hi ${OUTPUTDIR}/rh_sphere_lps.vtk \
       --rh_surface_lo ${OUTPUTDIR}/rh_sphere_${RESOLUTION}.vtk \
       --output ${OUTPUTDIR}/sphere_validation_${RESOLUTION}.npz -f

# Step6) Clear intermediate results
rm ${OUTPUTDIR}/lh_white_ids_${RESOLUTION}.npz
rm ${OUTPUTDIR}/rh_white_ids_${RESOLUTION}.npz

echo "Finished processing SBCI surfaces: $(date)"
