from __future__ import annotations

import csv
import html
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path("/Users/asus/ultralytics")
ASSET_DIR = ROOT / "docs" / "paper_assets"
DATASET_LABELS = ROOT / "datasets" / "dair_v2x_i" / "labels"

CLASS_NAMES = [
    "Car",
    "Truck",
    "Van",
    "Bus",
    "Cyclist",
    "Motorcyclist",
    "Pedestrian",
    "Trafficcone",
]

COLORS = {
    "baseline": "#0077BB",
    "proposed": "#EE7733",
    "gain": "#009988",
    "neutral": "#6B7280",
    "grid": "#E5E7EB",
    "text": "#111827",
}


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text).replace("\r", "\n")


def parse_final_class_metrics(log_path: Path) -> pd.DataFrame:
    text = strip_ansi(log_path.read_text(errors="ignore"))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    traffic_idxs = [i for i, line in enumerate(lines) if re.match(r"^Trafficcone\s+", line)]
    if not traffic_idxs:
        raise RuntimeError(f"Could not find final per-class block in {log_path}")

    start = traffic_idxs[-1] - 8
    rows = []
    for line in lines[start : traffic_idxs[-1] + 1]:
        parts = line.split()
        if len(parts) < 7:
            continue
        cls = parts[0]
        if cls not in {"all", *CLASS_NAMES}:
            continue
        rows.append(
            {
                "class": cls,
                "images": int(float(parts[1])),
                "instances": int(float(parts[2])),
                "precision": float(parts[3]),
                "recall": float(parts[4]),
                "mAP50": float(parts[5]),
                "mAP50_95": float(parts[6]),
            }
        )
    return pd.DataFrame(rows)


def collect_class_metrics() -> pd.DataFrame:
    baseline = parse_final_class_metrics(ROOT / "runs" / "baseline-b32_train.log")
    proposed = parse_final_class_metrics(ROOT / "runs" / "DWCA-P2-b32_train.log")
    merged = baseline.merge(proposed, on=["class", "images", "instances"], suffixes=("_baseline", "_proposed"))
    for metric in ["precision", "recall", "mAP50", "mAP50_95"]:
        merged[f"{metric}_gain"] = merged[f"{metric}_proposed"] - merged[f"{metric}_baseline"]
    return merged


def collect_val_scale_stats() -> pd.DataFrame:
    rows = []
    for path in sorted((DATASET_LABELS / "val").glob("*.txt")):
        text = path.read_text(errors="ignore").strip()
        if not text:
            continue
        for line in text.splitlines():
            parts = line.split()
            if len(parts) < 5:
                continue
            cls = int(float(parts[0]))
            w = float(parts[3]) * 640
            h = float(parts[4]) * 640
            short = min(w, h)
            area = w * h
            if short < 16:
                scale = "short<16"
            elif short < 32:
                scale = "16<=short<32"
            else:
                scale = "short>=32"
            rows.append(
                {
                    "class": CLASS_NAMES[cls],
                    "width_px": w,
                    "height_px": h,
                    "short_side_px": short,
                    "area_px2": area,
                    "scale_bin": scale,
                }
            )
    df = pd.DataFrame(rows)
    summary = (
        df.groupby(["class", "scale_bin"], observed=False)
        .size()
        .unstack(fill_value=0)
        .reindex(CLASS_NAMES)
        .reset_index()
    )
    for col in ["short<16", "16<=short<32", "short>=32"]:
        if col not in summary.columns:
            summary[col] = 0
    summary["total"] = summary[["short<16", "16<=short<32", "short>=32"]].sum(axis=1)
    summary["short<32"] = summary["short<16"] + summary["16<=short<32"]
    summary["short<32_pct"] = summary["short<32"] / summary["total"] * 100
    median = df.groupby("class", observed=False)["short_side_px"].median().reindex(CLASS_NAMES).reset_index()
    median.columns = ["class", "median_short_side_px"]
    return summary.merge(median, on="class")


def collect_training_curves() -> pd.DataFrame:
    rows = []
    for model, path in {
        "baseline-b32": ROOT / "runs" / "detect" / "runs" / "ablation" / "baseline-b32" / "results.csv",
        "DWCA-P2-b32": ROOT / "runs" / "detect" / "runs" / "ablation" / "DWCA-P2-b32" / "results.csv",
    }.items():
        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        for _, row in df.iterrows():
            rows.append(
                {
                    "model": model,
                    "epoch": int(row["epoch"]),
                    "precision": float(row["metrics/precision(B)"]),
                    "recall": float(row["metrics/recall(B)"]),
                    "mAP50": float(row["metrics/mAP50(B)"]),
                    "mAP50_95": float(row["metrics/mAP50-95(B)"]),
                    "train_box_loss": float(row["train/box_loss"]),
                    "val_box_loss": float(row["val/box_loss"]),
                }
            )
    return pd.DataFrame(rows)


