function [result] = plotwmhist(sc,fc,plt_title,filename)

sc_nodiag = sc;
sc_nodiag = sc_nodiag > 0;
sc_nodiag = sc_nodiag - diag(diag(sc_nodiag));
 
sc_noconn = ones(size(sc_nodiag))-sc_nodiag;
sc_noconn = sc_noconn - diag(diag(sc_noconn));
 
set1_conn = fc .* sc_nodiag;
set1_conn(~sc_nodiag) = nan;

set2_conn = fc .* sc_noconn;
set2_conn(~sc_noconn) = nan;

idx = tril(true(size(set1_conn)));
set1_conn(idx) = nan;
set2_conn(idx) = nan;
 
set1_conn_vec = set1_conn(find(set1_conn));
set1_conn_vec = set1_conn_vec(~isnan(set1_conn_vec));
 
set2_conn_vec = set2_conn(find(set2_conn));
set2_conn_vec = set2_conn_vec(~isnan(set2_conn_vec));

wm_mean = mean(set1_conn_vec);
wm_count = size(set1_conn_vec, 1);
wm_var = var(set1_conn_vec);

no_mean = mean(set2_conn_vec);
no_count = size(set2_conn_vec, 1);
no_var = var(set2_conn_vec);

[h,p] = ttest2(set1_conn_vec, set2_conn_vec);

plt = figure('visible', 'off');
myBins = linspace(-1,1, 100);

histogram(set1_conn_vec,myBins,'FaceColor','#440154','FaceAlpha',0.6,'Normalization','probability')
hold on
histogram(set2_conn_vec,myBins,'FaceColor','#FDE725','FaceAlpha',0.6,'Normalization','probability')

box off
ylim([0, 0.1]);

legend('With WM','W/O WM','location','northwest')
legend boxoff

title(plt_title);
text(0.3, 0.095, sprintf('p-value: %12.2e', p))

saveas(plt, filename);

result = {plt_title, wm_mean, wm_var, wm_count, no_mean, no_var, no_count};
end

