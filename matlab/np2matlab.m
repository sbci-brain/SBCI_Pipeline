% MATLAB R2009b
% Generate connectivity matrices from numpy results
function [sc,fc] = np2matlab(filename)

load(filename, 'sc', 'fc', 'time_series');

% load structural connectivity
sc = full(sc);

% load functional connectivity
n = size(time_series, 1);
[ii,jj] = ndgrid(1:n);

B = zeros(n);
B(ii>=jj) = fc;
fc = B';

fc = fc + fc';
fc = fc - diag(diag(fc)); 

%idx = tril(true(size(fc)));
%fc(idx) = 0;

end