def write_csv(path: Path, rows: list[dict] | pd.DataFrame) -> None:
    if isinstance(rows, pd.DataFrame):
        rows.to_csv(path, index=False, float_format="%.6g")
        return
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        "<style>",
        ".title{font:700 22px Arial,Helvetica,sans-serif;fill:#111827}",
        ".label{font:13px Arial,Helvetica,sans-serif;fill:#111827}",
        ".tick{font:12px Arial,Helvetica,sans-serif;fill:#374151}",
        ".note{font:12px Arial,Helvetica,sans-serif;fill:#4B5563}",
        ".grid{stroke:#E5E7EB;stroke-width:1}",
        ".axis{stroke:#111827;stroke-width:1.5}",
        "</style>",
        "</defs>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
    ]


def esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def bar_chart_grouped(path: Path, data: pd.DataFrame, metrics: list[str], labels: list[str], title: str) -> None:
    width, height = 980, 540
    margin = dict(left=86, right=36, top=72, bottom=92)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    maxv = max(float(data[f"{m}_proposed"].max()) for m in metrics) * 100
    maxv = math.ceil(maxv / 10) * 10
    lines = svg_header(width, height)
    lines.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">{esc(title)}</text>')
    for yv in range(0, int(maxv) + 1, 10):
        y = margin["top"] + plot_h - (yv / maxv) * plot_h
        lines.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width-margin["right"]}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{margin["left"]-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{yv}</text>')
    lines.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"]+plot_h}" class="axis"/>')
    lines.append(f'<line x1="{margin["left"]}" y1="{margin["top"]+plot_h}" x2="{width-margin["right"]}" y2="{margin["top"]+plot_h}" class="axis"/>')
    group_w = plot_w / len(metrics)
    bar_w = 42
    for i, (metric, label) in enumerate(zip(metrics, labels)):
        cx = margin["left"] + group_w * (i + 0.5)
        vals = [
            ("baseline-b32", float(data[f"{metric}_baseline"].iloc[0]) * 100, COLORS["baseline"]),
            ("DWCA-P2-b32", float(data[f"{metric}_proposed"].iloc[0]) * 100, COLORS["proposed"]),
        ]
        for j, (name, val, color) in enumerate(vals):
            x = cx + (j - 0.5) * (bar_w + 12) - bar_w / 2
            h = (val / maxv) * plot_h
            y = margin["top"] + plot_h - h
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{h:.1f}" fill="{color}" rx="4"/>')
            lines.append(f'<text x="{x+bar_w/2:.1f}" y="{y-7:.1f}" text-anchor="middle" class="tick">{val:.1f}</text>')
        lines.append(f'<text x="{cx:.1f}" y="{margin["top"]+plot_h+30}" text-anchor="middle" class="label">{esc(label)}</text>')
    lines.append(f'<rect x="{width-260}" y="74" width="14" height="14" fill="{COLORS["baseline"]}"/><text x="{width-238}" y="86" class="tick">baseline-b32</text>')
    lines.append(f'<rect x="{width-260}" y="98" width="14" height="14" fill="{COLORS["proposed"]}"/><text x="{width-238}" y="110" class="tick">DWCA-P2-b32</text>')
    lines.append('<text x="26" y="290" transform="rotate(-90 26 290)" text-anchor="middle" class="label">Metric value (%)</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def horizontal_gain_chart(path: Path, df: pd.DataFrame, title: str) -> None:
    data = df[df["class"] != "all"].copy()
    data["gain_pct"] = data["mAP50_95_gain"] * 100
    width, height = 980, 560
    margin = dict(left=160, right=64, top=70, bottom=58)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    minv = math.floor(min(0, data["gain_pct"].min()) / 2) * 2
    maxv = math.ceil(max(0, data["gain_pct"].max()) / 2) * 2
    if maxv == minv:
        maxv = minv + 1
    def xscale(v: float) -> float:
        return margin["left"] + (v - minv) / (maxv - minv) * plot_w
    lines = svg_header(width, height)
    lines.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">{esc(title)}</text>')
    for xv in np.linspace(minv, maxv, int(maxv - minv) + 1):
        x = xscale(float(xv))
        lines.append(f'<line x1="{x:.1f}" y1="{margin["top"]}" x2="{x:.1f}" y2="{margin["top"]+plot_h}" class="grid"/>')
        lines.append(f'<text x="{x:.1f}" y="{height-28}" text-anchor="middle" class="tick">{xv:.0f}</text>')
    x0 = xscale(0)
    lines.append(f'<line x1="{x0:.1f}" y1="{margin["top"]}" x2="{x0:.1f}" y2="{margin["top"]+plot_h}" class="axis"/>')
    row_h = plot_h / len(data)
    for i, (_, row) in enumerate(data.iterrows()):
        y = margin["top"] + row_h * (i + 0.5)
        val = float(row["gain_pct"])
        x = xscale(val)
        x_left = min(x, x0)
        w = abs(x - x0)
        color = COLORS["gain"] if val >= 0 else "#CC3311"
        lines.append(f'<text x="{margin["left"]-12}" y="{y+5:.1f}" text-anchor="end" class="label">{esc(row["class"])}</text>')
        lines.append(f'<rect x="{x_left:.1f}" y="{y-12:.1f}" width="{w:.1f}" height="24" fill="{color}" rx="4"/>')
        tx = x + (8 if val >= 0 else -8)
        anchor = "start" if val >= 0 else "end"
        lines.append(f'<text x="{tx:.1f}" y="{y+5:.1f}" text-anchor="{anchor}" class="tick">{val:+.1f}</text>')
    lines.append(f'<text x="{margin["left"]+plot_w/2}" y="{height-8}" text-anchor="middle" class="label">mAP@0.5:0.95 gain (percentage points)</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def line_chart(path: Path, curves: pd.DataFrame, metric: str, title: str, ylabel: str) -> None:
    width, height = 980, 540
    margin = dict(left=78, right=36, top=72, bottom=68)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    yvals = curves[metric] * 100
    minv = max(0, math.floor(yvals.min() / 10) * 10)
    maxv = min(100, math.ceil(yvals.max() / 5) * 5)
    if maxv <= minv:
        maxv = minv + 10
    max_epoch = curves["epoch"].max()
    def xscale(v):
        return margin["left"] + v / max_epoch * plot_w
    def yscale(v):
        return margin["top"] + plot_h - (v - minv) / (maxv - minv) * plot_h
    lines = svg_header(width, height)
    lines.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">{esc(title)}</text>')
    for yv in range(int(minv), int(maxv) + 1, 5):
        y = yscale(yv)
        lines.append(f'<line x1="{margin["left"]}" y1="{y:.1f}" x2="{width-margin["right"]}" y2="{y:.1f}" class="grid"/>')
        lines.append(f'<text x="{margin["left"]-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{yv}</text>')
    for xv in range(0, int(max_epoch) + 1, 50):
        x = xscale(xv)
        lines.append(f'<line x1="{x:.1f}" y1="{margin["top"]}" x2="{x:.1f}" y2="{margin["top"]+plot_h}" class="grid"/>')
        lines.append(f'<text x="{x:.1f}" y="{height-35}" text-anchor="middle" class="tick">{xv}</text>')
    lines.append(f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{margin["top"]+plot_h}" class="axis"/>')
    lines.append(f'<line x1="{margin["left"]}" y1="{margin["top"]+plot_h}" x2="{width-margin["right"]}" y2="{margin["top"]+plot_h}" class="axis"/>')
    for model, color in [("baseline-b32", COLORS["baseline"]), ("DWCA-P2-b32", COLORS["proposed"])]:
        sub = curves[curves["model"] == model].sort_values("epoch")
        points = " ".join(f'{xscale(r.epoch):.1f},{yscale(r[metric]*100):.1f}' for _, r in sub.iterrows())
        lines.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.6"/>')
    lines.append(f'<rect x="{width-260}" y="74" width="14" height="14" fill="{COLORS["baseline"]}"/><text x="{width-238}" y="86" class="tick">baseline-b32</text>')
    lines.append(f'<rect x="{width-260}" y="98" width="14" height="14" fill="{COLORS["proposed"]}"/><text x="{width-238}" y="110" class="tick">DWCA-P2-b32</text>')
    lines.append(f'<text x="{width/2}" y="{height-8}" text-anchor="middle" class="label">Epoch</text>')
    lines.append(f'<text x="24" y="{height/2}" transform="rotate(-90 24 {height/2})" text-anchor="middle" class="label">{esc(ylabel)}</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def stacked_scale_chart(path: Path, stats: pd.DataFrame) -> None:
    width, height = 1080, 560
    margin = dict(left=150, right=42, top=72, bottom=88)
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    lines = svg_header(width, height)
    lines.append(f'<text x="{width/2}" y="38" text-anchor="middle" class="title">Validation set object scale distribution at 640 input</text>')
    for xv in range(0, 101, 20):
        x = margin["left"] + xv / 100 * plot_w
        lines.append(f'<line x1="{x:.1f}" y1="{margin["top"]}" x2="{x:.1f}" y2="{margin["top"]+plot_h}" class="grid"/>')
        lines.append(f'<text x="{x:.1f}" y="{height-42}" text-anchor="middle" class="tick">{xv}</text>')
    row_h = plot_h / len(stats)
    seg_colors = [("#0077BB", "short<16"), ("#33BBEE", "16<=short<32"), ("#BBBBBB", "short>=32")]
    for i, (_, row) in enumerate(stats.iterrows()):
        y = margin["top"] + row_h * i + row_h * 0.22
        bar_h = row_h * 0.56
        x = margin["left"]
        total = float(row["total"])
        lines.append(f'<text x="{margin["left"]-12}" y="{y+bar_h/2+5:.1f}" text-anchor="end" class="label">{esc(row["class"])}</text>')
        for color, col in seg_colors:
            val = float(row[col])
            w = val / total * plot_w if total else 0
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bar_h:.1f}" fill="{color}"/>')
            x += w
        pct = float(row["short<32_pct"])
        lines.append(f'<text x="{width-margin["right"]-4}" y="{y+bar_h/2+5:.1f}" text-anchor="end" class="tick">short&lt;32: {pct:.1f}%</text>')
    lx = margin["left"]
    for color, label in seg_colors:
        lines.append(f'<rect x="{lx}" y="{height-28}" width="14" height="14" fill="{color}"/>')
        lines.append(f'<text x="{lx+20}" y="{height-16}" class="tick">{esc(label)}</text>')
        lx += 168
    lines.append(f'<text x="{margin["left"]+plot_w/2}" y="{height-8}" text-anchor="middle" class="label">Instance proportion (%)</text>')
    lines.append("</svg>")
    path.write_text("\n".join(lines), encoding="utf-8")


def build() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    class_metrics = collect_class_metrics()
    scale_stats = collect_val_scale_stats()
    curves = collect_training_curves()
    main_metrics = pd.DataFrame(
        [
            {
                "class": "all",
                "precision_baseline": 0.857,
                "recall_baseline": 0.808,
                "mAP50_baseline": 0.860,
                "mAP50_95_baseline": 0.602,
                "precision_proposed": 0.860,
                "recall_proposed": 0.835,
                "mAP50_proposed": 0.884,
                "mAP50_95_proposed": 0.644,
            }
        ]
    )
    for metric in ["precision", "recall", "mAP50", "mAP50_95"]:
        main_metrics[f"{metric}_gain"] = main_metrics[f"{metric}_proposed"] - main_metrics[f"{metric}_baseline"]

    write_csv(ASSET_DIR / "class_metrics_baseline_vs_dwca_p2_b32.csv", class_metrics)
    write_csv(ASSET_DIR / "main_metrics_table5_baseline_vs_dwca_p2_b32.csv", main_metrics)
    write_csv(ASSET_DIR / "val_scale_distribution_640.csv", scale_stats)
    write_csv(ASSET_DIR / "training_curves_baseline_vs_dwca_p2_b32.csv", curves)

    bar_chart_grouped(
        ASSET_DIR / "main_metrics_comparison.svg",
        main_metrics,
        ["precision", "recall", "mAP50", "mAP50_95"],
        ["P", "R", "mAP@0.5", "mAP@0.5:0.95"],
        "Main detection metrics on DAIR-V2X-I validation set",
    )
    horizontal_gain_chart(
        ASSET_DIR / "class_map50_95_gain.svg",
        class_metrics,
        "Per-class mAP@0.5:0.95 gain of DWCA-P2-b32 over baseline-b32",
    )
    line_chart(
        ASSET_DIR / "training_map50_95_curve.svg",
        curves,
        "mAP50_95",
        "Validation mAP@0.5:0.95 curves",
        "mAP@0.5:0.95 (%)",
    )
    line_chart(
        ASSET_DIR / "training_recall_curve.svg",
        curves,
        "recall",
        "Validation recall curves",
        "Recall (%)",
    )
    stacked_scale_chart(ASSET_DIR / "val_scale_distribution_640.svg", scale_stats)


if __name__ == "__main__":
    build()
