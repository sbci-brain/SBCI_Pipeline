#!/usr/bin/env python3
"""
Visualize Python 2 vs Python 3 structural-connectivity differences.

This focuses on distribution-level diagnostics rather than anatomical layout:
raw differences, absolute differences, relative differences, log-scale
differences, and Py2-vs-Py3 scatter.
"""

import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy.io as scio


def load_sc(path):
    data = scio.loadmat(path)
    if "sc" not in data:
        raise KeyError(f'{path} does not contain key "sc"')
    return np.asarray(data["sc"], dtype=np.float64)


def percentile_lines(ax, values, percentiles=(50, 90, 95, 99, 99.9)):
    for p in percentiles:
        x = np.percentile(values, p)
        ax.axvline(x, color="k", alpha=0.25, linewidth=0.8)
        ax.text(x, ax.get_ylim()[1] * 0.92, f"p{p:g}", rotation=90,
                va="top", ha="right", fontsize=7)


def hist(ax, values, title, xlabel, bins=120, log_y=True, pct=True):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    ax.hist(values, bins=bins, color="#4c78a8", alpha=0.85)
    if log_y:
        ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    if values.size and pct:
        percentile_lines(ax, values)


def write_summary(path, py2, py3, masks):
    diff = py3 - py2
    abs_diff = np.abs(diff)

    with open(path, "w") as f:
        f.write(f"shape: {py2.shape}\n")
        f.write(f"py2 sum: {py2.sum():.16g}\n")
        f.write(f"py3 sum: {py3.sum():.16g}\n")
        f.write(f"sum diff: {(py3.sum() - py2.sum()):.16g}\n")
        f.write(f"sum diff percent: {100 * (py3.sum() - py2.sum()) / py2.sum():.16g}\n")
        f.write(f"max abs diff: {abs_diff.max():.16g}\n")
        f.write(f"mean abs diff all: {abs_diff.mean():.16g}\n")
        f.write(f"relative L1: {abs_diff.sum() / np.abs(py2).sum():.16g}\n")
        f.write(f"relative L2: {np.linalg.norm(diff) / np.linalg.norm(py2):.16g}\n")
        union = masks["nonzero_union"]
        f.write(f"corr nonzero union: {np.corrcoef(py2[union].ravel(), py3[union].ravel())[0, 1]:.16g}\n")

        for name, mask in masks.items():
            vals = abs_diff[mask]
            f.write(f"\n[{name}] n={vals.size}\n")
            if vals.size == 0:
                continue
            f.write(f"abs diff mean: {vals.mean():.16g}\n")
            for p in [50, 90, 95, 99, 99.9, 99.99, 100]:
                f.write(f"abs diff p{p:g}: {np.percentile(vals, p):.16g}\n")

            rel = vals / (np.abs(py2[mask]) + 1e-12)
            f.write(f"relative diff mean: {rel.mean():.16g}\n")
            for p in [50, 90, 95, 99, 99.9, 99.99, 100]:
                f.write(f"relative diff p{p:g}: {np.percentile(rel, p):.16g}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--py2_sc", required=True, help="Py2 smoothed_sc .mat file")
    parser.add_argument("--py3_sc", required=True, help="Py3 smoothed_sc .mat file")
    parser.add_argument("--out_dir", required=True, help="Output directory for PNGs and summary")
    parser.add_argument("--sample", type=int, default=500000,
                        help="Maximum points for scatter plot [default: %(default)s]")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    py2 = load_sc(args.py2_sc)
    py3 = load_sc(args.py3_sc)
    if py2.shape != py3.shape:
        raise ValueError(f"Shape mismatch: Py2={py2.shape}, Py3={py3.shape}")

    diff = py3 - py2
    abs_diff = np.abs(diff)
    log2 = np.log1p(1e7 * py2)
    log3 = np.log1p(1e7 * py3)
    log_diff = log3 - log2

    masks = {
        "all": np.ones(py2.shape, dtype=bool),
        "nonzero_union": (py2 != 0) | (py3 != 0),
        "py2_gt_0": py2 > 0,
        "py2_gt_1": py2 > 1,
        "py2_gt_10": py2 > 10,
    }

    write_summary(os.path.join(args.out_dir, "sc_difference_distribution_summary.txt"),
                  py2, py3, masks)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    hist(axes[0, 0], diff[masks["nonzero_union"]], "Raw Difference Distribution", "Py3 - Py2")
    hist(axes[0, 1], abs_diff[masks["nonzero_union"]], "Absolute Difference Distribution", "|Py3 - Py2|")
    hist(axes[1, 0], log_diff[masks["nonzero_union"]], "Log-SC Difference Distribution",
         "log(1e7*Py3+1) - log(1e7*Py2+1)")
    hist(axes[1, 1], abs_diff[masks["py2_gt_10"]] / (np.abs(py2[masks["py2_gt_10"]]) + 1e-12),
         "Relative Difference Distribution (Py2 > 10)", "|Py3-Py2| / Py2")
    fig.suptitle("SBCI Structural Connectivity Difference Overview", fontsize=15, fontweight="bold")
    fig.savefig(os.path.join(args.out_dir, "sc_difference_histograms.png"), dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)
    for ax, name in zip(axes, ["py2_gt_0", "py2_gt_1", "py2_gt_10"]):
        vals = abs_diff[masks[name]] / (np.abs(py2[masks[name]]) + 1e-12)
        hist(ax, vals, f"Relative Difference ({name})", "|Py3-Py2| / Py2", bins=120)
    fig.savefig(os.path.join(args.out_dir, "sc_relative_difference_by_threshold.png"), dpi=180)
    plt.close(fig)

    union_idx = np.flatnonzero(masks["nonzero_union"].ravel())
    rng = np.random.default_rng(0)
    if union_idx.size > args.sample:
        union_idx = rng.choice(union_idx, size=args.sample, replace=False)

    py2_flat = py2.ravel()[union_idx]
    py3_flat = py3.ravel()[union_idx]
    fig, ax = plt.subplots(figsize=(7, 7), constrained_layout=True)
    ax.scatter(py2_flat, py3_flat, s=2, alpha=0.18, color="#4c78a8", edgecolors="none")
    maxv = max(float(py2_flat.max()), float(py3_flat.max()))
    ax.plot([0, maxv], [0, maxv], "r--", linewidth=1)
    ax.set_xlabel("Py2 SC")
    ax.set_ylabel("Py3 SC")
    ax.set_title("Py2 vs Py3 SC Scatter (Nonzero Union Sample)")
    ax.set_xlim(0, maxv)
    ax.set_ylim(0, maxv)
    fig.savefig(os.path.join(args.out_dir, "sc_py2_vs_py3_scatter.png"), dpi=180)
    plt.close(fig)

    print(f"Saved SC difference distribution plots to: {args.out_dir}")


if __name__ == "__main__":
    main()
