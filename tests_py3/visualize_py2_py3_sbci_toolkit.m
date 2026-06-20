function visualize_py2_py3_sbci_toolkit(toolkit_dir, subject_dir, py2_dir, py3_sc_dir, py3_fc_dir, out_dir, resolution, bandwidth, atlas_index)
% Visualize Python 2 vs Python 3 SBCI SC/FC outputs with SBCI_Toolkit.
%
% Example MATLAB batch call:
%   visualize_py2_py3_sbci_toolkit('~/SBCI_Toolkit', pwd, ...
%       'dwi_pipeline/sbci_connectome', ...
%       'dwi_pipeline/sbci_connectome_py3_sameinput', ...
%       'dwi_pipeline/sbci_connectome_py3_step6', ...
%       'dwi_pipeline/sbci_connectome_py3_sameinput/toolkit_visualization', ...
%       'ico4', '0.005', 21)

if nargin < 9 || isempty(atlas_index)
    atlas_index = 21;
end
if nargin < 8 || isempty(bandwidth)
    bandwidth = '0.005';
end
if nargin < 7 || isempty(resolution)
    resolution = 'ico4';
end

toolkit_dir = char(expand_user(toolkit_dir));
subject_dir = char(expand_user(subject_dir));
py2_dir = char(expand_user(py2_dir));
py3_sc_dir = char(expand_user(py3_sc_dir));
py3_fc_dir = char(expand_user(py3_fc_dir));
out_dir = char(expand_user(out_dir));

if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

addpath(toolkit_dir);
addpath(fullfile(toolkit_dir, 'io'));
addpath(fullfile(toolkit_dir, 'plotting'));
addpath(fullfile(toolkit_dir, 'analysis'));
addpath(fullfile(toolkit_dir, 'sfc'));

label_dir = fullfile(toolkit_dir, 'example_data', 'fsaverage_label');
[sbci_parc, ~, ~] = load_sbci_data(label_dir, resolution);

fprintf('Using atlas %d: %s\n', atlas_index, sbci_parc(atlas_index).atlas{1});
roi_exclusion_index = [];

py2_sc_file = fullfile(subject_dir, py2_dir, sprintf('smoothed_sc_avg_%s_%s.mat', bandwidth, resolution));
py3_sc_file = fullfile(subject_dir, py3_sc_dir, sprintf('smoothed_sc_avg_%s_%s.mat', bandwidth, resolution));
py2_fc_file = fullfile(subject_dir, py2_dir, sprintf('fc_avg_%s.mat', resolution));
py3_fc_file = fullfile(subject_dir, py3_fc_dir, sprintf('fc_avg_%s.mat', resolution));

py2_sc = load(py2_sc_file);
py3_sc = load(py3_sc_file);
py2_fc = load(py2_fc_file);
py3_fc = load(py3_fc_file);

sc2 = sym_sc(py2_sc.sc);
sc3 = sym_sc(py3_sc.sc);
fc2 = py2_fc.fc;
fc3 = py3_fc.fc;

sc2_plot = log((1e7 * sc2) + 1);
sc3_plot = log((1e7 * sc3) + 1);
sc_diff = sc3_plot - sc2_plot;
fc_diff = fc3 - fc2;

set(0, 'DefaultFigureVisible', 'off');

plot_and_save(fc2, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 2 FC', fullfile(out_dir, sprintf('py2_fc_%s.png', resolution)), ...
    [-0.1 0.35], 'FC');
plot_and_save(fc3, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 3 FC', fullfile(out_dir, sprintf('py3_fc_%s.png', resolution)), ...
    [-0.1 0.35], 'FC');
plot_and_save(fc_diff, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 3 - Python 2 FC', fullfile(out_dir, sprintf('diff_fc_%s.png', resolution)), ...
    symmetric_clim(fc_diff), 'Delta FC');

plot_and_save(sc2_plot, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 2 log SC', fullfile(out_dir, sprintf('py2_sc_%s.png', resolution)), ...
    [0 3.5], 'log SC');
plot_and_save(sc3_plot, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 3 log SC', fullfile(out_dir, sprintf('py3_sc_%s.png', resolution)), ...
    [0 3.5], 'log SC');
plot_and_save(sc_diff, sbci_parc(atlas_index), roi_exclusion_index, ...
    'Python 3 - Python 2 log SC', fullfile(out_dir, sprintf('diff_sc_%s.png', resolution)), ...
    symmetric_clim(sc_diff), 'Delta log SC');

save_summary(out_dir, fc2, fc3, sc2, sc3);
fprintf('Saved SBCI_Toolkit visualizations to: %s\n', out_dir);

end

function sc = sym_sc(sc)
sc = sc + sc' - 2 * diag(diag(sc));
end

function plot_and_save(data, parc, roi_mask, fig_title, out_file, clim, legend_text)
fig = plot_sbci_mat(data, parc, 'roi_mask', roi_mask, 'figid', 1, ...
    'clim', clim, 'legend', legend_text);
title(fig_title, 'Interpreter', 'none');
set(fig, 'Color', 'w', 'Position', [100 100 1200 1000]);
print(fig, out_file, '-dpng', '-r180');
close(fig);
end

function c = symmetric_clim(data)
m = max(abs(data(:)));
if m == 0
    m = 1;
end
c = [-m m];
end

function save_summary(out_dir, fc2, fc3, sc2, sc3)
summary_file = fullfile(out_dir, 'py2_py3_visualization_summary.txt');
fid = fopen(summary_file, 'w');
fprintf(fid, 'FC max abs diff: %.16g\n', max(abs(fc3(:) - fc2(:))));
fprintf(fid, 'FC mean abs diff: %.16g\n', mean(abs(fc3(:) - fc2(:))));
fprintf(fid, 'SC max abs diff: %.16g\n', max(abs(sc3(:) - sc2(:))));
fprintf(fid, 'SC mean abs diff: %.16g\n', mean(abs(sc3(:) - sc2(:))));
fclose(fid);
end

function p = expand_user(p)
p = string(p);
if startsWith(p, "~")
    p = string(getenv('HOME')) + extractAfter(p, 1);
end
end
