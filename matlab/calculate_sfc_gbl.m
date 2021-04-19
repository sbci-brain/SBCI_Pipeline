% FUNCTION NAME:
%   calculate_sfc_gbl
%
% DESCRIPTION:
%   calculate the global SFC given the SC and FC matrices
%
% INPUT:
%   sc - (matrix) A PxP matrix of continuous SC data   
%   fc - (matrix) A PxP matrix of continuous FC data
%   triangular - (logical) If true, the FC and SC matrices are 
%       symmeterised before calculating SFC
%
% OUTPUT:
%   sfc_gbl - (vector) A vector of length P with SFC_gbl values
%
% ASSUMPTIONS AND LIMITATIONS:
%   Removes diagonals and assumes the SC and FC matrices are either
%   symmetric or triangular.
%
function [sfc_gbl] = calculate_sfc_gbl(sc, fc, triangular)
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
    sfc_gbl = nan(size(fc, 1),1);
    
    % find constant columns, the indices 
    % of constants will be set equal to NaN
    nanmask = ~all(~diff(fc)) & ~all(~diff(sc));
    
    % remove constant columns
    fc = fc(nanmask, nanmask);
    sc = sc(nanmask, nanmask);
    
    % calculate global SFC
    result = zeros(size(fc,1), 1);
    n = size(fc, 1);

    for p = 1:n
        % innerproduct definition of correlation
        % which is more suitable to functional data
        vec_fc = squeeze(fc(p,:));
        vec_sc = squeeze(sc(p,:));

        norm_fc = sqrt(sum(vec_fc.^2));
        norm_sc = sqrt(sum(vec_sc.^2));

        result(p) = dot(vec_fc, vec_sc) / (norm_fc * norm_sc);
    end
    
    % populate the results with calculated SFC
    sfc_gbl(nanmask) = result;
end
