#!/bin/bash

# Scan the ADNI BIDS directory and categorize subjects by available modalities.
#
# Usage: ./adni_scan_subjects.sh [output_dir]
#   output_dir: where to write subject lists and the scan log (default: current dir)
#
# Output files:
#   adni_scan_log.txt              — per-subject table of available modalities
#   subjects_anat_dwi_func.txt     — complete subjects (all three modalities)
#   subjects_anat_dwi_only.txt     — subjects with anat + DWI but no fMRI
#   subjects_anat_func_only.txt    — subjects with anat + fMRI but no DWI
#   subjects_anat_only.txt         — subjects with only T1w

BASE_DIR="/overflow/zzhanglab/ADNI/ADNI-bids"
OUT_DIR="${1:-.}"
mkdir -p "$OUT_DIR"

LOG="${OUT_DIR}/adni_scan_log.txt"
LIST_ALL3="${OUT_DIR}/subjects_anat_dwi_func.txt"
LIST_DWI_ONLY="${OUT_DIR}/subjects_anat_dwi_only.txt"
LIST_FUNC_ONLY="${OUT_DIR}/subjects_anat_func_only.txt"
LIST_ANAT_ONLY="${OUT_DIR}/subjects_anat_only.txt"

> "$LIST_ALL3"
> "$LIST_DWI_ONLY"
> "$LIST_FUNC_ONLY"
> "$LIST_ANAT_ONLY"

n_all3=0; n_dwi_only=0; n_func_only=0; n_anat_only=0; n_total=0

printf "%-32s  %-4s  %-4s  %-4s\n" "Subject" "T1w" "DWI" "Func" > "$LOG"
printf "%-32s  %-4s  %-4s  %-4s\n" "--------------------------------" "----" "----" "----" >> "$LOG"

for SUBJ_DIR in "${BASE_DIR}"/sub-*; do
    [ -d "$SUBJ_DIR" ] || continue
    SUBJ=$(basename "$SUBJ_DIR")
    n_total=$((n_total + 1))

    # ── Check T1w ────────────────────────────────────────────────────────────
    HAS_ANAT=0
    T1=$(find "${SUBJ_DIR}/anat" -maxdepth 1 -name "*_T1w.nii*" 2>/dev/null | head -1)
    [ -n "$T1" ] && HAS_ANAT=1

    # ── Check DWI (needs nii + bval + bvec + json, dir-AP) ───────────────────
    HAS_DWI=0
    if [ -d "${SUBJ_DIR}/dwi" ]; then
        DWI=$(find "${SUBJ_DIR}/dwi" -maxdepth 1 -name "*_dir-AP_dwi.nii*" 2>/dev/null | head -1)
        if [ -n "$DWI" ]; then
            BASE="${DWI%%_dir-AP_dwi.nii*}"
            if [ -f "${BASE}_dir-AP_dwi.bval" ] && \
               [ -f "${BASE}_dir-AP_dwi.bvec" ] && \
               [ -f "${BASE}_dir-AP_dwi.json" ]; then
                HAS_DWI=1
            fi
        fi
    fi

    # ── Check resting-state fMRI (needs nii + json) ───────────────────────────
    HAS_FUNC=0
    if [ -d "${SUBJ_DIR}/func" ]; then
        BOLD=$(find "${SUBJ_DIR}/func" -maxdepth 1 -name "*_task-rest_bold.nii*" 2>/dev/null | head -1)
        if [ -n "$BOLD" ]; then
            BOLD_JSON="${BOLD%%_task-rest_bold.nii*}_task-rest_bold.json"
            [ -f "$BOLD_JSON" ] && HAS_FUNC=1
        fi
    fi

    # ── Log and classify ─────────────────────────────────────────────────────
    T1_STR=$([ $HAS_ANAT  -eq 1 ] && echo "yes" || echo "no")
    DWI_STR=$([ $HAS_DWI  -eq 1 ] && echo "yes" || echo "no")
    FUNC_STR=$([ $HAS_FUNC -eq 1 ] && echo "yes" || echo "no")
    printf "%-32s  %-4s  %-4s  %-4s\n" "$SUBJ" "$T1_STR" "$DWI_STR" "$FUNC_STR" >> "$LOG"

    if   [ $HAS_ANAT -eq 1 ] && [ $HAS_DWI -eq 1 ] && [ $HAS_FUNC -eq 1 ]; then
        echo "$SUBJ" >> "$LIST_ALL3";    n_all3=$((n_all3 + 1))
    elif [ $HAS_ANAT -eq 1 ] && [ $HAS_DWI -eq 1 ]; then
        echo "$SUBJ" >> "$LIST_DWI_ONLY"; n_dwi_only=$((n_dwi_only + 1))
    elif [ $HAS_ANAT -eq 1 ] && [ $HAS_FUNC -eq 1 ]; then
        echo "$SUBJ" >> "$LIST_FUNC_ONLY"; n_func_only=$((n_func_only + 1))
    else
        echo "$SUBJ" >> "$LIST_ANAT_ONLY"; n_anat_only=$((n_anat_only + 1))
    fi
done

{
    echo ""
    echo "────────────────────────────────────────"
    echo "  Summary (${n_total} subjects scanned)"
    echo "────────────────────────────────────────"
    printf "  %-38s %d\n" "Anat + DWI + fMRI (complete):"  $n_all3
    printf "  %-38s %d\n" "Anat + DWI only:"                $n_dwi_only
    printf "  %-38s %d\n" "Anat + fMRI only:"               $n_func_only
    printf "  %-38s %d\n" "Anat only:"                      $n_anat_only
    echo ""
    echo "  Subject lists written to: ${OUT_DIR}/"
    echo "    subjects_anat_dwi_func.txt  ← use this for adni_submit_corrections.sh"
    echo "    subjects_anat_dwi_only.txt"
    echo "    subjects_anat_func_only.txt"
    echo "    subjects_anat_only.txt"
    echo "  Full log: ${LOG}"
} | tee -a "$LOG"
