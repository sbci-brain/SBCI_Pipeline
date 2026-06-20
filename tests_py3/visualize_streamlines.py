#!/usr/bin/env python3
"""
visualize_streamlines.py
-------------------------
Renders Python 2 and Python 3 tractograms side-by-side using nibabel +
matplotlib.  Loads existing .trk files — no new data created, no stochasticity.

Three-row figure:
  Row 1 — Axial view    (XY plane)   Py2 | Py3 | overlay
  Row 2 — Coronal view  (XZ plane)   Py2 | Py3 | overlay
  Row 3 — Sagittal view (YZ plane)   Py2 | Py3 | overlay

Streamlines are coloured by local orientation (RGB convention:
  red = left/right, green = anterior/posterior, blue = inferior/superior).

Usage (run on cluster from subject root):
  python3 /path/to/SBCI_Pipeline/tests_py3/visualize_streamlines.py \\
      --trk_py2  dwi_pipeline/set/streamline/set_random_loop1.trk \\
      --trk_py3  dwi_pipeline/set/streamline_py3/set_random_loop1.trk \\
      --n_streamlines 2000 \\
      --output streamline_comparison.png
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

try:
    import nibabel as nib
    from nibabel.streamlines import load as load_trk
except ImportError:
    raise ImportError('nibabel is required: pip install nibabel')


# ------------------------------------------------------------------ #
#  Helpers                                                            #
# ------------------------------------------------------------------ #
def load_streamlines(trk_path, n_max=None, rng=None):
    """Load streamlines from .trk, optionally subsample."""
    tractogram = load_trk(trk_path)
    streamlines = list(tractogram.streamlines)
    if n_max is not None and len(streamlines) > n_max:
        if rng is None:
            rng = np.random.default_rng(42)   # fixed seed — no new stochasticity
        idx = rng.choice(len(streamlines), size=n_max, replace=False)
        streamlines = [streamlines[i] for i in idx]
    return streamlines


def direction_color(pts):
    """
    Colour each point by the local tangent direction (RGB convention).
    Returns an (N, 3) float array in [0, 1].
    """
    if len(pts) < 2:
        return np.ones((len(pts), 3)) * 0.5
    tangents = np.diff(pts, axis=0)
    # Pad so lengths match
    tangents = np.vstack([tangents, tangents[-1]])
    norms = np.linalg.norm(tangents, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    tangents = np.abs(tangents / norms)          # absolute value → RGB
    return tangents                              # shape (N, 3)


def plot_projection(ax, streamlines, axis0, axis1,
                    alpha=0.25, lw=0.4, max_pts=200):
    """
    Draw streamlines projected onto (axis0, axis1) axes.
    Each streamline is coloured by its mean direction colour.
    """
    for sl in streamlines:
        if len(sl) < 2:
            continue
        # Subsample long streamlines for speed
        if len(sl) > max_pts:
            idx = np.linspace(0, len(sl)-1, max_pts, dtype=int)
            sl = sl[idx]
        col = direction_color(sl).mean(axis=0)     # single colour per line
        ax.plot(sl[:, axis0], sl[:, axis1],
                color=col, alpha=alpha, lw=lw, rasterized=True)


def endpoint_scatter(ax, streamlines, axis0, axis1,
                     color, alpha=0.3, s=1.5):
    """Scatter the start endpoints of all streamlines."""
    pts = np.array([sl[0] for sl in streamlines if len(sl) > 0])
    if len(pts):
        ax.scatter(pts[:, axis0], pts[:, axis1],
                   c=color, alpha=alpha, s=s, rasterized=True)


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #
def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument('--trk_py2',  required=True,
                   help='Python 2 tractogram (.trk)')
    p.add_argument('--trk_py3',  required=True,
                   help='Python 3 tractogram (.trk)')
    p.add_argument('--n_streamlines', type=int, default=2000,
                   help='Number of streamlines to render per version [%(default)s]')
    p.add_argument('--output', default='streamline_comparison.png')
    args = p.parse_args()

    print(f'Loading Python 2 tractogram: {args.trk_py2}')
    sl_py2 = load_streamlines(args.trk_py2, n_max=args.n_streamlines)
    print(f'  → {len(sl_py2)} streamlines loaded')

    print(f'Loading Python 3 tractogram: {args.trk_py3}')
    sl_py3 = load_streamlines(args.trk_py3, n_max=args.n_streamlines)
    print(f'  → {len(sl_py3)} streamlines loaded')

    # Axis pairs: (axis0, axis1) → plane label
    views = [
        (0, 1, 'Axial  (X–Y)'),
        (0, 2, 'Coronal  (X–Z)'),
        (1, 2, 'Sagittal  (Y–Z)'),
    ]
    axis_names = ['X (mm)', 'Y (mm)', 'Z (mm)']

    fig = plt.figure(figsize=(18, 16))
    fig.suptitle(
        f'SBCI Tractography — Python 2 vs Python 3\n'
        f'({args.n_streamlines} streamlines per version, '
        f'coloured by local orientation)',
        fontsize=15, fontweight='bold', y=0.99)

    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.25)

    for row, (a0, a1, view_label) in enumerate(views):
        # Compute shared axis limits from combined data
        all_pts_a0 = np.concatenate(
            [sl[:, a0] for sl in sl_py2 + sl_py3 if len(sl) > 0])
        all_pts_a1 = np.concatenate(
            [sl[:, a1] for sl in sl_py2 + sl_py3 if len(sl) > 0])
        lo0, hi0 = np.percentile(all_pts_a0, [1, 99])
        lo1, hi1 = np.percentile(all_pts_a1, [1, 99])

        for col, (sl_set, label) in enumerate(
                [(sl_py2, 'Python 2'), (sl_py3, 'Python 3')]):
            ax = fig.add_subplot(gs[row, col])
            plot_projection(ax, sl_set, a0, a1)
            ax.set_xlim(lo0, hi0); ax.set_ylim(lo1, hi1)
            ax.set_xlabel(axis_names[a0]); ax.set_ylabel(axis_names[a1])
            ax.set_facecolor('black')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_edgecolor('gray')
            ax.set_title(f'{view_label}\n{label}', fontsize=10, fontweight='bold')

        # Overlay panel (col 2): endpoints Py2 in blue, Py3 in red
        ax_ov = fig.add_subplot(gs[row, 2])
        endpoint_scatter(ax_ov, sl_py2, a0, a1, color='royalblue',
                         alpha=0.4, s=2)
        endpoint_scatter(ax_ov, sl_py3, a0, a1, color='tomato',
                         alpha=0.4, s=2)
        ax_ov.set_xlim(lo0, hi0); ax_ov.set_ylim(lo1, hi1)
        ax_ov.set_xlabel(axis_names[a0]); ax_ov.set_ylabel(axis_names[a1])
        ax_ov.set_facecolor('black')
        ax_ov.tick_params(colors='white')
        for spine in ax_ov.spines.values():
            spine.set_edgecolor('gray')
        ax_ov.set_title(f'{view_label}\nEndpoints overlay', fontsize=10)

        # Legend on first overlay panel only
        if row == 0:
            from matplotlib.lines import Line2D
            legend_els = [
                Line2D([0], [0], marker='o', color='w',
                       markerfacecolor='royalblue', markersize=8, label='Python 2'),
                Line2D([0], [0], marker='o', color='w',
                       markerfacecolor='tomato',    markersize=8, label='Python 3'),
            ]
            ax_ov.legend(handles=legend_els, loc='upper right',
                         fontsize=8, facecolor='#222222', labelcolor='white')

    plt.savefig(args.output, dpi=150, bbox_inches='tight', facecolor='#111111')
    print(f'Saved → {args.output}')


if __name__ == '__main__':
    main()
