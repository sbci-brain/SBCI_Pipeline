function [] = plotmatrix(mat,roi,plt_title,filename,colors)
%plt = figure('visible', 'off', 'Renderer', 'painters', 'Position', [0,0,2*875,2*656]);
plt = figure('visible', 'off');
imagesc(mat)

ticks = [0; find(diff(roi))];
xticks(ticks);
yticks(ticks);
grid on

yticklabels([]);
xticklabels([]);

if ~isempty(colors)
  caxis(colors)
end

colorbar()
colormap(viridis())

title(plt_title);
saveas(plt, filename);
end

