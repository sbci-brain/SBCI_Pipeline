#!/bin/bash

echo "Cleaning the folder tree to reduce space"

OUTPUTDIR=psc_sbci_final_files

echo "Begin copying files to ${OUTPUTDIR}"
mkdir -p ${OUTPUTDIR}

#------------------------------------------------------------------------
#let's first handle the "structure" folder; this folder takes about 500MBs
mkdir -p ${OUTPUTDIR}/structure

#t1 bet and croped t1 bet
mv dwi_pipeline/structure/t1_bet.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/t1_bet_cropped.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/t1_boundingBox.pkl ${OUTPUTDIR}/structure/

#t1 registration to dwi
mv dwi_pipeline/structure/t1_warped.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/output0GenericAffine.mat ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/output1Warp.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/t1_n4.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/t1_wholebrain_warped.nii.gz ${OUTPUTDIR}/structure/

#t1 freesurfer
mv dwi_pipeline/structure/t1_freesurfer ${OUTPUTDIR}/structure/

#map_wm.nii.gz map_gm.nii.gz map_csf.nii.gz and interface.nii.gz
mv dwi_pipeline/structure/map_wm.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/map_gm.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/map_csf.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/interface.nii.gz ${OUTPUTDIR}/structure/
mv dwi_pipeline/structure/seeding_mask.nii.gz ${OUTPUTDIR}/structure/

#let's now handle the "diffusion" folder; keep about 1.3 GB data
#------------------------------------------------------------------------
#keep the raw data for later use;
mkdir -p ${OUTPUTDIR}/diffusion 

mv dwi_pipeline/diffusion/dwi_boundingBox.pkl ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/dwi_fodf.nii.gz ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/fodf.bval ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/fodf.bvec ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/frf.txt ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/b0_mask_resampled.nii.gz ${OUTPUTDIR}/diffusion/
mv dwi_pipeline/diffusion/dti ${OUTPUTDIR}/diffusion/dti
mv dwi_pipeline/diffusion/fodf ${OUTPUTDIR}/diffusion/

#let's now handle the "set" folder;
#------------------------------------------------------------------------
mkdir -p ${OUTPUTDIR}/set/preprocess

#surfaces
mv dwi_pipeline/set/preprocess/surfaces_id.npy ${OUTPUTDIR}/set/preprocess/
mv dwi_pipeline/set/preprocess/surfaces_type.npy ${OUTPUTDIR}/set/preprocess/

mkdir -p ${OUTPUTDIR}/set/out_surf
mv dwi_pipeline/set/out_surf/surfaces.vtk ${OUTPUTDIR}/set/out_surf/

#masks
mv dwi_pipeline/set/out_surf/flow_mask.npy ${OUTPUTDIR}/set/out_surf/
mv dwi_pipeline/set/out_surf/seed_mask.npy ${OUTPUTDIR}/set/out_surf/
mv dwi_pipeline/set/out_surf/intersections_mask.npy ${OUTPUTDIR}/set/out_surf/

#surface flow
mv dwi_pipeline/set/out_surf/smoothed.vtk ${OUTPUTDIR}/set/out_surf/
mv dwi_pipeline/set/out_surf/flow_*_1.vtk ${OUTPUTDIR}/set/out_surf/
mv dwi_pipeline/set/out_surf/flow_*_1.hdf5 ${OUTPUTDIR}/set/out_surf/

#seeding
mv dwi_pipeline/set/out_surf/seeding_map_0.npy ${OUTPUTDIR}/set/out_surf/

#copy streamline folder and remove .fib
mkdir -p ${OUTPUTDIR}/set/streamline
mv dwi_pipeline/set/streamline/set_filtered_intersections.npz ${OUTPUTDIR}/set/streamline/

#copy sbci_connectome
mkdir -p ${OUTPUTDIR}/sbci_connectome

#FC
# mv dwi_pipeline/sbci_connectome/fc_ts.npz  ${OUTPUTDIR}/sbci_connectome/ # too large to keep right now (1.8GB)
mv dwi_pipeline/sbci_connectome/fc_avg_*.mat ${OUTPUTDIR}/sbci_connectome/
mv dwi_pipeline/sbci_connectome/fc_avg_*_ts.mat ${OUTPUTDIR}/sbci_connectome/

#SC
mv dwi_pipeline/sbci_connectome/subject_xing_sphere_avg_coords.tsv ${OUTPUTDIR}/sbci_connectome/ #template coordinates
mv dwi_pipeline/sbci_connectome/smoothed_sc_avg_*.mat ${OUTPUTDIR}/sbci_connectome/
mv dwi_pipeline/sbci_connectome/sub_sc_avg_*.mat ${OUTPUTDIR}/sbci_connectome/
mv dwi_pipeline/sbci_connectome/*.vtk ${OUTPUTDIR}/sbci_connectome/

#copy psc_connectome folder
mv dwi_pipeline/psc_connectome/ ${OUTPUTDIR}

#delete the fsfast folder
rm -r fsfast

#delete the fmri folder
rm -r fmri

#delete the remaining files in dwi_pipeline/
rm -r dwi_pipeline/

