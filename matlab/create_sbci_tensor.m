% MATLAB r2019b

% extract atlas free tensors for each subject
clear variables;
close all;

% parameters
curr_path = '/home/user/project/subjects/';
output_path = '/home/user/project/connectome/';

% matrix containing all the subject ids to get the results from
load('/home/user/project/SUBJECT_IDS.mat');
startID = 1;
endID = length(ids);

% folder within subject where SBCI results are held
foldername = 'dwi_sbci_connectome/SBCI';
avg_path = 'SBCI_AVG';

% percent reduction of the vertices in the surface meshes in SBCI
reduction = '99';

% number of BOLD runs
n_runs = 4;

% atlases to collect
atlases = [{'aparc.a2005s'}; {'aparc.a2009s'};
           {'aparc'}; {'oasis.chubs'};
           {'PALS_B12_Brodmann'}; {'PALS_B12_Lobes'}; 
           {'PALS_B12_OrbitoFrontal'}; {'PALS_B12_Visuotopic'};
           {'Yeo2011_7Networks_N1000'}; {'Yeo2011_17Networks_N1000'}]; 

for i = 1:length(atlases)
    % load the average mapping
    load(sprintf('/%s/%s/%s_avg_roi_0.%s.mat', curr_path, avg_path, atlases{i}, reduction));
    
    sorted_idx = sorted_idx+1;
    labels = labels(sorted_idx);
    
    atlas_mapping(:,1,i) = sorted_idx;
    atlas_mapping(:,2,i) = labels;    

    atlas_names{i} = names;
end

idx = 1;

for i = startID:endID
    sub_id = ids(i);
    processed_path = sprintf('/%s/%s/%s', curr_path, sub_id, foldername);
        
    % check if the folder exists
    if ~exist(processed_path, 'dir')
        disp(sub_id)
        continue;
    end
        
    % go into the folder
    cd(processed_path)
        
    % load the data   
    for j = 1:n_runs
      load(sprintf('./RUN00%d/fc_partial_avg_0.%d.mat', j, reduction))           

      % save as full matrix (not upper triangular)
      sbci_fc_tensor(:,:,j,idx) = fc + fc' - 2*diag(diag(fc));   
    end
    
    load(sprintf('smoothed_sc_avg_0.005_0.%s.mat', reduction))
    
    % save as normalised matrix (other versions of MATLAB use sum(sc(:))
    sbci_sc_tensor(:,:,idx) = sc / sum(sc, 'all');
    
    idx = idx + 1;                
end
    
cd(output_path);
save -v7.3 SBCI_connectivity sbci_fc_tensor sbci_sc_tensor atlases atlas_mapping atlas_names ids 
