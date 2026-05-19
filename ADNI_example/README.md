# ADNI SBCI Pipeline — Longleaf User Guide

Adaptation of the SBCI pipeline for ADNI diffusion MRI and resting-state fMRI data on the
UNC Longleaf HPC cluster.

> **Order matters.** Most steps restructure the subject folder, causing earlier steps to fail
> if re-run afterward. If you need to restart preprocessing for a subject, you must begin
> again from `adni_dwi_eddy_correction.sh`. Do not run steps out of order.

---

## Table of Contents

1. [Why ADNI requires a separate pipeline](#1-why-adni-requires-a-separate-pipeline)
2. [Key ADNI acquisition parameters](#2-key-adni-acquisition-parameters)
3. [Software prerequisites](#3-software-prerequisites)
4. [Configuration](#4-configuration)
5. [Prepare a subject list](#5-prepare-a-subject-list)
6. [Phase 0 — ADNI-specific corrections](#6-phase-0--adni-specific-corrections)
7. [Phase 1 — SBCI preprocessing](#7-phase-1--sbci-preprocessing)
8. [Phase 2 — PSC tractography](#8-phase-2--psc-tractography)
9. [Phase 3 — SBCI connectome](#9-phase-3--sbci-connectome)
10. [Quality control](#10-quality-control)
11. [Clean subject folders](#11-clean-subject-folders)
12. [Scripts reference](#12-scripts-reference)

---

## 1. Why ADNI requires a separate pipeline

The standard SBCI pipeline assumes that DWI and fMRI data were acquired in **two opposite
phase-encoding directions** (AP and PA). The AP/PA pair is fed into FSL `topup` to estimate
the B0 field distortion, which `eddy` then corrects.

**ADNI does not collect opposite phase-encoding data.** Every subject has only a single
phase-encoding direction (`dir-AP` in BIDS filenames). Two custom scripts handle this:

- `adni_dwi_eddy_correction.sh` — uses **Synb0-DISCO** to synthesize an undistorted b0
  from the T1w image. The real (distorted) b0 and synthetic (undistorted) b0 are fed into
  `topup` as if they were a genuine AP/PA pair. `eddy_cuda` then corrects the full DWI series.

- `adni_fmri_correction.sh` — reuses the B0 fieldmap (in Hz) produced by the DWI step.
  The fieldmap is registered into fMRI voxel space (6-DOF rigid) and applied via FSL `fugue`.

**ADNI also has a mixed-scanner cohort.** Siemens TrioTim and Philips Achieva dStream scanners
use different JSON field names. The scripts detect the scanner type automatically and fall back
gracefully when fields are missing.

**Not all subjects have all three modalities.** The scripts handle this:
- anat + DWI only → DWI script runs; fMRI script skips (no func data)
- anat + DWI + fMRI → both scripts run fully
- anat + fMRI only → DWI script skips; fMRI script copies raw BOLD without B0 correction

---

## 2. Key ADNI acquisition parameters

| Modality | TR | TE | PE direction | TotalReadoutTime | Voxel size | b-values |
|---|---|---|---|---|---|---|
| DWI | 12.4 s | 95 ms | j (A→P) | 0.0449 s (Siemens) | 2 mm iso | b=0 (×1), b=1000 (×30) |
| rsfMRI | 3 s | 30 ms | j (A→P) | — | 3.4 mm iso | — |
| T1w (MPRAGE) | 2.3 s | 3 ms | — | — | 1 mm iso | — |

Philips scanners use `PhaseEncodingAxis` / `EstimatedTotalReadoutTime` /
`EstimatedEffectiveEchoSpacing` instead of the Siemens field names. The scripts handle both.

---

## 3. Software prerequisites

All modules are available on Longleaf. No manual installation is needed.

| Software | Longleaf module | Notes |
|---|---|---|
| FSL | `fsl/6.0.7` | topup, eddy, BET, fugue, flirt |
| FreeSurfer | `freesurfer/6.0.0` | recon-all in preproc_step3 |
| MRtrix3 | `mrtrix3/3.0.8` | mrconvert in preproc_step1 |
| ANTs | `ants/2.5.4` | registration in preproc_step2 |
| Synb0-DISCO | Apptainer `.sif` | see path below |
| CUDA | via GPU partition | required by eddy_cuda |

Key file paths on Longleaf:

```
BIDS root + output:  /overflow/zzhanglab/ADNI/ADNI-bids/
Scripts:             /nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example/
Synb0-DISCO image:   /work/users/z/z/zz10c/app/synb0-disco_v3.1.sif
FreeSurfer license:  /nas/longleaf/apps/freesurfer/8.2.0/freesurfer/license.txt
PSC_Pipeline:        /nas/longleaf/home/zz10c/software/PSC_Pipeline/
SBCI_Pipeline:       /nas/longleaf/home/zz10c/software/SBCI_Pipeline/
```

---

## 4. Configuration

Two files need to be configured before the first run.

### sbci_config

Located at `ADNI_example/sbci_config`. The critical settings for ADNI:

```bash
DATASET_NAME=ADNI

# Single-shell acquisition: b=0 and b=1000 only (no b=2000 shell)
DTI_BVALS=(0 1000)
FODF_BVALS=(0 1000)

# Pipeline installation paths
PSC_PATH=/nas/longleaf/home/zz10c/software/PSC_Pipeline/
SBCI_PATH=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/
FREESURFER_PATH=/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/

# Where averaged SBCI templates will be written (shared across subjects)
OUTPUT_PATH=/overflow/zzhanglab/ADNI/ADNI-bids/SBCI_AVE
```

### preprocess.sh / process_psc.sh / process_sbci.sh

Each of these orchestration scripts has **two lines** that you may need to update:

```bash
# Line 1 — source your personal bashrc that loads the conda env / modules
source ~/.bashrc_sbci

# Line 2 — point to the ADNI sbci_config (already set correctly if using ADNI_example)
export SBCI_CONFIG=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example/sbci_config
```

---

## 5. Prepare a subject list

The subject list is a plain text file — one BIDS subject ID per line, no trailing slashes.
Generate it from the BIDS root:

```bash
cd /overflow/zzhanglab/ADNI/ADNI-bids
ls -d sub-* > subject_list_all.txt
```

For the full cohort, split into smaller lists of ~400–500 subjects so that you do not
flood the SLURM queue:

```bash
split -l 400 subject_list_all.txt subject_list_
# produces subject_list_aa, subject_list_ab, ...
```

To test the pipeline on a single subject before committing the full cohort, pass the subject
ID directly as an argument to the correction scripts (see Phase 0 below).

---

## 6. Phase 0 — ADNI-specific corrections

These two scripts run **before** `preprocess.sh`. Each takes a single subject ID as its only
argument. For the full cohort, use `adni_submit_corrections.sh` to submit one job pair per
subject.

### Step 0a — Scan for complete subjects

Before submitting any jobs, identify which subjects have all three modalities:

```bash
cd /overflow/zzhanglab/ADNI/ADNI-bids
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example

$SCRIPTS/adni_scan_subjects.sh .
```

This writes four subject list files to the current directory:

| File | Contents |
|---|---|
| `subjects_anat_dwi_func.txt` | Complete subjects — use this for correction jobs |
| `subjects_anat_dwi_only.txt` | Anat + DWI, no fMRI |
| `subjects_anat_func_only.txt` | Anat + fMRI, no DWI |
| `subjects_anat_only.txt` | T1w only |

Also writes `adni_scan_log.txt` with a per-subject table.

### Step 0b — Submit correction jobs

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
DATA=/overflow/zzhanglab/ADNI/ADNI-bids

$SCRIPTS/adni_submit_corrections.sh $DATA/subjects_anat_dwi_func.txt $SCRIPTS
```

This submits **two SLURM jobs per subject** — one for DWI, one for fMRI — with the fMRI job
set to run only after the DWI job succeeds (`--dependency=afterok`). The terminal prints a
table of submitted job IDs:

```
Subject                           DWI job      fMRI job
--------------------------------  -------      --------
sub-005S6427                      4821301      4821302
sub-130S4417                      4821303      4821304
...
```

**To test on a single subject first:**

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example

# DWI correction only
sbatch $SCRIPTS/adni_dwi_eddy_correction.sh sub-130S4417

# fMRI correction only (after DWI completes)
sbatch $SCRIPTS/adni_fmri_correction.sh sub-130S4417
```

Runtime: DWI ~12 h per subject (topup ~30 min + eddy_cuda ~6–10 h on GPU); fMRI ~30 min.
GPU partitions tried in order: `l40-gpu`, `a100-gpu`, `volta-gpu`.

**DWI outputs** (written to `/overflow/zzhanglab/ADNI/ADNI-bids/<subject>/dwi/`):

| File | Used by |
|---|---|
| `eddy_corrected_data.nii.gz` | preproc_step1 |
| `eddy_corrected_data.eddy_rotated_bvecs` | preproc_step1 |
| `ap_dwi.bval` | preproc_step1 |
| `field_hz.nii.gz` | adni_fmri_correction.sh |
| `hifi_b0.nii.gz` | adni_fmri_correction.sh |

**fMRI output** (written to `/overflow/zzhanglab/ADNI/ADNI-bids/<subject>/fmri/`):

| File | Used by |
|---|---|
| `bold_distcorr.nii.gz` | preproc_step5_fmri.sh |

Both scripts are idempotent — they exit cleanly if outputs already exist (safe to resubmit).
Both scripts handle Philips vs Siemens JSON field names automatically.

---

## 7. Phase 1 — SBCI preprocessing

After Phase 0 completes, run `preprocess.sh`. This submits steps 1–5 as a SLURM dependency
chain for each subject.

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
OUT=/overflow/zzhanglab/ADNI/ADNI-bids
IN=/overflow/zzhanglab/ADNI/ADNI-bids/subjects_anat_dwi_func.txt

$SCRIPTS/preprocess.sh $IN $OUT $SCRIPTS
```

### What each step does

| Step | Script | Runs from | Purpose |
|---|---|---|---|
| 1 | `preproc_step1_preparedata.sh` | subject BIDS dir | Reorient T1 + DWI; flip gradients; assemble `dwi_pipeline/` |
| 2 | `preproc_step2_t1_dwi_registration.sh` | `dwi_pipeline/` | Register T1 → DWI space; DTI metrics |
| 3 | `preproc_step3_t1_freesurfer.sh` | `dwi_pipeline/` | FreeSurfer recon-all; warp parcellation to DWI space |
| 4 | `preproc_step4_fodf_estimation.sh` | `dwi_pipeline/` | Tissue segmentation; fODF estimation (sh_order 6) |
| 5 | `preproc_step5_fmri.sh` | subject BIDS dir | FSFast nuisance regression on bold_distcorr.nii.gz |

Step 5 depends on step 3 (not step 4), so it runs in parallel with step 4.

**ADNI-specific change in step 4:** `--sh_order 6` (not 8). ADNI has 30 gradient directions
at b=1000; sh_order 6 requires 28 directions (OK), sh_order 8 requires 45 (not enough).

**ADNI-specific changes in step 5 (FSFast):**

| Parameter | Standard pipeline | ADNI |
|---|---|---|
| TR | 2.5 s | 3 s |
| Frame skip | none | `-nskip 4` (12 s steady-state at TR=3 s) |
| Detrending | `-polyfit 1` | `-polyfit 2` (more drift at longer TR) |

### Resulting folder structure after preprocess.sh

```
/overflow/zzhanglab/ADNI/ADNI-bids/sub-XXXXXXX/
├── anat/                   (raw T1)
├── dwi/                    (raw DWI + eddy correction outputs from Phase 0)
├── fmri/                   (bold_distcorr.nii.gz from Phase 0)
└── dwi_pipeline/           (created by preproc_step1)
    ├── t1.nii.gz
    ├── data.nii.gz          (eddy-corrected DWI, reoriented)
    ├── flip_x.bval/.bvec
    ├── structure/           (T1 registration, segmentation, FreeSurfer outputs)
    └── diffusion/           (DTI metrics, fODF)
```

---

## 8. Phase 2 — PSC tractography

Run after preprocess.sh has completed for all subjects.

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
OUT=/overflow/zzhanglab/ADNI/ADNI-bids
IN=/overflow/zzhanglab/ADNI/ADNI-bids/subjects_anat_dwi_func.txt

$SCRIPTS/process_psc.sh $IN $OUT $SCRIPTS
```

The script submits `psc_step1_tractography.sh` for each subject. This runs whole-brain
probabilistic tractography (particle filter tracking, SET algorithm) and computes the
PSC structural connectome.

Runtime: ~48 h per subject.

---

## 9. Phase 3 — SBCI connectome

Run after process_psc.sh has completed.

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
OUT=/overflow/zzhanglab/ADNI/ADNI-bids
IN=/overflow/zzhanglab/ADNI/ADNI-bids/subjects_anat_dwi_func.txt

$SCRIPTS/process_sbci.sh $IN $OUT $SCRIPTS
```

The script submits SBCI steps 1–6 in a dependency chain. Step 1 (grid construction) runs
once for the whole cohort before the per-subject steps begin.

| SBCI step | Purpose |
|---|---|
| 1 | Build average cortical grid from fsaverage template (runs once) |
| 2 | Register each subject's surfaces to the grid; build seed masks |
| 3 | Run SET tractography (×N_RUNS in parallel) |
| 4 | Register subject surfaces; downsample meshes |
| 5 | Map streamline endpoints to grid; compute smoothed SC matrix |
| 6 | Project fMRI timeseries onto grid; concatenate runs; compute FC matrix |

Output files per subject (in `dwi_pipeline/sbci_connectome/`):
- `smoothed_sc_avg_0.005_ico4.mat` — smoothed structural connectivity
- `fc_avg_ico4.mat` — functional connectivity

Shared template outputs (in `OUTPUT_PATH` = `/overflow/zzhanglab/ADNI/ADNI-bids/SBCI_AVE/`):
- Average surface meshes used by step 5 and 6

---

## 10. Quality control

Three QC scripts check whether key output files exist for each subject. Each takes three
arguments: `IN` (subject list), `DATA` (data path), `OUT` (where to write the log file).

### After preprocess.sh — check fODF

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
OUT=/overflow/zzhanglab/ADNI/ADNI-bids
IN=/overflow/zzhanglab/ADNI/ADNI-bids/subjects_anat_dwi_func.txt

$SCRIPTS/preprocess_qc.sh $IN $OUT $OUT
mv $OUT/preprocess_qc_log $OUT/preprocess_qc_log_adni
```

Checks for: `dwi_pipeline/diffusion/fodf/fodf.nii.gz`

### After process_psc.sh — check PSC connectome

```bash
$SCRIPTS/psc_qc.sh $IN $OUT $OUT
mv $OUT/psc_qc_log $OUT/psc_qc_log_adni
```

Checks for: `dwi_pipeline/psc_connectome/ABCD_desikan_cm_count_processed.mat`

### After process_sbci.sh — check SC and FC matrices

```bash
$SCRIPTS/sbci_qc.sh $IN $OUT $OUT
mv $OUT/sbci_qc_log $OUT/sbci_qc_log_adni
```

Checks for:
- SC: `dwi_pipeline/sbci_connectome/smoothed_sc_avg_0.005_ico4.mat`
- FC: `dwi_pipeline/sbci_connectome/fc_avg_ico4.mat`

Reports both SC and FC status per subject on the same line.

### Extract failed subjects for resubmission

```bash
awk -F' ' '/FAILED/ {print $1}' preprocess_qc_log_list_aa > failed_list_aa.txt
```

Resubmit failed subjects by using `failed_list_aa.txt` as the new `IN` argument.

### Visual QC after Phase 0

Before committing the full cohort, visually inspect the Phase 0 outputs for 2–3 subjects:

**DWI eddy correction:**
```bash
# Overlay eddy-corrected b0 on T1 to check alignment
fsleyes dwi/hifi_b0.nii.gz anat/*_T1w.nii.gz
```

**fMRI B0 correction:**
```bash
# Compare mean BOLD before and after correction
fslmaths fmri/bold.nii.gz -Tmean fmri/mean_bold_raw.nii.gz
fsleyes fmri/mean_bold_raw.nii.gz fmri/bold_distcorr.nii.gz
```

Check that the frontal lobe is less stretched and brain edges are sharper after correction.
Also verify that `b0_u.nii.gz` (synthetic b0) and `b0.nii.gz` (real b0) look anatomically
similar with no large geometric differences.

---

## 11. Clean subject folders

After QC confirms that processing is complete, run the cleaning step to remove large
intermediate files and save disk space. This step is **irreversible** — do not run it
until you are confident all subjects have finished correctly.

```bash
SCRIPTS=/nas/longleaf/home/zz10c/software/SBCI_Pipeline/ADNI_example
OUT=/overflow/zzhanglab/ADNI/ADNI-bids
IN=/overflow/zzhanglab/ADNI/ADNI-bids/subjects_anat_dwi_func.txt

$SCRIPTS/clean_subject_folders.sh $IN $OUT $SCRIPTS
```

This submits `postproc_clean_folders.sh` for each subject. It deletes intermediate
files in `dwi_pipeline/` while keeping the final connectome matrices.

After cleaning, expect approximately 6 GB per subject (down from ~9 GB with raw imaging data).

---

## 12. Scripts reference

### ADNI-specific scripts (run before preprocess.sh)

| Script | Purpose | Submission |
|---|---|---|
| `adni_scan_subjects.sh` | Scan BIDS dir; write categorized subject lists | `$SCRIPTS/adni_scan_subjects.sh [outdir]` |
| `adni_submit_corrections.sh` | Submit one DWI + fMRI job pair per subject | `$SCRIPTS/adni_submit_corrections.sh <list> $SCRIPTS` |
| `adni_dwi_eddy_correction.sh` | DWI eddy + distortion correction (single subject, ~12 h) | `sbatch script.sh sub-XXXXXX` |
| `adni_fmri_correction.sh` | fMRI B0 correction (single subject, ~30 min) | `sbatch script.sh sub-XXXXXX` |

### Orchestration scripts (take IN OUT SCRIPTS arguments)

| Script | Purpose |
|---|---|
| `preprocess.sh` | Submits preproc steps 1–5 per subject as SLURM dependency chain |
| `process_psc.sh` | Submits psc_step1 per subject |
| `process_sbci.sh` | Submits sbci_steps 1–6 (step1 once, steps 2–6 per subject) |
| `clean_subject_folders.sh` | Submits postproc_clean_folders per subject |

### Per-subject processing scripts (no SLURM headers — submitted by orchestration scripts)

| Script | Purpose |
|---|---|
| `preproc_step1_preparedata.sh` | Reorient images; flip gradients; assemble dwi_pipeline/ |
| `preproc_step2_t1_dwi_registration.sh` | Register T1 → DWI; DTI metrics |
| `preproc_step3_t1_freesurfer.sh` | FreeSurfer recon-all; parcellation warp |
| `preproc_step4_fodf_estimation.sh` | Tissue segmentation; fODF (sh_order 6) |
| `preproc_step5_fmri.sh` | FSFast nuisance regression (TR=3, nskip=4, polyfit=2) |
| `psc_step1_tractography.sh` | Whole-brain PFT tractography; PSC connectome |
| `sbci_step1_process_grid.sh` | Build cortical grid from fsaverage template |
| `sbci_step2_prepare_set.sh` | Register surfaces; build seeding masks |
| `sbci_step3_run_set.sh` | Run SET tractography |
| `sbci_step4_process_surfaces.sh` | Register subject surfaces; downsample meshes |
| `sbci_step5_structural.sh` | Endpoint mapping; smoothed SC matrix |
| `sbci_step6_functional.sh` | FC timeseries projection; FC matrix |
| `postproc_clean_folders.sh` | Remove intermediate files |

### QC scripts

| Script | Checks |
|---|---|
| `preprocess_qc.sh` | `fodf.nii.gz` exists |
| `psc_qc.sh` | PSC connectome `.mat` exists |
| `sbci_qc.sh` | SC and FC `.mat` files exist (reports both) |

---

## Appendix — why the DWI fieldmap approach works for fMRI

The B0 field distortion (measured in Hz) is a physical property of the scanner's static
magnetic field — it does not depend on the pulse sequence. The same Hz fieldmap estimated
from the DWI Synb0-DISCO + topup step can therefore be applied to the fMRI BOLD data, with
appropriate scaling for the different readout time (via `fugue --dwell`).

This avoids running Synb0-DISCO a second time on the fMRI data. Synb0-DISCO's CNN was
trained on DWI b0 contrast, not BOLD contrast, so the DWI-derived fieldmap is more reliable
than one estimated directly from the fMRI.

## Appendix — Synb0-DISCO notes

Synb0-DISCO v3.1 with `--notopup` does **not** produce `b0_all.nii.gz`. The script manually
merges `b0_d_smooth.nii.gz` + `b0_u.nii.gz` with `fslmerge` before calling `topup`.

Always pass the **full-brain T1** (`t1.nii.gz`), not the skull-stripped version.
Synb0-DISCO runs its own internal BET; passing a pre-stripped T1 causes it to over-erode.

The `acqparams.txt` has both rows with the **same** PE direction:
```
0  1  0  0.0449     # real b0 — actual PE direction, actual readout time
0  1  0  0.000      # synthetic b0 — same PE direction, zero readout time
```
Row 2 is not an opposite-PE acquisition. The zero readout time tells topup that the
synthetic b0 has no distortion at all, which is how topup estimates the correct field.

---

## References

- Schilling KG et al. (2019). Synthesized b0 for diffusion distortion correction (Synb0-DisCo). *Magnetic Resonance Imaging*, 64, 62–70.
- Andersson JLR & Sotiropoulos SN (2016). An integrated approach to correction for off-resonance effects and subject movement in diffusion MR imaging. *NeuroImage*, 125, 1063–1078.
- Jenkinson M et al. (2002). FSL. *NeuroImage*, 62, 782–790.
- Fischl B (2012). FreeSurfer. *NeuroImage*, 62, 774–781.
