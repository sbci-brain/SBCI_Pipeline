#!/bin/bash

#SBATCH -N 1
#SBATCH -n 4
#SBATCH -p general
#SBATCH -t 6:00:00
#SBATCH --mem=24g
#SBATCH --output=adni_fmri_correction-%j.log

# =============================================================================
# ADNI Resting-State fMRI B0 Distortion Correction — single subject
#
# Usage: sbatch adni_fmri_correction.sh <subject_id>
#   e.g. sbatch adni_fmri_correction.sh sub-130S4417
#
# Do not run this script directly for multiple subjects. Use
# adni_submit_corrections.sh to submit one job per subject.
#
# Prerequisite: adni_dwi_eddy_correction.sh must have completed, producing
#   ${OUTPUT_BASE}/<subject>/dwi/field_hz.nii.gz
#   ${OUTPUT_BASE}/<subject>/dwi/hifi_b0.nii.gz
#
# Strategy: Reuse the Hz fieldmap from the DWI step. Register hifi_b0 into
# fMRI space (6-DOF rigid) and apply the resampled fieldmap via FSL fugue.
#
# Output: ${OUTPUT_BASE}/<subject>/fmri/bold_distcorr.nii.gz
#         Feeds into preproc_step5_fmri.sh (FSFast).
# =============================================================================

SUBJ="${1:?ERROR: Subject ID required. Usage: sbatch adni_fmri_correction.sh sub-XXXXXX}"

BASE_DIR="/overflow/zzhanglab/ADNI/ADNI-bids"
OUTPUT_BASE="/overflow/zzhanglab/ADNI/ADNI-bids"

module load fsl/6.0.7

# ── Helper: map BIDS PhaseEncodingDirection to fugue --unwarpdir string ───────
pe_to_unwarpdir () {
    case "$1" in
        j)   echo "y"  ;;
        j-)  echo "y-" ;;
        i)   echo "x"  ;;
        i-)  echo "x-" ;;
        k)   echo "z"  ;;
        k-)  echo "z-" ;;
        *)   echo "" ;;
    esac
}

SUBJ_DIR="${BASE_DIR}/${SUBJ}"
DWI_EDDY_DIR="${OUTPUT_BASE}/${SUBJ}/dwi"
FMRI_OUT="${OUTPUT_BASE}/${SUBJ}/fmri"
mkdir -p "$FMRI_OUT"

echo ""
echo "════════════════════════════════════════"
echo "  fMRI correction: ${SUBJ}"
echo "  $(date)"
echo "════════════════════════════════════════"

# ── Locate fMRI input files ───────────────────────────────────────────────────
FUNC_DIR="${SUBJ_DIR}/func"
BOLD_RAW=$(find "$FUNC_DIR" -maxdepth 1 -name "*_task-rest_bold.nii*" 2>/dev/null | head -1)
BOLD_JSON="${BOLD_RAW%%_task-rest_bold.nii*}_task-rest_bold.json"

if [ -z "$BOLD_RAW" ] || [ ! -f "$BOLD_JSON" ]; then
    echo "  [ERROR] No func data found — cannot proceed."
    exit 1
fi

if [ -f "${FMRI_OUT}/bold_distcorr.nii.gz" ]; then
    echo "  [SKIP] fMRI distortion correction already done."
    exit 0
fi

# ── Check for DWI fieldmap ────────────────────────────────────────────────────
FIELD_HZ="${DWI_EDDY_DIR}/field_hz.nii.gz"
DWI_B0="${DWI_EDDY_DIR}/hifi_b0.nii.gz"
HAS_FIELDMAP=1
if [ ! -f "$FIELD_HZ" ] || [ ! -f "$DWI_B0" ]; then
    HAS_FIELDMAP=0
    echo "  [WARN] No DWI fieldmap found — will copy BOLD without B0 correction."
    echo "         (adni_dwi_eddy_correction.sh may not have completed yet)"
fi

# ── Parse fMRI acquisition parameters ────────────────────────────────────────
# Siemens: PhaseEncodingDirection / EffectiveEchoSpacing
# Philips: PhaseEncodingAxis      / EstimatedEffectiveEchoSpacing
PE_DIR=$(grep -m1 '"PhaseEncodingDirection"' "$BOLD_JSON" | awk -F'"' '{print $4}')
if [ -z "$PE_DIR" ]; then
    PE_DIR=$(grep -m1 '"PhaseEncodingAxis"' "$BOLD_JSON" | awk -F'"' '{print $4}')
    [ -n "$PE_DIR" ] && echo "  [INFO] Philips scanner — using PhaseEncodingAxis: ${PE_DIR}"
