% FUNCTION NAME:
%   calculate_sfc_loc
%
% DESCRIPTION:
%   calculate the local SFC given the SC and FC matrices and a parcellation
%
% INPUT:
%   sc - (matrix) A PxP matrix of continuous SC data   
%   fc - (matrix) A PxP matrix of continuous FC data
%   min_area - (integer) A threshold for ROI size
%   parcellation - (matrix) A Px2 matrix with parcellation output from SBCI
%   triangular - (logical) If true, the FC and SC matrices are 
%       symmeterised before calculating SFC
%
% OUTPUT:
%   sfc_loc - (vector) A vector of length P with SFC_loc values
%
% ASSUMPTIONS AND LIMITATIONS:
%   Removes diagonals, assumes the SC and FC matrices are either
%   symmetric or triangular. and that the parcellation or SC, FC, 
%   matrices have not been rearranged in any way from SBCI output.
%
function [sfc_loc] = calculate_sfc_loc(sc, fc, parcellation, min_area, triangular)
    if ~exist('min_area','var')
        min_area = 10;
    end
    
    if ~exist('triangular','var')
        triangular = false;
    end
 
    % symmeterise matrices
    if (triangular == true)
        sc = sc + sc';
        fc = fc + fc';   
    end
    
    % remove diagonal elements
    sc = sc - diag(diag(sc)); 
    fc = fc - diag(diag(fc));

    % somewhere to place the results
    sfc_loc = nan(size(fc, 1),1);
    
    % find constant columns, the indices 
    % of constants will be set equal to NaN
    nanmask = ~all(~diff(fc)) & ~all(~diff(sc));
    
    % remove constant columns
    fc = fc(nanmask, nanmask);
    sc = sc(nanmask, nanmask);
    labels = parcellation(nanmask,2);
    
    % calculate local SFC
    rois = unique(labels);
    p = size(rois, 1);
            
    result = zeros(size(fc,1), 1);

    for i = 1:p
        % create SC and FC matrices from 
        % the vertices of the selected ROI
        mask = (labels == rois(i));
        
        roi_fc = fc(mask,mask);
        roi_sc = sc(mask,mask);
        
        roi_n = size(roi_fc, 1);
        
        % if the ROI is too small SFCs will be inflated
        % so set to NaN if the area is below a threshold
        if roi_n < min_area
            result(mask) = nan;
            continue;
        end
        
        loc_result = zeros(roi_n, 1);
        
        for k = 1:roi_n
            % innerproduct definition of correlation
            % which is more suitable to functional data
            vec_fc = squeeze(roi_fc(k,:));
            vec_sc = squeeze(roi_sc(k,:));
            
            norm_fc = sqrt(sum(vec_fc.^2));
            norm_sc = sqrt(sum(vec_sc.^2));
            
            loc_result(k) = dot(vec_fc, vec_sc) / (norm_fc * norm_sc);
        end
        
        % populate the result vector with the roi's SFCs
        result(mask) = loc_result;
    end
    
    % populate the results with calculated SFC
    sfc_loc(nanmask) = result;
end
