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

% number of BOLD runs
n_runs = 4;

% atlases to collect
atlases = [{'aparc.a2009s'}; {'aparc'};];
% alternate names to give atlases
alt_names = [{'destrieux'}; {'desikan'};];

for i = 1:length(atlases)
    % load the average mapping
    load(sprintf('/%s/%s/%s_avg_roi.mat', curr_path, avg_path, atlases{i}));
    
    atlas_names{i} = names;
end

for atlas_idx = 1:length(atlases)
    atlas = atlases{atlas_idx};
    atlas_name = alt_names{atlas_idx};
    
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
        load(sprintf('%s_csc.mat', atlas))

        sc = sc + sc';   
        sc = sc - diag(diag(sc));    
        sc = sc / sum(sc, 'all');
        
        % load the data      
        for run = 1:n_runs       
            load(sprintf('./RUN00%d/%s_cfc.mat', run, atlas_name))           

            fc = fc + fc';
            fc = fc - diag(diag(fc)); 
            
            eval(sprintf('%s_cfc_tensor(:,:,run,idx) = fc;', atlas_name));   
        end

        eval(sprintf('%s_csc_tensor(:,:,idx) = sc;', atlas_name)); 
      
        fc_names{atlas_idx} = sprintf('%s_cfc_tensor ', atlas_name);
        sc_names{atlas_idx} = sprintf('%s_csc_tensor ', atlas_name);
        
        idx = idx + 1;               
    end
end   

cd(output_path);

command = sprintf('save -v7.3 SBCI_CFC_%drun_atlas %s atlas_names ids', n_runs, fc_names{:});
eval(command);
command = sprintf('save -v7.3 SBCI_CSC_atlas %s atlas_names ids', sc_names{:});
eval(sprintf('%s %s', filename, raw_fc_names{:}));

