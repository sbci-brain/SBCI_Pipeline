#!/bin/bash

#SBATCH -N 1
#SBATCH -n 8
#SBATCH -p general
#SBATCH -t 12:00:00
#SBATCH --mem=32g
#SBATCH --output=adni_dwi_eddy-%j.log

# =============================================================================
# ADNI DWI Eddy/Distortion Correction — single subject
#
# Usage: sbatch adni_dwi_eddy_correction.sh <subject_id>
#   e.g. sbatch adni_dwi_eddy_correction.sh sub-130S4417
#
# Do not run this script directly for multiple subjects. Use
# adni_submit_corrections.sh to submit one job per subject.
#
# Strategy: Synb0-DISCO synthesizes an undistorted b0 from the T1w image.
# The real (distorted) b0 and synthetic (undistorted) b0 are fed into FSL
# topup as if they were an AP/PA pair. FSL eddy_cuda then uses the resulting
# field estimate to correct eddy currents and head motion.
#
# Outputs (under ${OUTPUT_BASE}/<subject>/dwi/):
#   eddy_corrected_data.nii.gz           — motion + eddy + distortion corrected DWI
#   eddy_corrected_data.eddy_rotated_bvecs — bvecs rotated for head motion
#   ap_dwi.bval                          — b-values (copied from BIDS)
#   field_hz.nii.gz                      — B0 fieldmap in Hz (used by fMRI script)
#   hifi_b0.nii.gz                       — distortion-corrected b0
#   topup_results.*                      — topup coefficient files
# =============================================================================

SUBJ="${1:?ERROR: Subject ID required. Usage: sbatch adni_dwi_eddy_correction.sh sub-XXXXXX}"

BASE_DIR="/overflow/zzhanglab/ADNI/ADNI-bids"
OUTPUT_BASE="/overflow/zzhanglab/ADNI/ADNI-bids"
SYNB0_SIF="/work/users/z/z/zz10c/app/synb0-disco_v3.1.sif"
FREESURFER_LICENSE="/nas/longleaf/apps/freesurfer/8.2.0/freesurfer/license.txt"

module load fsl/6.0.7
module load gcc/11.2.0

# ── Helper: map BIDS PhaseEncodingDirection to FSL acqparams vector ──────────
pe_to_vec () {
    case "$1" in
        j)   echo "0 1 0"  ;;
        j-)  echo "0 -1 0" ;;
        i)   echo "1 0 0"  ;;
        i-)  echo "-1 0 0" ;;
        k)   echo "0 0 1"  ;;
        k-)  echo "0 0 -1" ;;
        *)   echo "" ;;
    esac
}

SUBJ_DIR="${BASE_DIR}/${SUBJ}"
OUT="${OUTPUT_BASE}/${SUBJ}/dwi"
mkdir -p "$OUT"

echo ""
echo "════════════════════════════════════════"
echo "  DWI eddy correction: ${SUBJ}"
echo "  $(date)"
echo "════════════════════════════════════════"

# ── Locate input files ────────────────────────────────────────────────────────
DWI_DIR="${SUBJ_DIR}/dwi"
ANAT_DIR="${SUBJ_DIR}/anat"

AP_DWI=$(find "$DWI_DIR" -maxdepth 1 -name "*_dir-AP_dwi.nii*" 2>/dev/null | head -1)
T1_RAW=$(find "$ANAT_DIR" -maxdepth 1 -name "*_T1w.nii*"       2>/dev/null | head -1)

if [ -z "$AP_DWI" ] || [ -z "$T1_RAW" ]; then
    echo "  [ERROR] Required DWI or T1 not found — cannot proceed."
    exit 1
fi

AP_BVAL="${AP_DWI%%_dir-AP_dwi.nii*}_dir-AP_dwi.bval"
AP_BVEC="${AP_DWI%%_dir-AP_dwi.nii*}_dir-AP_dwi.bvec"
AP_JSON="${AP_DWI%%_dir-AP_dwi.nii*}_dir-AP_dwi.json"

for f in "$AP_BVAL" "$AP_BVEC" "$AP_JSON"; do
    if [ ! -f "$f" ]; then
        echo "  [ERROR] Missing: $(basename $f)"
        exit 1
    fi
done

if [ -f "${OUT}/eddy_corrected_data.nii.gz" ]; then
    echo "  [SKIP] Eddy correction already done."
    exit 0
fi

