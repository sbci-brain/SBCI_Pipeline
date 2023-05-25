import os

# list folders in a directory
def get_folder_list(path):
    return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
ACT_PATH = '/scratch/tbaran2_lab/ACT'
CONFIG_PATH = os.path.join(ACT_PATH,'bids', 'config.json')
OUTPUT_BIDS_PATH = os.path.join('/scratch/tbaran2_lab/ACT_BIDS')
session='01'
dicom_dirs = get_folder_list(os.path.join(ACT_PATH, 'dicom'))
# dicom_dirs = ['/scratch/tbaran2_lab/ACT/dicom/001_S_0105']
print(len(dicom_dirs))
for dicom_dir in dicom_dirs:
    screen_id = dicom_dir.split('_')[-1]
    dicom_dir_path = os.path.join(ACT_PATH, 'dicom', dicom_dir)
    command = 'sbatch convert_step1.sh {} {} {} {} {}'.format(dicom_dir_path, screen_id, session,CONFIG_PATH, OUTPUT_BIDS_PATH)
    print(command)
    os.system(command)
    