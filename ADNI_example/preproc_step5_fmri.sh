#!/bin/bash

# =============================================================================
# preproc_step5_fmri.sh — ADNI resting-state fMRI preprocessing
#
# Adapted from integrated_pipeline/preproc_step5_fmri.sh for ADNI-specific
# acquisition parameters:
#   - TR = 3 s  (not 2.5 s)
#   - 48 slices, Siemens interleaved slice ordering
#   - Single run per subject (no run-* in filename)
#   - Input BOLD is the distortion-corrected image from adni_fmri_correction.sh
#     (bold_distcorr.nii.gz); raw bold.nii is used as fallback if absent
#   - No pre-computed motion .tsv files; FSFast handles motion correction
#     internally via -mcextreg
#
# Changes from integrated_pipeline version:
#   1. Added data-preparation block: copies BOLD into fsfast/bold/001/f.nii.gz
#   2. -TR 2.5 → -TR 3
#   3. Added -nskip 4 (skip 12 s of T1 saturation at TR=3)
#   4. -polyfit 1 → -polyfit 2 (quadratic detrending; TR=3 s has more drift)
#   5. SUBJECTS_DIR updated to match ADNI working directory structure
#
# Expected working directory structure before running this script:
#   <subject_dir>/
#   ├── dwi_pipeline/structure/t1_freesurfer/  (from preproc_step3)
#   └── fmri_distcorr/bold_distcorr.nii.gz            (from adni_fmri_correction.sh)
#       OR func/<subject>_task-rest_bold.nii           (raw fallback)
#
# Outputs:
#   fmri/bold/001/fc.surface.lh.nii.gz
#   fmri/bold/001/fc.surface.rh.nii.gz
#   fmri/bold/001/fc.mni.nii.gz
# =============================================================================

echo "Sourcing SBCI config file"
source ${SBCI_CONFIG}

echo "Sourcing FREESURFER_HOME"
source ${FREESURFER_PATH}/SetUpFreeSurfer.sh

echo "Begin FSFast fMRI preprocessing: $(date)"

export SUBJECTS_DIR=$(pwd)/dwi_pipeline/structure

# =============================================================================
# Data preparation: place BOLD into FSFast directory layout
#
# FSFast expects: fsfast/bold/<3-digit-run>/f.nii.gz
# ADNI has a single resting-state run → run 001
# Input priority:
#   1. fmri_distcorr/bold_distcorr.nii.gz  (B0-corrected, from adni_fmri_correction.sh)
#   2. func/*_task-rest_bold.nii(.gz)       (raw fallback)
# =============================================================================

RUN_DIR="fsfast/bold/001"
mkdir -p "${RUN_DIR}"

if [ ! -f "${RUN_DIR}/f.nii.gz" ]; then
    if [ -f "fmri_distcorr/bold_distcorr.nii.gz" ]; then
        echo "Using B0-corrected BOLD: fmri_distcorr/bold_distcorr.nii.gz"
        cp "fmri_distcorr/bold_distcorr.nii.gz" "${RUN_DIR}/f.nii.gz"
    else
        BOLD_RAW=$(find func -maxdepth 1 -name "*_task-rest_bold.nii*" | head -1)
        if [ -z "$BOLD_RAW" ]; then
            echo "ERROR: No BOLD file found. Exiting."
            exit 1
        fi
        echo "WARNING: B0-corrected BOLD not found. Using raw: ${BOLD_RAW}"
        echo "         Run adni_fmri_correction.sh first for best results."
        if [[ "$BOLD_RAW" != *.gz ]]; then
            fslchfiletype NIFTI_GZ "$BOLD_RAW" "${RUN_DIR}/f.nii.gz"
        else
            cp "$BOLD_RAW" "${RUN_DIR}/f.nii.gz"
        fi
    fi
else
    echo "fsfast/bold/001/f.nii.gz already exists. Skipping copy."
fi

# =============================================================================
# FSFast preprocessing
# preproc-sess performs:
#   - Motion correction (mcflirt-based)
#   - Slice timing correction (Siemens interleaved: bottom-up alternating)
#   - Spatial smoothing (5 mm FWHM)
#   - Registration to fsaverage surface and MNI305 volume
# =============================================================================

