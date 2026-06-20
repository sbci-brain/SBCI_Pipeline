#!/usr/bin/env python3
"""
visualize_connectivity.py
--------------------------
Generates a multi-panel comparison figure from Python 2 vs Python 3
SBCI Step 3 filtered intersection files.  Uses ONLY existing .npz data —
no new tractography, no stochasticity.

Panels produced (3 rows × 4 columns):
  Row 1 — Connectivity matrices: Py2 | Py3 | Difference | Per-pair scatter
  Row 2 — Streamline counts:     Bar chart per run | Percentage difference
  Row 3 — Endpoint distributions: X / Y / Z histograms | Total count bar

Usage (run on cluster from subject root):
  python3 /path/to/SBCI_Pipeline/tests_py3/visualize_connectivity.py \\
      --py2_dir dwi_pipeline/set/streamline \\
      --py3_dir dwi_pipeline/set/streamline_py3 \\
      --n_runs 4 \\
      --output sbci_connectivity_comparison.png
"""

import argparse
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')          # works on cluster without a display
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


# ------------------------------------------------------------------ #
#  I/O helpers                                                        #
# ------------------------------------------------------------------ #
def load_intersections(path):
    d = np.load(path)
    return d['surf_ids0'], d['tri_ids0'], d['pts0'], \
           d['surf_ids1'], d['tri_ids1'], d['pts1']


def build_matrix(surf_ids0, surf_ids1):
    """Symmetric surface-pair connectivity matrix."""
    n = int(max(surf_ids0.max(), surf_ids1.max())) + 1
    mat = np.zeros((n, n), dtype=np.float64)
    for s0, s1 in zip(surf_ids0, surf_ids1):
        mat[s0, s1] += 1
        if s0 != s1:
            mat[s1, s0] += 1
    return mat


