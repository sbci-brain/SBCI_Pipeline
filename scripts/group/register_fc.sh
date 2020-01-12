#!/bin/bash

SCRIPT_PATH=/scratch/mcole22/sbc_pipeline/gitrepo/SBCI/scripts

SIZE=${1}
AVGDIR=${2}
OUTPUTDIR=${3}

python ${SCRIPT_PATH}/concon/normalise_vtk.py \
       --surface ${OUTPUTDIR}/lh_sphere_reg_lps.vtk \
       --output ${OUTPUTDIR}/lh_sphere_reg_lps_norm.vtk -f

python ${SCRIPT_PATH}/concon/normalise_vtk.py \
       --surface ${AVGDIR}/lh_sphere_avg_lps.vtk \
       --output ${OUTPUTDIR}/lh_sphere_avg_lps_norm.vtk -f

python ${SCRIPT_PATH}/concon/normalise_vtk.py \
       --surface ${OUTPUTDIR}/rh_sphere_reg_lps.vtk \
       --output ${OUTPUTDIR}/rh_sphere_reg_lps_norm.vtk -f

python ${SCRIPT_PATH}/concon/normalise_vtk.py \
       --surface ${AVGDIR}/rh_sphere_avg_lps.vtk \
       --output ${OUTPUTDIR}/rh_sphere_avg_lps_norm.vtk -f

python ${SCRIPT_PATH}/register_fc.py \
       --lh_surface ${OUTPUTDIR}/lh_sphere_reg_lps_norm.vtk \
       --lh_average ${OUTPUTDIR}/lh_sphere_avg_lps_norm.vtk \
       --rh_surface ${OUTPUTDIR}/rh_sphere_reg_lps_norm.vtk \
       --rh_average ${OUTPUTDIR}/rh_sphere_avg_lps_norm.vtk \
       --time_series ${OUTPUTDIR}/fc_ts_partial_${SIZE}.npz \
       --output ${OUTPUTDIR}/registered_fc_ts.npz -f

python ${SCRIPT_PATH}/calculate_fc.py \
       --time_series ${OUTPUTDIR}/registered_fc_ts.npz \
       --mesh ${AVGDIR}/mapping_avg_${SIZE}.npz \
       --output ${OUTPUTDIR}/fc_partial_avg_${SIZE}.npz -f
