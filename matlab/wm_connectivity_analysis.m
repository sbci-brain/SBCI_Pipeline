% MATLAB R2009b
% Perform region-based analysis
clear variables;

folder = './test_data/connectivity/RN015_ENTRY';
ress = [{'99'}, {'97'}, {'95'}];

%cons = [{'pg'}, {'p'}, {''}];
%descs = [{'FC|SC with motion, wm, vcsf, gs'}, {'FC|SC with motion, wm, vcsf'}, {'FC|SC'}];

cons = [{'pg'}, {'p'}];
descs = [{'FC|SC controlling for gs'}, {'FC|SC'}];


% brain regions (r: right, l: left, f: frontal, t: temporal, etc.)
rfl = fliplr([65,61,60,57,53,52,51,50,47,45,37]);
rsu = [68];
rlc = fliplr([59,56,49,43,36]);
rpl = fliplr([64,62,58,55,41]);
rtl = fliplr([67,66,63,48,42,40,39,35]);
rol = fliplr([54,46,44,38]);

lfl = [3,11,13,16,17,18,19,23,26,27,31];
lsu = [34];
llc = [2,9,15,22,25];
lpl = [7,21,24,28,30];
ltl = [1,5,6,8,14,29,32,33];
lol = [4,10,12,20];

regions = [{lfl}, {rfl}, {"LFL"}, {"RFL"}, {"lfl_rfl"};
           {lpl}, {rpl}, {"LPL"}, {"RPL"}, {"lpl_rpl"};
           %{ltl}, {rtl}, {"LTL"}, {"RTL"}, {"ltl_rtl"};
           {lol}, {rol}, {"LOL"}, {"ROL"}, {"lol_rol"};
           
           %{lfl}, {rpl}, {"LFL"}, {"RPL"}, {"lfl_rpl"};
           %{rfl}, {lpl}, {"RFL"}, {"LPL"}, {"rfl_lpl"};
           {lfl}, {lpl}, {"LFL"}, {"LPL"}, {"lfl_lpl"};
           {rfl}, {rpl}, {"RFL"}, {"RPL"}, {"rfl_rpl"};
                      
           %{lfl}, {rtl}, {"LFL"}, {"RTL"}, {"lfl_rtl"};
           %{rfl}, {ltl}, {"RFL"}, {"LTL"}, {"rfl_ltl"};
           {lfl}, {ltl}, {"LFL"}, {"LTL"}, {"lfl_ltl"};
           {rfl}, {rtl}, {"RFL"}, {"RTL"}, {"rfl_rtl"};
           
           %{lfl}, {rol}, {"LFL"}, {"ROL"}, {"lfl_rol"};
           %{rfl}, {lol}, {"RFL"}, {"LOL"}, {"rfl_lol"};
           %{lfl}, {lol}, {"LFL"}, {"LOL"}, {"lfl_lol"};
           %{rfl}, {rol}, {"RFL"}, {"ROL"}, {"rfl_rol"};
           
           %{lpl}, {rtl}, {"LPL"}, {"RTL"}, {"lpl_rtl"};
           %{rpl}, {ltl}, {"RPL"}, {"LTL"}, {"rpl_ltl"};
           {lpl}, {ltl}, {"LPL"}, {"LTL"}, {"lpl_ltl"};
           {rpl}, {rtl}, {"RPL"}, {"RTL"}, {"rpl_rtl"};
           
           %{lpl}, {rol}, {"LPL"}, {"ROL"}, {"lpl_rol"};
           %{rpl}, {lol}, {"RPL"}, {"LOL"}, {"rpl_lol"};
           %{lpl}, {lol}, {"LPL"}, {"LOL"}, {"lpl_lol"};
           %{rpl}, {rol}, {"RPL"}, {"ROL"}, {"rpl_rol"};
           
           %{lol}, {rtl}, {"LOL"}, {"RTL"}, {"lol_rtl"};
           %{rol}, {ltl}, {"ROL"}, {"LTL"}, {"rol_ltl"};
           {lol}, {ltl}, {"LOL"}, {"LTL"}, {"lol_ltl"};
           {rol}, {rtl}, {"ROL"}, {"RTL"}, {"rol_rtl"}];

