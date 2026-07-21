#!/usr/bin/env python3
"""Generate the README v1.2 benchmark charts from the shipped v1.2 CSVs.

Every plotted value is read from a CSV; nothing is hand-entered.
Reads results_v1_2_fertility.csv and results_v1_2_split.csv.
Output: ../assets/fertility_v1_2.svg and ../assets/split_rate_v1_2.svg.

Requires matplotlib (not a package dependency): pip install matplotlib
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
FERT_CSV = os.path.join(HERE, "results_v1_2_fertility.csv")
SPLIT_CSV = os.path.join(HERE, "results_v1_2_split.csv")
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

V12_COLOR = "#D97706"   # saffron family, validated for light surfaces
V11_COLOR = "#8896A6"   # slate gray: the superseded model
QWEN_COLOR = "#2a78d6"
INK = "#24292f"
INK_MUTED = "#57606a"
GRID = "#d8d8d8"

SCRIPTS = {
    "devanagari": "Devanagari\n(Hindi)",
    "gurmukhi": "Gurmukhi\n(Punjabi)",
    "tamil": "Tamil",
    "telugu": "Telugu",
    "bengali": "Bengali",
    "kannada": "Kannada",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "svg.fonttype": "none",
    "svg.hashsalt": "akshara-v1.2",
    "text.color": INK,
    "axes.edgecolor": INK_MUTED,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK_MUTED,
})


def load(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def pick(rows, key_field, key, val_field):
    return {r["script"]: float(r[val_field]) for r in rows
            if r[key_field] == key and r["script"] in SCRIPTS}


def style_axes(ax):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def fertility_chart():
    rows = load(FERT_CSV)
    v12 = pick(rows, "tokenizer", "akshara_v1_2_64k", "fertility_tok_per_word")
    v11 = pick(rows, "tokenizer", "akshara_v1_1_16k", "fertility_tok_per_word")
    qwen = pick(rows, "tokenizer", "qwen3_14b", "fertility_tok_per_word")
    scripts = list(SCRIPTS)
    xs = range(len(scripts))
    fig, ax = plt.subplots(figsize=(9.0, 4.4), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar([x - 0.26 for x in xs], [v12[s] for s in scripts], width=0.25,
           color=V12_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="AksharaTokenizer v1.2 (64k)")
    ax.bar([x for x in xs], [v11[s] for s in scripts], width=0.25,
           color=V11_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="AksharaTokenizer v1.1 (16k)")
    ax.bar([x + 0.26 for x in xs], [qwen[s] for s in scripts], width=0.25,
           color=QWEN_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="Qwen3-14B")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SCRIPTS[s] for s in scripts], fontsize=9.5)
    ax.set_ylabel("tokens per word (lower is better)", fontsize=10)
    ax.set_title("Fertility on FLORES-200 devtest", fontsize=13,
                 fontweight="bold", loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    out = os.path.join(ASSETS, "fertility_v1_2.svg")
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)
    return out


def split_chart():
    rows = load(SPLIT_CSV)
    v12 = pick(rows, "model", "v1.2", "split_pct")
    v11 = pick(rows, "model", "v1.1", "split_pct")
    scripts = list(SCRIPTS)
    xs = range(len(scripts))
    fig, ax = plt.subplots(figsize=(8.6, 4.0), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar([x - 0.19 for x in xs], [v12[s] for s in scripts], width=0.36,
           color=V12_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="AksharaTokenizer v1.2 (64k)")
    ax.bar([x + 0.19 for x in xs], [v11[s] for s in scripts], width=0.36,
           color=V11_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="AksharaTokenizer v1.1 (16k)")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SCRIPTS[s] for s in scripts], fontsize=9.5)
    ax.set_ylabel("aksharas split %  (lower is better)", fontsize=10)
    ax.set_title("Akshara split rate on FLORES-200 devtest", fontsize=13,
                 fontweight="bold", loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9.5, loc="upper right")
    style_axes(ax)
    fig.tight_layout()
    out = os.path.join(ASSETS, "split_rate_v1_2.svg")
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)
    return out


def main():
    os.makedirs(ASSETS, exist_ok=True)
    for path in (fertility_chart(), split_chart()):
        print("wrote", path)


if __name__ == "__main__":
    main()
