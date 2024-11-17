#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

OUTPUTDIR=dwi_pipeline/sbci_connectome
SCDIR=dwi_pipeline/structure/t1_freesurfer

if [ -z ${SCRIPT_PATH+x} ]; then 
    SCRIPT_PATH=${SBCI_PATH}/scripts
fi

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
       --output ${OUTPUTDIR}/lh_sphere_reg_norm.vtk -f

python ${SCRIPT_PATH}/normalise_vtk.py \
       --surface ${OUTPUTDIR}/rh_sphere_reg_lps.vtk \
       --output ${OUTPUTDIR}/rh_sphere_reg_norm.vtk -f

python ${SCRIPT_PATH}/get_coords.py --lh_surface ${OUTPUTDIR}/lh_sphere_reg_norm.vtk --rh_surface ${OUTPUTDIR}/rh_sphere_reg_norm.vtk --output ${OUTPUTDIR}/subject_coords.npz -f

echo "Finished processing SBCI surfaces: $(date)"