result = table("N/A", 0, 0, 0, 0, 0, 0, 'VariableNames', ...
    {'ID', 'wm_mean', 'wm_var', 'wm_count', 'no_mean', 'no_var', 'no_count'});

result = repmat(result, length(cons) * length(ress) * size(regions,1) * 6, 1);

k = 1;

for j = 1:length(ress)
  for i = 1:length(cons)    
    con = cons{i};
    res = ress{j};
    desc = descs{i};
    
    load(sprintf('%s/masks%s.mat', folder, res));

    [sc,fc] = np2matlab(sprintf('%s/connectivity%s%s.mat', folder, res, con));
    [sc,fc,nan_mask,sorted_idx,roi_labels] = sortandmask(sprintf('%s/mapping%s%s.mat', folder, res, con), sc, fc);

    stats = plotwmhist(sc, fc, sprintf('0.%s %s', res, desc), sprintf('%s%s.png', res, con));
    
    result(k, 1:end) = stats;
    k = k + 1;
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % generate plots between selected regions %
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    for u = 1:size(regions,1)
      mask_a = find(ismember(roi_labels, regions{u,1})');
      mask_b = find(ismember(roi_labels, regions{u,2})');

      region_mask = [mask_a, mask_b];

      region_sc = sc(region_mask, region_mask);
      region_fc = fc(region_mask, region_mask);

      stats = plotwmhist(region_sc, region_fc, ...
          sprintf('0.%s %s - %s & %s', res, desc, regions{u, 3}, regions{u, 4}), ...
          sprintf('%s%s_%s_0.png', res, con, regions{u, 5}));
    
      result(k, 1:end) = stats;
      k = k + 1;
    
      plotmatrix(log(region_sc), roi_labels(region_mask), ...
          sprintf('0.%s %s - %s & %s SC', res, desc, regions{u, 3}, regions{u, 4}), ...
          sprintf('%s%s_%s_sc.png', res, con, regions{u, 5}), []);
    
      plotmatrix(region_fc, roi_labels(region_mask), ...
          sprintf('0.%s %s - %s & %s FC', res, desc, regions{u, 3}, regions{u, 4}), ...
          sprintf('%s%s_%s_fc.png', res, con, regions{u, 5}), [-0.9, 0.9]);

      r1 = size(mask_a, 2);
      r2 = size(region_mask, 2);
      
      section = [{1:r1}, {(r1+1):r2};
                 {1:r1}, {1:r1};
                 {(r1+1):r2}, {(r1+1):r2}];
      
      labels = [{sprintf('0.%s %s - Across %s & %s', res, desc, regions{u, 3}, regions{u, 4})}, ...
                {sprintf('0.%s %s - Within %s', res, desc, regions{u, 3})}, ...
                {sprintf('0.%s %s - Within %s', res, desc, regions{u, 4})}];
    
      for v = 1:3
        inter_sc = region_sc(section{v,1}, section{v,2});
        inter_fc = region_fc(section{v,1}, section{v,2});
    
        padded_sc = padarray(inter_sc, max(size(inter_sc)) - size(inter_sc), nan, 'post');
        padded_fc = padarray(inter_fc, max(size(inter_fc)) - size(inter_fc), nan, 'post');

        stats = plotwmhist(padded_sc, padded_fc, labels{v}, ...
            sprintf('%s%s_%s_%s.png', res, con, regions{u, 5}, string(v)));
    
        result(k, 1:end) = stats;
        k = k + 1;
      end
    end
    
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    % generate plots for each of the following distance masks %
    %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
    masks = [{mask05(sorted_idx+1, sorted_idx+1)}, {'5mm'};
             {mask10(sorted_idx+1, sorted_idx+1)}, {'10mm'};
             {mask15(sorted_idx+1, sorted_idx+1)}, {'15mm'};
             {mask20(sorted_idx+1, sorted_idx+1)}, {'20mm'}];
         
    for u = 1:size(masks, 1)
      dst_mask = masks{u,1};
      dst_mask = dst_mask(nan_mask, nan_mask);

      fc(dst_mask) = nan;

      stats = plotwmhist(sc, fc, ...
          sprintf('0.%s %s - %s mask', res, desc, masks{u,2}), ...
          sprintf('%s%s_%s.png', res, con, masks{u,2}));
    
      result(k, 1:end) = stats;
      k = k + 1;
    end
  end
end

writetable(result, 'result.txt');
