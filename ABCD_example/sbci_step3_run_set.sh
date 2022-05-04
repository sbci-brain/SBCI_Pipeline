#!/bin/bash

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

if [ -z ${SCRIPT_PATH+x} ]; then 
    SCRIPT_PATH=${SBCI_PATH}/scripts
fi

RUN=$1

echo "Begin processing SET: $(date)"

cd dwi_pipeline
cd structure

# compute pft maps
scil_compute_maps_for_particle_filter_tracking.py map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz --interface interface.nii.gz -f

cd ..

# generate surface seed map
scil_surface_seed_map.py set/out_surf/flow_${STEPS}_1.vtk \
        set/out_surf/seeding_map_rand_loop_${RUN}.npy \
        --triangle_weight set/out_surf/seeding_map_0.npy -f

# points (3D position) where to seed
scil_surface_seeds_from_map.py set/out_surf/flow_${STEPS}_1.vtk \
	set/out_surf/seeding_map_rand_loop_${RUN}.npy \
	${N_SEED}000 \
        set/out_surf/seeds_random_loop${RUN}.npz\
        --random_number_generator ${RUN} -f

mkdir set/streamline

scil_surface_pft_dipy.py diffusion/fodf/fodf.nii.gz \
	structure/map_include.nii.gz \
	structure/map_exclude.nii.gz \
	set/out_surf/flow_${STEPS}_1.vtk \
        set/out_surf/seeds_random_loop${RUN}.npz \
        set/streamline/set_random_loop${RUN}.trk \
        --algo 'prob' \
        --step 0.2 \
        --theta 20 \
        --sfthres 0.1 \
        --max_length 250 \
        --random_seed $((RNG + RUN)) \
        --compress 0.2 \
        --particles 15 \
        --back 2 \
        --forward 1 -f

scil_convert_tractogram.py set/streamline/set_random_loop${RUN}.trk \
        set/streamline/set_random_loop${RUN}.fib -f

# calculate interections (SBCI cuts subcortical fibers 
# into n choose 2 pairs between n intersecting ROIs)
python ${SCRIPT_PATH}/trim_cortical_fibers.py \
        --surfaces set/out_surf/flow_${STEPS}_1.vtk \
        --surface_map set/preprocess/surfaces_type.npy \
        --surface_mask set/out_surf/intersections_mask.npy \
        --aparc set/preprocess/aparc.a2009s+aseg.nii.gz \
        --rois ${ROIS[*]} \
        --streamline set/streamline/set_random_loop${RUN}.fib \
        --out_tracts set/streamline/set_random_loop${RUN}_cut.fib \
        --output set/streamline/intersections_random_loop${RUN}.npz -f

# combine intersection with flow
scil_surface_combine_flow.py set/out_surf/flow_${STEPS}_1.vtk \
		set/out_surf/flow_${STEPS}_1.hdf5 \
        	set/streamline/intersections_random_loop${RUN}.npz \
              	set/streamline/set_random_loop${RUN}_cut.fib \
        	set/streamline/set_random_loop${RUN}.fib \
                --compression_rate 0.2
    
# filter long and short fibers
scil_surface_filtering.py set/out_surf/flow_${STEPS}_1.vtk \
        set/streamline/intersections_random_loop${RUN}.npz \
        set/streamline/set_random_loop${RUN}.fib \
        set/streamline/set_random_loop${RUN}_filtered.fib \
        --out_intersections set/streamline/intersections_random_loop${RUN}_filtered.npz \
        --min_length 10 \
        --max_length 250 -f

cd ..
echo "Finished processing SET: $(date)"
