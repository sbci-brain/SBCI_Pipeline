# SBCI
Surface-Based Connectivity Integration

This is an advanced MRI post-processing pipeline that builds structural connectivity (SC) and functional connectivity (FC) on the white matter surface of the brain and returns three imaging biomarkers representative of the relationships between SC and FC.

What you will need:
1. T1w anatomical data
2. Multi-shell dwi data
3. Resting-state fMRI data

The data are assumed to be minimaly preprocessed - i.e., using FSL's pipeline to perforrm eddy correction and susceptibility-induced distortion correction.

## Installing Prerequisites

If using a managed system such as Bluehive (UofR), Longleaf (UNC), or Sherlock (Stanford) with Slurm and module management included, prerequisites should be able to be installed using commands similar to these:

```
module load qt/5.8.0 gcc/6.3.0 mrtrix3/3.0rc3 freesurfer/6.0.0 ants/2.3.1 fsl/5.0.9
module load java/10.0.2 matlab/2017b dcm2niix/1.0.20190902 pigz/2.6 anaconda/4.3.0
module load git
```

Otherwise, steps for installing some of the prerequisite software are included later in this document.

It's recommended that you create a `.bashrc_sbci` file in your home folder and add these lines (along with others mentioned below) to a `.bashrc_sbci` file so that you can source it everytime the pipeline is sent to a cluster. See the section **Using a Bashrc File** for more information.

### Setting up the Python Environment 

If you have Anaconda installed (either through a module or manually, see below), the following commands set up a clean Python 2.7 environment with all the neccesary packages installed. If a module is not available (or undesired), it's possible to download the latest anaconda2 here: https://repo.anaconda.com/archive/

```
conda create -n sbci python=2.7
conda activate sbci

conda install numpy scipy matplotlib ipython jupyter cython

pip install h5py==2.9.0
pip install imageio==2.4.1
pip install moviepy==0.2.3.5
pip install openpyxl==2.4.8
pip install pandas==0.20.3
pip install Pillow==5.2.0
pip install requests==2.19.1
pip install scikit-learn==0.19.0
pip install vtk==8.1.2
pip install PyMCubes==0.0.9
pip install nibabel==2.4.0
pip install git+https://github.com/MarcCote/tractconverter@master#tractconverter
pip install fury==0.4.0
pip install dipy==0.16.0
pip install trimeshpy==0.0.2
```