fi
if [ -z "$PE_DIR" ]; then
    PE_DIR="j"
    echo "  [WARN] PE direction not found in JSON — defaulting to j"
fi

EFF_ES=$(grep -m1 '"EffectiveEchoSpacing"' "$BOLD_JSON" | awk -F': ' '{print $2}' | tr -d ', ')
if [ -z "$EFF_ES" ]; then
    EFF_ES=$(grep -m1 '"EstimatedEffectiveEchoSpacing"' "$BOLD_JSON" | awk -F': ' '{print $2}' | tr -d ', ')
    [ -n "$EFF_ES" ] && echo "  [INFO] Philips scanner — using EstimatedEffectiveEchoSpacing: ${EFF_ES} s"
fi
if [ -z "$EFF_ES" ]; then
    EFF_ES="0.000360"
    echo "  [WARN] EffectiveEchoSpacing not found in JSON — defaulting to 0.000360 s"
fi

UNWARP_DIR=$(pe_to_unwarpdir "$PE_DIR")
if [ -z "$UNWARP_DIR" ]; then
    echo "  [ERROR] Unknown PhaseEncodingDirection: ${PE_DIR}"
    exit 1
fi
echo "  fMRI PE: ${PE_DIR} → fugue unwarpdir: ${UNWARP_DIR}"
echo "  EffectiveEchoSpacing: ${EFF_ES} s"

# ── Step 1: Ensure gzipped BOLD ───────────────────────────────────────────────
echo "  [1/6] Compressing BOLD..."
BOLD_GZ="${FMRI_OUT}/bold.nii.gz"
if [[ "$BOLD_RAW" != *.gz ]]; then
    fslchfiletype NIFTI_GZ "$BOLD_RAW" "$BOLD_GZ"
else
    cp "$BOLD_RAW" "$BOLD_GZ"
fi

# ── No fieldmap: copy BOLD as-is ─────────────────────────────────────────────
if [ "$HAS_FIELDMAP" -eq 0 ]; then
    cp "$BOLD_GZ" "${FMRI_OUT}/bold_distcorr.nii.gz"
    echo "  [WARN] bold_distcorr.nii.gz is uncorrected (no DWI fieldmap available)."
    exit 0
fi

# ── Step 2: Temporal mean of BOLD ─────────────────────────────────────────────
echo "  [2/6] Computing mean BOLD..."
fslmaths "$BOLD_GZ" -Tmean "${FMRI_OUT}/mean_bold.nii.gz"

# ── Step 3: Brain-extract mean BOLD ──────────────────────────────────────────
echo "  [3/6] Brain-extracting mean BOLD..."
bet "${FMRI_OUT}/mean_bold.nii.gz" \
    "${FMRI_OUT}/mean_bold_brain.nii.gz" \
    -m -f 0.30

# ── Step 4: Register DWI hifi_b0 → fMRI space (6-DOF) ───────────────────────
echo "  [4/6] Registering DWI b0 → fMRI space..."
flirt \
    -in      "$DWI_B0" \
    -ref     "${FMRI_OUT}/mean_bold.nii.gz" \
    -out     "${FMRI_OUT}/b0_in_fmri_space.nii.gz" \
    -omat    "${FMRI_OUT}/b0_to_fmri.mat" \
    -dof     6 \
    -cost    normcorr \
    -searchrx -10 10 \
    -searchry -10 10 \
    -searchrz -10 10

flirt \
    -in      "$FIELD_HZ" \
    -ref     "${FMRI_OUT}/mean_bold.nii.gz" \
    -out     "${FMRI_OUT}/field_hz_fmri.nii.gz" \
    -init    "${FMRI_OUT}/b0_to_fmri.mat" \
    -applyxfm \
    -interp  trilinear

# ── Step 5: Lightly smooth the fieldmap ──────────────────────────────────────
echo "  [5/6] Smoothing resampled fieldmap..."
fslmaths "${FMRI_OUT}/field_hz_fmri.nii.gz" \
         -s 1.5 \
         "${FMRI_OUT}/field_hz_fmri_smooth.nii.gz"

# ── Step 6: Apply B0 distortion correction via fugue ─────────────────────────
echo "  [6/6] Applying distortion correction to full 4-D BOLD..."
fugue \
    --loadfmap="${FMRI_OUT}/field_hz_fmri_smooth.nii.gz" \
    --dwell="${EFF_ES}" \
    -i     "$BOLD_GZ" \
    --mask="${FMRI_OUT}/mean_bold_brain_mask.nii.gz" \
    --unwarpdir="${UNWARP_DIR}" \
    -u     "${FMRI_OUT}/bold_distcorr.nii.gz" \
    --verbose

echo "  Done: ${FMRI_OUT}/bold_distcorr.nii.gz"
echo "  $(date)"
