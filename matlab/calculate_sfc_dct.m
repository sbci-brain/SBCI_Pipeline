% FUNCTION NAME:
%   calculate_sfc_dct
%
% DESCRIPTION:
%   calculate the discrete SFC given the parcellated SC and FC matrices
%
% INPUT:
%   sc - (matrix) A PxP matrix of discrete SC data   
%   fc - (matrix) A PxP matrix of discrete FC data
%   triangular - (logical) If true, the FC and SC matrices are 
%       symmeterised before calculating SFC
%
% OUTPUT:
%   sfc_dct - (vector) A vector of length P with SFC_fct values
%
% ASSUMPTIONS AND LIMITATIONS:
%   Removes diagonals and assumes the SC and FC matrices are either
%   symmetric or triangular, and that they are already parcellated.
%
function [sfc_dct] = calculate_sfc_dct(sc, fc, triangular)
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
    sfc_dct = nan(size(fc, 1),1);
    
    % find constant columns, the indices 
    % of constants will be set equal to NaN
    nanmask = ~all(~diff(fc)) & ~all(~diff(sc));
    
    % remove constant columns
    fc = fc(nanmask, nanmask);
    sc = sc(nanmask, nanmask);
    
    % calculate discrete SFC
    result = zeros(size(fc,1), 1);
    n = size(fc, 1);

    for p = 1:n
        % innerproduct definition of correlation
        % which is more suitable to functional data
        vec_fc = squeeze(fc(p,:));
        vec_sc = squeeze(sc(p,:));

        result(p) = corr2(vec_fc, vec_sc);
    end
    
    % populate the results with calculated SFC
    sfc_dct(nanmask) = result;
end
