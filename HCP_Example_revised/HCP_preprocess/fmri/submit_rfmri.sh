#!/bin/bash

start=1

# Get the total number of subjects (lines) in the directory
# end=10
end=$(ls $baseDir | wc -l)
batchSize=5

while [ $start -lt $end ]
do
  nextEnd=$((start + batchSize - 1))
  if [ $nextEnd -gt $end ]; then
    nextEnd=$end
  fi

  echo "Submitting job for subjects ${start} to ${nextEnd}"
  sbatch /nas/longleaf/home/yifzhang/zhengwu/HCP/HCP_rfMRI_preprocessing/zhengwu_code.sh $start $nextEnd

  start=$((nextEnd + 1))
done