# ── Step 1: Ensure gzipped inputs ────────────────────────────────────────────
echo "  [1/6] Compressing inputs..."
DWI_GZ="${OUT}/ap_dwi.nii.gz"
T1_GZ="${OUT}/t1.nii.gz"
cp "$AP_BVAL" "${OUT}/ap_dwi.bval"
cp "$AP_BVEC" "${OUT}/ap_dwi.bvec"

if [[ "$AP_DWI" != *.gz ]]; then
    fslchfiletype NIFTI_GZ "$AP_DWI" "$DWI_GZ"
else
    cp "$AP_DWI" "$DWI_GZ"
fi
if [[ "$T1_RAW" != *.gz ]]; then
    fslchfiletype NIFTI_GZ "$T1_RAW" "$T1_GZ"
else
    cp "$T1_RAW" "$T1_GZ"
fi

# ── Parse acquisition parameters ─────────────────────────────────────────────
# Siemens: PhaseEncodingDirection / TotalReadoutTime
# Philips: PhaseEncodingAxis      / EstimatedTotalReadoutTime
PE_DIR=$(grep -m1 '"PhaseEncodingDirection"' "$AP_JSON" | awk -F'"' '{print $4}')
if [ -z "$PE_DIR" ]; then
    PE_DIR=$(grep -m1 '"PhaseEncodingAxis"' "$AP_JSON" | awk -F'"' '{print $4}')
    [ -n "$PE_DIR" ] && echo "  [INFO] Philips scanner — using PhaseEncodingAxis: ${PE_DIR}"
fi
if [ -z "$PE_DIR" ]; then
    PE_DIR="j"
    echo "  [WARN] PE direction not found in JSON — defaulting to j"
fi

TOTAL_RT=$(grep -m1 '"TotalReadoutTime"' "$AP_JSON" | awk -F': ' '{print $2}' | tr -d ', ')
if [ -z "$TOTAL_RT" ]; then
    TOTAL_RT=$(grep -m1 '"EstimatedTotalReadoutTime"' "$AP_JSON" | awk -F': ' '{print $2}' | tr -d ', ')
    [ -n "$TOTAL_RT" ] && echo "  [INFO] Philips scanner — using EstimatedTotalReadoutTime: ${TOTAL_RT} s"
fi
if [ -z "$TOTAL_RT" ]; then
    TOTAL_RT="0.0449"
    echo "  [WARN] TotalReadoutTime not found in JSON — defaulting to 0.0449 s"
fi

PE_VEC=$(pe_to_vec "$PE_DIR")
if [ -z "$PE_VEC" ]; then
    echo "  [ERROR] Unknown PhaseEncodingDirection: ${PE_DIR}"
    exit 1
fi
echo "  PE direction: ${PE_DIR} → FSL vec: ${PE_VEC}"
echo "  TotalReadoutTime: ${TOTAL_RT} s"

# ── Check for Philips trailing-volume mismatch ────────────────────────────────
# Philips appends an extra ADC/reference volume that dcm2niix puts in the NIfTI
# but omits from bvec/bval. Strip it.
NVOLS_NII=$(fslval "$DWI_GZ" dim4)
NVOLS_BVEC=$(awk 'NR==1{print NF}' "${OUT}/ap_dwi.bvec")
if [ "$NVOLS_NII" -gt "$NVOLS_BVEC" ]; then
    echo "  [WARN] NIfTI has ${NVOLS_NII} vols but bvec has ${NVOLS_BVEC} — trimming trailing $((NVOLS_NII - NVOLS_BVEC)) volume(s)"
    fslroi "$DWI_GZ" "${OUT}/ap_dwi_tmp.nii.gz" 0 "$NVOLS_BVEC"
    mv "${OUT}/ap_dwi_tmp.nii.gz" "$DWI_GZ"
fi

# ── Step 2: Extract b0 volume ─────────────────────────────────────────────────
echo "  [2/6] Extracting b0..."
fslroi "$DWI_GZ" "${OUT}/b0.nii.gz" 0 1

# ── Step 3: Skull-strip T1 ────────────────────────────────────────────────────
echo "  [3/6] Brain-extracting T1..."
if [ ! -f "${OUT}/t1_bet.nii.gz" ]; then
    bet "$T1_GZ" "${OUT}/t1_bet.nii.gz" -R -f 0.35 -m
else
    echo "  T1 BET already done."
fi

# ── Step 4: Synb0-DISCO ───────────────────────────────────────────────────────
echo "  [4/6] Running Synb0-DISCO..."
SYNB0_IN="${OUT}/synb0_input"
SYNB0_OUT="${OUT}/synb0_output"
mkdir -p "$SYNB0_IN" "$SYNB0_OUT"

