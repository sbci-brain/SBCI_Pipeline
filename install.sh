#!/bin/bash
# .bashrc

module load qt 
module load gcc/9.1.0 
module load mrtrix3 
module load freesurfer/6.0.0 
module load ants/2.3.1 
module load fsl
module load java/1.8.0_111 
module load matlab 
module load dcm2niix 
module load pigz/2.6 
module load anaconda
module load git

### LOAD ENVIRONMENT ###
conda activate sbci
############### CREATE THE ENVIRONMENT. USED ONLY ONE TIME ###############
# create env variable for SBCI
export PATH="/home/ywang330/SBCI_Pipeline/scripts:$PATH" 
export PYTHONPATH="/home/ywang330/SBCI_Pipeline:$PYTHONPATH"


# create env variable for PSC
export PATH="/home/ywang330/PSC_Pipeline/scripts:$PATH"
export PYTHONPATH="/home/ywang330/PSC_Pipeline:$PYTHONPATH"

scil_surface.py

extraction_sccm_withfeatures_cortical.py

echo "done."