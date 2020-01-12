#!/bin/bash

SCRIPT_PATH=/scratch/mcole22/sbc_pipeline/gitrepo/SBCI/scripts
CONCON_PATH=/scratch/mcole22/concon/build/bin

SIZE=${1}
SCDIR=${2}
FCDIR=${3}
AVGDIR=${4}
OUTPUTDIR=${5}

mkdir -p ${OUTPUTDIR}

mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/lh.sphere.reg ${OUTPUTDIR}/lh_sphere_reg.vtk
mris_convert --to-scanner ${SCDIR}/dwi_psc_connectome/structure/t1_freesurfer/surf/rh.sphere.reg ${OUTPUTDIR}/rh_sphere_reg.vtk

# flip from RAS (Right-Anterior-Superior, the standard coordinate system for freesurfer output) to
# LPS (Left-Posterior-Superior), the standard for SET (because it makes more sense with MI-Brain).
scil_surface.py ${OUTPUTDIR}/lh_sphere_reg.vtk --fx --fy --out_surface ${OUTPUTDIR}/lh_sphere_reg_lps.vtk -f
scil_surface.py ${OUTPUTDIR}/rh_sphere_reg.vtk --fx --fy --out_surface ${OUTPUTDIR}/rh_sphere_reg_lps.vtk -f

python ${SCRIPT_PATH}/concon/intersections_to_sphere.py \
       --lh_surface ${OUTPUTDIR}/lh_sphere_reg_lps.vtk \
       --rh_surface ${OUTPUTDIR}/rh_sphere_reg_lps.vtk \
       --intersections ${OUTPUTDIR}/snapped_fibers_${SIZE}.npz \
       --output ${OUTPUTDIR}/subject_xing_sphere_avg_coords_${SIZE}.tsv -f

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
  --LOAD_xing_postfix "_xing_sphere_avg_coords_${SIZE}.tsv" \
  --LOAD_kernel_path "" \
  --LOAD_kernel_postfix "" \
  --LOAD_mask_file MASK \
  --SAVE_Compute_Kernel_prefix "${OUTPUTDIR}/" \
  --SAVE_Compute_Kernel_postfix "_avg_0.005_${SIZE}.raw" \
  --LOAD_grid_file "${AVGDIR}/lh_grid_avg.m" \
  --LOAD_rh_grid_file "${AVGDIR}/rh_grid_avg.m" 

# convert the binary output of concon into something we can use
python ${SCRIPT_PATH}/concon/convert_raw.py \
       --input ${OUTPUTDIR}/subject_avg_0.005_${SIZE}.raw \
       --mesh ${AVGDIR}/mapping_avg_${SIZE}.npz \
       --output ${OUTPUTDIR}/smoothed_avg_sc_0.005_${SIZE} -f

# calculate SCFC metric and project onto the mesh
python ${SCRIPT_PATH}/calculate_sc_fc_cor_map.py \
       --fc_matrix ${OUTPUTDIR}/fc_partial_${SIZE}.npz \
       --sc_matrix ${OUTPUTDIR}/smoothed_avg_sc_0.005_${SIZE}.npz \
       --mesh ${AVGDIR}/mapping_avg_${SIZE}.npz \
       --fisher \
       --output ${OUTPUTDIR}/smoothed_fisher_avg_fc_sc_corr_map_${SIZE}.npz -f

python ${SCRIPT_PATH}/embed_data.py \
       --lh_surface ${AVGDIR}/lh_white_avg_lps_${SIZE}.vtk \
       --rh_surface ${AVGDIR}/rh_white_avg_lps_${SIZE}.vtk \
       --data ${OUTPUTDIR}/smoothed_fisher_avg_fc_sc_corr_map_${SIZE}.npz \
       --mesh ${AVGDIR}/mapping_avg_${SIZE}.npz \
       --suffix _smoothed_fisher_avg_fc_sc_ -f

python ${SCRIPT_PATH}/embed_data_upsample.py \
       --lh_surface ${AVGDIR}/lh_white_avg_lps.vtk \
       --rh_surface ${AVGDIR}/rh_white_avg_lps.vtk \
       --data ${OUTPUTDIR}/smoothed_fisher_avg_fc_sc_corr_map_${SIZE}.npz \
       --mesh ${AVGDIR}/mapping_avg_${SIZE}.npz \
       --suffix _smoothed_fisher_avg_fc_sc_${SIZE}_full_ -f
