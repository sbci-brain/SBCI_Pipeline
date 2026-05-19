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

printf "Subject\t SC Status\t FC Status\n" > ${OUT}/sbci_qc_log

for i in $(seq 1 ${#subjects[@]}); do
    idx=$((i - 1))
    cd ${DATA}/${subjects[$idx]}

    SCSTATUS="COMPLETE"
    FCSTATUS="COMPLETE"

    if [ ! -f "./dwi_pipeline/sbci_connectome/smoothed_sc_avg_0.005_ico4.mat" ]; then
        SCSTATUS="FAILED"
    fi
    if [ ! -f "./dwi_pipeline/sbci_connectome/fc_avg_ico4.mat" ]; then
        FCSTATUS="FAILED" 
    fi

    #cd dwi_pipeline/structure
    #mkdir -p ${OUT}/${subjects[$idx]}
    #fsleyes render -of ${OUT}/${subjects[$idx]}/t1_parc.png -sortho t1_warped.nii.gz wmparc_warped_label.nii.gz 

    printf "${subjects[$idx]}\t ${SCSTATUS}\t ${FCSTATUS}\n" >> ${OUT}/sbci_qc_log

    cd ${rootdir}
done

