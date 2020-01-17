% MATLAB R2009b
% Sort the connectivity matrices by ROI and remove masked vertices
function [sc,fc,nan_mask,sorted_idx,roi_labels] = sortandmask(filename,sc,fc)

load(filename, 'sorted_idx', 'lh_labels', 'rh_labels');

% create masks
tmp_labels = cat(2, lh_labels, rh_labels);
tmp_labels = tmp_labels(sorted_idx+1);

nan_mask = ~(tmp_labels == -1);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

fc = fc(sorted_idx+1, sorted_idx+1);
sc = sc(sorted_idx+1, sorted_idx+1);

fc = fc(nan_mask, nan_mask);
sc = sc(nan_mask, nan_mask);

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

roi_labels = cat(2, lh_labels, rh_labels+100);
roi_labels = roi_labels(sorted_idx+1);
roi_labels = roi_labels(nan_mask);

[~,~,roi_labels] = unique(roi_labels);

end

