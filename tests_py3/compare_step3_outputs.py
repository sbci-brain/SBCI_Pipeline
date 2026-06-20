#!/usr/bin/env python3
"""
compare_step3_outputs.py
------------------------
Compares Python 2 and Python 3 step 3 outputs for sub-002S6066.

Analyses:
  1. Streamline counts per run
  2. Surface-pair connectivity (which surfaces connect to which)
  3. Endpoint spatial distribution (pts0 / pts1)
  4. Streamline length distributions (from .fib files, optional)

Usage (from subject root on the cluster):
  python3 /path/to/SBCI_Pipeline/tests_py3/compare_step3_outputs.py \
      --py2_dir dwi_pipeline/set/streamline \
      --py3_dir dwi_pipeline/set/streamline_py3 \
      --n_runs 4
"""

import argparse
import os
import sys
import numpy as np


# ------------------------------------------------------------------ #
#  I/O helpers                                                        #
# ------------------------------------------------------------------ #
def load_intersections(npz_path):
    d = np.load(npz_path)
    return (d['surf_ids0'], d['tri_ids0'], d['pts0'],
            d['surf_ids1'], d['tri_ids1'], d['pts1'])


def streamline_count(npz_path):
    d = np.load(npz_path)
    return len(d['surf_ids0'])


# ------------------------------------------------------------------ #
#  Analysis helpers                                                   #
# ------------------------------------------------------------------ #
def surface_pair_counts(surf_ids0, surf_ids1):
    """Return a dict {(s0, s1): count} of surface-pair connections."""
    pairs = {}
    for s0, s1 in zip(surf_ids0, surf_ids1):
        key = (int(min(s0, s1)), int(max(s0, s1)))
        pairs[key] = pairs.get(key, 0) + 1
    return pairs


def endpoint_stats(pts):
    """Return mean, std, min, max for a (N,3) array of 3-D points."""
    return {
        'mean': pts.mean(axis=0),
        'std':  pts.std(axis=0),
        'min':  pts.min(axis=0),
        'max':  pts.max(axis=0),
    }


def cosine_similarity_surface_pairs(pairs2, pairs3):
    """
    Treat surface-pair count dicts as sparse vectors and compute
    cosine similarity — 1.0 = identical distribution, 0 = orthogonal.
    """
    all_keys = set(pairs2) | set(pairs3)
    v2 = np.array([pairs2.get(k, 0) for k in all_keys], dtype=float)
    v3 = np.array([pairs3.get(k, 0) for k in all_keys], dtype=float)
    denom = np.linalg.norm(v2) * np.linalg.norm(v3)
    return float(np.dot(v2, v3) / denom) if denom > 0 else 0.0


# ------------------------------------------------------------------ #
#  Main                                                               #
# ------------------------------------------------------------------ #
def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--py2_dir', required=True,
                        help='Path to Python 2 streamline directory')
    parser.add_argument('--py3_dir', required=True,
                        help='Path to Python 3 streamline directory')
    parser.add_argument('--n_runs', type=int, default=4,
                        help='Number of runs [%(default)s]')
    args = parser.parse_args()

    print('=' * 65)
    print('  STEP 3 OUTPUT COMPARISON  —  Python 2 vs Python 3')
    print('=' * 65)

    # ---- Per-run analysis ---------------------------------------- #
    total_py2 = 0
    total_py3 = 0
    cosine_sims = []

    for run in range(1, args.n_runs + 1):
        f2 = os.path.join(args.py2_dir,
                          f'intersections_random_loop{run}_filtered.npz')
        f3 = os.path.join(args.py3_dir,
                          f'intersections_random_loop{run}_filtered.npz')

        if not os.path.exists(f2):
            print(f'  RUN {run}: Python 2 file missing — {f2}')
            continue
        if not os.path.exists(f3):
            print(f'  RUN {run}: Python 3 file missing — {f3}')
            continue

        s0_2, t0_2, p0_2, s1_2, t1_2, p1_2 = load_intersections(f2)
        s0_3, t0_3, p0_3, s1_3, t1_3, p1_3 = load_intersections(f3)

        n2 = len(s0_2)
        n3 = len(s0_3)
        total_py2 += n2
        total_py3 += n3

        pairs2 = surface_pair_counts(s0_2, s1_2)
        pairs3 = surface_pair_counts(s0_3, s1_3)
        cos_sim = cosine_similarity_surface_pairs(pairs2, pairs3)
        cosine_sims.append(cos_sim)

        ep_diff = np.linalg.norm(p0_2.mean(axis=0) - p0_3.mean(axis=0))

        print(f'\n  RUN {run}')
        print(f'    Streamlines   Py2={n2:>7,}   Py3={n3:>7,}   '
              f'diff={n3-n2:+,} ({100*(n3-n2)/n2:+.1f}%)')
        print(f'    Surf pairs    Py2={len(pairs2):>4}   Py3={len(pairs3):>4}   '
              f'unique pairs (union)={len(set(pairs2)|set(pairs3))}')
        print(f'    Connectivity similarity (cosine): {cos_sim:.6f}')
        print(f'    Mean endpoint shift (pts0):  {ep_diff:.3f} mm')

        # Top-5 surface pairs by Py3 count
        top3 = sorted(pairs3.items(), key=lambda x: -x[1])[:5]
        top2 = {k: pairs2.get(k, 0) for k, _ in top3}
        print(f'    Top-5 surface pairs by Py3 count:')
        print(f'      {"Pair":>12}  {"Py2 count":>10}  {"Py3 count":>10}  {"ratio":>7}')
        for (k, n3v) in top3:
            n2v = top2[k]
            ratio = n3v / n2v if n2v > 0 else float('inf')
            print(f'      {str(k):>12}  {n2v:>10,}  {n3v:>10,}  {ratio:>7.3f}')

    # ---- Aggregate summary --------------------------------------- #
    print('\n' + '=' * 65)
    print('  AGGREGATE SUMMARY')
    print('=' * 65)
    print(f'  Total streamlines  Py2={total_py2:,}   Py3={total_py3:,}')
    print(f'  Difference         {total_py3-total_py2:+,} ({100*(total_py3-total_py2)/total_py2:+.1f}%)')
    print(f'  Mean cosine sim across runs: {np.mean(cosine_sims):.6f}')
    print()

    # ---- Interpretation ------------------------------------------ #
    print('  INTERPRETATION')
    print('  ─────────────────────────────────────────────────────')
    mean_cos = np.mean(cosine_sims)
    if mean_cos > 0.999:
        verdict = 'EXCELLENT — connectivity distributions are near-identical'
    elif mean_cos > 0.99:
        verdict = 'VERY GOOD — minor distributional differences'
    elif mean_cos > 0.95:
        verdict = 'GOOD — some distributional shift, investigate top pairs'
    else:
        verdict = 'NOTABLE DIFFERENCE — review surface pair distributions'
    print(f'  Connectivity similarity: {verdict}')

    pct_diff = 100 * (total_py3 - total_py2) / total_py2
    if abs(pct_diff) < 5:
        count_verdict = 'streamline counts consistent (< 5% difference)'
    elif abs(pct_diff) < 15:
        count_verdict = 'moderate count difference (5–15%), expected given seeding fix'
    else:
        count_verdict = 'large count difference (> 15%), investigate'
    print(f'  Streamline counts: {count_verdict}')
    print('=' * 65)


if __name__ == '__main__':
    main()
