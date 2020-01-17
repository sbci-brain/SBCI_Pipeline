% MATLAB R2019b
% Plots a connectivity matrix with a grid denoting the ROIs
function [] = plotmatrix(mat,roi,plt_title,filename,colors)

plt = figure('visible', 'off');
imagesc(mat)

% display a grid of ROIs
ticks = [0; find(diff(roi))];
xticks(ticks);
yticks(ticks);
grid on

% remove ticks
yticklabels([]);
xticklabels([]);

% set limits to colorbar
if ~isempty(colors)
  caxis(colors)
end

% set colors
colorbar()
colormap(viridis())

% set title and save
title(plt_title);
saveas(plt, filename);

end