cd fsfast
echo t1_freesurfer > subjectname

SUBJECT_ID=.

preproc-sess \
    -s ${SUBJECT_ID} \
    -fwhm 5 \
    -stc siemens \
    -surface fsaverage lhrh \
    -per-run \
    -fsd bold \
    -mni305 \
    -force

# =============================================================================
# Extract nuisance signals: white matter and ventricular CSF
# =============================================================================

fcseed-config -wm   -fcname wm.dat   -fsd bold -mean -cfg wm.config   -force
fcseed-config -vcsf -fcname vcsf.dat -fsd bold -mean -cfg vcsf.config -force

fcseed-sess -s ${SUBJECT_ID} -cfg wm.config   -force
fcseed-sess -s ${SUBJECT_ID} -cfg vcsf.config -force

# =============================================================================
# Nuisance regression model definition (mkanalysis-sess)
#
# Nuisance regressors:
#   vcsf.dat 1    — ventricular CSF mean signal
#   wm.dat 1      — white matter mean signal
#   global.waveform.dat 1 — whole-brain global signal
#   -mcextreg     — 6 FSFast-internal motion parameters (from preproc-sess MC)
#
# Temporal processing:
#   -TR 3         — ADNI repetition time
#   -stc siemens  — slice timing correction (interleaved Siemens, 48 slices)
#   -nskip 4      — discard first 4 frames (12 s T1 saturation at TR=3 s)
#   -polyfit 2    — quadratic detrending (longer TR → more low-freq drift)
#   -hpf 0.009    — highpass filter cutoff in Hz  (111 s period)
#   -lpf 0.08     — lowpass filter cutoff in Hz   (12.5 s period)
#   -inorm        — intensity normalisation
#   -fwhm 5       — spatial smoothing (redundant with preproc-sess but kept
#                   here so mkanalysis records it in the design matrix)
# =============================================================================

mkanalysis-sess -analysis fc.surface.lh \
    -surface fsaverage lh \
    -per-run \
    -nskip 4 \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 2 \
    -fsd bold \
    -TR 3 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force

mkanalysis-sess -analysis fc.surface.rh \
    -surface fsaverage rh \
    -per-run \
    -nskip 4 \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 2 \
    -fsd bold \
    -TR 3 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force

mkanalysis-sess -analysis fc.mni \
    -mni305 \
    -per-run \
    -nskip 4 \
    -fwhm 5 \
    -notask \
    -nuisreg vcsf.dat 1 \
    -nuisreg wm.dat 1 \
    -nuisreg global.waveform.dat 1 \
    -mcextreg \
    -polyfit 2 \
    -fsd bold \
    -TR 3 \
    -stc siemens \
    -hpf 0.009 \
    -lpf 0.08 \
    -inorm \
    -force

# =============================================================================
# Apply nuisance regression; save residuals as cleaned BOLD
# =============================================================================

selxavg3-sess -analysis fc.surface.lh -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.surface.rh -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force
selxavg3-sess -analysis fc.mni        -s ${SUBJECT_ID} -no-con-ok -run-wise -svres -force

# =============================================================================
# Collect outputs
# =============================================================================

cd ..

find ./fsfast/bold/ -regextype sed -regex ".*/[0-9]\+$" -type d -printf "%f\n" > ./fcruns

while read BOLDRUN; do
    mkdir -p fmri/bold/${BOLDRUN}
    mv ./fsfast/bold/fc.surface.lh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz \
       ./fmri/bold/${BOLDRUN}/fc.surface.lh.nii.gz
    mv ./fsfast/bold/fc.surface.rh/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz \
       ./fmri/bold/${BOLDRUN}/fc.surface.rh.nii.gz
    mv ./fsfast/bold/fc.mni/pr${BOLDRUN}/res/res-${BOLDRUN}.nii.gz \
       ./fmri/bold/${BOLDRUN}/fc.mni.nii.gz
done < ./fcruns

echo "Finished FSFast fMRI preprocessing: $(date)"