Append the following line to `.bashrc_sbci` (or the script file that's executed when a user logs in), so that the correct Python environment is running each time the pipeline is used.

```
conda activate sbci
```

### Installing the SBCI Pipeline

Clone the SBCI pipeline: `git clone https://github.com/sbci-brain/SBCI_Pipeline.git`; move `SBCI_Pipeline/third_party/scilpy_set.zip` to a local folder, e.g.,`/home/yourname/set`; and unzip it. Then run the following commands to install SET (Surface Enhanced Tractography):
	
```
cd /home/yourname/Software/set
python setup.py build_all
pip install -e .
```

Test the SET installation with `scil_surface.py`, you should see:
```
	usage: scil_surface.py [-h] [--vts_mask VTS_MASK]
	                       [-a ANNOT | -l LABEL | -m MORPH | --vts_scalar VTS_SCALAR | --vts_color VTS_COLOR | --vts_label VTS_LABEL | --image_mask IMAGE_MASK | --vts_val VTS_VAL]
	                       [-i INDICES [INDICES ...]] [--inverse_mask]
	                       [--save_vts_mask SAVE_VTS_MASK]
	                       [--save_vts_scalar SAVE_VTS_SCALAR]
	                       [--save_vts_color SAVE_VTS_COLOR]
	                       [--save_vts_label SAVE_VTS_LABEL]
	                       [--masked_labels_value MASKED_LABELS_VALUE]
	                       [-v | --save_image SAVE_IMAGE] [--no_scalar_for_masked]
	                       [--no_scalar_at NO_SCALAR_AT] [--white] [-f]
	                       surface
	scil_surface.py: error: too few arguments
```

SBCI should now be installed. Check scripts in `HCP_example` for an example of how to use the SBCI pipeline on some sample HCP (Human Connectome Project) data. 
- **Note:** The sbci_config file needs to be updated according to the local computing environment.
- **Note**: Line 12 of the script `preproc_step2_t1_dwi_registration.sh` will need to be modified to point to the appropriate template. A template has been included in this repository in the folder `data/mni_152_sym_09c`, so make the followinig modification: 
	```
	export template_dir="/PATH/TO/SBCI_PIPELINE/data/mni_152_sym_09c"
	```
	Changing `/PATH/TO/SBCI_PIPELINE/` to the location of your installation of SBCI. This will be moved out of the script in future versions of the pipeline and into the sbci_config file.
- **Note**: The script `preproc_step4_fmri.sh` will need to be modified, depending on how the fMRI data are to be processed.
- For freesurfer to run correctly, append the following lines to `.bashrc_sbci` (or the script file that's executed when a user logs in), editing depending on where the installation of Freesurfer is.

	``` 
	export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/bin:$PATH"
	export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/toolbox:$PATH"

	source /nas/longleaf/apps/freesurfer/6.0.0/freesurfer/SetUpFreeSurfer.sh
	```

### Installing the PSC Pipeline

Clone the PSC pipeline: `git clone https://github.com/zhengwu/PSC_Pipeline.git`;
 - See the README.md file on the github website for PSC. Skip Step 1 since a python2 environment has already been set up, and go directly to step 2.
 - Check if the installation is successful: 

	 ```
 	:~$conda activate sbci
 	:~$extraction_sccm_withfeatures_cortical.py 
 	usage: extraction_sccm_withfeatures_cortical.py [-h] [--save_sl ]
 	                                                [--save_diffusion ]
 	                                                TRACTS FAIMG MDIMG APARC
 	                                                LABELS_TXT LUT_TXT SUB_ID
 	                                                MINLEN MAXLEN DILATION_DIST
 	                                                DILATION_WINDSIZE INROILEN PRE
 	extraction_sccm_withfeatures_cortical.py: error: too few arguments
	 ```
 
### Alternative Installation of Prerequisites

If using a system without module management, prerequisites can be installed manually:

- **Anaconda**: Follow the insctructions [here](https://docs.anaconda.com/anaconda/install/linux/); Test the installatioin by running the command `which python`. Ih there are issues, try adding the anaconda path to `.bashrc_sbci` (or the script file that's executed when a user logs in), like so.

	```
	export PATH="/PATH/TO/ANACONDA/bin:$PATH"
	```
	Replacing `/PATH/TO/ANACONDA/` with the location of the anaconda installation.

- **Freesurfer**: Follow the instructions [here](https://surfer.nmr.mgh.harvard.edu/fswiki/rel6downloads); if using Ubuntu, libpng12 might be an issue (see solution [here](https://www.linuxuprising.com/2018/05/fix-libpng12-0-missing-in-ubuntu-1804.html)). 

- **mrtrix**: `conda install -c mrtrix3 mrtrix3`

- **ANTs**: Download and unzip and copy of ANTs [here](http://stnava.github.io/ANTs/) and place in a suitable folder (`/home/yourname/Software/ANTs`, for example). After the installation is done, append the following lines to `.bashrc_sbci` (or the script file that's executed when a user logs in).
	    
	```
	export ANTSPATH=/home/yourname/Software/ANTs/install/bin #this is the ants bin path
	export PATH=${ANTSPATH}:$PATH
	export PATH="$HOME/Software/ANTs/Scripts:$PATH"
	```
	Run the following commands to validate the installation: 
	```
	which antsRegistration #should print out the full path to antsRegistration, and
	antsRegistrationSyN.sh #should print out the usage for that script.
	```
- **FSL**: Follow the instructions [here](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation/).

## Using a Bashrc File

So that the working environment is the same each time the pipeline is run, it is recommended to create a `.bashrc_sbci` to be sourced each time the pipeline is run. The following is an example of a .bashrc file that works for Longleaf at time of writing. Just change `/PATH/TO/PSC_PIPELINE/` to the location of the PSC installation.

```
# .bashrc

module load qt/5.8.0 gcc/6.3.0 mrtrix3/3.0rc3 freesurfer/6.0.0 ants/2.3.1 fsl/5.0.9
module load java/10.0.2 matlab/2017b dcm2niix/1.0.20190902 pigz/2.6 anaconda/4.3.0
module load git

module unload python

# Needed to make conda play nice on longleaf
source /nas/longleaf/apps/anaconda/4.3.0/anaconda/etc/profile.d/conda.sh

# Direct to Freesurfer installation
export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/bin:$PATH"
export PATH="/nas/longleaf/apps/freesurfer/6.0.0/freesurfer/fsfast/toolbox:$PATH"

# Direct to the PSC installation
export PATH="/PATH/TO/PSC_PIPELINE/scripts:$PATH"
export PYTHONPATH="/PATH/TO/PSC_PIPELINE:$PYTHONPATH"

# Direct to the Ants installation
export ANTSPATH="/nas/longleaf/apps/ants/2.3.1/src/build/bin/"

source /nas/longleaf/apps/freesurfer/6.0.0/freesurfer/SetUpFreeSurfer.sh

# Load the Python environment
conda activate sbci
```
