# SBCI Pipeline Documentation

This repository provides comprehensive instructions for running the **Structural Brain Connectivity Imaging (SBCI)** pipeline on the **HCP_Aging** and **HCP_Development** datasets. Follow the steps below to download, preprocess, configure, and execute the SBCI pipeline effectively.

## Table of Contents

- [Data Download](#data-download)
- [Data Preprocessing](#data-preprocessing)
- [Configure `sbci_config`](#configure-sbci_config)
- [Modify Scripts](#modify-scripts)
- [Generate Subject List](#generate-subject-list)
- [Run the SBCI Pipeline](#run-the-sbci-pipeline)
- [Troubleshooting](#troubleshooting)



## Data Download

To run the SBCI pipeline on the HCP_Aging and HCP_Development datasets, you need to download the raw image data.

1. **Download from NDA Website**

   Visit the [NDA (National Database for Autism Research) website](https://nda.nih.gov/) and download the following unprocessed image data:

   - **HCP_Aging**
   - **HCP_Development**

   Specifically, download the **T1**, **dMRI**, and **rfMRI** datasets.

   **Note**: Ensure you have the necessary permissions and access rights to download the data from NDA.

## Data Preprocessing

Follow these steps within the `HCP_preprocess` directory.

1. **Navigate to `HCP_preprocess` Folder**

   The `HCP_preprocess` folder contains scripts and instructions for preprocessing T1, dMRI, and fMRI data.

2. **dMRI Preprocessing**

   - **Merge Directories**: Combine `dir 98` and `dir 99` for dMRI data.
   - **Eddy Correction & Distortion Correction**: Utilize FSL's pipeline to perform eddy current correction and susceptibility-induced distortion correction.

3. **fMRI Preprocessing**
   - **Merge  images**: Merge `AP` and `PA` for fMRI data and apply topup.
   - **Generate TSV Files**: Create TSV files for fMRI data.
4. **Convert to BIDS Format**:
   
   Transform the  data into the BIDS (Brain Imaging Data Structure) format

**Important**: Update the `base directions` and `output direction` in the preprocessing scripts to reflect your local file paths.

## Configure `sbci_config`

Proper configuration of the `sbci_config` file is crucial for the SBCI pipeline to function correctly.

1. **Edit Script and Concon Paths**

   Open the `sbci_config` file and modify lines 9-10 to point to the `scripts` and `concon` directories in this repository:

   ```bash
   SCRIPT_PATH=/home/user/SBCI/scripts
   CONCON_PATH=/home/user/SBCI/concon
   ```

   - Replace `/home/user/SBCI/scripts` with the absolute path to your `scripts` directory.
   - Replace `/home/user/SBCI/concon` with the absolute path to your `concon` directory.

2. **Set Working Directory Paths**

   Modify lines 42-43 to specify your working directories:

   ```bash
   REFDIR=/home/user/project/subjects_dir/reference_subject/dwi_sbci_connectome/structure/fsaverage
   AVGDIR=/home/user/project/subjects_dir/SBCI_AVG
   ```

   - **REFDIR**:
     - Replace `/home/user/project/subjects_dir/reference_subject` with the path to your reference subject directory.
     - The `reference_subject` should be the name of the test HCP subject (e.g., `103818`).
     - **Do not** change anything to the right of `reference_subject` on line 42.

   - **AVGDIR**:
     - Replace `/home/user/project/subjects_dir/SBCI_AVG` with the path to your `SBCI_AVG` directory.
     - **Do not** change `SBCI_AVG` on line 43.

3. **Optional Configurations**

   Feel free to adjust other settings such as resolution or parcellations to explore available configurations.

## Modify Scripts

Ensure that the scripts reference the correct local paths by modifying specific lines in the following scripts:

- `preprocess.sh`
- `process_psc.sh`
- `process_sbci.sh`

**Example Modifications (Lines 8-12):**

```bash
# CHANGE LOCATION TO YOUR SOURCE FILE
echo "Sourcing .bashrc"
source /path/to/your/.bashrc_sbci

# CHANGE LOCATION TO THE CONFIGURATION FILE FOR SBCI
export SBCI_CONFIG=/path/to/your/sbci_config
```

- **Explanation**:
  - **Line 9**: Sources your custom `.bashrc_sbci` file. Update the path to where your `.bashrc_sbci` is located.
  - **Line 12**: Sets the `SBCI_CONFIG` environment variable to point to your `sbci_config` file. Update the path accordingly.


## Generate Subject List

Create a list of subjects you wish to process. The list should follow the structure below:

```
sub-HCA6002236/ses-V1_MR
sub-HCA6010538/ses-V1_MR
sub-HCA6018857/ses-V1_MR
sub-HCA6030645/ses-V1_MR
sub-HCA6047359/ses-V1_MR
sub-HCA6051047/ses-V1_MR
```

- **Each Line Represents**:
  - A subject/session pair in the format `sub-<SubjectID>/ses-<SessionID>`.


## Run the SBCI Pipeline

Execute the SBCI pipeline using the prepared scripts and configurations.

### Command Structure

```bash
/path/to/preprocess.sh /path/to/subject_list /path/to/output_data /path/to/SBCI_pipeline
```

### Example Command

```bash
/nas/longleaf/home/yifzhang/zhengwu/SBCI_Pipeline/HCP_example_final/preprocess.sh \
/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/test_data/subject_list \
/overflow/zzhanglab/HCP_Aging_Development_Data/HCP_preprocess_data/test_data \
/nas/longleaf/home/yifzhang/zhengwu/SBCI_Pipeline/HCP_example_final
```

- **Arguments**:
  1. **Path to `preprocess.sh`**: The preprocessing script.
  2. **Path to Subject List**: The text file containing the list of subjects (e.g., `subject_list.txt`).
  3. **Output Data Path**: Directory where the preprocessed data will be stored.
  4. **SBCI Pipeline Path**: Directory containing the SBCI pipeline scripts.



**Notes:**

- Ensure all paths are absolute and correctly point to the respective files and directories.
- Verify that you have the necessary permissions to execute the scripts and write to the output directories.
- Monitor the terminal for any error messages during execution and address them as needed.

## Troubleshooting

- **Permissions Issues**: Ensure you have execute permissions for all scripts. Use `chmod +x script.sh` to make a script executable.
- **Path Errors**: Double-check all file and directory paths in your configuration and scripts.
- **Missing Dependencies**: Ensure all prerequisite software (e.g., FSL) is correctly installed and accessible in your environment.
- **Insufficient Resources**: Verify that your system has enough memory and storage to handle the processing tasks.
- **Data Format Issues**: Ensure that the downloaded data is correctly formatted and organized as per BIDS standards.