def pad_matrix(mat, n):
    """Zero-pad mat to (n × n) so all matrices can be averaged."""
    out = np.zeros((n, n), dtype=np.float64)
    out[:mat.shape[0], :mat.shape[1]] = mat
    return out


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--py2_dir', required=True,
                   help='Python 2 streamline directory')
    p.add_argument('--py3_dir', required=True,
                   help='Python 3 streamline directory')
    p.add_argument('--n_runs', type=int, default=4)
    p.add_argument('--output', default='sbci_connectivity_comparison.png',
                   help='Output PNG path')
    args = p.parse_args()

    counts2, counts3 = [], []
    mats2,   mats3   = [], []
    pts_py2, pts_py3 = [], []

    for run in range(1, args.n_runs + 1):
        f2 = os.path.join(args.py2_dir,
                          f'intersections_random_loop{run}_filtered.npz')
        f3 = os.path.join(args.py3_dir,
                          f'intersections_random_loop{run}_filtered.npz')
        if not os.path.exists(f2):
            print(f'  Missing Py2 run {run}: {f2}'); continue
        if not os.path.exists(f3):
            print(f'  Missing Py3 run {run}: {f3}'); continue

        s0_2, _, p0_2, s1_2, _, _ = load_intersections(f2)
        s0_3, _, p0_3, s1_3, _, _ = load_intersections(f3)

        counts2.append(len(s0_2));  counts3.append(len(s0_3))
        mats2.append(build_matrix(s0_2, s1_2))
        mats3.append(build_matrix(s0_3, s1_3))
        pts_py2.append(p0_2);       pts_py3.append(p0_3)

    if not counts2:
        raise RuntimeError('No runs found — check --py2_dir / --py3_dir paths.')

    # Average connectivity matrices across runs
    n_surf = max(m.shape[0] for m in mats2 + mats3)
    avg2 = np.mean([pad_matrix(m, n_surf) for m in mats2], axis=0)
    avg3 = np.mean([pad_matrix(m, n_surf) for m in mats3], axis=0)
    diff = avg3 - avg2

    pts2 = np.concatenate(pts_py2, axis=0)
    pts3 = np.concatenate(pts_py3, axis=0)
    runs = list(range(1, len(counts2) + 1))

    # ---------------------------------------------------------------- #
    #  Figure layout                                                    #
    # ---------------------------------------------------------------- #
    fig = plt.figure(figsize=(22, 17))
    fig.suptitle(
        'SBCI Step 3 — Python 2 vs Python 3 Output Comparison',
        fontsize=17, fontweight='bold', y=0.99)
    gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.45, wspace=0.38)

    # ── Row 1: Connectivity matrices ──────────────────────────────── #
    cmap_mat = 'hot'
    shared_log_max = np.log1p(max(avg2.max(), avg3.max()))

    ax1 = fig.add_subplot(gs[0, 0])
    im1 = ax1.imshow(np.log1p(avg2), cmap=cmap_mat, aspect='auto',
                     vmin=0, vmax=shared_log_max)
    ax1.set_title('Python 2\nConnectivity Matrix (log)', fontsize=11, fontweight='bold')
    ax1.set_xlabel('Surface index'); ax1.set_ylabel('Surface index')
    plt.colorbar(im1, ax=ax1, fraction=0.046, label='log(count + 1)')

    ax2 = fig.add_subplot(gs[0, 1])
    im2 = ax2.imshow(np.log1p(avg3), cmap=cmap_mat, aspect='auto',
                     vmin=0, vmax=shared_log_max)
    ax2.set_title('Python 3\nConnectivity Matrix (log)', fontsize=11, fontweight='bold')
    ax2.set_xlabel('Surface index')
    plt.colorbar(im2, ax=ax2, fraction=0.046, label='log(count + 1)')

    ax3 = fig.add_subplot(gs[0, 2])
    vabs = max(np.abs(diff).max(), 1.0)
    im3 = ax3.imshow(diff, cmap='RdBu_r', aspect='auto',
                     vmin=-vabs, vmax=vabs)
    ax3.set_title('Difference\n(Py3 − Py2)', fontsize=11, fontweight='bold')
    ax3.set_xlabel('Surface index')
    plt.colorbar(im3, ax=ax3, fraction=0.046, label='Δ count')

    ax4 = fig.add_subplot(gs[0, 3])
    f2_flat = avg2.flatten(); f3_flat = avg3.flatten()
    mask = (f2_flat > 0) | (f3_flat > 0)
    ax4.scatter(f2_flat[mask], f3_flat[mask],
                alpha=0.35, s=10, color='steelblue', rasterized=True)
    lim = max(f2_flat[mask].max(), f3_flat[mask].max())
    ax4.plot([0, lim], [0, lim], 'r--', lw=1.5, label='y = x  (perfect)')
    corr = np.corrcoef(f2_flat[mask], f3_flat[mask])[0, 1]
    ax4.set_title(f'Per-pair Scatter\n(r = {corr:.6f})', fontsize=11, fontweight='bold')
    ax4.set_xlabel('Py2 count'); ax4.set_ylabel('Py3 count')
    ax4.legend(fontsize=8)

    # ── Row 2: Streamline counts ──────────────────────────────────── #
    x = np.arange(len(runs)); w = 0.35
    ax5 = fig.add_subplot(gs[1, :2])
    b2 = ax5.bar(x - w/2, counts2, w, label='Python 2',
                 color='royalblue', alpha=0.85, edgecolor='black', lw=0.5)
    b3 = ax5.bar(x + w/2, counts3, w, label='Python 3',
                 color='tomato',    alpha=0.85, edgecolor='black', lw=0.5)
    ax5.set_xticks(x); ax5.set_xticklabels([f'Run {r}' for r in runs])
    ax5.set_ylabel('Streamline count')
    ax5.set_title('Streamline Count per Run', fontsize=12, fontweight='bold')
    ax5.legend()
    ylo = min(counts2 + counts3) * 0.985
    yhi = max(counts2 + counts3) * 1.015
    ax5.set_ylim(ylo, yhi)
    for bar in b2:
        ax5.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + (yhi - ylo) * 0.003,
                 f'{int(bar.get_height()):,}',
                 ha='center', va='bottom', fontsize=7)
    for bar in b3:
        ax5.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + (yhi - ylo) * 0.003,
                 f'{int(bar.get_height()):,}',
                 ha='center', va='bottom', fontsize=7)

    diffs_pct = [100 * (n3 - n2) / n2 for n2, n3 in zip(counts2, counts3)]
    ax6 = fig.add_subplot(gs[1, 2:])
    colors = ['seagreen' if d >= 0 else 'tomato' for d in diffs_pct]
    bars = ax6.bar([f'Run {r}' for r in runs], diffs_pct,
                   color=colors, alpha=0.85, edgecolor='black', lw=0.5)
    ax6.axhline(0, color='black', lw=1)
    mean_diff = np.mean(diffs_pct)
    ax6.axhline(mean_diff, color='navy', lw=1.8, linestyle='--',
                label=f'Mean {mean_diff:+.2f}%')
    ax6.set_ylabel('Count difference (%)'); ax6.set_xlabel('Run')
    ax6.set_title('Py3 − Py2 Count Difference (%)', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=9)
    for bar, val in zip(bars, diffs_pct):
        offset = 0.008 * max(abs(v) for v in diffs_pct) if diffs_pct else 0.01
        ax6.text(bar.get_x() + bar.get_width() / 2,
                 val + (offset if val >= 0 else -offset * 2.5),
                 f'{val:+.2f}%', ha='center', va='bottom', fontsize=9)

    # ── Row 3: Endpoint distributions ────────────────────────────── #
    dim_labels = ['X (mm)', 'Y (mm)', 'Z (mm)']
    for i in range(3):
        ax = fig.add_subplot(gs[2, i])
        ax.hist(pts2[:, i], bins=80, density=True,
                alpha=0.6, color='royalblue', label='Python 2')
        ax.hist(pts3[:, i], bins=80, density=True,
                alpha=0.6, color='tomato',    label='Python 3')
        ax.set_xlabel(dim_labels[i]); ax.set_ylabel('Density')
        ax.set_title(f'Endpoint {dim_labels[i]}\nDistribution', fontsize=11)
        if i == 0:
            ax.legend(fontsize=9)

    total2 = sum(counts2); total3 = sum(counts3)
    ax_tot = fig.add_subplot(gs[2, 3])
    bar_tot = ax_tot.bar(['Python 2', 'Python 3'], [total2, total3],
                         color=['royalblue', 'tomato'],
                         alpha=0.85, edgecolor='black', lw=0.8)
    ax_tot.set_ylabel('Total streamlines (all runs)')
    pct = 100 * (total3 - total2) / total2
    ax_tot.set_title(
        f'Total Streamlines\nΔ = {total3 - total2:+,}  ({pct:+.2f}%)',
        fontsize=11, fontweight='bold')
    for bar, val in zip(bar_tot, [total2, total3]):
        ax_tot.text(bar.get_x() + bar.get_width() / 2,
                    val + total2 * 0.004,
                    f'{val:,}', ha='center', fontsize=10, fontweight='bold')

    # ── Save ─────────────────────────────────────────────────────── #
    plt.savefig(args.output, dpi=150, bbox_inches='tight', facecolor='white')
    print(f'Saved → {args.output}')


if __name__ == '__main__':
    main()
