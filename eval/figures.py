"""
figures.py — generates the figures for the Results section from the CSVs
analyze.py produced.

    pip install matplotlib numpy
    python figures.py --run 20260815-143022

Writes vector PDFs to figures/<run>/. PDF rather than PNG because IEEE
templates typeset with pdflatex and a raster figure at column width is the
single most common reason a submission looks amateur in print.

Figures produced
  fig_style_heatmap.pdf   participants x features similarity      (heatmap)
  fig_cross_matrix.pdf    twin x source discriminability          (heatmap)
  fig_feature_bars.pdf    person vs twin, mean across participants (grouped bars)
  fig_latency.pdf         per-turn latency distribution           (box plot)
  fig_consistency.pdf     cross-session consistency per twin      (bar + mean line)
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import style_metrics as sm  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"
FIGURES_DIR = Path(__file__).resolve().parent / "figures"

# IEEE two-column: a single-column figure is 3.5in wide, double-column is 7.16in.
# Sizing the figure correctly here — rather than scaling it in LaTeX — is what
# keeps tick labels legible at print size.
COL_W = 3.5
DOUBLE_W = 7.16

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.size": 8,
        "axes.labelsize": 8,
        "axes.titlesize": 9,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "legend.fontsize": 7,
        "figure.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    }
)


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.is_file():
        print(f"  [skip] {path.name} not found")
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def heatmap(ax, data: np.ndarray, row_labels: List[str], col_labels: List[str], cmap: str, vmin=0.0, vmax=1.0):
    im = ax.imshow(data, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(row_labels)))
    ax.set_yticklabels(row_labels)
    # Annotate only when the grid is small enough that numbers stay readable;
    # past roughly 200 cells the text becomes noise and the colour does the work.
    if data.size <= 200:
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                val = data[i, j]
                ax.text(
                    j, i, f"{val:.2f}",
                    ha="center", va="center", fontsize=5.5,
                    color="white" if val < (vmin + vmax) / 2 else "black",
                )
    return im


def fig_style_heatmap(rows: List[Dict[str, str]], out: Path) -> None:
    if not rows:
        return
    labels = [r["label"] for r in rows]
    data = np.array([[float(r[n]) for n in sm.FEATURE_NAMES] for r in rows])
    col_labels = [sm.FEATURE_LABELS[n] for n in sm.FEATURE_NAMES]

    height = max(2.0, 0.28 * len(labels) + 1.6)
    fig, ax = plt.subplots(figsize=(DOUBLE_W, height))
    im = heatmap(ax, data, labels, col_labels, cmap="YlGnBu")
    ax.set_xlabel("Communication feature")
    ax.set_ylabel("Participant")
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.015)
    cbar.set_label("Per-feature similarity", fontsize=7)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def fig_cross_matrix(rows: List[Dict[str, str]], out: Path) -> None:
    if not rows:
        return
    labels = [r[list(r.keys())[0]] for r in rows]
    data = np.array([[float(r[c]) for c in labels] for r in rows])

    size = max(2.6, 0.32 * len(labels) + 1.5)
    fig, ax = plt.subplots(figsize=(min(size, DOUBLE_W), min(size, 6.0)))
    im = heatmap(ax, data, labels, labels, cmap="magma", vmin=data.min(), vmax=data.max())
    ax.set_xlabel("Source participant")
    ax.set_ylabel("Twin")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cbar.set_label("Style similarity", fontsize=7)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def fig_feature_bars(rows: List[Dict[str, str]], out: Path) -> None:
    if not rows:
        return
    by_feature: Dict[str, Dict[str, List[float]]] = {}
    for r in rows:
        d = by_feature.setdefault(r["feature"], {"source": [], "twin": []})
        d["source"].append(float(r["source"]))
        d["twin"].append(float(r["twin"]))

    names = [n for n in sm.FEATURE_NAMES if n in by_feature]
    src = np.array([np.mean(by_feature[n]["source"]) for n in names])
    twn = np.array([np.mean(by_feature[n]["twin"]) for n in names])

    # Features span three orders of magnitude (response length ~117 vs lexical
    # diversity ~0.36). Plotted raw, everything but response length flattens to
    # zero. Scaling each feature by its own max keeps all twelve comparable and
    # makes the person-vs-twin gap the thing the eye actually reads.
    scale = np.maximum(np.maximum(src, twn), 1e-9)
    src_n, twn_n = src / scale, twn / scale

    x = np.arange(len(names))
    width = 0.38
    fig, ax = plt.subplots(figsize=(DOUBLE_W, 2.5))
    ax.bar(x - width / 2, src_n, width, label="Source person", color="#2c6fbb")
    ax.bar(x + width / 2, twn_n, width, label="Twin output", color="#e08a2e")
    ax.set_xticks(x)
    ax.set_xticklabels([sm.FEATURE_LABELS[n] for n in names], rotation=35, ha="right")
    ax.set_ylabel("Normalised value")
    ax.set_ylim(0, 1.15)
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def fig_latency(rows: List[Dict[str, str]], out: Path) -> None:
    if not rows:
        return
    labels = [r["label"] for r in rows]
    means = [float(r["mean_s"]) for r in rows]
    medians = [float(r["median_s"]) for r in rows]
    p95s = [float(r["p95_s"]) for r in rows]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(COL_W, 2.3))
    ax.bar(x, medians, 0.6, label="median", color="#3d8b5f")
    ax.plot(x, means, "o", ms=3, color="#1b3a2b", label="mean")
    ax.plot(x, p95s, "^", ms=3, color="#b03a2e", label="p95")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Response latency (s)")
    ax.legend(frameon=False, ncol=3, fontsize=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def fig_consistency(rows: List[Dict[str, str]], out: Path) -> None:
    if not rows:
        return
    labels = [r["label"] for r in rows]
    means = [float(r["mean_pairwise"]) for r in rows]
    lows = [float(r["mean_pairwise"]) - float(r["min"]) for r in rows]
    highs = [float(r["max"]) - float(r["mean_pairwise"]) for r in rows]

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(COL_W, 2.3))
    ax.bar(x, means, 0.6, yerr=[lows, highs], capsize=2, color="#7a5fa8", ecolor="#3a2b52", error_kw={"lw": 0.7})
    ax.axhline(float(np.mean(means)), ls="--", lw=0.8, color="#b03a2e",
               label=f"mean = {np.mean(means):.3f}")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Cross-session consistency")
    ax.set_ylim(0, 1.0)
    ax.legend(frameon=False, fontsize=6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.4)
    ax.set_axisbelow(True)
    fig.savefig(out)
    plt.close(fig)
    print(f"  wrote {out.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate paper figures from analysed results.")
    parser.add_argument("--run", required=True)
    args = parser.parse_args()

    res = RESULTS_DIR / args.run
    if not res.is_dir():
        raise SystemExit(f"No results for run {args.run}. Run analyze.py first.")

    out = FIGURES_DIR / args.run
    out.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating figures -> {out}\n")

    fig_style_heatmap(read_csv(res / "style_similarity.csv"), out / "fig_style_heatmap.pdf")
    fig_cross_matrix(read_csv(res / "cross_matrix.csv"), out / "fig_cross_matrix.pdf")
    fig_feature_bars(read_csv(res / "feature_values.csv"), out / "fig_feature_bars.pdf")
    fig_latency(read_csv(res / "latency.csv"), out / "fig_latency.pdf")
    fig_consistency(read_csv(res / "consistency.csv"), out / "fig_consistency.pdf")

    print(f"\nCopy these into your LaTeX project's figures/ folder.\n")


if __name__ == "__main__":
    main()
