# Running a minimally pre-processed subject

The data in the `dataset` folder are an example of anonomised, minimally preprocessed DTI data. Data from MRI were extracted from DICOM format, corrected for distortion plus eddy currents and movements, before naming and arranging the files to comply with the [BIDS](https://bids.neuroimaging.io) standards. Ideally this is how most data will be supplied before running this pipeline.

## Checking the input data

The SBCI pipeline assumes that the data have had some minimal preprocessing applied via [FSL](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/). As such, we assume that the data are in the format that is usually output by FSL. To make sure, run `mrinfo` from Mrtrix3, for the T1 and dwi images:
 * `mrinfo ./dwi/example-subject_dwi.nii.gz`,
 *  and `mrinfo ./anat/example-subject_T1w.nii.gz`  

from within the subject's folder, and you should get output like this:

     ************************************************ 
     Image name:  "example_dataset/example-subject/dwi/example-subject_dwi.nii.gz"
     ***********************************************
     Dimensions:  112 x 112 x 72 x 142 
     Voxel size:  2 x 2 x 2 x 1 
     Data strides:  [ -1 2 3 4 ]
     Format:  NIfTI-1.1 (GZip compressed) 
     Data type: 32 bit float (little endian) 
     Intensity scaling: offset = 0, multiplier = 1 
     Transform:  1  0 -0  -109.3 
                 0  1 -0  -96.65
                -0  0  1  -70.26 
     comments:  stable:0004

Notice that the first number on the 'Data strides' row is -1, and all the others are positive. If you have any other combination of positive/negative data strides, you will have to perform the relevant flipping of the images using tools like `mrconvert` and `scil_flip_grad.py`. See the script `preproc_step1_preparedata.sh` for an example of how to use them. 
## Setup sbci_config

The majority of the parameters/options needed to run the SBCI pipeline can be set using the `sbci_config` file. For each project that you wish to run the pipeline for, there will be several lines that you need to modify. 

* `DATASET_NAME`: Change this to your study's name. Some files output by the PSC or SBCI pipeline will be named after whatever is set here.
* `DTI_BVALS`: The b-values from which the DTI shell is extracted and metrics are calculated. Typically a single shell (b-value) is all you need. You can check the b-values available for the data in this example by opening the file `example-subject_dwi.bval` in your preferred editor. Note that the values do not have to exactly match those in the file, just be reasonable close.
* `FODF_BVALS`: The b-values from which the [Fiber Orientation Distribution Function](https://doi.org/10.1016/j.neuroimage.2004.07.037) (fODF) is calculated. It is best to have a good range of b-values here to obtain higher quality tractography (estimation of nerve tracts). 
* `N_RUNS`: The tractography takes a little time to run, so to speed it up, SBCI runs tractography this many times in parallel for each subject and the results concatenated together. The higher this number, the greater the number of resulting tracts.
* `N_SEEDS`: The number of of seed points ($\times$ 1000) from which to grow tracts and begin estimation. The seeds are uniformly distributed over the cortical and subcortical surfaces. The greater the number of seeds, the greater the number of resulting tracts.
* `STEPS`: This specifies the amount to which we use the anatomical prior calculated by [Surface-Enchanced Tractography](https://doi.org/10.1016/j.neuroimage.2017.12.036) (SET). This may need to change depending on the age and pathology of your study (young brains, for example, are still in development and less 'unfolding' of the brain should be performed). 
* `RNG`: Random seed used to aid reproducibility. You can set this to any number you please, but if you want to re-run a study, set this to the same number originally used in that study.
* `BANDWIDTH`: The bandwidth used to estimate the continuous structural connectome via kernel density estimation. We found 0.005 works nicely for HCP data, but methods for selecting the bandwidth are outlined [here](https://doi.org/10.1016/j.media.2017.04.013).
* `ROIS`: This is a list of subcortical regions to include. It's recommended to always include the barinstem and grey nuclei as anatomical constraints for tractography. The numbers for the regions of interest (ROIS) are taken from the Freesurfer segmentation [here](https://surfer.nmr.mgh.harvard.edu/fswiki/FsTutorial/AnatomicalROI/FreeSurferColorLUT). 
* `RESOLUTION`: The percentage of vertices to be removed from the high resolution representation of the cortical surface output by Freesurfer. Values range between 0-1.

As well as pipeline parameters, the `sbci_config` file contains information about where the pipeline has been installed and where to place the results.

* `SBCI_PATH`: Change this to the absolute path of the cloned SBCI git repository (eg. /home/user/SBCI/).
* `PSC_PATH`: If installed, change this to the absolute path of the PSC pipeline.
* `FREESURFER_PATH`: Change this to the absolute path of your Freesurfer installation.
* `OUTPUT_PATH`: Change this to the absolute path you wish to output SBCI data shared between subjects (mapping between high and low resolution of the average brain, etc.) and can be used with the [SBCI Toolkit](https://github.com/sbci-brain/SBCI_Toolkit) in MATLAB to perform post-processing tasks. Individual subject results will be saved in `/PATH/TO/INPUT/SUBJECT/dwi_pipeline/sbci_connectome/`.   

## Setup the environment

Before you run each script, make sure the Anaconda environment is active and the appropriate modules have been loaded and/or software installed. Instructions for setting up the environment are in the root folder of this repository along with the installation instructions. 

## Process the subject

Depending on your workflow, it might be best to run each of the pipeline steps one at a time for all subjects before moving onto the next. At the very least, it is best to do that with a test subject for each new study to make sure everything works as expected before mass processing. The scripts are designed to be run one after the other within each subject's root folder. The one exception is `sbci_step1_process_grid.sh` which can be run from any folder. However, you decide to run the scripts, they should be run in the following order:

* [preproc_step1_preparedata.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/preproc_step1_preparedata.sh "preproc_step1_preparedata.sh"): Prepares data that are in BIS format to the format expected for SBCII.
* [preproc_step2_t1_dwi_registration.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/preproc_step2_t1_dwi_registration.sh "preproc_step2_t1_dwi_registration.sh"): Prepares the data for tractography and registers T1 to diffusion space.
* [preproc_step3_t1_freesurfer.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/preproc_step3_t1_freesurfer.sh "preproc_step3_t1_freesurfer.sh"): Runs Freesurfer `recon-all` on the processed T1.
* [preproc_step4_fodf_estimation.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/preproc_step4_fodf_estimation.sh "preproc_step4_fodf_estimation.sh"): Segments the processed T1 image and calculates the fODF for tracking.

The pre-processing is now complete for DTI data and ready for SBCI to start tractography. If you also have resting state fMRI, you can also run the following step:

* [preproc_step5_fmri.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/preproc_step5_fmri.sh "preproc_step5_fmri.sh"): Pre-processes resting state fMRI data (not available in example data). This step can run after step 3, or not be run at all if the data are not available.

Now the data are ready to be processed through SBCI. The following steps need to be run in order, and only after the previous steps are complete:

* [sbci_step1_process_grid.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step1_process_grid.sh "sbci_step1_process_grid.sh"): Calculates mapping between Freesurfer meshes and the low resolution representations output by SBCI. Unlike every other step, this step only needs to be run once (instead of once per subject), but it has to be performed before any of the other SBCI steps below. 
* [sbci_step2_prepare_set.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step2_prepare_set.sh "sbci_step2_prepare_set.sh"): Converts, moves, and generates data to prepare for tractography using SET.
* [sbci_step3_run_set.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step3_run_set.sh "sbci_step3_run_set.sh"): Processes the tractography. Note that unlike every other script, this script requires an input. The input is a number, so if you set `N_STEPS=3` then you need to run this script 3 times with inputs 1,2, and 3.
* [sbci_step4_process_surfaces.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step4_process_surfaces.sh "sbci_step4_process_surfaces.sh"): Calculates the subject-specific mapping between Freesurfer meshes and the low resolution representations output by SBCI.
* [sbci_step5_structural.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step5_structural.sh "sbci_step5_structural.sh"): Calculates the structural connectivity matrix for a subject.
* [sbci_step6_functional.sh](https://github.com/sbci-brain/SBCI_Pipeline/blob/master/integrated_pipeline/sbci_step6_functional.sh "sbci_step6_functional.sh"): Calculates the functional connectivity matrix for a subject. This step cannot be run in the example because we have no resting state fMRI.

### Automated process

Included in this example are three scripts that will automatically run all the preprocessing steps, SBCI steps, and PSC steps, respectively. Each script takes the same three inputs:

* A file containing all the subject names you wish to process, 
* The base path containing all the subject data
* the path to the integrated_pipeline folder included in this repository

To run the preprocessing for this example, edit the indicated lines within each of the three scripts, then run them like so: 

* `./preprocess subject_list /PATH/TO/SBCI/integrated_pipeline/ /PATH/TO/example_dataset/`

Be sure to let each script finish before starting the next.

### Checking the results

Using `sbatch`, each script should output a log file. It is good practice to check through them for any warnings or errors. A simple way to do so from within the command prompt is to use a command similar to `grep -i error /PATH/TO/LOGFILES/*.log`. It will output several lines because several processes try to mininimise error, but it will output all malicious errors too.

Other checks that may be performed are: 

* Check the registration after running `prepoc_step3_t1_freesurfer.sh`. You can use tools like [fsleyes](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FSLeyes) and [QATools](https://surfer.nmr.mgh.harvard.edu/fswiki/QATools) to do quality checks on all the Freesurfer steps. 
* After running `preproc_step4_fodf_estimation.sh`, you can visualise the fODF using [mrview](https://mrtrix.readthedocs.io/en/latest/reference/commands/mrview.html) from Mrtrix3. 
* You can also visualise surface seeds, and intersections after running `sbci_step3_run_set.sh` using the command `scil_visualize_set_output.py` from the command line (the usage of which can be found using the `-h` flag).
 
The results will be in `/PATH/TO/INPUT/SUBJECT/dwi_pipeline/sbci_connectome/` as .mat files. The sample scripts in the matlab folder of this repository will show you one way to collect the results of multiple subjects in easy to analyse tensors.

## Mass processing

I have included two scripts that I use when processing entire datasets on Bluehive at the University of Rochester: `preprocess.sh` and `process_sbci.sh`. These scripts automatically process an entire directory. They might not be ideal for other people, but it is an example of how a small dataset can be automated.
