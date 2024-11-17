#!/bin/bash

#SBATCH -N 1
#SBATCH -n 1
#SBATCH -p general
#SBATCH -t 20:00:00
#SBATCH --mem=24g
#SBATCH --output=dwicat_process-%x_%j.log

# Load necessary modules
module load fsl/6.0.6
module load mrtrix3/3.0.3
module load gcc/11.2.0

# Set the base directories
base_dir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_Developmet_unprocessedDiff/imagingcollection01"
output_base_dir="/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/HCP_Development"

# Get the start and end indices from the script arguments
startIndex=$1
endIndex=$2

# Get the directories based on the given range
dirs=($(ls -d ${base_dir}/* | sed -n "${startIndex},${endIndex}p"))

# Loop over each directory
for dir in "${dirs[@]}"; do
    subject=$(basename $dir)
    output_dir="${output_base_dir}/${subject}/dwi"
    mkdir -p $output_dir

    echo "Processing ${subject}: Starting..."

    cd $dir/unprocessed/Diffusion
    if [ ! -e "$dir/unprocessed/Diffusion/${subject}_dMRI_dir98_PA.nii.gz" ] || \
       [ ! -e "$dir/unprocessed/Diffusion/${subject}_dMRI_dir98_AP.nii.gz" ] || \
       [ ! -e "$dir/unprocessed/Diffusion/${subject}_dMRI_dir99_AP.nii.gz" ]; then
        echo "Required files not found for ${subject}. Skipping..."
        continue
    fi


    if [ -e "$output_dir/eddy_corrected_data.nii.gz" ]; then
        echo "Eddy correction already completed for ${subject}. Skipping..."
        continue
    fi


    echo "Processing ${subject}: Extracting PA b0 images..."
    if [ ! -e $output_dir/${subject}_dMRI_dir98_PA_b0.nii.gz ]; then
        dwiextract -bzero -fslgrad ${subject}_dMRI_dir98_PA.bvec ${subject}_dMRI_dir98_PA.bval ${subject}_dMRI_dir98_PA.nii.gz $output_dir/${subject}_dMRI_dir98_PA_b0.nii.gz -force
    fi

    echo "Processing ${subject}: Converting AP images to MIF format..."
    mrconvert ${subject}_dMRI_dir98_AP.nii.gz $output_dir/${subject}_dMRI_dir98_AP.mif -fslgrad ${subject}_dMRI_dir98_AP.bvec ${subject}_dMRI_dir98_AP.bval -force
    mrconvert ${subject}_dMRI_dir99_AP.nii.gz $output_dir/${subject}_dMRI_dir99_AP.mif -fslgrad ${subject}_dMRI_dir99_AP.bvec ${subject}_dMRI_dir99_AP.bval -force

    echo "Processing ${subject}: Concatenating DWI series..."
    dwicat $output_dir/${subject}_dMRI_dir98_AP.mif $output_dir/${subject}_dMRI_dir99_AP.mif $output_dir/merged_dwi.mif -force

    echo "Processing ${subject}: Converting merged DWI to NIfTI..."
    mrconvert $output_dir/merged_dwi.mif $output_dir/merged_dwi.nii.gz -export_grad_fsl $output_dir/merged.bvec $output_dir/merged.bval -force

    echo "Processing ${subject}: Extracting merged b0 images..."
    if [ ! -e $output_dir/merged_b0.nii.gz ]; then
        dwiextract -bzero $output_dir/merged_dwi.nii.gz $output_dir/merged_b0.nii.gz -fslgrad $output_dir/merged.bvec $output_dir/merged.bval -force
    fi

    bvec="$output_dir/merged.bvec"
    bval="$output_dir/merged.bval"
    json_file="${subject}_dMRI_dir98_AP.json"

    echo "Processing ${subject}: Extracting information from b0 image and JSON file..."
    AP=$(fslval $output_dir/merged_b0.nii.gz dim4)
    AP_readout=$(cat ${json_file} | grep -m 1 "TotalReadoutTime" | sed 's/"TotalReadoutTime": //' | sed 's/,//')

    PA=$(cat ${subject}_dMRI_dir98_PA.json | grep -m 1 "PhaseEncodingDirection" | sed 's/"PhaseEncodingDirection": "//' | sed 's/",//' | sed 's/"//')
    PA_b0=$(fslval $output_dir/${subject}_dMRI_dir98_PA_b0.nii.gz dim4)
    PA_readout=$(cat ${subject}_dMRI_dir98_PA.json | grep -m 1 "TotalReadoutTime" | sed 's/"TotalReadoutTime": //' | sed 's/,//')

    echo "Processing ${subject}: Creating acqparams.txt..."
    rm -rf $output_dir/acqparams.txt
    i=0
    while [ $i -lt ${PA_b0} ]; do
        echo "0 1 0 ${PA_readout}" >> $output_dir/acqparams.txt
        i=$(( $i + 1 ))
    done

    i=0
    while [ $i -lt ${AP} ]; do
        echo "0 -1 0 ${AP_readout}" >> $output_dir/acqparams.txt
        i=$(( $i + 1 ))
    done

    echo "Processing ${subject}: Merging PA and AP b0 images..."
    fslmerge -t $output_dir/PA_AP_b0.nii.gz $output_dir/${subject}_dMRI_dir98_PA_b0.nii.gz $output_dir/merged_b0.nii.gz

    echo "Processing ${subject}: Running topup for distortion correction..."
    if [ ! -e $output_dir/my_hifi_b0_brain.nii.gz ]; then
        topup --imain=$output_dir/PA_AP_b0.nii.gz --datain=$output_dir/acqparams.txt --config=b02b0.cnf --out=$output_dir/my_topup_results --iout=$output_dir/my_hifi_b0
        fslmaths $output_dir/my_hifi_b0 -Tmean $output_dir/my_hifi_b0
        bet $output_dir/my_hifi_b0 $output_dir/my_hifi_b0_brain -m
    fi

    echo "Processing ${subject}: Preparing index file for eddy..."
    indx=""
    read -d '' -r -a bvals < $bval
    len=${#bvals[@]}
    for ((i=1; i<=${len}; i+=1)); do indx="$indx 8"; done
    echo $indx > $output_dir/index.txt

    echo "Cleaning up .mif files for ${subject}..."
    rm -f $output_dir/*.mif

    eddy_script="$output_dir/eddy_correction.sh"
    cat <<EOT > $eddy_script
#!/bin/bash

#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=40G
#SBATCH --time=20:00:00
#SBATCH --partition=a100-gpu,volta-gpu
#SBATCH --output=${output_dir}/eddy_cuda_only-%j.log
#SBATCH --gres=gpu:1
#SBATCH --qos=gpu_access

module load fsl/6.0.6     

echo "Running eddy correction for ${subject}..."

eddy_cuda --imain=$output_dir/merged_dwi.nii.gz \
          --mask=$output_dir/my_hifi_b0_brain_mask.nii.gz \
          --acqp=$output_dir/acqparams.txt \
          --index=$output_dir/index.txt \
          --bvecs=$output_dir/merged.bvec \
          --bvals=$output_dir/merged.bval \
          --topup=$output_dir/my_topup_results \
          --niter=8 \
          --fwhm=10,8,4,2,0,0,0,0 \
          --repol \
          --cnr_maps \
          --out=$output_dir/eddy_corrected_data \
          --mporder=6 \
          --verbose

echo "Eddy correction for ${subject} completed."

EOT

    echo "Submitting eddy correction job for ${subject}..."
    sbatch $eddy_script

    echo "Processing ${subject}: Job submitted."

done

echo "All subjects processed."
