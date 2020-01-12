#!/bin/bash

SCRIPT_PATH=/scratch/mcole22/sbc_pipeline/gitrepo/SBCI/scripts
CONCON_PATH=/scratch/mcole22/concon/build/bin

SIZE=0.99
SCDIR=/scratch/mcole22/sbc_pipeline/final_data/SC/RN001_ENTRY
OUTPUTDIR=/scratch/mcole22/sbc_pipeline/final_data/AVG

mkdir ${OUTPUTDIR}

#mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/fsaverage/surf/lh.white_avg ${OUTPUTDIR}/lh_white_avg.vtk
mris_convert ${SCDIR}/dwi_psc_connectome/structure/fsaverage/surf/lh.white_avg ${OUTPUTDIR}/lh_white_avg.vtk
mris_convert ${SCDIR}/dwi_psc_connectome/structure/fsaverage/surf/rh.white_avg ${OUTPUTDIR}/rh_white_avg.vtk
mris_convert ${SCDIR}/dwi_psc_connectome/structure/fsaverage/surf/lh.sphere.reg.avg ${OUTPUTDIR}/lh_sphere_avg.vtk
mris_convert ${SCDIR}/dwi_psc_connectome/structure/fsaverage/surf/rh.sphere.reg.avg ${OUTPUTDIR}/rh_sphere_avg.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_surface.py ${OUTPUTDIR}/lh_sphere_avg.vtk --fx --fy --out_surface ${OUTPUTDIR}/lh_sphere_avg_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/rh_sphere_avg.vtk --fx --fy --out_surface ${OUTPUTDIR}/rh_sphere_avg_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/lh_white_avg.vtk --fx --fy --out_surface ${OUTPUTDIR}/lh_white_avg_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/rh_white_avg.vtk --fx --fy --out_surface ${OUTPUTDIR}/rh_white_avg_lps.vtk -f

python ${SCRIPT_PATH}/downsample_surface.py \
       --surface ${OUTPUTDIR}/lh_white_avg_lps.vtk \
       --output ${OUTPUTDIR}/lh_white_avg_${SIZE}.vtk \
       --reduction ${SIZE} -f

python ${SCRIPT_PATH}/downsample_surface.py \
       --surface ${OUTPUTDIR}/rh_white_avg_lps.vtk \
       --output ${OUTPUTDIR}/rh_white_avg_${SIZE}.vtk \
       --reduction ${SIZE} -f

python ${SCRIPT_PATH}/map_surfaces.py \
       --lh_surface_hi ${OUTPUTDIR}/lh_white_avg_lps.vtk \
       --lh_surface_lo ${OUTPUTDIR}/lh_white_avg_${SIZE}.vtk \
       --rh_surface_hi ${OUTPUTDIR}/rh_white_avg_lps.vtk \
       --rh_surface_lo ${OUTPUTDIR}/rh_white_avg_${SIZE}.vtk \
       --output ${OUTPUTDIR}/mapping_avg_${SIZE}.npz -f

python ${SCRIPT_PATH}/group_roi_vertices.py \
       --lh_annot ${SCDIR}/dwi_psc_connectome/structure/fsaverage/label/lh.aparc.annot \
       --rh_annot ${SCDIR}/dwi_psc_connectome/structure/fsaverage/label/rh.aparc.annot \
       --mesh ${OUTPUTDIR}/mapping_avg_${SIZE}.npz \
       --output ${OUTPUTDIR}/desikan_avg_roi_${SIZE}.npz -f

python ${SCRIPT_PATH}/concon/mesh_to_sphere.py \
       --lh_surface ${OUTPUTDIR}/lh_sphere_avg_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_sphere_avg_lps.vtk \
       --mesh ${OUTPUTDIR}/mapping_avg_${SIZE}.npz \
       --suffix _${SIZE} -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUTDIR}/lh_sphere_avg_lps_${SIZE}.vtk \
       --output ${OUTPUTDIR}/tmp_lh_grid.m -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUTDIR}/rh_sphere_avg_lps_${SIZE}.vtk \
       --output ${OUTPUTDIR}/tmp_rh_grid.m -f

python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUTDIR}/tmp_lh_grid.m --output ${OUTPUTDIR}/lh_grid_avg.m -f
python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUTDIR}/tmp_rh_grid.m --output ${OUTPUTDIR}/rh_grid_avg.m -f

rm ${OUTPUTDIR}/tmp_lh_grid.m
rm ${OUTPUTDIR}/tmp_rh_grid.m
