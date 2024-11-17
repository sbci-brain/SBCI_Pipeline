#!/bin/bash


IN=${1} #subject list
DATA=${2} #path of the data
OUT=${3} #path to write the qc log

# get all subject names
mapfile -t subjects < ${IN}

# make sure there are subjects
if [[ ${#subjects[@]} -eq 0 ]]; then
    echo "no subjects found in ${IN}"
    exit 1
fi

echo "Checking ${#subjects[@]} subject(s)"

rootdir=$(pwd)

printf "Subject\t Status\n" > ${OUT}/psc_qc_log

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))
    cd ${DATA}/${subjects[$idx]}

    if [ ! -f "./dwi_pipeline/psc_connectome/HCP_Aging_desikan_cm_count_processed.mat" ]; then
	printf "${subjects[$idx]}\t FAILED\n" >> ${OUT}/psc_qc_log
    else
	printf "${subjects[$idx]}\t COMPLETE\n" >> ${OUT}/psc_qc_log
	#cd dwi_pipeline/structure
	#mkdir -p ${OUT}/${subjects[$idx]}
	#fsleyes render -of ${OUT}/${subjects[$idx]}/t1_parc.png -sortho t1_warped.nii.gz wmparc_warped_label.nii.gz 
    fi

    cd ${rootdir}
done

