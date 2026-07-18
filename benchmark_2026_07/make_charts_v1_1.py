#!/usr/bin/env python3
"""Generate the README benchmark charts from results_v1_1.csv.

Every plotted value is read from the CSV; nothing is hand-entered.
Output: ../assets/fertility_v1_1.svg and ../assets/byte_fallback_v1_1.svg.

Requires matplotlib (not a package dependency): pip install matplotlib
"""
import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "results_v1_1.csv")
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

AKSHARA_COLOR = "#D97706"  # saffron family, validated for light surfaces
QWEN_COLOR = "#2a78d6"
INK = "#24292f"
INK_MUTED = "#57606a"
GRID = "#d8d8d8"

# CSV script name -> (fertility chart label, byte-fallback chart label)
SCRIPTS = {
    "devanagari": ("Devanagari\n(Hindi)", "Hindi"),
    "gurmukhi": ("Gurmukhi\n(Punjabi)", "Punjabi"),
    "tamil": ("Tamil", "Tamil"),
    "telugu": ("Telugu", "Telugu"),
    "bengali": ("Bengali", "Bengali"),
    "kannada": ("Kannada", "Kannada"),
    "english": ("English", None),  # info row in the fertility table only
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "svg.fonttype": "none",
    "svg.hashsalt": "akshara-v1.1",
    "text.color": INK,
    "axes.edgecolor": INK_MUTED,
    "axes.labelcolor": INK,
    "xtick.color": INK,
    "ytick.color": INK_MUTED,
})


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def by_tokenizer(rows, tokenizer, field):
    out = {}
    for r in rows:
        if r["tokenizer"] == tokenizer and r["script"] in SCRIPTS:
            out[r["script"]] = float(r[field])
    return out


def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)


def fertility_chart(rows):
    scripts = list(SCRIPTS)
    akshara = by_tokenizer(rows, "akshara_v1_1_16k", "fertility_tok_per_word")
    qwen = by_tokenizer(rows, "qwen3_14b", "fertility_tok_per_word")
    xs = range(len(scripts))
    fig, ax = plt.subplots(figsize=(8.6, 4.2), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar([x - 0.19 for x in xs], [akshara[s] for s in scripts], width=0.36,
           color=AKSHARA_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="AksharaTokenizer v1.1 (16k)")
    ax.bar([x + 0.19 for x in xs], [qwen[s] for s in scripts], width=0.36,
           color=QWEN_COLOR, edgecolor="white", linewidth=1, zorder=3,
           label="Qwen3-14B")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SCRIPTS[s][0] for s in scripts], fontsize=9.5)
    ax.set_ylabel("tokens per word (lower is better)", fontsize=10)
    ax.set_title("Fertility on FLORES-200 devtest", fontsize=13,
                 fontweight="bold", loc="left", pad=12)
    ax.legend(frameon=False, fontsize=9.5, loc="upper left")
    style_axes(ax)
    fig.tight_layout()
    out = os.path.join(ASSETS, "fertility_v1_1.svg")
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)
    return out


def byte_fallback_chart(rows):
    scripts = [s for s in SCRIPTS if SCRIPTS[s][1]]
    akshara = by_tokenizer(rows, "akshara_v1_1_16k", "unk_bytefallback_pct")
    xs = range(len(scripts))
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=100)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.bar(list(xs), [akshara[s] for s in scripts], width=0.55,
           color=AKSHARA_COLOR, edgecolor="white", linewidth=1, zorder=3)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([SCRIPTS[s][1] for s in scripts], fontsize=10)
    ax.set_ylabel("byte-fallback %  (lower is better)", fontsize=10)
    ax.set_title("Byte-fallback rate, v1.1 (16k)", fontsize=13,
                 fontweight="bold", loc="left", pad=12)
    style_axes(ax)
    fig.tight_layout()
    out = os.path.join(ASSETS, "byte_fallback_v1_1.svg")
    fig.savefig(out, metadata={"Date": None})
    plt.close(fig)
    return out


def main():
    os.makedirs(ASSETS, exist_ok=True)
    rows = load_rows()
    for path in (fertility_chart(rows), byte_fallback_chart(rows)):
        print("wrote", path)


if __name__ == "__main__":
    main()
