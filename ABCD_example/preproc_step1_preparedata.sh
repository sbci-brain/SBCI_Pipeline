#!/bin/bash

echo "Begin preparing data: $(date)"

# flip T1
cd anat
mrconvert *_T1w.nii* -stride 1,2,3 t1.nii.gz -force
cd ..

# flip dMRI
cd dwi
run_count=$(ls -f *[0-9]_dwi.nii* | wc -l)

# some subjects have multiple runs (if so, merge them into one)
if [ ${run_count} -gt 1 ]; then
    # combine dwi image files
    fslmerge -t dwi_all *[0-9]_dwi.nii*

    # combine b-value files
    for f in $(ls *[0-9]_dwi.bval); do 
        read -d '' -r -a bvals < ${f}
        length=${#bvals[@]}
        echo -n ' '${bvals[@]:0:length} >> bval_all.bval
    done

    # combine b-vector files
    for f in $(ls *[0-9]_dwi.bvec | sed 's/\..*$//'); do
        read -d '' -r -a bvals < ${f}.bval
        length=${#bvals[@]}
        read -d '' -r -a bvecs < ${f}.bvec
        echo -n ' '${bvecs[@]:0:length} >> bvecs_1
        echo -n ' '${bvecs[@]:length:length} >> bvecs_2
        echo -n ' '${bvecs[@]:length+length:length} >> bvecs_3
    done

    echo $(cat bvecs_1) > bvec_all.bvec
    echo $(cat bvecs_2) >> bvec_all.bvec
    echo $(cat bvecs_3) >> bvec_all.bvec

    mrconvert dwi_all.nii* -stride 1,2,3,4 flipped_data.nii.gz -force
    scil_convert_gradient_fsl_to_mrtrix.py bval_all.bval bvec_all.bvec encoding.b  -f

    # remove intermediate files
    rm -rf dwi_all.nii*
    rm -rf bval_all.bval
    rm -rf bvec_all.bvec
    rm -rf bvecs_1 bvecs_2 bvecs_3
fi

# if only one subject, skip all the merging steps
if [ ${run_count} -eq 1 ]; then
    mrconvert *_dwi.nii* -stride 1,2,3,4 flipped_data.nii.gz -force
    scil_convert_gradient_fsl_to_mrtrix.py *_dwi.bval *_dwi.bvec encoding.b  -f
fi

scil_flip_grad.py --mrtrix encoding.b encoding_x.b x -f
scil_convert_gradient_mrtrix_to_fsl.py encoding_x.b flip_x.bval flip_x.bvec -f 
cd ..

# move final files to one folder
mkdir -p dwi_pipeline
cd dwi_pipeline

mv ../anat/t1.nii.gz t1.nii.gz
mv ../dwi/flip_x.bval flip_x.bval
mv ../dwi/flip_x.bvec flip_x.bvec
mv ../dwi/flipped_data.nii.gz data.nii.gz

echo "Finished preparing data: $(date)"