cp "${OUT}/t1.nii.gz" "${SYNB0_IN}/T1.nii.gz"
cp "${OUT}/b0.nii.gz" "${SYNB0_IN}/b0.nii.gz"

# acqparams: both rows use the SAME PE direction.
# Row 2 readout = 0.000 tells topup the synthetic b0 has no distortion.
ACQP="${OUT}/acqparams.txt"
printf "%s %s\n%s %s\n" "$PE_VEC" "$TOTAL_RT" "$PE_VEC" "0.000" > "$ACQP"
cp "$ACQP" "${SYNB0_IN}/acqparams.txt"

if [ ! -f "${SYNB0_OUT}/b0_u.nii.gz" ]; then
    apptainer run --nv \
        -B "${SYNB0_IN}:/INPUTS" \
        -B "${SYNB0_OUT}:/OUTPUTS" \
        -B "${FREESURFER_LICENSE}:/extra/freesurfer/license.txt" \
        "${SYNB0_SIF}" \
        --notopup
else
    echo "  Synb0-DISCO output already exists."
fi

if [ ! -f "${SYNB0_OUT}/b0_u.nii.gz" ]; then
    echo "  [ERROR] Synb0-DISCO failed — b0_u.nii.gz not produced."
    exit 1
fi

# Synb0-DISCO v3.1 with --notopup does not concatenate outputs. Merge manually.
if [ ! -f "${SYNB0_OUT}/b0_all.nii.gz" ]; then
    echo "  Merging b0_d_smooth + b0_u → b0_all.nii.gz..."
    fslmerge -t "${SYNB0_OUT}/b0_all.nii.gz" \
        "${SYNB0_OUT}/b0_d_smooth.nii.gz" \
        "${SYNB0_OUT}/b0_u.nii.gz"
fi

# ── Step 5: topup ─────────────────────────────────────────────────────────────
echo "  [5/6] Running topup..."
if [ ! -f "${OUT}/topup_results_fieldcoef.nii.gz" ]; then
    topup \
        --imain="${SYNB0_OUT}/b0_all.nii.gz" \
        --datain="${ACQP}" \
        --config=b02b0.cnf \
        --out="${OUT}/topup_results" \
        --iout="${OUT}/hifi_b0" \
        --fout="${OUT}/field_hz" \
        --verbose

    fslmaths "${OUT}/hifi_b0" -Tmean "${OUT}/hifi_b0"
    bet "${OUT}/hifi_b0" "${OUT}/hifi_b0_brain" -m -f 0.20
else
    echo "  Topup already done."
fi

# ── Step 6: Submit eddy_cuda as a GPU job ────────────────────────────────────
echo "  [6/6] Submitting eddy_cuda GPU job..."

NVOLS=$(fslval "$DWI_GZ" dim4)
python3 -c "print(' '.join(['1']*${NVOLS}))" > "${OUT}/index.txt"

EDDY_SCRIPT="${OUT}/run_eddy_cuda.sh"
cat > "$EDDY_SCRIPT" <<EDDY_HEREDOC
#!/bin/bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=40G
#SBATCH --time=20:00:00
#SBATCH --partition=l40-gpu,a100-gpu,volta-gpu
#SBATCH --gres=gpu:1
#SBATCH --qos=gpu_access
#SBATCH --output=${OUT}/eddy_cuda-%j.log

module load fsl/6.0.7

echo "Running eddy_cuda for ${SUBJ} at \$(date)..."

eddy_cuda \\
    --imain=${DWI_GZ} \\
    --mask=${OUT}/hifi_b0_brain_mask.nii.gz \\
    --acqp=${OUT}/acqparams.txt \\
    --index=${OUT}/index.txt \\
    --bvecs=${OUT}/ap_dwi.bvec \\
    --bvals=${OUT}/ap_dwi.bval \\
    --topup=${OUT}/topup_results \\
    --niter=8 \\
    --fwhm=10,8,4,2,0,0,0,0 \\
    --repol \\
    --cnr_maps \\
    --out=${OUT}/eddy_corrected_data \\
    --verbose

echo "eddy_cuda done for ${SUBJ} at \$(date)."
EDDY_HEREDOC

chmod +x "$EDDY_SCRIPT"
sbatch "$EDDY_SCRIPT"
echo "  GPU eddy job submitted for ${SUBJ}."
echo "  Main DWI script done: $(date)"
