#!/bin/bash

SCRIPT_PATH=/scratch/mcole22/sbc_pipeline/gitrepo/SBCI/scripts
CONCON_PATH=/scratch/mcole22/concon/build/bin

SIZE=${1}
SCDIR=${2}
FCDIR=${3}
OUTPUTDIR=${4}

mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/lh.sphere ${OUTPUTDIR}/lh_sphere.vtk
mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/rh.sphere ${OUTPUTDIR}/rh_sphere.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_surface.py ${OUTPUTDIR}/lh_sphere.vtk --fx --fy --out_surface ${OUTPUTDIR}/lh_sphere_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/rh_sphere.vtk --fx --fy --out_surface ${OUTPUTDIR}/rh_sphere_lps.vtk -f

python ${SCRIPT_PATH}/concon/intersections_to_sphere.py \
       --lh_surface ${OUTPUTDIR}/lh_sphere_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_sphere_lps.vtk \
       --intersections ${OUTPUTDIR}/snapped_fibers_${SIZE}.npz \
       --output ${OUTPUTDIR}/subject_xing_sphere_coords_${SIZE}.tsv -f

python ${SCRIPT_PATH}/concon/mesh_to_sphere.py \
       --lh_surface ${OUTPUTDIR}/lh_sphere_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_sphere_lps.vtk \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --suffix _${SIZE} -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUTDIR}/lh_sphere_lps_${SIZE}.vtk \
       --output ${OUTPUTDIR}/tmp_lh_grid_${SIZE}.m -f

python ${SCRIPT_PATH}/concon/vtk_to_m.py \
       --surface ${OUTPUTDIR}/rh_sphere_lps_${SIZE}.vtk \
       --output ${OUTPUTDIR}/tmp_rh_grid_${SIZE}.m -f

python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUTDIR}/tmp_lh_grid_${SIZE}.m --output ${OUTPUTDIR}/lh_grid_${SIZE}.m -f
python ${SCRIPT_PATH}/concon/normalise_m.py --surface ${OUTPUTDIR}/tmp_rh_grid_${SIZE}.m --output ${OUTPUTDIR}/rh_grid_${SIZE}.m -f

rm ${OUTPUTDIR}/tmp_lh_grid_${SIZE}.m
rm ${OUTPUTDIR}/tmp_rh_grid_${SIZE}.m

# run concon to get the smooth SC matrix
${CONCON_PATH}/c3_main \
  Compute_Kernel \
  --verbose 10 \
  --subj subject \
  --sigma 0.005 \
  --epsilon 0.001 \
  --final_thold 0.000000001 \
  --OPT_VAL_exp_num_kern_samps 6 \
  --OPT_VAL_exp_num_harm_samps 5 \
  --OPT_VAL_num_harm 33 \
  --LOAD_xing_path "${OUTPUTDIR}/" \
  --LOAD_xing_postfix "_xing_sphere_coords_${SIZE}.tsv" \
  --LOAD_kernel_path "" \
  --LOAD_kernel_postfix "_0.005_${SIZE}.raw" \
  --LOAD_mask_file MASK \
  --SAVE_Compute_Kernel_prefix "${OUTPUTDIR}/" \
  --SAVE_Compute_Kernel_postfix "_0.005_${SIZE}.raw" \
  --LOAD_grid_file "${OUTPUTDIR}/lh_grid_${SIZE}.m" \
  --LOAD_rh_grid_file "${OUTPUTDIR}/rh_grid_${SIZE}.m" 

# convert the binary output of concon into something we can use
python ${SCRIPT_PATH}/concon/convert_raw.py \
       --input ${OUTPUTDIR}/subject_0.005_${SIZE}.raw \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --output ${OUTPUTDIR}/smoothed_sc_0.005_${SIZE} -f

# calculate SCFC metric and project onto the mesh
python ${SCRIPT_PATH}/calculate_sc_fc_cor_map.py \
       --fc_matrix ${OUTPUTDIR}/fc_partial_${SIZE}.npz \
       --sc_matrix ${OUTPUTDIR}/smoothed_sc_0.005_${SIZE}.npz \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --fisher \
       --output ${OUTPUTDIR}/smoothed_fisher_fc_sc_corr_map_${SIZE}.npz -f

python ${SCRIPT_PATH}/embed_data.py \
       --lh_surface ${OUTPUTDIR}/lh_white_${SIZE}.vtk \
       --rh_surface ${OUTPUTDIR}/rh_white_${SIZE}.vtk \
       --data ${OUTPUTDIR}/smoothed_fisher_fc_sc_corr_map_${SIZE}.npz \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --suffix _smoothed_fisher_fc_sc_ -f

python ${SCRIPT_PATH}/embed_data_upsample.py \
       --lh_surface ${SCDIR}/dwi_psc_connectome/set_3000k_n75/out_surf/lh_white_s2w2.vtk \
       --rh_surface ${SCDIR}/dwi_psc_connectome/set_3000k_n75/out_surf/rh_white_s2w2.vtk \
       --data ${OUTPUTDIR}/smoothed_fisher_fc_sc_corr_map_${SIZE}.npz \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --suffix _smoothed_fisher_fc_sc_${SIZE}_full_ -f

# project onto the inflated surface
mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/lh.inflated ${OUTPUTDIR}/lh_inflated.vtk
mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/rh.inflated ${OUTPUTDIR}/rh_inflated.vtk

scil_surface.py ${OUTPUTDIR}/lh_inflated.vtk --fx --fy --out_surface ${OUTPUTDIR}/lh_inflated_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/rh_inflated.vtk --fx --fy --out_surface ${OUTPUTDIR}/rh_inflated_lps.vtk -f

python ${SCRIPT_PATH}/embed_data_upsample.py \
       --lh_surface ${OUTPUTDIR}/lh_inflated_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_inflated_lps.vtk \
       --data ${OUTPUTDIR}/smoothed_fisher_fc_sc_corr_map_${SIZE}.npz \
       --mesh ${OUTPUTDIR}/mapping_${SIZE}.npz \
       --suffix _smoothed_fisher_fc_sc_${SIZE}_full_ -f
