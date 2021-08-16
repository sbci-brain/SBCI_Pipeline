#!/bin/bash

SUBJECT_DIR=${1}
FS_HOME=${2}
CONFIG_DIR=${3}

export FREESURFER_HOME=${FS_HOME}
export SUBJECTS_DIR=${SUBJECT_DIR}/dwi_sbci_connectome/structure

date
echo "Sourcing FREESURFER_HOME"

source $FREESURFER_HOME/SetUpFreeSurfer.sh

cd ${SUBJECT_DIR}/fsfast

SUBJECT_ID=t1_freesurfer

preproc-sess -s ${SUBJECT_ID} -fwhm 5 -surface fsaverage lhrh -per-run -fsd bold -mni305

fcseed-sess -s ${SUBJECT_ID} -cfg ${CONFIG_DIR}/wm.config
fcseed-sess -s ${SUBJECT_ID} -cfg ${CONFIG_DIR}/vcsf.config

cd ..

echo "Functional Preprocessing Complete."
date
