import os

# get all folder name under a folder
def get_subfolders(path,output):
    l = [name for name in os.listdir(path)
            if os.path.isdir(os.path.join(path, name))]
    # output l to a text file
    with open(output, 'w') as f:
        for item in l:
            f.write("%s\n" % item)

get_subfolders('/scratch/tbaran2_lab/ACT_BIDS', './ACT.txt')