#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
results_dir="${SBCI_NEW_TEST_RESULTS:-${SCRIPT_DIR}/results/new}"
data_dir="${SCRIPT_DIR}/data"
scripts_path="${REPO_ROOT}/scripts/scripts_py3"
RUN=1
STEPS=75
N_SEED=1000000

echo "Copying files..."
mkdir -p "$results_dir"
cp "$data_dir"/*h.aparc.a2009s.annot "$results_dir"
cp "$data_dir"/*h.pial "$results_dir"
cp "$data_dir"/*h.white "$results_dir"
cp "$data_dir"/roi_00004.vtk "$results_dir"

echo "Converting files..."
cd "$results_dir"
mris_convert --to-scanner lh.pial lh.pial.vtk
mris_convert --to-scanner rh.pial rh.pial.vtk
mris_convert --to-scanner lh.white lh.white.vtk
mris_convert --to-scanner rh.white rh.white.vtk
scil_surface_flip.py lh.pial.vtk lh_pial_lps.vtk x y -f
scil_surface_flip.py rh.pial.vtk rh_pial_lps.vtk x y -f
scil_surface_flip.py lh.white.vtk lh_white_lps.vtk x y -f
scil_surface_flip.py rh.white.vtk rh_white_lps.vtk x y -f

echo "Preparing mask files..."
python "$scripts_path"/scil_surface.py lh_white_lps.vtk --annot lh.aparc.a2009s.annot --save_vts_label  lh_labels.npy -f
python "$scripts_path"/scil_surface.py rh_white_lps.vtk --annot rh.aparc.a2009s.annot --save_vts_label  rh_labels.npy -f

python "$scripts_path"/scil_surface.py lh_white_lps.vtk --vts_val 0.0 --save_vts_mask  lh_zero_mask.npy -f
python "$scripts_path"/scil_surface.py rh_white_lps.vtk --vts_val 0.0 --save_vts_mask  rh_zero_mask.npy -f

python "$scripts_path"/scil_surface.py lh_white_lps.vtk --annot lh.aparc.a2009s.annot \
    -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
    --save_vts_mask lh_flow_mask.npy -f

python "$scripts_path"/scil_surface.py rh_white_lps.vtk --annot rh.aparc.a2009s.annot \
    -i -1 0 6 7 8 9 10 35 42 67 --inverse_mask \
    --save_vts_mask rh_flow_mask.npy -f

python "$scripts_path"/scil_surface.py lh_white_lps.vtk --annot lh.aparc.a2009s.annot \
    -i -1 0 --inverse_mask \
    --save_vts_mask lh_seed_mask.npy -f

python "$scripts_path"/scil_surface.py rh_white_lps.vtk --annot rh.aparc.a2009s.annot\
    -i -1 0 --inverse_mask \
    --save_vts_mask rh_seed_mask.npy -f

python "$scripts_path"/scil_surface.py lh_white_lps.vtk --annot lh.aparc.a2009s.annot \
    -i -1 0 --inverse_mask \
    --save_vts_mask lh_intersections_mask.npy -f

python "$scripts_path"/scil_surface.py rh_white_lps.vtk --annot rh.aparc.a2009s.annot \
    -i -1 0 --inverse_mask \
    --save_vts_mask rh_intersections_mask.npy -f

# 对于roi_00004生成的文件，不代表实际意义，只是作为占位符
python "$scripts_path"/scil_surface.py roi_00004.vtk \
    --vts_val 1.0 --save_vts_mask roi_00004_seed_mask.npy -f

python "$scripts_path"/scil_surface.py roi_00004.vtk \
    --vts_val 1.0 --save_vts_mask roi_00004_intersections_mask.npy -f

python "$scripts_path"/scil_surface.py roi_00004.vtk \
    --vts_val 0.0 --save_vts_mask roi_00004_flow_mask.npy -f

#concatenate mask
python "$scripts_path"/scil_surface_map_concatenate.py lh_flow_mask.npy rh_flow_mask.npy \
    --outer_surfaces_map lh_zero_mask.npy rh_zero_mask.npy \
    --inner_surfaces roi_00004_flow_mask.npy \
    --out_map flow_mask.npy -f

python "$scripts_path"/scil_surface_map_concatenate.py lh_seed_mask.npy rh_seed_mask.npy \
    --outer_surfaces_map lh_zero_mask.npy rh_zero_mask.npy \
    --inner_surfaces roi_00004_seed_mask.npy \
    --out_map seed_mask.npy -f

python "$scripts_path"/scil_surface_map_concatenate.py lh_intersections_mask.npy rh_intersections_mask.npy \
    --outer_surfaces_map lh_intersections_mask.npy rh_intersections_mask.npy \
    --inner_surfaces roi_00004_intersections_mask.npy \
    --out_map intersections_mask.npy -f

echo "Concatenating and smoothing files..."
## 旧版本的脚本有bug，必须要有inner_surfaces选项，因此随便指定一个roi_00004.vtk
python "$scripts_path"/scil_surface_concatenate.py lh_white_lps.vtk rh_white_lps.vtk \
    --outer_surfaces lh_pial_lps.vtk rh_pial_lps.vtk \
    --inner_surfaces roi_00004.vtk \
    --out_surface_id surfaces_id.npy \
    --out_surface_type_map surfaces_type.npy \
    --out_concatenated_surface surfaces.vtk -f

scil_surface_smooth.py surfaces.vtk smoothed.vtk \
    --vts_mask flow_mask.npy \
    --nb_steps 2 --step_size 2.0 -f

# can be 75 for HCP, maybe 100 for low resolution data
python "$scripts_path"/scil_surface_flow.py smoothed.vtk flow_${STEPS}_1.vtk \
    --vts_mask flow_mask.npy \
    --nb_step ${STEPS} \
    --step_size 1.0 \
    --gaussian_threshold 0.2 \
    --angle_threshold 2 \
    --out_flow flow_${STEPS}_1.hdf5 -f

echo "Generating seeds map files..."
python "$scripts_path"/scil_surface_seed_map.py surfaces.vtk seeding_map_0.npy \
    --vts_mask seed_mask.npy \
    --triangle_area_weighting -f

python "$scripts_path"/scil_surface_seed_map.py flow_${STEPS}_1.vtk seeding_map_rand_loop_${RUN}.npy \
    --triangle_weight seeding_map_0.npy -f

python "$scripts_path"/scil_surface_seeds_from_map.py flow_${STEPS}_1.vtk \
    seeding_map_rand_loop_${RUN}.npy ${N_SEED} \
    seeds_random_loop${RUN}.npz\
    --random_number_generator ${RUN} -f
echo "Done."
