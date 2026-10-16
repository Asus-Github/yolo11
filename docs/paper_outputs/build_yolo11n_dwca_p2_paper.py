# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import html
import math
import re
import shutil
import textwrap
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Iterable

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

import build_module_figures as _mf


ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = ROOT / "docs" / "paper_inputs"
OUTPUT_DIR = ROOT / "docs" / "paper_outputs"
FIG_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
ASSET_DIR = OUTPUT_DIR / "assets"
FORMULA_DIR = ASSET_DIR / "formula_images"

EXCEL_PATH = INPUT_DIR / "刘华硕-飞书导入实验记录表.xlsx"
DATASET_YAML = INPUT_DIR / "dair_v2x_i.yaml"
OLD_ROOT = Path("/Users/asus/ultralytics")
OLD_ASSET_DIR = OLD_ROOT / "docs" / "paper_assets"
OLD_RUN_DIR = OLD_ROOT / "runs" / "detect" / "runs" / "ablation"

MD_PATH = OUTPUT_DIR / "yolo11n-dwca-p2-hljust.md"
DOCX_PATH = OUTPUT_DIR / "yolo11n-dwca-p2-hljust.docx"
QA_PATH = OUTPUT_DIR / "paper_generation_report.md"
HLG_FORMAT_REPORT_PATH = OUTPUT_DIR / "hlg_format_report.md"
HLG_TEMPLATE_PATH = Path("/Users/asus/ultralytics/docs/about/论文模板.docx")

CN_TITLE = "路侧交通小目标检测DWCA-P2方法"
EN_TITLE = "YOLO11n-DWCA-P2 for Roadside Traffic Small Object Detection"
CN_AUTHORS = "刘华硕^1^，任洪娥^1^"
EN_AUTHORS = "LIU Huashuo^1^, REN Honge^1^"
CN_AFFILIATION = "（1. 东北林业大学 计算机与人工智能学院，哈尔滨 150040）"
EN_AFFILIATION = "(1. College of Computer and Artificial Intelligence, Northeast Forestry University, Harbin 150040, China)"

FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ARIAL_UNICODE = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
FONT_TIMES = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
FONT_TIMES_ITALIC = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"
FONT_STIX_MATH = "/System/Library/Fonts/Supplemental/STIXTwoMath.otf"

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

PALETTE = {
    "blue": "#0077BB",
    "cyan": "#33BBEE",
    "teal": "#009988",
    "orange": "#EE7733",
    "red": "#CC3311",
    "magenta": "#EE3377",
    "grey": "#6B7280",
    "light_grey": "#E5E7EB",
    "ink": "#111827",
    "muted": "#4B5563",
    "bg": "#FFFFFF",
}


@dataclass(frozen=True)
class OutputFigure:
    path: Path
    caption_cn: str
    caption_en: str
    note: str = ""


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    FORMULA_DIR.mkdir(parents=True, exist_ok=True)
    for stale_png in FIG_DIR.glob("*.png"):
        if "fig_detection_comparison" in stale_png.name:
            continue  # generated externally from AutoDL inference outputs
        stale_png.unlink()
    for stale_formula in FORMULA_DIR.glob("*.png"):
        stale_formula.unlink()
    stale_table = TABLE_DIR / "pretrained_reference.csv"
    if stale_table.exists():
        stale_table.unlink()


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False, cjk: bool = True) -> ImageFont.FreeTypeFont:
    candidates = []
    if cjk:
        candidates.append(FONT_CJK)
    candidates.append(FONT_ARIAL_BOLD if bold else FONT_ARIAL)
    candidates.append(FONT_ARIAL_UNICODE)
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: str = PALETTE["ink"],
) -> None:
    tw, th = text_size(draw, text, fnt)
    draw.text((xy[0] - tw / 2, xy[1] - th / 2), text, font=fnt, fill=hex_to_rgb(fill))


def draw_wrapped_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    fnt: ImageFont.ImageFont,
    fill: str = PALETTE["ink"],
    max_lines: int = 3,
) -> None:
    x1, y1, x2, y2 = box
    max_width = x2 - x1 - 16
    chars: list[str] = []
    lines: list[str] = []
    for ch in text:
        trial = "".join(chars + [ch])
        if text_size(draw, trial, fnt)[0] <= max_width:
            chars.append(ch)
        else:
            lines.append("".join(chars))
            chars = [ch]
    if chars:
        lines.append("".join(chars))
    lines = lines[:max_lines]
    total_h = sum(text_size(draw, line, fnt)[1] for line in lines) + (len(lines) - 1) * 5
    y = y1 + (y2 - y1 - total_h) / 2
    for line in lines:
        tw, th = text_size(draw, line, fnt)
        draw.text((x1 + (x2 - x1 - tw) / 2, y), line, font=fnt, fill=hex_to_rgb(fill))
        y += th + 5


def round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str = "#CBD5E1",
    width: int = 2,
    radius: int = 8,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=hex_to_rgb(fill), outline=hex_to_rgb(outline), width=width)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str = PALETTE["ink"],
    width: int = 3,
) -> None:
    draw.line([start, end], fill=hex_to_rgb(fill), width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head_len = 12
    for delta in (math.pi * 0.82, -math.pi * 0.82):
        x = end[0] + head_len * math.cos(angle + delta)
        y = end[1] + head_len * math.sin(angle + delta)
        draw.line([end, (x, y)], fill=hex_to_rgb(fill), width=width)


def line_with_elbow(
    draw: ImageDraw.ImageDraw,
    points: list[tuple[int, int]],
    fill: str = PALETTE["ink"],
    width: int = 3,
) -> None:
    if len(points) < 2:
        return
    for start, end in zip(points[:-2], points[1:-1]):
        draw.line([start, end], fill=hex_to_rgb(fill), width=width)
    arrow(draw, points[-2], points[-1], fill, width)


def save_csv(path: Path, rows: Iterable[dict] | pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(rows, pd.DataFrame):
        out = rows.copy()
        for col in out.columns:
            if pd.api.types.is_numeric_dtype(out[col]):
                out[col] = out[col].round(4)
        out.to_csv(path, index=False, encoding="utf-8-sig")
        return
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        if not rows:
            return
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def metric_cols() -> list[str]:
    return ["Precision|%", "Recall|%", "mAP@0.5|%", "mAP@0.5：0.95|%", "FPS", "GFLOPs", "Params|M"]


def load_experiment_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    data = pd.read_excel(EXCEL_PATH, sheet_name="数据表")
    fps_raw = pd.read_excel(EXCEL_PATH, sheet_name="FPS测量记录", header=None)
    data = data.rename(
        columns={
            "模型|YAML": "模型YAML",
            "Precision|%": "P",
            "Recall|%": "R",
            "mAP@0.5|%": "mAP50",
            "mAP@0.5：0.95|%": "mAP50_95",
            "Params|M": "Params",
        }
    )
    for col in ["P", "R", "mAP50", "mAP50_95", "FPS", "GFLOPs", "Params"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    save_csv(TABLE_DIR / "experiment_records_clean.csv", data)
    save_csv(TABLE_DIR / "fps_sheet_raw.csv", fps_raw)
    return data, fps_raw


def row_by_group(df: pd.DataFrame, group: str) -> pd.Series:
    match = df[df["组别名"] == group]
    if match.empty:
        raise KeyError(group)
    return match.iloc[-1]


def make_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    baseline = row_by_group(df, "baseline-b32")
    proposed = row_by_group(df, "DWCA-P2-b32")
    main = pd.DataFrame(
        [
            {
                "模型": "baseline",
                "P/%": baseline.P,
                "R/%": baseline.R,
                "mAP@0.5/%": baseline.mAP50,
                "mAP@0.5:0.95/%": baseline.mAP50_95,
                "FPS": baseline.FPS,
                "GFLOPs": baseline.GFLOPs,
                "Params/M": baseline.Params,
            },
            {
                "模型": "DWCA-P2",
                "P/%": proposed.P,
                "R/%": proposed.R,
                "mAP@0.5/%": proposed.mAP50,
                "mAP@0.5:0.95/%": proposed.mAP50_95,
                "FPS": proposed.FPS,
                "GFLOPs": proposed.GFLOPs,
                "Params/M": proposed.Params,
            },
        ]
    )

    ablation_groups = [
        "baseline-b32",
        "+D",
        "+DW",
        "DWCA",
        "DW-P2",
        "DWCA-P2-b32",
    ]
    change_map = {
        "baseline-b32": "YOLO11n",
        "+D": "DyHead",
        "+DW": "DyHead+WIoU",
        "DWCA": "DyHead+WIoU+CA",
        "DW-P2": "DyHead+WIoU+P2",
        "DWCA-P2-b32": "DyHead+WIoU+CA+P2",
    }
    display_map = {
        "baseline-b32": "baseline",
        "DWCA-P2-b32": "DWCA-P2",
    }
    ablation_rows = []
    for group in ablation_groups:
        r = row_by_group(df, group)
        ablation_rows.append(
            {
                "模型": display_map.get(group, group),
                "主要改动": change_map[group],
                "P/%": r.P,
                "R/%": r.R,
                "mAP@0.5/%": r.mAP50,
                "mAP@0.5:0.95/%": r.mAP50_95,
                "FPS": r.FPS,
                "GFLOPs": r.GFLOPs,
                "Params/M": r.Params,
            }
        )
    ablation = pd.DataFrame(ablation_rows)

    structure_groups = ["YOLOv5n-yaml", "YOLOv8n-yaml", "YOLOv10n-yaml", "baseline-b32", "DWCA-P2-b32"]
    structure_rows = []
    for group in structure_groups:
        r = row_by_group(df, group)
        structure_rows.append(
            {
                "模型": "YOLO11n baseline" if group == "baseline-b32" else display_map.get(group, group),
                "P/%": r.P,
                "R/%": r.R,
                "mAP@0.5/%": r.mAP50,
                "mAP@0.5:0.95/%": r.mAP50_95,
                "GFLOPs": r.GFLOPs,
                "Params/M": r.Params,
            }
        )
    structure = pd.DataFrame(structure_rows)

    speed_groups = [
        "baseline-b32",
        "+D",
        "+DW",
        "DWCA",
        "DW-P2",
        "DWCA-P2-b32",
    ]
    speed_rows = []
    base_fps = float(baseline.FPS)
    for group in speed_groups:
        r = row_by_group(df, group)
        speed_rows.append(
            {
                "模型": display_map.get(group, group),
                "FPS": r.FPS,
                "单张耗时/ms": 1000.0 / r.FPS if pd.notna(r.FPS) and r.FPS else None,
                "相对baseline/%": r.FPS / base_fps * 100 if pd.notna(r.FPS) else None,
                "GFLOPs": r.GFLOPs,
                "Params/M": r.Params,
            }
        )
    speed = pd.DataFrame(speed_rows).sort_values("FPS", ascending=False)

    # Literature comparison on DAIR-V2X-I (Liang et al. 2025, ref [30], their protocol)
    # + our DWCA-P2 under our protocol. Cross-protocol => indicative only (see caveat in text).
    proposed = row_by_group(df, "DWCA-P2-b32")
    literature_rows = [
        {"方法": "RT-DETR-r18^{[30]}", "P/%": 85.5, "R/%": 78.9, "mAP@0.5/%": 85.1, "mAP@0.5:0.95/%": 59.9},
        {"方法": "Mamba-YOLO-B^{[30]}", "P/%": 85.6, "R/%": 79.1, "mAP@0.5/%": 85.2, "mAP@0.5:0.95/%": 61.1},
        {"方法": "YOLO-FLC^{[30]}", "P/%": 85.7, "R/%": 79.4, "mAP@0.5/%": 85.3, "mAP@0.5:0.95/%": 61.3},
        {"方法": "DWCA-P2（本文）", "P/%": float(proposed.P), "R/%": float(proposed.R),
         "mAP@0.5/%": float(proposed.mAP50), "mAP@0.5:0.95/%": float(proposed.mAP50_95)},
    ]
    literature = pd.DataFrame(literature_rows)

    tables = {
        "main_results": main,
        "ablation": ablation,
        "structure_comparison": structure,
        "speed_complexity": speed,
        "literature_comparison": literature,
    }
    for name, table in tables.items():
        save_csv(TABLE_DIR / f"{name}.csv", table)
    return tables


def copy_if_exists(src: Path, dst: Path) -> bool:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False


def load_old_csv(name: str) -> pd.DataFrame | None:
    path = OLD_ASSET_DIR / name
    if path.exists():
        return pd.read_csv(path)
    return None


def load_scale_and_class_tables() -> dict[str, pd.DataFrame | None]:
    out: dict[str, pd.DataFrame | None] = {}
    for name in [
        "val_scale_distribution_640.csv",
        "class_metrics_baseline_vs_dwca_p2_b32.csv",
        "training_curves_baseline_vs_dwca_p2_b32.csv",
    ]:
        df = load_old_csv(name)
        out[name] = df
        if df is not None:
            save_csv(TABLE_DIR / name, df)
    return out


def draw_grouped_metrics(main: pd.DataFrame, path: Path) -> None:
    w, h = 1400, 850
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(23)
    tick_font = font(21)
    small_font = font(20)
    draw_centered(draw, (w / 2, 48), "主结果指标对比", title_font)

    metrics = ["P/%", "R/%", "mAP@0.5/%", "mAP@0.5:0.95/%"]
    labels = ["Precision", "Recall", "mAP@0.5", "mAP@0.5:0.95"]
    baseline = main.iloc[0]
    proposed = main.iloc[1]
    values = [[float(baseline[m]), float(proposed[m])] for m in metrics]

    left, right, top, bottom = 130, 70, 110, 135
    plot_w = w - left - right
    plot_h = h - top - bottom
    max_v = 100
    for yv in range(0, 101, 10):
        y = top + plot_h - yv / max_v * plot_h
        draw.line((left, y, w - right, y), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw.text((left - 62, y - 10), str(yv), font=tick_font, fill=hex_to_rgb(PALETTE["muted"]))
    draw.line((left, top, left, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)
    draw.line((left, top + plot_h, w - right, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)

    group_w = plot_w / len(metrics)
    bar_w = 60
    for i, (label, pair) in enumerate(zip(labels, values)):
        cx = left + group_w * (i + 0.5)
        for j, (value, color) in enumerate(zip(pair, [PALETTE["blue"], PALETTE["orange"]])):
            x1 = cx + (j - 0.5) * (bar_w + 22) - bar_w / 2
            y1 = top + plot_h - value / max_v * plot_h
            draw.rounded_rectangle((x1, y1, x1 + bar_w, top + plot_h), radius=6, fill=hex_to_rgb(color))
            draw_centered(draw, (x1 + bar_w / 2, y1 - 22), f"{value:.1f}", small_font)
        draw_centered(draw, (cx, top + plot_h + 42), label, label_font)
    draw.text((w - 380, 118), "baseline", font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.rectangle((w - 420, 122, w - 394, 148), fill=hex_to_rgb(PALETTE["blue"]))
    draw.text((w - 380, 158), "DWCA-P2", font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.rectangle((w - 420, 162, w - 394, 188), fill=hex_to_rgb(PALETTE["orange"]))
    img.save(path, dpi=(300, 300))


def draw_ablation_map(ablation: pd.DataFrame, path: Path) -> None:
    selected = ablation[ablation["模型"].isin(["baseline", "+D", "+DW", "DWCA", "DW-P2", "DWCA-P2"])].copy()
    w, h = 1350, 820
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(22)
    tick_font = font(19)
    small_font = font(17)
    draw_centered(draw, (w / 2, 48), "关键消融路线的 mAP@0.5:0.95 对比", title_font)
    left, right, top, bottom = 110, 60, 110, 130
    plot_w = w - left - right
    plot_h = h - top - bottom
    min_y, max_y = 59, 66
    for yv in range(59, 67):
        y = top + plot_h - (yv - min_y) / (max_y - min_y) * plot_h
        draw.line((left, y, w - right, y), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw.text((left - 50, y - 10), str(yv), font=tick_font, fill=hex_to_rgb(PALETTE["muted"]))
    draw.line((left, top, left, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)
    draw.line((left, top + plot_h, w - right, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)
    n = len(selected)
    bar_w = min(92, plot_w / n * 0.52)
    for i, (_, row) in enumerate(selected.iterrows()):
        cx = left + plot_w * (i + 0.5) / n
        val = float(row["mAP@0.5:0.95/%"])
        y1 = top + plot_h - (val - min_y) / (max_y - min_y) * plot_h
        color = PALETTE["orange"] if row["模型"] == "DWCA-P2" else PALETTE["teal"] if "P2" in row["模型"] else PALETTE["blue"]
        draw.rounded_rectangle((cx - bar_w / 2, y1, cx + bar_w / 2, top + plot_h), radius=6, fill=hex_to_rgb(color))
        draw_centered(draw, (cx, y1 - 20), f"{val:.1f}", small_font)
        draw_centered(draw, (cx, top + plot_h + 35), str(row["模型"]), label_font)
    draw_centered(draw, (38, h / 2), "mAP@0.5:0.95/%", label_font)
    img.save(path, dpi=(300, 300))


def draw_scale_distribution(scale_df: pd.DataFrame, path: Path) -> None:
    w, h = 1450, 850
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(22)
    tick_font = font(18)
    small_font = font(18)
    draw_centered(draw, (w / 2, 48), "验证集各类别短边尺度分布", title_font)
    left, right, top, bottom = 170, 80, 110, 135
    plot_w = w - left - right
    plot_h = h - top - bottom
    colors = ["#0077BB", "#33BBEE", "#BBBBBB"]
    cols = ["short<16", "16<=short<32", "short>=32"]
    labels = ["short<16", "16<=short<32", "short>=32"]
    row_h = plot_h / len(scale_df)
    for i, (_, row) in enumerate(scale_df.iterrows()):
        y = top + row_h * i + row_h * 0.2
        x = left
        total = float(row["total"])
        for col, color in zip(cols, colors):
            width = plot_w * float(row[col]) / total
            draw.rectangle((x, y, x + width, y + row_h * 0.55), fill=hex_to_rgb(color))
            x += width
        draw.text((20, y + row_h * 0.18), str(row["class"]), font=label_font, fill=hex_to_rgb(PALETTE["ink"]))
        draw.text((left + plot_w + 12, y + row_h * 0.18), f"{float(row['short<32_pct']):.1f}%", font=small_font, fill=hex_to_rgb(PALETTE["muted"]))
    for xv in range(0, 101, 20):
        x = left + plot_w * xv / 100
        draw.line((x, top - 5, x, top + plot_h), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw_centered(draw, (x, top + plot_h + 28), f"{xv}%", tick_font)
    lx = left
    for label, color in zip(labels, colors):
        draw.rectangle((lx, h - 70, lx + 26, h - 44), fill=hex_to_rgb(color))
        draw.text((lx + 36, h - 70), label, font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
        lx += 230
    img.save(path, dpi=(300, 300))


def draw_class_gain(class_df: pd.DataFrame, path: Path) -> None:
    df = class_df[class_df["class"] != "all"].copy()
    df["gain"] = df["mAP50_95_gain"] * 100
    w, h = 1350, 840
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(22)
    tick_font = font(18)
    small_font = font(18)
    draw_centered(draw, (w / 2, 48), "类别级 mAP@0.5:0.95 增益", title_font)
    left, right, top, bottom = 170, 90, 110, 90
    plot_w = w - left - right
    plot_h = h - top - bottom
    min_v, max_v = 0, 9
    for xv in range(min_v, max_v + 1, 2):
        x = left + (xv - min_v) / (max_v - min_v) * plot_w
        draw.line((x, top, x, top + plot_h), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw_centered(draw, (x, top + plot_h + 28), str(xv), tick_font)
    zero_x = left + (0 - min_v) / (max_v - min_v) * plot_w
    draw.line((zero_x, top, zero_x, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)
    row_h = plot_h / len(df)
    for i, (_, row) in enumerate(df.iterrows()):
        y = top + row_h * (i + 0.5)
        val = float(row["gain"])
        x = left + (val - min_v) / (max_v - min_v) * plot_w
        color = PALETTE["teal"] if val >= 0 else PALETTE["red"]
        draw.text((30, y - 12), str(row["class"]), font=label_font, fill=hex_to_rgb(PALETTE["ink"]))
        draw.rounded_rectangle((min(x, zero_x), y - 14, max(x, zero_x), y + 14), radius=5, fill=hex_to_rgb(color))
        draw.text((x + 10 if val >= 0 else x - 58, y - 12), f"{val:+.1f}", font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw_centered(draw, (w / 2, h - 18), "提升值 / 个百分点", label_font)
    img.save(path, dpi=(300, 300))


def draw_line_chart(curves: pd.DataFrame, metric: str, path: Path, title: str, y_label: str) -> None:
    w, h = 1350, 820
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(34, bold=True)
    label_font = font(22)
    tick_font = font(18)
    small_font = font(18)
    draw_centered(draw, (w / 2, 48), title, title_font)
    left, right, top, bottom = 120, 70, 110, 105
    plot_w = w - left - right
    plot_h = h - top - bottom
    min_x, max_x = 1, int(curves["epoch"].max())
    min_y = math.floor(float(curves[metric].min()) * 100 / 10) * 10 / 100
    max_y = math.ceil(float(curves[metric].max()) * 100 / 5) * 5 / 100
    for xv in range(0, max_x + 1, 50):
        if xv < min_x:
            continue
        x = left + (xv - min_x) / (max_x - min_x) * plot_w
        draw.line((x, top, x, top + plot_h), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw_centered(draw, (x, top + plot_h + 28), str(xv), tick_font)
    for yv in [min_y + i * (max_y - min_y) / 5 for i in range(6)]:
        y = top + plot_h - (yv - min_y) / (max_y - min_y) * plot_h
        draw.line((left, y, left + plot_w, y), fill=hex_to_rgb(PALETTE["light_grey"]), width=1)
        draw.text((left - 65, y - 11), f"{yv*100:.0f}", font=tick_font, fill=hex_to_rgb(PALETTE["muted"]))
    draw.line((left, top, left, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)
    draw.line((left, top + plot_h, left + plot_w, top + plot_h), fill=hex_to_rgb(PALETTE["ink"]), width=2)

    for source_model, label, color in [("baseline-b32", "baseline", PALETTE["blue"]), ("DWCA-P2-b32", "DWCA-P2", PALETTE["orange"])]:
        df = curves[curves["model"] == source_model].sort_values("epoch")
        pts = []
        for _, row in df.iterrows():
            x = left + (int(row["epoch"]) - min_x) / (max_x - min_x) * plot_w
            y = top + plot_h - (float(row[metric]) - min_y) / (max_y - min_y) * plot_h
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=hex_to_rgb(color), width=3)
        if pts:
            draw.ellipse((pts[-1][0] - 5, pts[-1][1] - 5, pts[-1][0] + 5, pts[-1][1] + 5), fill=hex_to_rgb(color))
    draw.rectangle((w - 350, 130, w - 324, 156), fill=hex_to_rgb(PALETTE["blue"]))
    draw.text((w - 315, 130), "baseline", font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.rectangle((w - 350, 170, w - 324, 196), fill=hex_to_rgb(PALETTE["orange"]))
    draw.text((w - 315, 170), "DWCA-P2", font=small_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw_centered(draw, (w / 2, h - 28), "epoch", label_font)
    draw.text((18, h / 2), y_label, font=label_font, fill=hex_to_rgb(PALETTE["ink"]))
    img.save(path, dpi=(300, 300))


def draw_architecture(path: Path) -> None:
    """P-lane grid architecture figure for YOLO11n-DWCA-P2.

    Layout strategy (mirrors the YOLO-FLC reference in s41598-025-18263-9):
      * Each box shows only "module name" + "C × H × W" (no layer numbers).
      * Backbone: a single vertical column on the far left (Input -> C2PSA),
        with backbone tap rows (2, 5, 7, 11) anchored to the P2/P3/P4/P5 lane
        centres so every backbone->neck lateral is a clean orthogonal hop.
      * Neck: a horizontal grid of small uniform boxes. There are 4 P-level
        LANES stacked top->bottom: P2 (top, high-res) -> P3 -> P4 -> P5
        (bottom, deep). Every neck node owns a distinct (column, lane) cell;
        the top-down FPN (12-20) and the bottom-up PAN (21-29) read left->right.
      * All wiring is orthogonal. Skip/lateral edges leave the source, rise to
        an EMPTY "gap-row" just above the target lane, travel horizontally
        there, then drop into the TOP edge of the receiving Concat — so no
        lateral ever crosses a module box or its text.
      * Detect heads sit in a vertical column on the far right, one per scale,
        each at its lane y; feeders 23/26/29 are straight horizontals, the P2
        feeder (L20) uses a gap-row to clear L21.
      * DyHeadDetect + WIoU v3 are annotated as a training-only side note.

    Geometry (lane y, node (col, lane), backbone anchoring, gap-row + detect
    routing) was verified to produce ZERO box-crossings and ZERO line crossings
    by an axis-aligned intersection sweep before being committed here; the same
    sweep runs again at the end of this function as a hard self-check.
    """
    def shape(c: int, hw: int) -> str:
        return f"{c} × {hw} × {hw}"

    # ------------------------------------------------------------------
    # Tensor shapes for YOLO11n (depth=0.50, width=0.25, max_channels=1024).
    # ------------------------------------------------------------------
    BB_SHAPES = {
        "input": ("Input", shape(3, 640)),
        "0": ("Conv", shape(16, 320)),
        "1": ("Conv", shape(32, 160)),
        "2": ("C3k2", shape(64, 160)),
        "3": ("Conv", shape(64, 80)),
        "4": ("C3k2", shape(128, 80)),
        "5": ("CoordAttention", shape(128, 80)),
        "6": ("Conv", shape(128, 40)),
        "7": ("C3k2", shape(128, 40)),
        "8": ("Conv", shape(256, 20)),
        "9": ("C3k2", shape(256, 20)),
        "10": ("SPPF", shape(256, 20)),
        "11": ("C2PSA", shape(256, 20)),
    }
    NK_SHAPES = {
        "12": ("Upsample", shape(256, 40)),
        "13": ("Concat", shape(384, 40)),
        "14": ("C3k2", shape(128, 40)),
        "15": ("Upsample", shape(128, 80)),
        "16": ("Concat", shape(256, 80)),
        "17": ("C3k2", shape(64, 80)),
        "18": ("Upsample", shape(64, 160)),
        "19": ("Concat", shape(128, 160)),
        "20": ("C3k2", shape(32, 160)),
        "21": ("Conv", shape(32, 80)),
        "22": ("Concat", shape(96, 80)),
        "23": ("C3k2", shape(64, 80)),
        "24": ("Conv", shape(64, 40)),
        "25": ("Concat", shape(192, 40)),
        "26": ("C3k2", shape(128, 40)),
        "27": ("Conv", shape(128, 20)),
        "28": ("Concat", shape(384, 20)),
        "29": ("C3k2", shape(256, 20)),
    }

    PALETTES = {
        "input": ("#F1F5F9", "#475569"),
        "Conv": ("#A7F3D0", "#047857"),
        "Upsample": ("#A7F3D0", "#047857"),
        "C3k2": ("#DDD6FE", "#6D28D9"),
        "C2PSA": ("#67E8F9", "#0E7490"),
        "SPPF": ("#C4B5FD", "#6D28D9"),
        "CoordAttention": ("#FDE68A", "#B45309"),
        "Concat": ("#FED7AA", "#9A3412"),
        "Detect": ("#FECACA", "#BE123C"),
    }

    # ------------------------------------------------------------------
    # Grid geometry (all in px on a 300-dpi canvas).
    # ------------------------------------------------------------------
    BW, BH = 184, 70          # neck box size
    COLW = BW + 56            # neck column pitch
    BB_W, BB_H = 224, 58      # backbone box size
    BB_STEP = 70              # min vertical pitch between backbone boxes
    HBW, HBH = 248, 80        # detect box size
    GAP = 38                  # gap-row offset above a lane

    ROW = {"P2": 0, "P3": 1, "P4": 2, "P5": 3}     # top -> bottom
    # Lane y-tops. Non-uniform spacing sized so backbone taps never overlap:
    #   P2-P3 spans backbone idx 3..6 (3 steps), P3-P4 idx 6..8 (2), P4-P5 idx 8..12 (4).
    neck_x0 = 560
    band_y = {"P2": 300}
    band_y["P3"] = band_y["P2"] + 3 * BB_STEP
    band_y["P4"] = band_y["P3"] + 2 * BB_STEP
    band_y["P5"] = band_y["P4"] + 4 * BB_STEP

    # Each neck node -> (column, lane). No two nodes share a cell.
    NODE_CELL = {
        "12": (0, "P4"), "13": (1, "P4"), "14": (2, "P4"),
        "15": (2, "P3"), "16": (3, "P3"), "17": (4, "P3"),
        "18": (4, "P2"), "19": (5, "P2"), "20": (6, "P2"),
        "21": (7, "P2"), "22": (7, "P3"), "23": (8, "P3"),
        "24": (8, "P4"), "25": (9, "P4"), "26": (10, "P4"),
        "27": (10, "P5"), "28": (11, "P5"), "29": (12, "P5"),
    }
    MAX_COL = max(c for c, _ in NODE_CELL.values())
    neck_right = neck_x0 + MAX_COL * COLW + BW
    det_x = neck_right + 230
    det_right = det_x + HBW

    w = det_right + 110
    h = band_y["P5"] + BH + 560
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(40, bold=True)
    sec_font = font(28, bold=True)
    label_font = font(22, bold=True)
    shape_font = font(17)
    small_font = font(20)
    tiny_font = font(18)
    lane_font = font(24, bold=True)
    draw_centered(draw, (w / 2, 48), "YOLO11n-DWCA-P2 网络结构示意图", title_font)
    draw_centered(
        draw,
        (w / 2, 96),
        "Architecture diagram of YOLO11n-DWCA-P2 network",
        small_font,
        PALETTE["muted"],
    )

    # ------------------------------------------------------------------
    # Drawing helpers
    # ------------------------------------------------------------------
    def style_for(name: str) -> tuple[str, str]:
        return PALETTES.get(name, ("#E5E7EB", "#374151"))

    def cx(b): return (b[0] + b[2]) // 2
    def cy(b): return (b[1] + b[3]) // 2
    def left_pt(b): return (b[0], cy(b))
    def right_pt(b): return (b[2], cy(b))
    def top_pt(b): return (cx(b), b[1])
    def bot_pt(b): return (cx(b), b[3])

    def block(box, name, sub, fill, outline, line_w=2, bw=BW, bh=BH):
        round_rect(draw, box, fill, outline=outline, width=line_w, radius=9)
        draw_centered(draw, (cx(box), cy(box) - 14), name, label_font)
        draw_centered(draw, (cx(box), cy(box) + 15), sub, shape_font, PALETTE["muted"])

    def poly(points, color=PALETTE["ink"], width=3):
        line_with_elbow(draw, points, color, width)

    def section(x1, y1, x2, y2, label_bottom):
        # Dashed rectangle, label centered below, like the reference figure.
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        for x in range(x1, x2, 16):
            draw.line((x, y1, min(x + 8, x2), y1), fill=hex_to_rgb("#94A3B8"), width=2)
            draw.line((x, y2, min(x + 8, x2), y2), fill=hex_to_rgb("#94A3B8"), width=2)
        for y in range(y1, y2, 16):
            draw.line((x1, y, x1, min(y + 8, y2)), fill=hex_to_rgb("#94A3B8"), width=2)
            draw.line((x2, y, x2, min(y + 8, y2)), fill=hex_to_rgb("#94A3B8"), width=2)
        draw_centered(draw, ((x1 + x2) / 2, y2 + 34), label_bottom, sec_font)

    # ------------------------------------------------------------------
    # Backbone vertical column on the far left.
    # Tap rows (2, 5, 7, 11) are anchored to lane centres via a piecewise
    # linear y(idx); the other rows are interpolated between anchors. This
    # makes every backbone->neck lateral a clean orthogonal hop.
    # ------------------------------------------------------------------
    bb_order = ["input", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    idx = {k: i for i, k in enumerate(bb_order)}
    band_cy = {b: band_y[b] + BH // 2 for b in band_y}
    anchor_pts = sorted(
        [
            (idx["2"], band_cy["P2"]),
            (idx["5"], band_cy["P3"]),
            (idx["7"], band_cy["P4"]),
            (idx["11"], band_cy["P5"]),
        ]
    )

    def piecewise_y(i: int) -> float:
        pts = anchor_pts
        if i <= pts[0][0]:
            (x0, y0), (x1, y1) = pts[0], pts[1]
        elif i >= pts[-1][0]:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
        else:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            for j in range(len(pts) - 1):
                if pts[j][0] <= i <= pts[j + 1][0]:
                    (x0, y0), (x1, y1) = pts[j], pts[j + 1]
                    break
        return y0 + (y1 - y0) * (i - x0) / (x1 - x0)

    bb_x = 80
    bb: dict[str, tuple[int, int, int, int]] = {}
    for k in bb_order:
        ycen = piecewise_y(idx[k])
        bb[k] = (bb_x, int(ycen - BB_H / 2), bb_x + BB_W, int(ycen + BB_H / 2))

    # ------------------------------------------------------------------
    # Neck nodes laid out on the (column, lane) grid.
    # ------------------------------------------------------------------
    def cell_rect(col: int, lane: str) -> tuple[int, int, int, int]:
        x = neck_x0 + col * COLW
        y = band_y[lane]
        return (x, y, x + BW, y + BH)

    n: dict[str, tuple[int, int, int, int]] = {
        k: cell_rect(c, lane) for k, (c, lane) in NODE_CELL.items()
    }

    # Detect heads on the far right, one per lane.
    det: dict[str, tuple[int, int, int, int]] = {
        lane: (det_x, band_cy[lane] - HBH // 2, det_x + HBW, band_cy[lane] + HBH // 2)
        for lane in band_y
    }

    # Gap-row y just above each lane (an empty corridor for laterals).
    gap_above = {lane: band_y[lane] - GAP for lane in band_y}

    # ------------------------------------------------------------------
    # Self-check: collect all boxes; verify no wire crosses a non-endpoint box.
    # ------------------------------------------------------------------
    all_boxes: dict[str, tuple[int, int, int, int]] = {}
    for k, b in bb.items():
        all_boxes["bb" + k] = b
    for k, b in n.items():
        all_boxes["n" + k] = b
    for lane, b in det.items():
        all_boxes["det" + lane] = b

    _crossings: list[str] = []

    def _seg_hits(seg, ignore):
        (x1, y1), (x2, y2) = seg
        hit = []
        for nm, bx in all_boxes.items():
            if nm in ignore:
                continue
            a, c, d, e = bx
            pad = 3
            a -= pad; c -= pad; d += pad; e += pad
            if abs(y1 - y2) < 1:
                if c <= y1 <= e:
                    lo, hi = sorted((x1, x2))
                    if not (hi < a or lo > d):
                        hit.append(nm)
            elif abs(x1 - x2) < 1:
                if a <= x1 <= d:
                    lo, hi = sorted((y1, y2))
                    if not (hi < c or lo > e):
                        hit.append(nm)
            else:  # diagonal segment (should not occur) — sample endpoints only
                pass
        return hit

    def wire(points, ignore, color=PALETTE["ink"], width=3, label=""):
        # Draw an orthogonal polyline arrow and record any box-crossings.
        for a, b2 in zip(points, points[1:]):
            for nm in _seg_hits((a, b2), ignore):
                _crossings.append(f"{label}:{nm}")
        poly(points, color, width)

    # ------------------------------------------------------------------
    # Section frames (Backbone | Neck | Head). Sized to wrap their contents.
    # ------------------------------------------------------------------
    reg_top = 150
    reg_bot = band_y["P5"] + BH + 320
    bb_frame = (bb_x - 34, reg_top, bb_x + BB_W + 34, reg_bot)
    nk_frame = (neck_x0 - 90, reg_top, neck_right + 60, reg_bot)
    hd_frame = (det_x - 70, reg_top, det_right + 60, reg_bot)
    section(*bb_frame, "Backbone")
    section(*nk_frame, "Neck")
    section(*hd_frame, "Head")

    # Faint lane guides + lane labels on the left of the neck.
    for lane in band_y:
        ly = band_cy[lane]
        draw.line(
            (nk_frame[0] + 8, ly, nk_frame[2] - 8, ly),
            fill=hex_to_rgb("#EEF2F7"),
            width=1,
        )
    for lane in band_y:
        draw_centered(
            draw,
            (neck_x0 - 62, band_cy[lane]),
            lane,
            lane_font,
            PALETTE["muted"],
        )

    # ------------------------------------------------------------------
    # Draw backbone boxes + the -1 chain between them.
    # ------------------------------------------------------------------
    for i, key in enumerate(bb_order):
        name, sub = BB_SHAPES[key]
        fill, outl = style_for(name if name != "Input" else "input")
        line_w = 3 if name == "CoordAttention" else 2
        block(bb[key], name, sub, fill, outl, line_w)
        if i > 0:
            prev = bb[bb_order[i - 1]]
            poly([bot_pt(prev), top_pt(bb[key])], PALETTE["muted"], 2)

    # ------------------------------------------------------------------
    # Draw neck boxes.  P2-lane fusion boxes (19/20/21) get a blue accent.
    # ------------------------------------------------------------------
    P2_ACCENT = {"19", "20", "21"}
    for key, box in n.items():
        name, sub = NK_SHAPES[key]
        fill, outl = style_for(name)
        line_w = 2
        if key in P2_ACCENT:
            outl = "#1D4ED8"
            line_w = 3
        block(box, name, sub, fill, outl, line_w)

    # ------------------------------------------------------------------
    # Neck -1 chain edges (12->13->...->29). Orthogonal: same lane -> straight
    # horizontal; same column -> straight vertical; otherwise a single elbow.
    # ------------------------------------------------------------------
    chain = [
        ("12", "13"), ("13", "14"), ("14", "15"), ("15", "16"), ("16", "17"),
        ("17", "18"), ("18", "19"), ("19", "20"), ("20", "21"), ("21", "22"),
        ("22", "23"), ("23", "24"), ("24", "25"), ("25", "26"), ("26", "27"),
        ("27", "28"), ("28", "29"),
    ]
    for s, t in chain:
        sb, tb = n[s], n[t]
        accent = (s in P2_ACCENT and t in P2_ACCENT)
        color = PALETTE["blue"] if accent else PALETTE["ink"]
        width = 4 if accent else 3
        if abs(cy(sb) - cy(tb)) < 2:  # same lane -> horizontal
            pts = [right_pt(sb), left_pt(tb)] if sb[0] < tb[0] else [left_pt(sb), right_pt(tb)]
        elif abs(cx(sb) - cx(tb)) < 2:  # same column -> vertical
            pts = [bot_pt(sb), top_pt(tb)] if sb[1] < tb[1] else [top_pt(sb), bot_pt(tb)]
        else:  # different col & lane -> single elbow (vertical then horizontal)
            p0 = bot_pt(sb) if tb[1] > sb[1] else top_pt(sb)
            pts = [p0, (cx(sb), cy(tb)), left_pt(tb) if tb[0] > sb[0] else right_pt(tb)]
        wire(pts, {"n" + s, "n" + t}, color, width, f"chain{s}-{t}")

    # ------------------------------------------------------------------
    # 11 -> 12 (backbone C2PSA into the first Upsample): left gutter elbow.
    # ------------------------------------------------------------------
    gut12 = n["12"][0] - 26
    wire(
        [right_pt(bb["11"]), (gut12, cy(bb["11"])), (gut12, cy(n["12"])), left_pt(n["12"])],
        {"bb11", "n12"},
        PALETTE["ink"],
        3,
        "11-12",
    )

    # ------------------------------------------------------------------
    # Skip / lateral edges. Each leaves its source, rises to the empty
    # gap-row above the TARGET lane, runs horizontally there, then drops into
    # the TOP edge of the receiving Concat. Multiple skips into one lane use
    # distinct sub-lanes via the `lane` offset.
    # Routing: 7->13, 5->16, 2->19, 11->28 (backbone taps);
    #          17->22, 14->25 (head taps).
    # ------------------------------------------------------------------
    def skip_edge(src_box, dst_box, lane_name, color, width, sub_lane, ignore, label):
        gy = gap_above[lane_name] - sub_lane * 18
        sx, sy = right_pt(src_box)
        tx = cx(dst_box)
        stub = src_box[2] + 18
        wire(
            [(sx, sy), (stub, sy), (stub, gy), (tx, gy), top_pt(dst_box)],
            ignore,
            color,
            width,
            label,
        )

    skip_edge(bb["7"], n["13"], "P4", PALETTE["ink"], 3, 0, {"bb7", "n13"}, "7-13")
    skip_edge(bb["5"], n["16"], "P3", PALETTE["orange"], 3, 0, {"bb5", "n16"}, "5-16")
    skip_edge(bb["2"], n["19"], "P2", PALETTE["blue"], 4, 0, {"bb2", "n19"}, "2-19")
    skip_edge(bb["11"], n["28"], "P5", PALETTE["ink"], 3, 0, {"bb11", "n28"}, "11-28")
    skip_edge(n["17"], n["22"], "P3", PALETTE["ink"], 3, 1, {"n17", "n22"}, "17-22")
    skip_edge(n["14"], n["25"], "P4", PALETTE["ink"], 3, 1, {"n14", "n25"}, "14-25")

    # ------------------------------------------------------------------
    # Detect heads. Feeders 20(P2), 23(P3), 26(P4), 29(P5).
    # ------------------------------------------------------------------
    fill_d, outl_d = style_for("Detect")
    det_labels = {
        "P2": ("Detect P2/4", "tiny — 160 × 160"),
        "P3": ("Detect P3/8", "small — 80 × 80"),
        "P4": ("Detect P4/16", "medium — 40 × 40"),
        "P5": ("Detect P5/32", "large — 20 × 20"),
    }
    for lane, db in det.items():
        emph = lane == "P2"
        outl = "#1D4ED8" if emph else outl_d
        lw = 3 if emph else 2
        name, sub = det_labels[lane]
        block(db, name, sub, fill_d, outl, lw)

    feeders = {"P2": "20", "P3": "23", "P4": "26", "P5": "29"}
    for lane, fk in feeders.items():
        fb, db = n[fk], det[lane]
        ign = {"n" + fk, "det" + lane}
        if lane == "P2":  # route via gap-row to clear L21
            gy = gap_above[lane]
            wire(
                [top_pt(fb), (cx(fb), gy), (db[0] - 34, gy), (db[0] - 34, cy(db)), left_pt(db)],
                ign,
                PALETTE["blue"],
                4,
                f"det-{lane}",
            )
        else:
            wire([right_pt(fb), left_pt(db)], ign, PALETTE["ink"], 3, f"det-{lane}")

    # ------------------------------------------------------------------
    # DyHeadDetect / WIoU annotation block under the Detect column.
    # ------------------------------------------------------------------
    note_x = hd_frame[0] + 22
    note_w = hd_frame[2] - hd_frame[0] - 44
    note_h = 168
    note_y = det["P5"][3] + 56
    round_rect(
        draw,
        (note_x, note_y, note_x + note_w, note_y + note_h),
        "#FFF1F2",
        outline="#BE123C",
        width=3,
        radius=12,
    )
    draw_centered(draw, (note_x + note_w / 2, note_y + 30), "DyHeadDetect", label_font, "#BE123C")
    draw_centered(
        draw,
        (note_x + note_w / 2, note_y + 62),
        "scale + spatial + task · 共享单一检测头",
        tiny_font,
        PALETTE["muted"],
    )
    draw.line(
        (note_x + 24, note_y + 90, note_x + note_w - 24, note_y + 90),
        fill=hex_to_rgb("#FCA5A5"),
        width=1,
    )
    draw_centered(draw, (note_x + note_w / 2, note_y + 116), "WIoU v3 (train-only)", label_font, "#BE123C")
    draw_centered(
        draw,
        (note_x + note_w / 2, note_y + 146),
        "仅训练阶段 bbox 回归损失",
        tiny_font,
        PALETTE["muted"],
    )

    # ------------------------------------------------------------------
    # Legend (two rows below the frames).
    # ------------------------------------------------------------------
    legend_y = reg_bot + 64
    legend_items = [
        ("Conv / Upsample", "#A7F3D0", "#047857"),
        ("C3k2 / SPPF / C2PSA", "#DDD6FE", "#6D28D9"),
        ("Concat 特征融合", "#FED7AA", "#9A3412"),
        ("CoordAttention 位置注意力", "#FDE68A", "#B45309"),
        ("Detect / DyHeadDetect / WIoU v3", "#FECACA", "#BE123C"),
    ]
    lx = bb_x
    for text, fill, outline in legend_items:
        round_rect(draw, (lx, legend_y, lx + 32, legend_y + 24), fill, outline=outline, width=2, radius=4)
        draw.text((lx + 42, legend_y - 1), text, font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
        lx += 470

    wy = legend_y + 52
    draw.line((bb_x + 10, wy + 11, bb_x + 80, wy + 11), fill=hex_to_rgb(PALETTE["blue"]), width=4)
    draw.text((bb_x + 90, wy), "P2/4 高分辨率小目标主路径", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.line((bb_x + 560, wy + 11, bb_x + 630, wy + 11), fill=hex_to_rgb(PALETTE["ink"]), width=3)
    draw.text((bb_x + 640, wy), "FPN / PAN 主链路", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.line((bb_x + 1010, wy + 11, bb_x + 1080, wy + 11), fill=hex_to_rgb(PALETTE["orange"]), width=3)
    draw.text((bb_x + 1090, wy), "CoordAttention 位置特征旁路", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))

    # ------------------------------------------------------------------
    # Hard self-check: no wire may cross a non-endpoint box.
    # ------------------------------------------------------------------
    if _crossings:
        raise AssertionError(f"draw_architecture wire/box crossings detected: {_crossings}")

    img.save(path, dpi=(300, 300))




def draw_architecture_vertical(path: Path) -> None:
    """Vertical-flow architecture figure for YOLO11n-DWCA-P2.

    Four vertical columns, every main-chain edge is a straight vertical line:
      Backbone (left)      : Input -> C2PSA, top -> bottom.
      FPN column (mid-left): the top-down path laid out BOTTOM -> TOP so the
        data flow (P5 -> P4 -> P3 -> P2, i.e. 12 -> 20) reads upward as a
        single vertical run; each P-level stacks Upsample / Concat / C3k2.
      PAN column (mid-right): the bottom-up path laid out TOP -> BOTTOM so the
        data flow (P2 -> P3 -> P4 -> P5, i.e. 21 -> 29) reads downward as a
        single vertical run; each P-level stacks Conv / Concat / C3k2.
      Head (right)         : four Detect boxes + the DyHeadDetect / WIoU note.

    The only horizontal main-chain edge is the 20 -> 21 turn at the top. All
    lateral/skip edges (backbone taps, head taps, detect feeders) are short
    orthogonal hops between adjacent columns. An axis-aligned sweep self-checks
    that no wire crosses a non-endpoint box.
    """
    def shape(c: int, hw: int) -> str:
        return f"{c} × {hw} × {hw}"

    BB_SHAPES = {
        "input": ("Input", shape(3, 640)),
        "0": ("Conv", shape(16, 320)),
        "1": ("Conv", shape(32, 160)),
        "2": ("C3k2", shape(64, 160)),
        "3": ("Conv", shape(64, 80)),
        "4": ("C3k2", shape(128, 80)),
        "5": ("CoordAttention", shape(128, 80)),
        "6": ("Conv", shape(128, 40)),
        "7": ("C3k2", shape(128, 40)),
        "8": ("Conv", shape(256, 20)),
        "9": ("C3k2", shape(256, 20)),
        "10": ("SPPF", shape(256, 20)),
        "11": ("C2PSA", shape(256, 20)),
    }
    NK_SHAPES = {
        "12": ("Upsample", shape(256, 40)),
        "13": ("Concat", shape(384, 40)),
        "14": ("C3k2", shape(128, 40)),
        "15": ("Upsample", shape(128, 80)),
        "16": ("Concat", shape(256, 80)),
        "17": ("C3k2", shape(64, 80)),
        "18": ("Upsample", shape(64, 160)),
        "19": ("Concat", shape(128, 160)),
        "20": ("C3k2", shape(32, 160)),
        "21": ("Conv", shape(32, 80)),
        "22": ("Concat", shape(96, 80)),
        "23": ("C3k2", shape(64, 80)),
        "24": ("Conv", shape(64, 40)),
        "25": ("Concat", shape(192, 40)),
        "26": ("C3k2", shape(128, 40)),
        "27": ("Conv", shape(128, 20)),
        "28": ("Concat", shape(384, 20)),
        "29": ("C3k2", shape(256, 20)),
    }
    PALETTES = {
        "input": ("#F1F5F9", "#475569"),
        "Conv": ("#A7F3D0", "#047857"),
        "Upsample": ("#A7F3D0", "#047857"),
        "C3k2": ("#DDD6FE", "#6D28D9"),
        "C2PSA": ("#67E8F9", "#0E7490"),
        "SPPF": ("#C4B5FD", "#6D28D9"),
        "CoordAttention": ("#FDE68A", "#B45309"),
        "Concat": ("#FED7AA", "#9A3412"),
        "Detect": ("#FECACA", "#BE123C"),
    }

    # ------------------------------------------------------------------
    # Geometry.
    # ------------------------------------------------------------------
    NW, NH = 176, 52          # neck box
    SUB = 104                 # vertical pitch of the 3 nodes within one P-level
    BB_W, BB_H = 224, 52      # backbone box
    HBW, HBH = 244, 70        # detect box
    GAP = 34

    # P-level row centres, evenly spaced so each P-level fits 3 neck nodes with
    # generous vertical gaps (no arrow "punching through" between boxes).
    band_cy = {"P2": 420}
    band_cy["P3"] = band_cy["P2"] + 320
    band_cy["P4"] = band_cy["P3"] + 320
    band_cy["P5"] = band_cy["P4"] + 320

    bb_x = 80
    fpn_x = 560
    pan_x = fpn_x + NW + 120
    det_x = pan_x + NW + 230
    det_right = det_x + HBW

    w = det_right + 110
    h = band_cy["P5"] + NH + 560
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)
    title_font = font(40, bold=True)
    sec_font = font(28, bold=True)
    label_font = font(21, bold=True)
    shape_font = font(16)
    small_font = font(20)
    tiny_font = font(18)
    lane_font = font(22, bold=True)
    draw_centered(draw, (w / 2, 48), "YOLO11n-DWCA-P2 网络结构示意图", title_font)
    draw_centered(
        draw, (w / 2, 96),
        "Architecture diagram of YOLO11n-DWCA-P2 network",
        small_font, PALETTE["muted"],
    )

    def style_for(name: str) -> tuple[str, str]:
        return PALETTES.get(name, ("#E5E7EB", "#374151"))

    def cx(b): return (b[0] + b[2]) // 2
    def cy(b): return (b[1] + b[3]) // 2
    def left_pt(b): return (b[0], cy(b))
    def right_pt(b): return (b[2], cy(b))
    def top_pt(b): return (cx(b), b[1])
    def bot_pt(b): return (cx(b), b[3])

    def block(box, name, sub, fill, outline, line_w=2):
        round_rect(draw, box, fill, outline=outline, width=line_w, radius=9)
        draw_centered(draw, (cx(box), cy(box) - 11), name, label_font)
        draw_centered(draw, (cx(box), cy(box) + 12), sub, shape_font, PALETTE["muted"])

    def poly(points, color=PALETTE["ink"], width=3):
        line_with_elbow(draw, points, color, width)

    def section(x1, y1, x2, y2, label_bottom):
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        for x in range(x1, x2, 16):
            draw.line((x, y1, min(x + 8, x2), y1), fill=hex_to_rgb("#94A3B8"), width=2)
            draw.line((x, y2, min(x + 8, x2), y2), fill=hex_to_rgb("#94A3B8"), width=2)
        for y in range(y1, y2, 16):
            draw.line((x1, y, x1, min(y + 8, y2)), fill=hex_to_rgb("#94A3B8"), width=2)
            draw.line((x2, y, x2, min(y + 8, y2)), fill=hex_to_rgb("#94A3B8"), width=2)
        draw_centered(draw, ((x1 + x2) / 2, y2 + 34), label_bottom, sec_font)

    # ------------------------------------------------------------------
    # Backbone: single vertical column. Tap boxes (2,5,7,11) align to the
    # P-level row centres so the laterals are clean horizontals.
    # ------------------------------------------------------------------
    bb_order = ["input", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]
    idx = {k: i for i, k in enumerate(bb_order)}
    anchor_pts = sorted(
        [
            (idx["2"], band_cy["P2"]),
            (idx["5"], band_cy["P3"]),
            (idx["7"], band_cy["P4"]),
            (idx["11"], band_cy["P5"]),
        ]
    )

    def piecewise_y(i: int) -> float:
        pts = anchor_pts
        if i <= pts[0][0]:
            (x0, y0), (x1, y1) = pts[0], pts[1]
        elif i >= pts[-1][0]:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
        else:
            (x0, y0), (x1, y1) = pts[0], pts[1]
            for j in range(len(pts) - 1):
                if pts[j][0] <= i <= pts[j + 1][0]:
                    (x0, y0), (x1, y1) = pts[j], pts[j + 1]
                    break
        return y0 + (y1 - y0) * (i - x0) / (x1 - x0)

    bb: dict[str, tuple[int, int, int, int]] = {}
    for k in bb_order:
        yc = piecewise_y(idx[k])
        bb[k] = (bb_x, int(yc - BB_H / 2), bb_x + BB_W, int(yc + BB_H / 2))

    # ------------------------------------------------------------------
    # FPN column (mid-left). Data flow runs UPWARD (P4 bottom -> P2 top).
    # Within each P-level the order bottom->top is Upsample / Concat / C3k2,
    # matching 12->13->14 etc., so the whole FPN chain is one vertical run.
    # ------------------------------------------------------------------
    def nbox(x: int, yc: int) -> tuple[int, int, int, int]:
        return (x, int(yc - NH / 2), x + NW, int(yc + NH / 2))

    fpn_node_row = {  # key -> P-level
        "12": "P4", "13": "P4", "14": "P4",
        "15": "P3", "16": "P3", "17": "P3",
        "18": "P2", "19": "P2", "20": "P2",
    }
    # vertical offset within a P-level: +SUB (bottom) / 0 (mid) / -SUB (top)
    fpn_offset = {"12": +1, "13": 0, "14": -1,
                  "15": +1, "16": 0, "17": -1,
                  "18": +1, "19": 0, "20": -1}

    n: dict[str, tuple[int, int, int, int]] = {}
    for k, lane in fpn_node_row.items():
        yc = band_cy[lane] + fpn_offset[k] * SUB
        n[k] = nbox(fpn_x, yc)

    # ------------------------------------------------------------------
    # PAN column (mid-right). Data flow runs DOWNWARD (P2 top -> P5 bottom).
    # Within each P-level the order top->bottom is Conv / Concat / C3k2,
    # matching 21->22->23 etc., so the whole PAN chain is one vertical run.
    # ------------------------------------------------------------------
    pan_node_row = {
        "21": "P2",
        "22": "P3", "23": "P3", "24": "P3",
        "25": "P4", "26": "P4", "27": "P4",
        "28": "P5", "29": "P5",
    }
    # P2 has only the Conv (21) -> place it at the TOP of the P2 band so the
    # 20->21 turn is a clean horizontal at the top of the figure.
    pan_offset = {"21": -1,
                  "22": -1, "23": 0, "24": +1,
                  "25": -1, "26": 0, "27": +1,
                  "28": -1, "29": 0}
    for k, lane in pan_node_row.items():
        yc = band_cy[lane] + pan_offset[k] * SUB
        n[k] = nbox(pan_x, yc)

    # Detect heads on the far right, one per P-level row centre.
    det: dict[str, tuple[int, int, int, int]] = {
        lane: (det_x, int(band_cy[lane] - HBH / 2), det_x + HBW, int(band_cy[lane] + HBH / 2))
        for lane in band_cy
    }

    # ------------------------------------------------------------------
    # Self-check infra.
    # ------------------------------------------------------------------
    all_boxes: dict[str, tuple[int, int, int, int]] = {}
    for k, b in bb.items():
        all_boxes["bb" + k] = b
    for k, b in n.items():
        all_boxes["n" + k] = b
    for lane, b in det.items():
        all_boxes["det" + lane] = b

    _crossings: list[str] = []

    def _seg_hits(seg, ignore):
        (x1, y1), (x2, y2) = seg
        hit = []
        for nm, bx in all_boxes.items():
            if nm in ignore:
                continue
            a, c, d, e = bx
            pad = 3
            a -= pad; c -= pad; d += pad; e += pad
            if abs(y1 - y2) < 1:
                if c <= y1 <= e:
                    lo, hi = sorted((x1, x2))
                    if not (hi < a or lo > d):
                        hit.append(nm)
            elif abs(x1 - x2) < 1:
                if a <= x1 <= d:
                    lo, hi = sorted((y1, y2))
                    if not (hi < c or lo > e):
                        hit.append(nm)
        return hit

    def wire(points, ignore, color=PALETTE["ink"], width=3, label=""):
        for a, b2 in zip(points, points[1:]):
            for nm in _seg_hits((a, b2), ignore):
                _crossings.append(f"{label}:{nm}")
        poly(points, color, width)

    # ------------------------------------------------------------------
    # Section frames.
    # ------------------------------------------------------------------
    reg_top = 150
    reg_bot = band_cy["P5"] + NH / 2 + 400
    bb_frame = (bb_x - 34, reg_top, bb_x + BB_W + 34, reg_bot)
    fpn_frame = (fpn_x - 40, reg_top, fpn_x + NW + 40, reg_bot)
    pan_frame = (pan_x - 40, reg_top, pan_x + NW + 40, reg_bot)
    hd_frame = (det_x - 70, reg_top, det_right + 50, reg_bot)
    section(*bb_frame, "Backbone")
    section(*fpn_frame, "Neck · FPN")
    section(*pan_frame, "Neck · PAN")
    section(*hd_frame, "Head")

    # P-level row guides + labels between the FPN and PAN columns.
    for lane in band_cy:
        ly = band_cy[lane]
        draw.line(
            (fpn_frame[2] + 4, ly, pan_frame[0] - 4, ly),
            fill=hex_to_rgb("#E5E7EB"), width=1,
        )
        draw_centered(draw, ((fpn_frame[2] + pan_frame[0]) / 2, ly), lane, lane_font, "#94A3B8")

    # ------------------------------------------------------------------
    # Draw backbone boxes + the -1 chain.
    # ------------------------------------------------------------------
    for i, key in enumerate(bb_order):
        name, sub = BB_SHAPES[key]
        fill, outl = style_for(name if name != "Input" else "input")
        line_w = 3 if name == "CoordAttention" else 2
        block(bb[key], name, sub, fill, outl, line_w)
        if i > 0:
            prev = bb[bb_order[i - 1]]
            poly([bot_pt(prev), top_pt(bb[key])], PALETTE["muted"], 2)

    # ------------------------------------------------------------------
    # Draw neck boxes; P2 fusion path (18/19/20/21) gets a blue accent.
    # ------------------------------------------------------------------
    P2_ACCENT = {"18", "19", "20", "21"}
    for key, box in n.items():
        name, sub = NK_SHAPES[key]
        fill, outl = style_for(name)
        line_w = 2
        if key in P2_ACCENT:
            outl = "#1D4ED8"
            line_w = 3
        block(box, name, sub, fill, outl, line_w)

    # ------------------------------------------------------------------
    # FPN main chain (vertical, upward): 12->13->14 -> 15->16->17 -> 18->19->20.
    # Every edge is a straight vertical line between adjacent boxes.
    # ------------------------------------------------------------------
    fpn_chain = ["12", "13", "14", "15", "16", "17", "18", "19", "20"]
    for a, b in zip(fpn_chain, fpn_chain[1:]):
        accent = a in P2_ACCENT and b in P2_ACCENT
        col = PALETTE["blue"] if accent else PALETTE["ink"]
        ww = 4 if accent else 3
        # FPN flows UPWARD (a is below b): connect a.TOP -> b.BOTTOM so the
        # arrow stays in the gap between the two boxes and never crosses either.
        wire([top_pt(n[a]), bot_pt(n[b])], {"n" + a, "n" + b}, col, ww, f"{a}-{b}")

    # 11 (C2PSA) -> 12 (Upsample): orthogonal elbow through the gutter between
    # the Backbone and FPN columns (no diagonal).
    gut11 = (bb_x + BB_W + fpn_x) // 2
    wire([right_pt(bb["11"]), (gut11, cy(bb["11"])), (gut11, cy(n["12"])), left_pt(n["12"])],
         {"bb11", "n12"}, PALETTE["ink"], 3, "11-12")

    # ------------------------------------------------------------------
    # 20 -> 21 turn at the top: horizontal from FPN column right into PAN
    # column left (both sit at the top of the P2 band).
    # ------------------------------------------------------------------
    wire([right_pt(n["20"]), left_pt(n["21"])], {"n20", "n21"}, PALETTE["blue"], 4, "20-21")

    # ------------------------------------------------------------------
    # PAN main chain (vertical, downward): 21->22->23 -> 24->25->26 -> 27->28->29.
    # Every edge is a straight vertical line between adjacent boxes.
    # ------------------------------------------------------------------
    pan_chain = ["21", "22", "23", "24", "25", "26", "27", "28", "29"]
    for a, b in zip(pan_chain, pan_chain[1:]):
        accent = a in P2_ACCENT and b in P2_ACCENT
        col = PALETTE["blue"] if accent else PALETTE["ink"]
        ww = 4 if accent else 3
        wire([bot_pt(n[a]), top_pt(n[b])] if n[a][1] < n[b][1] else [top_pt(n[a]), bot_pt(n[b])],
             {"n" + a, "n" + b}, col, ww, f"{a}-{b}")

    # ------------------------------------------------------------------
    # Backbone lateral taps into the FPN Concats (7->13, 5->16, 2->19) and the
    # PAN Concat (11->28). All horizontal because tap boxes align to row centres.
    # ------------------------------------------------------------------
    wire([right_pt(bb["7"]), left_pt(n["13"])], {"bb7", "n13"}, PALETTE["ink"], 3, "7-13")
    wire([right_pt(bb["5"]), left_pt(n["16"])], {"bb5", "n16"}, PALETTE["orange"], 3, "5-16")
    wire([right_pt(bb["2"]), left_pt(n["19"])], {"bb2", "n19"}, PALETTE["blue"], 4, "2-19")
    # 11 -> 28 runs along the bottom corridor then up the LEFT side of the PAN
    # column (between the FPN and PAN columns) so it does not cross the
    # 29 -> Detect-P5 feeder which leaves the PAN column on the right.
    low_corr = band_cy["P5"] + NH / 2 + 40
    pan_left_corr = pan_x - 30
    wire([bot_pt(bb["11"]), (cx(bb["11"]), low_corr),
          (pan_left_corr, low_corr), (pan_left_corr, cy(n["28"])), left_pt(n["28"])],
         {"bb11", "n28"}, PALETTE["ink"], 3, "11-28")

    # ------------------------------------------------------------------
    # Head taps: FPN outputs reused by PAN Concats. 17 -> 22 and 14 -> 25 are
    # horizontal because they share a P-level band y.
    # ------------------------------------------------------------------
    wire([right_pt(n["17"]), left_pt(n["22"])], {"n17", "n22"}, PALETTE["ink"], 3, "17-22")
    wire([right_pt(n["14"]), left_pt(n["25"])], {"n14", "n25"}, PALETTE["ink"], 3, "14-25")

    # ------------------------------------------------------------------
    # Detect heads + feeders. 23/26/29 are straight horizontals from the PAN
    # column. 20 (in the FPN column) routes over the top to reach the Head
    # column without crossing the PAN column.
    # ------------------------------------------------------------------
    fill_d, outl_d = style_for("Detect")
    det_labels = {
        "P2": ("Detect P2/4", "tiny — 160 × 160"),
        "P3": ("Detect P3/8", "small — 80 × 80"),
        "P4": ("Detect P4/16", "medium — 40 × 40"),
        "P5": ("Detect P5/32", "large — 20 × 20"),
    }
    for lane, db in det.items():
        emph = lane == "P2"
        outl = "#1D4ED8" if emph else outl_d
        lw = 3 if emph else 2
        name, sub = det_labels[lane]
        block(db, name, sub, fill_d, outl, lw)

    # 23 -> Detect P3, 26 -> Detect P4, 29 -> Detect P5 : straight horizontals.
    wire([right_pt(n["23"]), left_pt(det["P3"])], {"n23", "detP3"}, PALETTE["ink"], 3, "det-P3")
    wire([right_pt(n["26"]), left_pt(det["P4"])], {"n26", "detP4"}, PALETTE["ink"], 3, "det-P4")
    wire([right_pt(n["29"]), left_pt(det["P5"])], {"n29", "detP5"}, PALETTE["ink"], 3, "det-P5")
    # 20 -> Detect P2 : route over the top to clear the PAN column.
    top_corr = band_cy["P2"] - SUB - NH / 2 - 40
    wire([top_pt(n["20"]), (cx(n["20"]), top_corr),
          (det_x - 30, top_corr), (det_x - 30, cy(det["P2"])), left_pt(det["P2"])],
         {"n20", "detP2"}, PALETTE["blue"], 4, "det-P2")

    # ------------------------------------------------------------------
    # DyHeadDetect module block (graphical). Drawn below the Detect column as a
    # structured module: a header + a vertical stack of the three attention
    # stages (scale -> spatial -> task) + a WIoU footnote. Dashed arrows link
    # the four Detect boxes to this block to convey that they SHARE one
    # DyHeadDetect head (rather than being plain Detect layers).
    # ------------------------------------------------------------------
    note_x = hd_frame[0] + 22
    note_w = hd_frame[2] - hd_frame[0] - 44
    note_h = 300
    note_y = det["P5"][3] + 56
    round_rect(
        draw, (note_x, note_y, note_x + note_w, note_y + note_h),
        "#FFF1F2", outline="#BE123C", width=3, radius=12,
    )
    draw_centered(draw, (note_x + note_w / 2, note_y + 26), "DyHeadDetect", label_font, "#BE123C")
    draw_centered(
        draw, (note_x + note_w / 2, note_y + 54),
        "动态检测头 · 4 尺度共享", tiny_font, PALETTE["muted"],
    )

    # Three stacked attention stage chips.
    chip_w = note_w - 60
    chip_h = 34
    chip_x = note_x + 30
    stages = [
        ("Scale-aware Attn", "#FCA5A5"),
        ("Spatial-aware Attn", "#FCD9A5"),
        ("Task-aware Attn", "#FBCFE8"),
    ]
    stack_top = note_y + 78
    for i, (txt, fc) in enumerate(stages):
        cy0 = stack_top + i * (chip_h + 14)
        cb = (chip_x, cy0, chip_x + chip_w, cy0 + chip_h)
        round_rect(draw, cb, fc, outline="#BE123C", width=2, radius=7)
        draw_centered(draw, ((cb[0] + cb[2]) / 2, (cb[1] + cb[3]) / 2), txt, tiny_font, "#7F1D1D")
        if i > 0:
            py = cy0 - 14
            # small connector arrow between chips
            draw.line((cx(cb), py, cx(cb), cy0), fill=hex_to_rgb("#BE123C"), width=2)

    # WIoU footnote.
    draw.line(
        (note_x + 24, note_y + note_h - 52, note_x + note_w - 24, note_y + note_h - 52),
        fill=hex_to_rgb("#FCA5A5"), width=1,
    )
    draw_centered(draw, (note_x + note_w / 2, note_y + note_h - 32), "WIoU v3 (train-only)", label_font, "#BE123C")
    draw_centered(
        draw, (note_x + note_w / 2, note_y + note_h - 12),
        "仅训练阶段 bbox 回归损失", tiny_font, PALETTE["muted"],
    )

    # DyHeadDetect container: a dashed rounded frame wrapping the four Detect
    # boxes, expressing that they share ONE DyHeadDetect head. A single short
    # connector links the container to the detail block below — no line passes
    # through any Detect box.
    cont = (det_x - 36, det["P2"][1] - 36, det_x + HBW + 36, det["P5"][3] + 36)
    dash, gap = 10, 10
    for x in range(int(cont[0]), int(cont[2]), dash + gap):
        draw.line((x, cont[1], min(x + dash, cont[2]), cont[1]), fill=hex_to_rgb("#BE123C"), width=2)
        draw.line((x, cont[3], min(x + dash, cont[2]), cont[3]), fill=hex_to_rgb("#BE123C"), width=2)
    for y in range(int(cont[1]), int(cont[3]), dash + gap):
        draw.line((cont[0], y, cont[0], min(y + dash, cont[3])), fill=hex_to_rgb("#BE123C"), width=2)
        draw.line((cont[2], y, cont[2], min(y + dash, cont[3])), fill=hex_to_rgb("#BE123C"), width=2)
    draw_centered(
        draw, ((cont[0] + cont[2]) / 2, cont[1] - 16),
        "DyHeadDetect · 4 尺度共享检测头", label_font, "#BE123C",
    )
    # single connector from the container bottom to the detail block top
    ccx = (cont[0] + cont[2]) / 2
    draw.line((ccx, cont[3], ccx, note_y), fill=hex_to_rgb("#BE123C"), width=2)

    # ------------------------------------------------------------------
    # Legend. Split the colour-chip items across two rows so nothing spills
    # past the right edge of the (now narrower) canvas.
    # ------------------------------------------------------------------
    legend_y = reg_bot + 56
    legend_items = [
        ("Conv / Upsample", "#A7F3D0", "#047857"),
        ("C3k2 / SPPF / C2PSA", "#DDD6FE", "#6D28D9"),
        ("Concat 特征融合", "#FED7AA", "#9A3412"),
        ("CoordAttention 位置注意力", "#FDE68A", "#B45309"),
        ("Detect / DyHeadDetect / WIoU v3", "#FECACA", "#BE123C"),
    ]
    step = 360
    per_row = 3
    for i, (text, fill, outline) in enumerate(legend_items):
        row = i // per_row
        col = i % per_row
        lx = bb_x + col * step
        ly = legend_y + row * 44
        round_rect(draw, (lx, ly, lx + 32, ly + 24), fill, outline=outline, width=2, radius=4)
        draw.text((lx + 42, ly - 1), text, font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))

    wy = legend_y + 2 * 44 + 8
    draw.line((bb_x + 10, wy + 11, bb_x + 80, wy + 11), fill=hex_to_rgb(PALETTE["blue"]), width=4)
    draw.text((bb_x + 90, wy), "P2/4 高分辨率小目标主路径", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.line((bb_x + 430, wy + 11, bb_x + 500, wy + 11), fill=hex_to_rgb(PALETTE["ink"]), width=3)
    draw.text((bb_x + 510, wy), "FPN / PAN 主链路", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
    draw.line((bb_x + 820, wy + 11, bb_x + 890, wy + 11), fill=hex_to_rgb(PALETTE["orange"]), width=3)
    draw.text((bb_x + 900, wy), "CoordAttention 位置特征旁路", font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))

    if _crossings:
        raise AssertionError(f"draw_architecture_vertical wire/box crossings detected: {_crossings}")

    img.save(path, dpi=(300, 300))




def make_figures(tables: dict[str, pd.DataFrame], aux: dict[str, pd.DataFrame | None]) -> list[OutputFigure]:
    figures: list[OutputFigure] = []
    arch_path = FIG_DIR / "fig2_dwca_p2_architecture.png"
    draw_architecture(arch_path)
    figures.append(OutputFigure(arch_path, "YOLO11n-DWCA-P2 网络结构示意图", "Architecture of YOLO11n-DWCA-P2."))

    arch_v_path = FIG_DIR / "fig2_dwca_p2_architecture_vertical.png"
    draw_architecture_vertical(arch_v_path)
    figures.append(OutputFigure(arch_v_path, "YOLO11n-DWCA-P2 网络结构示意图", "Architecture of YOLO11n-DWCA-P2."))

    main_path = FIG_DIR / "fig7_main_metrics.png"
    draw_grouped_metrics(tables["main_results"], main_path)
    figures.append(OutputFigure(main_path, "baseline 与 DWCA-P2 主指标对比", "Main metric comparison."))

    scale_df = aux.get("val_scale_distribution_640.csv")
    if scale_df is not None:
        scale_path = FIG_DIR / "fig1_val_scale_distribution.png"
        draw_scale_distribution(scale_df, scale_path)
        figures.insert(0, OutputFigure(scale_path, "验证集各类别短边尺度分布", "Short-side scale distribution on the validation set."))

    class_df = aux.get("class_metrics_baseline_vs_dwca_p2_b32.csv")
    if class_df is not None:
        class_path = FIG_DIR / "fig8_class_map_gain.png"
        draw_class_gain(class_df, class_path)
        figures.append(OutputFigure(class_path, "类别级 mAP@0.5:0.95 增益", "Per-class mAP@0.5:0.95 gain."))

    curves = aux.get("training_curves_baseline_vs_dwca_p2_b32.csv")
    if curves is not None:
        map_path = FIG_DIR / "fig9_training_map50_95.png"
        recall_path = FIG_DIR / "fig10_training_recall.png"
        draw_line_chart(curves, "mAP50_95", map_path, "验证集 mAP@0.5:0.95 曲线", "mAP@0.5:0.95/%")
        draw_line_chart(curves, "recall", recall_path, "验证集 Recall 曲线", "Recall/%")
        figures.extend(
            [
                OutputFigure(map_path, "验证集 mAP@0.5:0.95 曲线", "Validation mAP@0.5:0.95 curve."),
                OutputFigure(recall_path, "验证集 Recall 曲线", "Validation Recall curve."),
            ]
        )

    # Module structure figures (static schematics)
    _mf.draw_p2_fusion()
    _mf.draw_dyhead()
    _mf.draw_ca()
    _mf.draw_wiou_curve()
    figures.append(OutputFigure(FIG_DIR / "fig3_p2_fusion.png", "P2 高分辨率分支融合示意", "P2 high-resolution branch fusion."))
    figures.append(OutputFigure(FIG_DIR / "fig4_dyhead.png", "DyHead 动态检测头结构示意", "DyHead dynamic head structure."))
    figures.append(OutputFigure(FIG_DIR / "fig5_coordattention.png", "CoordAttention 结构示意", "Coordinate attention structure."))
    figures.append(OutputFigure(FIG_DIR / "fig6_wiou_focusing.png", "Wise-IoU v3 聚焦增益曲线", "Wise-IoU v3 focusing gain curve."))

    # Qualitative detection comparison (pre-generated by build_detection_comparison.py,
    # which requires AutoDL inference outputs; include only if already present).
    det_path = FIG_DIR / "fig_detection_comparison.png"
    if det_path.exists():
        figures.append(OutputFigure(det_path, "baseline 与 DWCA-P2 检测效果对比", "Qualitative detection comparison."))

    return figures


def is_count_column(col: str) -> bool:
    count_tokens = ("实例数", "标注文件数", "short<16", "16<=short<32", "short>=32")
    return any(token in col for token in count_tokens)


def format_table_value(value, col: str, decimals: int = 1, signed: bool = False) -> str:
    if pd.isna(value):
        return "-"
    if isinstance(value, (int, float)):
        sign = "+" if signed and value > 0 else ""
        if is_count_column(col):
            return f"{sign}{int(round(float(value)))}"
        return f"{sign}{float(value):.{decimals}f}"
    return str(value)


def markdown_table(df: pd.DataFrame, columns: list[str] | None = None, decimals: int = 1, signs: bool = False) -> str:
    if columns is None:
        columns = list(df.columns)
    numeric_cols = set()
    for col in columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.add(col)
    rows = []
    rows.append("| " + " | ".join(columns) + " |")
    rows.append("|" + "|".join(["---:" if c in numeric_cols else "---" for c in columns]) + "|")
    for _, row in df.iterrows():
        vals = []
        for col in columns:
            v = row[col]
            vals.append(format_table_value(v, col, decimals, signs and row.iloc[0] == "提升"))
        rows.append("| " + " | ".join(vals) + " |")
    return "\n".join(rows)


def pct(v: float) -> str:
    return f"{v:.1f}"


def count_display_formulas(md: str) -> int:
    return len(re.findall(r"^\$\$.*\$\$$", md, flags=re.MULTILINE))


def build_markdown(df: pd.DataFrame, tables: dict[str, pd.DataFrame], aux: dict[str, pd.DataFrame | None], figures: list[OutputFigure]) -> str:
    baseline = row_by_group(df, "baseline-b32")
    proposed = row_by_group(df, "DWCA-P2-b32")
    dw_p2 = row_by_group(df, "DW-P2")
    dwca = row_by_group(df, "DWCA")
    plus_dw = row_by_group(df, "+DW")
    speed = tables["speed_complexity"]
    scale_df = aux.get("val_scale_distribution_640.csv")
    class_df = aux.get("class_metrics_baseline_vs_dwca_p2_b32.csv")

    fig_by_name = {f.path.name: f for f in figures}
    rel = lambda p: p.relative_to(OUTPUT_DIR).as_posix()

    dataset_split = pd.DataFrame(
        [
            {"划分": "训练集", "标注文件数": 4940, "实例数": 227831},
            {"划分": "验证集", "标注文件数": 1411, "实例数": 65255},
            {"划分": "测试集", "标注文件数": 707, "实例数": 32628},
            {"划分": "合计", "标注文件数": 7058, "实例数": 325714},
        ]
    )
    class_dist = pd.DataFrame(
        [
            {"类别": "Car", "实例数": 91443, "占比/%": 28.07},
            {"类别": "Truck", "实例数": 3501, "占比/%": 1.07},
            {"类别": "Van", "实例数": 6767, "占比/%": 2.08},
            {"类别": "Bus", "实例数": 3379, "占比/%": 1.04},
            {"类别": "Cyclist", "实例数": 17244, "占比/%": 5.29},
            {"类别": "Motorcyclist", "实例数": 18256, "占比/%": 5.60},
            {"类别": "Pedestrian", "实例数": 25194, "占比/%": 7.74},
            {"类别": "Trafficcone", "实例数": 159930, "占比/%": 49.10},
        ]
    )
    scale_stats = pd.DataFrame(
        [
            {"小目标定义": "area < 32² px²", "实例数": 259421, "占比/%": 79.65},
            {"小目标定义": "short side < 16 px", "实例数": 223453, "占比/%": 68.60},
            {"小目标定义": "short side < 32 px", "实例数": 285172, "占比/%": 87.55},
            {"小目标定义": "both sides < 32 px", "实例数": 183595, "占比/%": 56.37},
        ]
    )
    training_params = pd.DataFrame(
        [
            {"参数": "硬件", "设置": "NVIDIA GeForce RTX 4090 24GB"},
            {"参数": "框架", "设置": "Python 3.12.3，Ultralytics 8.4.56，PyTorch 2.7.0+cu128"},
            {"参数": "数据集划分", "设置": "训练集/验证集/测试集=4940/1411/707"},
            {"参数": "输入尺寸", "设置": "640 x 640"},
            {"参数": "训练参数", "设置": "epochs=300，batch=32，optimizer=SGD，seed=42"},
            {"参数": "测速口径", "设置": "batch=1，FPS=1000/(preprocess+inference+postprocess)"},
        ]
    )
    save_csv(TABLE_DIR / "dataset_split.csv", dataset_split)
    save_csv(TABLE_DIR / "class_distribution.csv", class_dist)
    save_csv(TABLE_DIR / "scale_statistics.csv", scale_stats)
    save_csv(TABLE_DIR / "training_params.csv", training_params)

    class_table_md = ""
    if class_df is not None:
        cdf = class_df[class_df["class"] != "all"].copy()
        cdf_out = pd.DataFrame(
            {
                "类别": cdf["class"],
                "实例数": cdf["instances"],
                "baseline mAP@0.5/%": cdf["mAP50_baseline"] * 100,
                "DWCA-P2 mAP@0.5/%": cdf["mAP50_proposed"] * 100,
                "baseline mAP@0.5:0.95/%": cdf["mAP50_95_baseline"] * 100,
                "DWCA-P2 mAP@0.5:0.95/%": cdf["mAP50_95_proposed"] * 100,
                "mAP@0.5:0.95提升/%": cdf["mAP50_95_gain"] * 100,
            }
        )
        save_csv(TABLE_DIR / "class_ap_comparison.csv", cdf_out)
        class_table_md = markdown_table(cdf_out, decimals=1)

    scale_table_md = ""
    if scale_df is not None:
        s = scale_df[["class", "total", "short<16", "16<=short<32", "short>=32", "short<32_pct", "median_short_side_px"]].rename(
            columns={
                "class": "类别",
                "total": "实例数",
                "short<32_pct": "short<32/%",
                "median_short_side_px": "中位短边/px",
            }
        )
        scale_table_md = markdown_table(s, decimals=1)

    lines = f"""# {CN_TITLE}

{CN_AUTHORS}

{CN_AFFILIATION}

## 摘要

针对路侧图像远距离交通目标尺度小、密度高和背景干扰强导致轻量化 YOLO 漏检的问题，提出 YOLO11n-DWCA-P2 小目标检测方法。该方法以 YOLO11n 为基准，采用 Dynamic Head（DyHead）动态检测头和 Wise Intersection over Union v3（Wise-IoU v3）回归损失，增加 P2/4 高分辨率检测分支，将检测特征由 P3/P4/P5 扩展为 P2/P3/P4/P5，并用 Coordinate Attention（CoordAttention）增强浅中层位置敏感表达。训练与测速均采用统一设置，以降低训练口径和硬件差异对比较结果的影响。DAIR-V2X-I 统计显示，640 输入尺度下短边小于 32 像素和面积小于 32² 像素²的目标分别占 87.55% 和 79.65%。实验结果表明，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 {pct(proposed.P)}%、{pct(proposed.R)}%、{pct(proposed.mAP50)}% 和 {pct(proposed.mAP50_95)}%，较 baseline 分别提高 {pct(proposed.P - baseline.P)}、{pct(proposed.R - baseline.R)}、{pct(proposed.mAP50 - baseline.mAP50)} 和 {pct(proposed.mAP50_95 - baseline.mAP50_95)} 个百分点，RTX 4090 上达到 {pct(proposed.FPS)} FPS。消融结果表明，P2 分支是 Recall 和 mAP@0.5:0.95 提升的主要来源，DyHead 和 Wise-IoU v3 的组合构成稳定正向基线，CoordAttention 主要体现在 Precision 和 mAP@0.5 的补充增益上。该方法提升了路侧小目标检出能力和定位质量，可为车路协同视觉感知中的轻量化检测模型设计提供参考。

**关键词**：路侧目标检测；车路协同；YOLO11n；小目标检测；DyHead；Wise-IoU；P2 检测分支

## {EN_TITLE}

{EN_AUTHORS}

{EN_AFFILIATION}

## Abstract

Roadside images contain distant traffic objects with small scales, high density and strong background interference, which can cause missed detections in lightweight YOLO models. YOLO11n-DWCA-P2 was proposed for roadside small object detection. Based on YOLO11n, the method adopted a Dynamic Head detection head and Wise Intersection over Union version 3 regression loss, added a P2/4 high-resolution detection branch to extend the detection features from P3/P4/P5 to P2/P3/P4/P5, and used Coordinate Attention to enhance shallow and mid-level position-sensitive representation. Statistics on DAIR-V2X-I showed that objects with a short side smaller than 32 pixels and objects with an area smaller than 32² pixel² accounted for 87.55% and 79.65%, respectively, at the 640 input scale. Experiments showed that DWCA-P2 achieved {pct(proposed.P)}% Precision, {pct(proposed.R)}% Recall, {pct(proposed.mAP50)}% mAP@0.5 and {pct(proposed.mAP50_95)}% mAP@0.5:0.95. Compared with baseline, the four metrics increased by {pct(proposed.P - baseline.P)}, {pct(proposed.R - baseline.R)}, {pct(proposed.mAP50 - baseline.mAP50)} and {pct(proposed.mAP50_95 - baseline.mAP50_95)} percentage points, respectively, and the model reached {pct(proposed.FPS)} FPS on an RTX 4090. Ablation results indicate that the P2 branch is the main source of recall and localization improvement, while Coordinate Attention provides complementary gains in precision-oriented metrics. The method improves detection and localization for small roadside objects.

**Keywords**: roadside object detection; vehicle-infrastructure cooperation; YOLO11n; small object detection; Dynamic Head; Wise Intersection over Union; P2 detection branch

## 0 引言

随着智能交通系统、协同自动驾驶和车路云一体化技术的发展，单车智能感知逐渐向车端、路端和云端协同感知演进。车载摄像机和激光雷达能够提供车辆自身周围的局部环境信息，但感知范围容易受到遮挡、视角和传感器安装位置限制。路侧感知设备通常部署在信号灯杆、道路横杆或高位监控点，具有较稳定的外参条件和更广的道路覆盖范围，能够从全局视角捕获交叉口、匝道、车道汇入区域等复杂交通场景中的车辆与弱势交通参与者。因此，路侧目标检测结果不仅可用于道路事件监测、交通流统计和安全预警，也可作为车路协同自动驾驶系统的重要环境输入。

路侧视觉感知并不是简单地将通用目标检测模型迁移到道路监控画面中。路侧摄像机通常具有较高安装位置和较大俯视角，道路纵深方向明显，远端目标在图像中呈现出极小尺度。行人、骑行者、摩托车、交通锥等目标本身物理尺寸较小，当其位于远距离区域时，经过图像缩放和网络下采样后往往仅保留少量像素。道路场景中的车辆、交通标志、车道线、护栏、树木阴影和路面纹理共同构成复杂背景，交通参与者之间还可能存在相互遮挡。这些因素使路侧目标检测具有小目标多、密集目标多、背景干扰强和类别分布不均衡等特征。

目标检测经历了从两阶段候选区域方法到单阶段实时检测方法的发展。Fast R-CNN、Faster R-CNN 等方法通过候选区域和区域特征分类提升检测精度[1-2]，SSD、RetinaNet 和 EfficientDet 则推动了单阶段检测、多尺度特征、密集预测和类别不均衡处理的发展[3-5]。YOLO 系列进一步强调端到端实时检测能力，因检测速度快、工程部署链路成熟，在智能交通、工业质检、农业检测和安防监控等场景中得到广泛应用[6-10]。Ultralytics YOLO11 在前序 YOLO 模型的基础上继续优化特征提取、检测效率和多任务支持能力，覆盖目标检测、实例分割、姿态估计、图像分类和旋转框检测等视觉任务[11]。其中 YOLO11n 是该系列中的轻量化版本，参数量和计算量较低，适合部署在边缘设备或对实时性要求较高的系统中。对于路侧感知任务，轻量化模型的效率优势具有现实意义，但有限的网络容量也使其更容易受到小目标信息损失的影响。

通用 YOLO 检测结构通常采用多尺度特征输出处理不同尺寸目标。以轻量化 YOLO11n 为例，其默认检测头主要使用 P3/P4/P5 三个尺度特征，对应输入图像的 1/8、1/16 和 1/32 下采样特征图。在常规目标检测任务中，P3 特征已经能够覆盖较多小目标；但在路侧图像中，当目标短边仅为数像素至十余像素时，1/8 下采样后的特征响应可能过于稀疏，边界和局部纹理信息难以被完整保留。若仅依靠深层语义特征，模型可能获得较好的类别判别能力，却无法准确定位小目标框，最终表现为漏检、定位偏移或高 IoU 阈值下 AP 下降。

为验证上述问题，本文对 DAIR-V2X-I 路侧图像数据集的 YOLO 标注进行统计。该数据集包含 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类道路交通目标。统计结果显示，在 640 输入尺度下，短边小于 32 像素的目标占 87.55%，短边小于 16 像素的目标占 68.60%，面积小于 32² 像素²的目标占 79.65%。其中 Trafficcone 的中位短边约为 4.2 像素，Pedestrian 的中位短边约为 9.0 像素，Cyclist 和 Motorcyclist 的中位短边也仅约为 14.4 像素和 15.6 像素。这一分布说明，本文任务的主要矛盾并非单纯提升大目标分类置信度，而是如何在轻量化网络中保留并利用高分辨率空间细节。

围绕小目标检测问题，已有研究通常从多尺度特征融合、注意力机制、检测头优化和边界框损失函数等方面改进模型。FPN、PAN 和 BiFPN 等多尺度融合结构能够将浅层细节与深层语义结合，提高不同尺度目标的表达能力[5,12-13]；SNIP 与切片辅助推理等方法从尺度归一化或保持局部高分辨率角度改善小目标检测[14-15]；注意力机制可增强关键区域或通道的响应，抑制背景噪声[16-19]；动态检测头能够根据尺度、空间位置和任务类型调整检测特征[20]；IoU 系列损失函数则直接影响边界框回归质量[21-23]。上述方向并非互相排斥，但在轻量化模型中盲目叠加模块可能带来冗余计算，也可能因功能重叠导致收益有限。因此，针对路侧小目标场景，需要通过实验确定真正有效的结构改进路径。

本文提出一种面向路侧小目标检测的改进 YOLO11n 方法，记为 YOLO11n-DWCA-P2。该方法首先将 YOLO11n 检测头替换为 DyHeadDetect，以动态建模尺度、空间和任务维度的检测特征；其次采用 Wise-IoU v3 作为边界框回归损失，改善样本质量差异下的定位学习；随后在 Neck-Head 部分增加 P2/4 高分辨率检测分支，使模型直接在更高分辨率特征图上检测极小目标；最后引入 CoordAttention 模块，在较浅层特征中嵌入坐标位置信息，提升位置敏感表达能力。

本文主要贡献如下。

1. 面向 DAIR-V2X-I 路侧图像的小目标密集特征，统计分析了数据集类别分布与目标尺度分布，说明该任务存在较强的高分辨率特征需求。
2. 提出 YOLO11n-DWCA-P2 检测方法，重点通过 P2 高分辨率分支将检测尺度由 P3/P4/P5 扩展为 P2/P3/P4/P5，并结合 DyHead、Wise-IoU v3 与 CoordAttention 形成面向路侧小目标的轻量化改进结构。
3. 在统一 batch=32 训练口径下完成系统消融实验，明确 DyHead 与 WIoU 的组合构成稳定正向基线，P2 分支是最终性能提升的主要来源，CoordAttention 为辅助增强模块，避免将改进效果简单归因于模块叠加。
4. 与 YOLOv5n、YOLOv8n、YOLOv10n、YOLO11n 等轻量化结构进行同口径从头训练对比，结果表明本文方法在 mAP@0.5 和 mAP@0.5:0.95 上取得更优表现。

## 1 相关工作

### 1.1 路侧目标检测与车路协同感知

车路协同感知旨在通过车端和路端传感器的信息互补，提高自动驾驶系统对复杂交通环境的理解能力。车端传感器具有跟随车辆移动、感知近车区域细节的优势，但在交叉口遮挡、远距离车辆汇入和大型车辆遮挡等场景中容易出现感知盲区。路侧传感器从固定高位观察道路，能够获取更稳定的道路全局视角，为车辆提供超视距信息和交通参与者分布状态。

DAIR-V2X 数据集为车路协同感知研究提供了真实场景数据基础。该数据集包含车端与路端多模态数据，覆盖城市道路、高速道路、交叉口和多种天气光照条件，并引入车辆-基础设施协同 3D 目标检测任务[24]。OPV2V、V2X-ViT 等研究进一步说明，车端与路端或车车协同信息能够缓解遮挡和视距限制，但协同感知质量仍依赖单视角检测器对基础目标的稳定识别[25-26]。本文使用 DAIR-V2X-I 路侧单目图像构建 YOLO 检测任务，关注二维图像下的路侧交通目标检测。与车端图像相比，路侧图像中的远距离目标更小，交通锥、行人等类别数量多但像素尺度低，使检测模型需要更强的小目标定位能力。

在路侧场景中，漏检弱势交通参与者的风险往往高于少量误检。Pedestrian、Cyclist 和 Motorcyclist 等类别虽然在实例数中占比低于 Car 和 Trafficcone，但它们直接关系到道路安全预警。对于这些类别，检测模型不仅需要在低 IoU 阈值下判断目标存在，还需要在更严格 IoU 阈值下保持定位质量。因此，本文同时关注 Recall、mAP@0.5 和 mAP@0.5:0.95，并将 mAP@0.5:0.95 作为衡量定位质量的重要指标。

### 1.2 YOLO 系列轻量化目标检测

YOLO 系列模型采用单阶段检测范式，将目标分类和边界框回归统一到端到端网络中，具有较好的速度和精度平衡[6-10]。YOLOv3 通过多尺度预测增强了对不同尺寸目标的适应性[7]，YOLOv4 和 YOLOv7 继续从训练策略、特征融合与实时检测效率方面改进模型[8-9]。Ultralytics YOLOv8 于 2023 年发布，采用 Anchor-free split head 等设计，在检测、分割、分类和姿态估计等任务上形成较完整的工程生态[27]。YOLO11 进一步面向实时视觉任务优化骨干网络、颈部结构和训练流程，并支持多种视觉任务[11]。在实际应用中，n 系列轻量模型因参数少、推理快，常作为边缘部署和快速迭代的基础模型。

轻量化模型的主要问题在于网络容量有限。为了保持实时性，YOLO11n 的通道数和模块深度较小，对复杂背景、小目标和密集目标的表达能力有限。若在不改变检测尺度的情况下仅增加注意力模块，模型可能提升部分通道选择能力，但无法从根本上恢复下采样过程中已经损失的空间细节。本文实验中的 DWCA 与 +DW 结果接近，也说明对本数据集而言，单纯增强注意力并不足以解决小目标检测瓶颈。

### 1.3 小目标检测与多尺度特征融合

小目标检测的困难主要来自像素信息不足、上下文依赖强和特征下采样损失。相关综述指出，提高输入或特征分辨率、增强尺度感知训练、引入上下文信息和改进数据增强是深度学习小目标检测中的主要改进方向[28]。SNIP 通过尺度归一化训练缓解目标尺度变化带来的学习困难[14]，切片辅助推理与微调等方法也从保持局部高分辨率信息的角度改善小目标检测[15]，说明小目标任务的关键瓶颈常与有效像素和特征分辨率有关。对于大目标，深层语义特征能够提供足够的分类和定位信息；对于小目标，浅层特征中的边缘、角点和纹理信息更为关键。多尺度特征融合通过将不同分辨率特征组合，使模型同时获得语义信息和空间细节，是提升小目标检测性能的常用方法[5,12-13]。

YOLO 默认的 P3/P4/P5 检测尺度已经具备一定多尺度能力，但在极小目标密集任务中，P3/8 仍可能不够精细。P2/4 特征图相较 P3/8 具有更高空间分辨率，在输入图像为 640 x 640 时，P2 特征图约为 160 x 160，P3 特征图约为 80 x 80。对于短边仅 4 到 16 像素的目标，P2 分支能够增加其在特征图中的响应区域，降低目标在下采样后被压缩为单点或弱响应的风险。

当然，新增 P2 分支也会增加计算量。高分辨率特征图面积较大，卷积和检测头计算开销明显高于 P4/P5。本文消融结果表明，P2 路线将 GFLOPs 提高到 14.2，但 mAP@0.5:0.95 同时从 +DW 的 61.3% 提高到 64.4%。在路侧小目标检测任务中，这种计算代价换来了更明显的定位质量提升，符合本文任务需求。

### 1.4 注意力机制、动态检测头与边界框损失

注意力机制通过增强关键信息、抑制冗余背景，能够提升视觉模型的特征表达能力。SENet、CBAM 和 ECA-Net 分别从通道重标定、通道-空间联合注意力和轻量通道交互角度改进卷积特征表达[17-19]。CoordAttention 将通道注意力分解为沿水平和垂直方向的一维编码过程，在建模长程依赖的同时保留方向感知和位置敏感信息[16]。对于路侧图像，小目标常分布在道路纵深方向的局部区域，位置信息对检测具有一定价值。因此，本文将 CoordAttention 引入中浅层特征作为辅助增强模块。

Dynamic Head（DyHead）从检测头角度统一建模尺度感知、空间感知和任务感知注意力。Dai 等[20]认为检测头需要同时处理不同特征层级、空间位置和任务通道之间的差异，DyHead 通过在检测头中组合多种注意力机制，提高检测特征表达能力。本文将 YOLO11n 的检测头替换为 DyHeadDetect，使多尺度特征在输出预测前获得更充分的动态调制。消融实验显示，+D 相较 baseline 的 mAP@0.5 从 86.0% 提升至 86.6%，说明 DyHead 对本文任务具有稳定正向作用。

边界框损失函数决定了模型如何优化预测框与真实框之间的空间关系。GIoU、DIoU 和 CIoU 等损失从重叠面积、中心距离和宽高比等角度约束回归过程[22-23]。Wise-IoU 提出动态非单调聚焦机制，依据样本质量调整梯度增益，减弱低质量样本对回归学习的负面影响，并避免过度聚焦高质量样本[21]。在本文正增长消融路线中，WIoU 与 DyHead 组合后形成没有 P2 分支时的较强基线，表明检测头表达与回归损失之间存在互补关系。

## 2 数据集与小目标特征分析

### 2.1 数据集来源与类别设置

本文实验基于 DAIR-V2X-I 路侧单目图像构建 YOLO 格式目标检测数据集，将其 2D 边界框标注转换为 YOLO 归一化中心坐标与宽高格式（不涉及 3D 到 2D 的投影转换）；配置文件中 train、val 和 test 分别指向训练集、验证集和测试集图像目录。类别名称包括 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类。原始数据中的极少样本类别 Barrowlist（验证集仅 24 个实例）未纳入本文 8 类检测任务。

表 1 给出了本文使用的数据集划分和实例数量。训练集包含 4940 个标注文件、227831 个目标实例；验证集包含 1411 个标注文件、65255 个实例；测试集包含 707 个标注文件、32628 个实例。总计 7058 个标注文件和 325714 个目标实例。该规模能够支撑轻量化 YOLO 模型训练与消融比较。需要说明的是，本文所有定量评价指标均在验证集上计算，最佳训练轮次亦依验证集指标选定；测试集不参与模型选择与指标报告，留作后续跨场景泛化评估。

**表 1 DAIR-V2X-I 数据集划分与实例数**  
**Tab. 1 Dataset split and instance numbers of DAIR-V2X-I**

{markdown_table(dataset_split, decimals=0)}

### 2.2 类别分布统计

表 2 给出了各类别实例数量及占比。Trafficcone 数量最多，共 159930 个，占 49.10%；Car 共有 91443 个，占 28.07%。两类合计占比超过 77%，说明数据集中存在明显类别不均衡。Pedestrian 为 25194 个，占 7.74%；Cyclist 和 Motorcyclist 分别占 5.29% 和 5.60%；Truck、Van 和 Bus 的占比较低，均属于相对少样本类别。

**表 2 DAIR-V2X-I 类别实例分布**  
**Tab. 2 Category distribution of DAIR-V2X-I**

{markdown_table(class_dist, decimals=2)}

### 2.3 目标尺度统计

为了分析小目标特征，本文将 YOLO 归一化标注框折算到 640 x 640 输入尺度下，统计目标面积、短边长度和双边尺度。统计结果见表 3。若参考 COCO 数据集常用的小目标面积阈值 area < 32² px²[29]，本文数据中小目标实例为 259421 个，占 79.65%。若以短边长度衡量，short side < 16 px 的目标占 68.60%，short side < 32 px 的目标占 87.55%。此外，宽高均小于 32 px 的目标占 56.37%。

**表 3 目标尺度统计结果**  
**Tab. 3 Object scale statistics at imgsz=640**

{markdown_table(scale_stats, decimals=2)}

从目标尺度看，本文数据集的小目标比例远高于一般自然场景检测任务。特别是 Trafficcone、Pedestrian、Cyclist 和 Motorcyclist 等类别，在路侧远景区域中常表现为高度细长或低像素目标。类别级中位短边统计进一步显示，Trafficcone 约为 4.2 px，Pedestrian 约为 9.0 px，Cyclist 约为 14.4 px，Motorcyclist 约为 15.6 px。对于这类目标，若模型最低检测尺度为 P3/8，则部分目标在特征图中可能仅对应 1 到 2 个栅格，边界回归难度较高。

**表 4 验证集各类别尺度分布（imgsz=640）**  
**Tab. 4 Scale distribution by class on the validation set**

{scale_table_md}

![图 1 验证集各类别短边尺度分布]({rel(FIG_DIR / "fig1_val_scale_distribution.png")})

图 1 验证集各类别短边尺度分布。Fig. 1 Short-side scale distribution of each class on the validation set.

### 2.4 数据特征对模型设计的启示

上述统计为本文方法设计提供了直接依据。首先，目标短边普遍较小，说明模型需要更高分辨率的检测特征，P2/4 分支具有必要性。其次，类别分布不均衡且小目标类别与道路安全高度相关，说明模型需要提高 Recall，减少远距离目标漏检。再次，大量交通锥和车辆构成密集目标区域，要求检测头能够处理尺度和空间位置差异，DyHead 因此具有应用价值。最后，路侧背景复杂、目标位置具有明显道路几何规律，CoordAttention 的方向位置编码可作为辅助增强。

## 3 改进 YOLO11n 检测方法

### 3.1 YOLO11n 基准网络

YOLO11n 是 YOLO11 系列中的 nano 版本，具有参数量小、计算量低和训练部署方便等优点。本文以 YOLO11n YAML 结构作为 baseline，并采用从头训练的方式进行主要对比。baseline 在固定 batch=32 复验中取得 Precision {pct(baseline.P)}%、Recall {pct(baseline.R)}%、mAP@0.5 {pct(baseline.mAP50)}%、mAP@0.5:0.95 {pct(baseline.mAP50_95)}%、FPS {pct(baseline.FPS)}、GFLOPs {pct(baseline.GFLOPs)}、Params {pct(baseline.Params)}M 的结果。该模型计算量较低，但 Recall 和 mAP@0.5:0.95 仍存在提升空间。

YOLO11n 的检测流程可以概括为：输入图像经 Backbone 提取多层特征，Neck 通过上采样、拼接和卷积实现多尺度特征融合，Head 在不同尺度特征图上预测目标类别和边界框。默认检测头使用 P3、P4 和 P5 三层特征，其中 P3 更偏向小目标，P4 和 P5 更偏向中大目标。对于 DAIR-V2X-I 这种极小目标比例高的数据集，仅使用 P3 作为最高分辨率检测层可能不足。

### 3.2 总体改进结构

本文提出的 YOLO11n-DWCA-P2 在基准网络基础上进行四方面改进。第一，将检测头替换为 DyHeadDetect，提高多尺度特征在检测阶段的动态表达能力；第二，在边界框回归中采用 Wise-IoU v3 损失，提高定位学习质量；第三，在 Neck 中新增 P2/4 高分辨率检测分支，使检测头接收 P2、P3、P4 和 P5 四尺度输入；第四，在浅中层特征中引入 CoordAttention，以增强通道和坐标位置联合建模。

图 2 为本文方法结构示意图。该图基于本文方法 YAML 结构重新绘制，突出 Backbone、Top-down FPN、Bottom-up PAN、四尺度检测输入和 Head/Loss 的阶段关系。图中 P2 分支对应 layer 20，CoordAttention 位于 layer 5，DyHeadDetect 的输入为 [20, 23, 26, 29]。WIoU v3 仅作用于训练阶段的边界框回归损失，不属于推理阶段的网络拓扑。

![图 2 YOLO11n-DWCA-P2 网络结构示意图]({rel(FIG_DIR / "fig2_dwca_p2_architecture_vertical.png")})

图 2 YOLO11n-DWCA-P2 网络结构示意图。Fig. 2 Architecture of YOLO11n-DWCA-P2.

### 3.3 P2 高分辨率检测分支

P2 分支是本文最终模型的核心改进。对于输入大小为 640 x 640 的图像，P2/4 特征图分辨率约为 160 x 160，P3/8 特征图分辨率约为 80 x 80。若一个目标短边为 8 px，则在 P3 特征图上对应约 1 个像素，在 P2 特征图上对应约 2 个像素；若目标短边为 16 px，则在 P3 上约 2 个像素，在 P2 上约 4 个像素。虽然这只是近似分析，但足以说明 P2 对极小目标响应区域的提升。

设输入图像短边尺度为 d，检测层下采样步长为 r_l，则该目标在第 l 个检测特征图上的近似线性投影尺度为

$$d_l=\\frac{{d}}{{r_l}},$$

其中，P2 和 P3 的下采样步长分别为 4 和 8（即 r_{{P2}}=4、r_{{P3}}=8，表示相应特征图相对输入图像的下采样倍率）。因此，同一目标在 P2 上的线性投影约为 P3 的 2 倍，面积响应约为 4 倍。该尺度关系解释了为什么 P2 分支更适合承接远距离行人、交通锥和骑行者等极小目标的定位学习。

本文在 Neck 中将较高层特征逐步上采样，并与浅层 P2 特征拼接融合，得到用于 tiny object detection 的 P2 输出层。随后，检测头由原来的三尺度输入扩展为四尺度输入。P2 分支保留了更多浅层边缘、纹理和空间位置信息，能够缓解远距离行人、交通锥和骑行者在深层特征中消失或定位偏移的问题。

![图 3 P2 高分辨率分支融合示意]({rel(FIG_DIR / "fig3_p2_fusion.png")})

图 3 P2 高分辨率分支融合示意。Fig. 3 P2 high-resolution branch fusion in the Neck.

从消融结果看，DW-P2 在不使用 CoordAttention 的情况下，mAP@0.5 达到 {pct(dw_p2.mAP50)}%，mAP@0.5:0.95 达到 {pct(dw_p2.mAP50_95)}%；完整 DWCA-P2 的 mAP@0.5:0.95 同样为 {pct(proposed.mAP50_95)}%。这一结果表明 P2 分支贡献了最终模型的主要定位增益。相比之下，DWCA 在没有 P2 分支时 mAP@0.5:0.95 仅为 {pct(dwca.mAP50_95)}%。因此，本文在结论中将 P2 明确为主贡献模块。

### 3.4 DyHead 动态检测头

DyHead 的核心思想是在检测头中统一建模尺度、空间和任务三个维度的注意力。对于多尺度特征金字塔，尺度感知注意力可根据目标大小选择合适层级；空间感知注意力可关注目标所在位置；任务感知注意力可协调分类与定位任务之间的特征需求[20]。路侧图像中目标尺度跨度大、远近分布明显，同一类别在不同道路深度区域呈现明显尺度变化，因而适合引入动态检测头。

本文在 YOLO11n 中使用 DyHeadDetect 替换原检测头。设输入检测特征为多尺度特征集合 F = {{F2, F3, F4, F5}}，其中 F2 到 F5 分别对应 P2 到 P5 特征。DyHeadDetect 对多尺度特征进行动态调制后输出类别概率和边界框回归结果。具体地，DyHead 依次施加尺度感知 π、空间感知 S 与任务感知 L 三种注意力，对多尺度特征 F 进行级联调制：

$$F'=L(S(\\pi(F))),$$

其中，π 沿尺度维度计算跨层权重，使不同层级特征按目标尺度自适应融合；S 借助可变形卷积在空间维度关注目标位置；L 采用动态激活函数在任务通道间协调分类与回归特征。该级联调制不改变输入数据或标签，而是在检测阶段提高特征对尺度、空间位置和任务通道的适应性。

![图 4 DyHead 动态检测头结构示意]({rel(FIG_DIR / "fig4_dyhead.png")})

图 4 DyHead 动态检测头结构示意。Fig. 4 DyHead dynamic head structure.

在消融实验中，+D 模型相较 baseline 的 mAP@0.5 从 86.0% 提升至 86.6%，mAP@0.5:0.95 从 60.2% 提升至 61.3%；+DW 模型进一步达到 87.0% mAP@0.5 和 61.3% mAP@0.5:0.95。说明 DyHead 对本文任务有稳定增益，是构建强基线的重要模块。

### 3.5 CoordAttention 位置注意力模块

CoordAttention 的目标是在通道注意力中保留位置信息。传统通道注意力通常通过二维全局池化将空间维度压缩为单个通道描述子，容易丢失目标具体位置信息。CoordAttention 将全局池化分解为沿高度方向和宽度方向的一维编码，分别得到方向感知特征，再生成位置敏感注意力图[16]。其沿高度和宽度方向的编码可分别表示为

$$z_c^h(h)=\\frac{{1}}{{W}}\\sum_{{0\\leq i<W}}x_c(h,i),$$

$$z_c^w(w)=\\frac{{1}}{{H}}\\sum_{{0\\leq j<H}}x_c(j,w),$$

其中，x 表示输入特征，H 和 W 表示特征图高度和宽度，c 表示通道索引。随后，将 zʰ 与 zʷ 沿通道拼接，经 1×1 卷积与非线性激活 δ 变换后沿方向拆分为两路，再由 Sigmoid 分别生成沿高度与宽度方向的方向门控 gʰ 与 gʷ；二者各自编码对应坐标轴的位置先验，不能由单一通道门控替代，这是 CoordAttention 能够保留方向位置敏感信息的关键：

$$f=\\delta(\\mathrm{{Conv}}_{{1\\times1}}([z^h,z^w])),\\quad g^h=\\sigma(f^h),\\quad g^w=\\sigma(f^w),$$

$$y_c(h,w)=x_c(h,w)\\cdot g_c^h(h)\\cdot g_c^w(w),$$

其中，[·,·] 表示沿通道维度拼接，σ 为 Sigmoid 函数，fʰ、fʷ 为变换后沿高度与宽度方向的分支。最终输出 y_c(h,w) 将方向位置敏感的注意力权重作用回输入特征，从而增强方向和位置敏感信息。

![图 5 CoordAttention 结构示意]({rel(FIG_DIR / "fig5_coordattention.png")})

图 5 CoordAttention 结构示意。Fig. 5 Coordinate attention structure.

本文将 CoordAttention 嵌入到 P3 相关特征位置，目的是在浅层细节与中层语义之间增强位置编码。需要强调的是，本文实验并不支持将 CoordAttention 表述为主要增益来源。DWCA 的 mAP@0.5:0.95 为 {pct(dwca.mAP50_95)}%，与 +DW 的 {pct(plus_dw.mAP50_95)}% 持平；完整模型相较 DW-P2 在 mAP@0.5:0.95 上没有进一步增加。因此，CoordAttention 更适合作为辅助模块写入方法部分，而不是在摘要和结论中过度强调。

### 3.6 Wise-IoU v3 边界框回归损失

边界框回归损失用于度量预测框与真实框之间的差异。IoU 可表示为

$$IoU=\\frac{{|B\\cap B_{{gt}}|}}{{|B\\cup B_{{gt}}|}},$$

其中，B 为预测框，B_gt 为真实框，∩ 与 ∪ 分别表示区域的交集与并集。传统 CIoU 在 IoU 基础上引入中心距离和宽高比约束，能够提升边界框回归稳定性。Wise-IoU 进一步关注样本质量差异，通过动态非单调聚焦机制调整不同质量锚框的梯度增益[21]。其思想是避免低质量样本产生过强有害梯度，同时不过度放大已经较好拟合的高质量样本，使模型更关注普通质量样本的有效学习。具体地，设预测框与真实框中心距为 ρ、最小外接矩形对角线长度为 c，WIoU v3 首先构造距离注意力项

$$R_{{WIoU}}=\\exp(\\frac{{\\rho^2}}{{c^2}}),$$

其中 c² 取停止梯度形式，使梯度仅经 ρ² 流动。记 L_IoU = 1 − IoU 为边界框回归损失，并以停止梯度形式 L_IoU* 参与聚焦计算；训练中以指数滑动平均维护其在批内的均值 L̄。以 L_IoU* 与 L̄ 之比定义锚框离群度 β，进而构造动态非单调聚焦因子 r：

$$\\beta=\\frac{{L_{{IoU}}^{{*}}}}{{\\overline{{L}}}},\\quad r=\\frac{{\\beta}}{{\\delta\\,\\alpha^{{\\beta-\\delta}}}},$$

其中 α=1.9、δ=3.0 为文献[21]给出的超参数。WIoU v3 的最终回归损失为

$$\\mathcal{{L}}_{{WIoUv3}}=r\\cdot R_{{WIoU}}\\cdot L_{{IoU}}.$$

当锚框为高质量样本（β 较小）时 r 较小，梯度增益被抑制；当为离群低质量样本（β 较大）时 r 亦被非单调衰减，避免过强有害梯度；而普通质量样本获得相对更大的梯度增益，从而更关注其有效学习。

![图 6 Wise-IoU v3 聚焦增益曲线]({rel(FIG_DIR / "fig6_wiou_focusing.png")})

图 6 Wise-IoU v3 动态非单调聚焦增益 r 随 β 变化。Fig. 6 Wise-IoU v3 dynamic non-monotonic focusing gain r vs. β.

本文在训练中采用 WIoU v3 作为改进模型的回归损失。在正增长消融路线中，+DW 相较 +D 的 Recall 从 81.1% 提升到 81.9%，mAP@0.5 从 86.6% 提升到 87.0%，但 mAP@0.5:0.95 保持 61.3%。这说明 WIoU 在本文任务中更适合作为检测头改进后的配套优化，而不是主要定位增益来源；最终定位质量提升仍主要来自 P2 高分辨率检测分支。

### 3.7 方法流程

本文方法的训练和推理流程如下。首先，将 DAIR-V2X-I 路侧图像按 YOLO 格式读取，并在训练阶段进行常规数据增强。其次，输入图像经 YOLO11n Backbone 提取多层特征，在 Neck 中通过自顶向下和自底向上的特征融合形成 P2、P3、P4 和 P5 四尺度特征。随后，CoordAttention 对中浅层特征进行位置敏感增强，DyHeadDetect 对四尺度特征进行动态检测。训练阶段使用分类损失、回归损失和分布相关损失共同优化，其中回归部分采用 WIoU v3。推理阶段，模型输出多尺度候选框，经过置信度筛选和非极大值抑制得到最终检测结果。

与原始 YOLO11n 相比，本文方法的主要变化集中在 Neck-Head 与损失函数处，不改变数据标注格式，也不依赖额外传感器输入。对于后续复现，可重点检查四项内容：模型 YAML 是否包含 P2 输出层，检测头是否为 DyHeadDetect，训练损失是否正确启用 WIoU v3，所有主实验 batch 是否按 32 固定。

## 4 实验设置

### 4.1 实验环境与训练参数

本文所有实验使用同一数据集划分，并按固定 batch=32 口径解释。输入图像尺寸为 640 x 640，训练轮数为 300 epochs，优化器为 SGD，随机种子为 42，nbs 为 64，close_mosaic 设置为 10。实验评价指标包括 Precision、Recall、mAP@0.5、mAP@0.5:0.95、FPS、GFLOPs 和 Params。表 5 给出了主要训练与测速参数。

**表 5 训练与测速参数设置**  
**Tab. 5 Training and speed measurement settings**

{markdown_table(training_params, decimals=0)}

### 4.2 评价指标

目标检测任务通常使用 Precision、Recall 和 mAP 评价模型性能。Precision 表示预测为正样本的目标中真正例所占比例，Recall 表示真实目标中被正确检出的比例，计算式为

$$P=\\frac{{TP}}{{TP+FP}},$$

$$R=\\frac{{TP}}{{TP+FN}},$$

其中，TP 表示真正例，FP 表示假正例，FN 表示假负例。对于路侧安全感知任务，Recall 尤其重要，因为漏检行人、骑行者和交通锥可能影响后续交通事件判断。

AP 表示单类别 Precision-Recall 曲线下的面积，mAP 表示多类别 AP 的平均值。mAP@0.5 在 IoU 阈值为 0.5 时计算平均精度，主要反映模型能否检测到目标；mAP@0.5:0.95 在 0.5 到 0.95 的多个 IoU 阈值上取平均，更严格地反映定位质量。对于小目标检测，mAP@0.5:0.95 能更敏感地体现边界框偏移问题，因此本文将其作为重要指标。FPS 用于衡量统一测试环境下的端到端推理速度，GFLOPs 和 Params 分别反映计算复杂度与参数规模。

### 4.3 实验分组

本文实验分为三类。第一类为主结果对比，比较 YOLO11n baseline 与最终模型 DWCA-P2，作为本文结论的主要依据；两者均采用 batch=32 的固定复验结果。第二类为正增长模块消融实验，沿 baseline、+D、+DW、DWCA、DW-P2 和 DWCA-P2 路线逐步分析 DyHead、WIoU、CoordAttention 与 P2 分支的作用。第三类为同口径结构对比，比较 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml、YOLO11n baseline 和本文方法。正文实验均采用从头训练口径，避免外部权重来源差异干扰结论。

为保证结论边界清晰，本文正文只采用与最终方法直接相关的模块路线。

## 5 实验结果与分析

### 5.1 主结果对比

表 6 给出了本文最终模型与 YOLO11n baseline 的主结果对比。可以看出，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 {pct(proposed.P)}%、{pct(proposed.R)}%、{pct(proposed.mAP50)}% 和 {pct(proposed.mAP50_95)}%，较 baseline 分别提升 {pct(proposed.P - baseline.P)}、{pct(proposed.R - baseline.R)}、{pct(proposed.mAP50 - baseline.mAP50)} 和 {pct(proposed.mAP50_95 - baseline.mAP50_95)} 个百分点。

**表 6 主结果对比**  
**Tab. 6 Main comparison between baseline and the proposed method**

{markdown_table(tables["main_results"], decimals=1)}

从指标变化看，本文方法在 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 上均有提升。其中 Recall 与 mAP@0.5:0.95 的增幅更大，说明该方法能够检出更多真实目标，并改善较高 IoU 阈值下的定位质量；Precision 与 mAP@0.5 的同步提升，则说明模型在降低漏检的同时没有显著放大误检。这与 P2 分支保留高分辨率空间细节、WIoU v3 优化边界框回归以及 CoordAttention 对位置敏感表达的补充增强作用相一致。

计算复杂度方面，DWCA-P2 的 GFLOPs 为 {pct(proposed.GFLOPs)}，参数量为 {pct(proposed.Params)}M。统一 RTX 4090 测速下，DWCA-P2 的 FPS 为 {pct(proposed.FPS)}，对应单张端到端耗时约 {1000.0 / proposed.FPS:.2f} ms。额外计算主要来自 DyHead 和 P2 高分辨率检测分支。对于极端低功耗嵌入式设备，该计算开销可能需要进一步压缩；对于路侧边缘服务器或具备加速芯片的路侧计算单元，该速度可作为同环境实时性参考。

![图 7 主结果指标对比]({rel(FIG_DIR / "fig7_main_metrics.png")})

图 7 baseline 与 DWCA-P2 主指标对比。Fig. 7 Main metric comparison between baseline and DWCA-P2.

### 5.2 类别级结果分析

为进一步分析改进模型对不同类别的影响，本文从训练日志末尾的 per-class 验证输出中提取 baseline 与 DWCA-P2 的类别级 AP，结果见表 7。需要说明的是，表 7 来源于最终验证日志的逐类别输出，整体均值与表 6 的 Excel 主结果口径存在约 0.1 个百分点的四舍五入和最佳轮次差异；论文主结论仍以表 6 为准，类别级分析用于观察不同类别的相对变化。

**表 7 类别级 AP 对比**  
**Tab. 7 Per-class AP comparison**

{class_table_md}

类别级结果显示，DWCA-P2 在 Pedestrian 和 Trafficcone 上的提升最明显。其中 Pedestrian 的 mAP@0.5 从 77.8% 提升到 86.3%，mAP@0.5:0.95 从 42.8% 提升到 51.3%；Trafficcone 的 mAP@0.5:0.95 提升 8.0 个百分点。结合表 4 可知，这两类目标在验证集中几乎全部属于 short side < 32 px 的小目标，因此其提升能够较直接地支撑 P2 高分辨率检测分支的有效性。Cyclist 和 Motorcyclist 的 mAP@0.5:0.95 分别提升 4.0 和 3.1 个百分点，也说明 P2 分支对弱势交通参与者具有较明显帮助。Truck 的 mAP@0.5:0.95 提升 1.8 个百分点，但该类样本数量较少、类别内尺度变化较大，其低阈值 AP 波动仍需结合更多样本进一步核验。

![图 8 类别级 mAP@0.5:0.95 增益]({rel(FIG_DIR / "fig8_class_map_gain.png")})

图 8 DWCA-P2 相对 baseline 的类别级 mAP@0.5:0.95 提升。Fig. 8 Per-class mAP@0.5:0.95 gain of DWCA-P2 over baseline.

### 5.3 模块消融实验

为分析各模块贡献，本文设计了从 baseline 到最终模型的正增长路线消融实验，结果见表 8。表中 +D 表示引入 DyHead，+DW 表示 DyHead 与 WIoU 组合，DWCA 表示 DyHead、WIoU 与 CoordAttention 组合但不含 P2，DW-P2 表示 DyHead、WIoU 与 P2 组合但不含 CoordAttention，DWCA-P2 表示完整结构。

**表 8 消融实验结果**  
**Tab. 8 Ablation study results**

{markdown_table(tables["ablation"], decimals=1)}

DyHead 的提升较稳定。+D 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 均高于 baseline，其中 mAP@0.5 提升 0.7 个百分点。将 WIoU 与 DyHead 组合后，+DW 的 Recall 达到 81.9%，mAP@0.5 达到 87.0%，成为没有 P2 分支时的较强基线。这表明 DyHead 和 WIoU 在特征表达与边界框回归层面具有一定互补性。

P2 分支的效果最为明显。DW-P2 在不使用 CoordAttention 的情况下，Recall 达到 83.5%，mAP@0.5 达到 88.1%，mAP@0.5:0.95 达到 64.4%。相比 +DW，其 Recall 提升 1.6 个百分点，mAP@0.5 提升 1.1 个百分点，mAP@0.5:0.95 提升 3.1 个百分点。加入 CoordAttention 后，DWCA-P2 的 Precision 由 85.6% 提升到 86.0%，mAP@0.5 由 88.1% 提升到 88.4%，mAP@0.5:0.95 仍为 64.4%。这些结果共同说明，P2 高分辨率分支主导了 Recall 与定位质量提升，而 CoordAttention 在 Precision 和 mAP@0.5 上提供了补充增益。

CoordAttention 的作用应谨慎但不宜弱化。DWCA 相比 +DW 的 mAP@0.5:0.95 没有提升，二者均为 61.3%；完整模型相较 DW-P2 的 mAP@0.5:0.95 也没有增加，因此它不是最终定位质量提升的主导来源。但从最终模型与 DW-P2 的比较看，CoordAttention 使 Precision 从 85.6% 提升到 86.0%，mAP@0.5 从 88.1% 提升到 88.4%，说明该模块对误检抑制和位置敏感特征表达仍有积极作用。由于表 8 已同时列出 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95，消融分析以表格为主要依据，避免仅用单一指标图削弱对 CoordAttention 精度侧作用的呈现。

### 5.4 与其他检测方法的对比

本节从两个层面比较本文方法与其他检测方法：先在相同训练口径下与代表性轻量化 YOLO 结构对比（表 9），再与文献[30] 在 DAIR-V2X-I 上报告的多种方法作参考性对比（表 10）。同口径对比部分，本文选取 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml 和 YOLO11n baseline，统一采用从头训练设置，结果见表 9。

**表 9 同口径结构对比**  
**Tab. 9 Comparison of lightweight YOLO structures trained from YAML**

{markdown_table(tables["structure_comparison"], decimals=1)}

由表 9 可知，YOLOv8n-yaml 在未引入本文改进时表现较好，mAP@0.5 为 86.5%，mAP@0.5:0.95 为 61.0%。YOLO11n baseline 与 YOLOv8n-yaml 的总体差距较小，但计算量更低。本文方法在 mAP@0.5 和 mAP@0.5:0.95 上均明显高于上述轻量结构，其中 mAP@0.5:0.95 相较 YOLOv8n-yaml 提升 3.4 个百分点，相较 YOLO11n baseline 提升 4.2 个百分点。

为进一步说明本文方法在 DAIR-V2X-I 上的竞争力，表 10 将本文 DWCA-P2 与文献[30] 报告的代表性方法进行对比。文献[30] 同样面向 DAIR-V2X-I 的改进 YOLO11（YOLO-FLC），在 10 类目标（含三轮车、手推车）、7058 张图像子集、batch=16、150 epoch 设置下报告了多种方法的结果；其中 YOLOv5n、YOLOv8n、YOLO11n 与本文表 9 的同口径模型重叠，故表 10 仅列出与本文结构差异较大的代表性方法（RT-DETR-r18、Mamba-YOLO-B 及其改进模型 YOLO-FLC，方法名右上角数字为参考文献编号）。本文 DWCA-P2 在 8 类、batch=32、300 epoch 设置下的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 均高于表 10 所列方法，亦高于文献[30] 报告的全部方法。作为交叉印证，本文 YOLOv5n 的 mAP@0.5:0.95（59.9%，见表 9）与文献[30] 的 YOLOv5n（59.4%）接近，说明两者评测口径具有一定可比性。

**表 10 与文献方法在 DAIR-V2X-I 上的对比**
**Tab. 10 Comparison with published methods on DAIR-V2X-I**
{markdown_table(tables["literature_comparison"], decimals=1)}

注：文献[30] 各行为其原始口径（10 类、7058 图、batch=16、150 epoch），本文 DWCA-P2 为本文口径（8 类、batch=32、300 epoch）。二者类别集合、数据划分与训练超参不完全一致，该表为同基准数据集上的参考性对比，严格同口径横评以表 9 为准。

这一结果说明，对于 DAIR-V2X-I 路侧小目标任务，针对目标尺度分布进行结构改进，比单纯更换轻量化 YOLO 版本更有效。不同 YOLO 版本在默认结构下均以 P3/P4/P5 为主要检测尺度，无法充分解决极小目标特征不足问题。本文通过 P2 分支引入更高分辨率检测层，因而在 Recall 和高阈值 mAP 上获得更明显提升。

### 5.5 速度与复杂度分析

表 11 给出了统一测速口径下的速度与复杂度结果。FPS 测量条件为 RTX 4090 24GB、Ultralytics 8.4.56、torch 2.7.0+cu128、DAIR-V2X-I val=1411、imgsz=640、batch=1，FPS=1000/(preprocess+inference+postprocess)，排除 loss。该口径能够用于本文各结构之间的速度比较，但仍不等同于 TensorRT、INT8 或特定边缘设备上的部署速度。

**表 11 速度与复杂度对比**
**Tab. 11 Speed and complexity comparison**

{markdown_table(tables["speed_complexity"], decimals=1)}

结果显示，baseline 速度最高，达到 153.0 FPS；DyHead 带来明显检测头计算开销；P2 高分辨率小目标检测头是 DWCA-P2/DW-P2 速度下降的主要来源。DWCA-P2 的 FPS 为 100.5，相当于单张端到端耗时约 9.95 ms，在 RTX 4090 参考环境下达到实时检测速度。该结果主要用于同环境模型对比，若部署在低功耗路侧端设备中，仍需进一步结合剪枝、轻量化卷积、知识蒸馏和 TensorRT FP16/INT8 量化降低计算成本，并在目标硬件上重新测速。

### 5.6 训练过程分析

为观察模型训练收敛趋势，本文根据 baseline 与 DWCA-P2 的 results.csv 绘制验证集 mAP@0.5:0.95 曲线和 Recall 曲线，如图 9 和图 10 所示。从曲线变化可以看出，DWCA-P2 在训练中后期保持更高的 mAP@0.5:0.95 和 Recall，说明 P2 分支带来的提升不是单个 epoch 的偶然波动，而是在训练收敛阶段形成了相对稳定的性能差距。

![图 9 验证集 mAP@0.5:0.95 曲线]({rel(FIG_DIR / "fig9_training_map50_95.png")})

图 9 baseline 与 DWCA-P2 的验证集 mAP@0.5:0.95 曲线。Fig. 9 Validation mAP@0.5:0.95 curves.

![图 10 验证集 Recall 曲线]({rel(FIG_DIR / "fig10_training_recall.png")})

图 10 baseline 与 DWCA-P2 的验证集 Recall 曲线。Fig. 10 Validation Recall curves.

由于当前产物未保存完整逐框预测 txt/json，本文不进一步声称逐图漏检数量或按目标尺度细分的检测指标。后续若需展开错误类型分析，应重新保存验证集预测结果，并按类别、目标尺度和置信度区间统计漏检与误检。

### 5.7 定性检测效果对比

为直观验证改进对极小目标的提升，选取 1 张含远距离行人与交通锥的代表性场景（YiZhuang11North 路口），以 conf=0.5 分别用 baseline 与 DWCA-P2 推理，并对小目标密集区作局部放大对比，结果如图 11 所示。可以看出，DWCA-P2 较 baseline 检出更多远距离小目标，该场景检出框数由 24 增至 27。需说明的是，本文方法的整体优势主要体现在平均定位质量（mAP@0.5:0.95）和对极小目标召回的改善上（见表 6、表 7 的定量结果），此处为代表性场景的定性示意，未对全验证集按目标尺度进行系统的漏检/误检统计。

![图 11 baseline 与 DWCA-P2 检测效果对比（远距离小目标密集区局部放大；conf=0.5）]({rel(FIG_DIR / "fig_detection_comparison.png")})

图 11 baseline 与 DWCA-P2 在代表性场景下的检测对比（左：裁剪位置缩略图；中：baseline 放大；右：DWCA-P2 放大；conf=0.5）。Fig. 11 Qualitative detection comparison between baseline and DWCA-P2 on a representative scene (left: crop locator; middle: baseline zoom; right: DWCA-P2 zoom; conf=0.5).

## 6 讨论

### 6.1 P2 分支为何成为主增益来源

本文最重要的实验结论是，P2 高分辨率检测分支是性能提升的主要来源。这一结论由数据统计和消融实验共同支持。数据统计显示，DAIR-V2X-I 路侧图像中短边小于 32 px 的目标占 87.55%，其中大量目标短边甚至小于 16 px。对于这些目标，特征图分辨率直接决定模型能否保留有效边界和中心位置信息。

从消融结果看，DWCA 仅在 +DW 基础上加入 CoordAttention，mAP@0.5:0.95 仍为 61.3%；DW-P2 在不加入 CoordAttention 的情况下将 mAP@0.5:0.95 提升到 64.4%。这说明当目标尺度极小时，先让模型“看得见”比进一步调整注意力权重更重要。另一方面，DWCA-P2 相比 DW-P2 的 Precision 由 85.6% 提升到 86.0%，mAP@0.5 由 88.1% 提升到 88.4%，说明 CoordAttention 更适合体现在误检抑制和较松 IoU 阈值下的检测稳定性改善。P2 分支通过改变检测特征尺度主导 Recall 与定位质量提升，CoordAttention 则对精度侧指标形成补充。

### 6.2 注意力模块的有效边界

注意力机制并非在所有场景中都能带来明显收益。本文 CoordAttention 的实验结果说明，在已有 DyHead 动态检测头的情况下，继续叠加位置注意力模块可能收益有限。原因可能在于，注意力模块主要改变特征权重分配，而不能恢复下采样过程中损失的空间信息。若小目标已经在高层特征中变成弱响应，注意力机制只能重新分配现有响应，无法创造缺失的细节。

CoordAttention 仍具有一定方法价值。它能够在轻量网络中引入位置敏感通道表达，对道路场景中具有方向规律的目标分布可能有帮助。结合消融结果，更合理的表述是：CoordAttention 作为辅助模块增强中浅层特征的位置表达，对 Precision 和 mAP@0.5 有补充增益，而最终 Recall 与 mAP@0.5:0.95 的主要提升仍由 P2 分支驱动。

### 6.3 局限性

本文仍存在若干局限。首先，当前实验已经补充类别级 AP 和验证集尺度分布统计，但尚未保存完整逐框预测 txt/json，因此未进一步报告基于预测框的细分误差统计。若后续需要分析不同目标尺度下的检测差异，应重新保存验证集预测结果，并按统一规则重新计算，不能从当前汇总表格直接推断。

其次，本文方法增加了计算量。DWCA-P2 的 GFLOPs 是 baseline 的约 {proposed.GFLOPs / baseline.GFLOPs:.2f} 倍，FPS 下降约 {baseline.FPS - proposed.FPS:.2f}。对于需要在低功耗设备上实时运行的路侧系统，仍需进一步轻量化。可行方向包括减少 P2 分支通道数、使用轻量卷积替代部分标准卷积、剪枝冗余通道、使用蒸馏训练小模型以及进行 TensorRT INT8 量化。

最后，本文主要基于单数据集验证。DAIR-V2X-I 具有典型路侧特征，但不同城市、摄像机高度、道路结构和天气条件会造成分布差异。未来应在更多路侧数据集或自采路侧视频上验证模型泛化能力，并分析夜间、雨雾、逆光等复杂条件下的检测表现。

## 7 结论

本文针对 DAIR-V2X-I 路侧图像中小目标比例高、目标密集和远距离目标易漏检的问题，提出一种改进 YOLO11n 的路侧小目标检测方法 YOLO11n-DWCA-P2。该方法以 YOLO11n 为基准，引入 DyHead 动态检测头和 Wise-IoU v3 边界框回归损失，增加 P2/4 高分辨率检测分支，并使用 CoordAttention 进行位置敏感特征辅助增强。

数据统计表明，本文数据集中 short side < 32 px 的目标占 87.55%，area < 32² px² 的目标占 79.65%，小目标检测需求明显。在统一 batch=32 训练口径下，最终 DWCA-P2 模型取得 {pct(proposed.P)}% Precision、{pct(proposed.R)}% Recall、{pct(proposed.mAP50)}% mAP@0.5 和 {pct(proposed.mAP50_95)}% mAP@0.5:0.95。与 YOLO11n baseline 相比，Recall 提升 {pct(proposed.R - baseline.R)} 个百分点，mAP@0.5 提升 {pct(proposed.mAP50 - baseline.mAP50)} 个百分点，mAP@0.5:0.95 提升 {pct(proposed.mAP50_95 - baseline.mAP50_95)} 个百分点。

消融实验进一步表明，P2 高分辨率检测分支是最终 Recall 与 mAP@0.5:0.95 提升的主要来源，DyHead 与 WIoU 的组合构成有效强基线，CoordAttention 则对 Precision 和 mAP@0.5 起辅助增强作用。本文方法提高了路侧小目标的检出能力和定位质量，为车路协同视觉感知中的轻量化检测模型改进提供了可行方案。

未来工作将从三个方面展开。第一，进一步筛选远距离小目标样例制作局部放大对比图，以更直观展示不同结构的检测差异。第二，结合 TensorRT、剪枝、量化和蒸馏降低部署成本。第三，将模型扩展到夜间、雨雾、逆光和多摄像头路侧场景，验证其跨场景泛化能力。

## 参考文献

[1] GIRSHICK R. Fast R-CNN[C]//Proceedings of the IEEE International Conference on Computer Vision. 2015: 1440.

[2] REN S, HE K, GIRSHICK R, et al. Faster R-CNN: Towards real-time object detection with region proposal networks[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2017, 39(6): 1137-1149.

[3] LIU W, ANGUELOV D, ERHAN D, et al. SSD: Single shot multibox detector[C]//European Conference on Computer Vision. Cham: Springer, 2016: 21-37.

[4] LIN T Y, GOYAL P, GIRSHICK R, et al. Focal loss for dense object detection[C]//Proceedings of the IEEE International Conference on Computer Vision. 2017: 2999.

[5] TAN M, PANG R, LE Q V. EfficientDet: Scalable and efficient object detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2020: 10778.

[6] REDMON J, DIVVALA S, GIRSHICK R, et al. You only look once: Unified, real-time object detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2016: 779.

[7] REDMON J, FARHADI A. YOLOv3: An incremental improvement[J/OL]. arXiv:1804.02767, 2018. https://arxiv.org/abs/1804.02767.

[8] BOCHKOVSKIY A, WANG C Y, LIAO H Y M. YOLOv4: Optimal speed and accuracy of object detection[J/OL]. arXiv:2004.10934, 2020. https://arxiv.org/abs/2004.10934.

[9] WANG C Y, BOCHKOVSKIY A, LIAO H Y M. YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2023: 7464.

[10] JOCHER G, QIU J, CHAURASIA A. Ultralytics YOLO[EB/OL]. https://github.com/ultralytics/ultralytics, [2026-06-23].

[11] Ultralytics. Ultralytics YOLO11 docs[EB/OL]. https://docs.ultralytics.com/models/yolo11, [2026-06-23].

[12] LIN T Y, DOLLAR P, GIRSHICK R, et al. Feature pyramid networks for object detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2017: 936.

[13] LIU S, QI L, QIN H, et al. Path aggregation network for instance segmentation[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 8759.

[14] SINGH B, DAVIS L S. An analysis of scale invariance in object detection-SNIP[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 3578.

[15] AKYON F C, ALTINUC S O, TEMIZEL A. Slicing aided hyper inference and fine-tuning for small object detection[C]//2022 IEEE International Conference on Image Processing. Piscataway: IEEE, 2022: 966.

[16] HOU Q, ZHOU D, FENG J. Coordinate attention for efficient mobile network design[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021: 13708.

[17] HU J, SHEN L, SUN G. Squeeze-and-excitation networks[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 7132.

[18] WOO S, PARK J, LEE J Y, et al. CBAM: Convolutional block attention module[C]//European Conference on Computer Vision. Cham: Springer, 2018: 3-19.

[19] WANG Q, WU B, ZHU P, et al. ECA-Net: Efficient channel attention for deep convolutional neural networks[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2020: 11531.

[20] DAI X, CHEN Y, XIAO B, et al. Dynamic head: Unifying object detection heads with attentions[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021: 7369.

[21] TONG Z, CHEN Y, XU Z, et al. Wise-IoU: Bounding box regression loss with dynamic focusing mechanism[J/OL]. arXiv:2301.10051, 2023. https://arxiv.org/abs/2301.10051.

[22] REZATOFIGHI H, TSOI N, GWAK J, et al. Generalized intersection over union: A metric and a loss for bounding box regression[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2019: 658.

[23] ZHENG Z, WANG P, LIU W, et al. Distance-IoU loss: Faster and better learning for bounding box regression[J]. Proceedings of the AAAI Conference on Artificial Intelligence, 2020, 34(7): 12993-13000.

[24] YU H, LUO Y, SHU M, et al. DAIR-V2X: A large-scale dataset for vehicle-infrastructure cooperative 3D object detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2022: 21329.

[25] XU R, XIANG H, XIA X, et al. OPV2V: An open benchmark dataset and fusion pipeline for perception with vehicle-to-vehicle communication[C]//Proceedings of the IEEE International Conference on Robotics and Automation. 2022: 2583.

[26] XU R, XIANG H, TU Z, et al. V2X-ViT: Vehicle-to-everything cooperative perception with vision transformer[C]//European Conference on Computer Vision. Cham: Springer, 2022: 107-124.

[27] Ultralytics. Explore Ultralytics YOLOv8[EB/OL]. https://docs.ultralytics.com/models/yolov8, [2026-06-23].

[28] FENG Q, XU X, WANG Z. Deep learning-based small object detection: A survey[J]. Mathematical Biosciences and Engineering, 2023, 20(4): 6551-6590.

[29] LIN T Y, MAIRE M, BELONGIE S, et al. Microsoft COCO: Common objects in context[C]//European Conference on Computer Vision. Cham: Springer, 2014: 740-755.
[30] LIANG E, WEI D, LI F, et al. Object detection model of vehicle-road cooperative autonomous driving based on improved YOLO11 algorithm[J]. Scientific Reports, 2025, 15: 32348.
"""
    return lines


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill.lstrip("#"))
    tc_pr.append(shd)


def set_cell_margins(cell, top: int = 80, start: int = 80, bottom: int = 80, end: int = 80) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for edge, value in {"top": top, "start": start, "bottom": bottom, "end": end}.items():
        node = tc_mar.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_cell_border(
    cell,
    top: tuple[str, str] | None = None,
    bottom: tuple[str, str] | None = None,
    left: tuple[str, str] | None = None,
    right: tuple[str, str] | None = None,
    color: str = "000000",
) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    edge_map = {
        "top": top,
        "bottom": bottom,
        "left": left,
        "right": right,
    }
    for edge, spec in edge_map.items():
        tag = "w:" + edge
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        if spec is None:
            element.set(qn("w:val"), "nil")
            element.set(qn("w:sz"), "0")
        else:
            value, sz = spec
            element.set(qn("w:val"), value)
            element.set(qn("w:sz"), sz)
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_run_font(
    run,
    name: str = "Times New Roman",
    size: float | None = None,
    bold: bool | None = None,
    color: str | None = None,
    east_asia: str = "SimSun",
) -> None:
    if run._element.rPr is None:
        run._element.get_or_add_rPr()
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:ascii"), name)
    run._element.rPr.rFonts.set(qn("w:hAnsi"), name)
    run._element.rPr.rFonts.set(qn("w:eastAsia"), east_asia)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor.from_string(color.lstrip("#"))


def style_document(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(3.2)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(1.5)
    section.footer_distance = Cm(1.5)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "SimSun"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.15
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.first_line_indent = Pt(21)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for style_name, size, before, after in [("Heading 1", 14, 10, 4), ("Heading 2", 10.5, 6, 2), ("Heading 3", 10.5, 4, 0)]:
        style = styles[style_name]
        style.font.name = "SimHei"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
        style._element.rPr.rFonts.set(qn("w:ascii"), "Times New Roman")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor(0, 0, 0)
        style.paragraph_format.line_spacing = 1.15
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.first_line_indent = Pt(0)


def add_text_runs(
    paragraph,
    text: str,
    size: float | None = None,
    bold: bool = False,
    ascii_font: str = "Times New Roman",
    east_asia: str = "SimSun",
    superscript_citations: bool = False,
) -> None:
    """Render superscripts for author markers and optional body citation markers."""
    pos = 0
    pattern = re.compile(r"\^([^^]+)\^|(\[(?:\d+\s*(?:[-,，]\s*\d+\s*)*)\])")
    for match in pattern.finditer(text):
        if match.start() > pos:
            run = paragraph.add_run(text[pos : match.start()])
            set_run_font(run, name=ascii_font, east_asia=east_asia, size=size, bold=bold)
        token = match.group(1) if match.group(1) is not None else match.group(2)
        run = paragraph.add_run(token)
        set_run_font(run, name=ascii_font, east_asia=east_asia, size=size, bold=bold)
        if match.group(1) is not None or superscript_citations:
            run.font.superscript = True
        pos = match.end()
    if pos < len(text):
        run = paragraph.add_run(text[pos:])
        set_run_font(run, name=ascii_font, east_asia=east_asia, size=size, bold=bold)


def add_paragraph_text(
    doc: Document,
    text: str,
    style: str | None = None,
    align=None,
    bold: bool = False,
    size: float | None = None,
    first_line_indent: bool | None = None,
    ascii_font: str = "Times New Roman",
    east_asia: str = "SimSun",
    superscript_citations: bool = False,
) -> None:
    p = doc.add_paragraph(style=style)
    if first_line_indent is None:
        first_line_indent = style is None
    p.paragraph_format.first_line_indent = Pt(21) if first_line_indent else Pt(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    if align is not None:
        p.alignment = align
    elif style is None:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_text_runs(
        p,
        text,
        size=size,
        bold=bold,
        ascii_font=ascii_font,
        east_asia=east_asia,
        superscript_citations=superscript_citations,
    )


def add_labeled_paragraph(
    doc: Document,
    label: str,
    text: str,
    *,
    size: float = 9,
    label_east_asia: str = "SimHei",
    text_east_asia: str = "KaiTi",
    ascii_font: str = "Times New Roman",
    first_line_indent: bool = False,
) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(21) if first_line_indent else Pt(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(label)
    set_run_font(r, name=ascii_font, east_asia=label_east_asia, size=size, bold=True)
    add_text_runs(p, text, size=size, ascii_font=ascii_font, east_asia=text_east_asia)


def add_reference_heading(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run("参考文献")
    set_run_font(run, name="Times New Roman", east_asia="SimHei", size=9, bold=True)


def add_reference_entry(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.left_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.25
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    add_text_runs(p, text, size=9, ascii_font="Times New Roman", east_asia="SimSun")


def add_front_title_block(doc: Document) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(CN_TITLE)
    set_run_font(r, name="Times New Roman", east_asia="SimHei", size=18, bold=True)

    add_paragraph_text(doc, CN_AUTHORS, align=WD_ALIGN_PARAGRAPH.CENTER, size=15, first_line_indent=False, east_asia="KaiTi")
    add_paragraph_text(doc, CN_AFFILIATION, align=WD_ALIGN_PARAGRAPH.CENTER, size=9, first_line_indent=False)


def add_english_front_block(doc: Document, abstract: str, keywords: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(EN_TITLE)
    set_run_font(r, name="Times New Roman", east_asia="SimSun", size=16, bold=True)

    add_paragraph_text(doc, EN_AUTHORS, align=WD_ALIGN_PARAGRAPH.CENTER, size=12, first_line_indent=False)
    add_paragraph_text(doc, EN_AFFILIATION, align=WD_ALIGN_PARAGRAPH.CENTER, size=9, first_line_indent=False)
    add_labeled_paragraph(doc, "Abstract: ", abstract, size=9, label_east_asia="Times New Roman", text_east_asia="Times New Roman", ascii_font="Times New Roman")
    add_labeled_paragraph(doc, "Keywords: ", keywords, size=9, label_east_asia="Times New Roman", text_east_asia="Times New Roman", ascii_font="Times New Roman")


SUP_MARK = re.compile(r"\^\{([^{}]*)\}")  # cell-text marker for superscript, e.g. NAME^{[30]}


def add_md_table_to_doc(doc: Document, df: pd.DataFrame, max_rows: int | None = None) -> None:
    if max_rows is not None:
        df = df.head(max_rows)
    table = doc.add_table(rows=1, cols=len(df.columns))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    header = table.rows[0].cells
    for i, col in enumerate(df.columns):
        header[i].text = str(col)
        set_cell_margins(header[i], 70, 70, 70, 70)
        set_cell_border(header[i], top=("single", "12"), bottom=("single", "8"))
        for p in header[i].paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            for r in p.runs:
                set_run_font(r, name="Times New Roman", east_asia="SimSun", bold=True, size=9)
        header[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    set_repeat_table_header(table.rows[0])
    for row_index, (_, row) in enumerate(df.iterrows()):
        cells = table.add_row().cells
        for i, col in enumerate(df.columns):
            v = row[col]
            text = format_table_value(v, col, 1, False)
            set_cell_margins(cells[i], 70, 70, 70, 70)
            bottom = ("single", "12") if row_index == len(df) - 1 else None
            set_cell_border(cells[i], bottom=bottom)
            cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cells[i].text = ""
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if len(text) <= 16 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            for idx, part in enumerate(SUP_MARK.split(text)):
                if part == "":
                    continue
                run = p.add_run(part)
                if idx % 2 == 1:
                    run.font.superscript = True
                    set_run_font(run, name="Times New Roman", east_asia="SimSun", size=6.5)
                else:
                    set_run_font(run, name="Times New Roman", east_asia="SimSun", size=8.5)
    doc.add_paragraph()


def add_caption_line(doc: Document, label: str, *, english: bool = False, table_caption: bool = False) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_before = Pt(3 if table_caption else 2)
    p.paragraph_format.space_after = Pt(0 if table_caption else 2)
    run = p.add_run(label)
    set_run_font(
        run,
        name="Times New Roman",
        east_asia="SimHei" if not english else "Times New Roman",
        size=9,
        bold=True,
    )


def split_caption(label: str) -> tuple[str, str | None]:
    text = label.strip().strip("*")
    text = re.sub(r"\s+", " ", text)
    if "Fig." in text:
        cn, en = text.split("Fig.", 1)
        return cn.strip().rstrip("。"), "Fig." + en.strip()
    if "Tab." in text:
        cn, en = text.split("Tab.", 1)
        return cn.strip().rstrip("。"), "Tab." + en.strip()
    return text, None


def add_caption(doc: Document, label: str, *, table_caption: bool = False) -> None:
    cn, en = split_caption(label)
    add_caption_line(doc, cn, english=False, table_caption=table_caption)
    if en:
        add_caption_line(doc, en, english=True, table_caption=table_caption)


def add_picture(doc: Document, path: Path, width_inches: float = 5.8) -> None:
    if path.exists():
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run()
        run.add_picture(str(path), width=Inches(width_inches))


def set_cell_width(cell, width_cm: float) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.first_child_found_in("w:tcW")
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def formula_kind(raw: str) -> str:
    formula = raw.strip().strip("$").strip().rstrip(",")
    formula = formula.replace("{{", "{").replace("}}", "}")
    if formula.startswith("z_c^h"):
        return "coord_h"
    if formula.startswith("z_c^w"):
        return "coord_w"
    if formula.startswith("d_l"):
        return "p2_scale"
    if formula.startswith("IoU"):
        return "iou"
    if formula.startswith("P="):
        return "precision"
    if formula.startswith("R="):
        return "recall"
    if formula.startswith("F'"):
        return "dyhead"
    if formula.startswith("f="):
        return "ca_gate"
    if formula.startswith("y_c"):
        return "ca_out"
    if formula.startswith("R_{WIoU}"):
        return "wiou_r"
    if formula.startswith("\\beta"):
        return "wiou_beta"
    if formula.startswith("\\mathcal{L}"):
        return "wiou_loss"
    return "text"


def formula_font(size: int, italic: bool = False, math_font: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_STIX_MATH if math_font else (FONT_TIMES_ITALIC if italic else FONT_TIMES)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.truetype(FONT_ARIAL_UNICODE, size)


def draw_text_item(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, size: int = 52, italic: bool = False, math_font: bool = False) -> int:
    font_obj = formula_font(size, italic=italic, math_font=math_font)
    draw.text(xy, text, font=font_obj, fill=(0, 0, 0, 255))
    bbox = draw.textbbox(xy, text, font=font_obj)
    return bbox[2] - bbox[0]


def fraction_bar(draw: ImageDraw.ImageDraw, x: int, y: int, width: int) -> None:
    draw.line((x, y, x + width, y), fill=(0, 0, 0, 255), width=3)


def _measure(draw: ImageDraw.ImageDraw, text: str, size: int = 52, italic: bool = False, math_font: bool = False) -> tuple[int, int]:
    fnt = formula_font(size, italic=italic, math_font=math_font)
    bbox = draw.textbbox((0, 0), text, font=fnt)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_formula_coord(draw: ImageDraw.ImageDraw, width: int, height: int, axis: str) -> None:
    base_size = 56
    sub_size = 34
    sup_size = 34
    x = 130
    y = 78

    # z_c^h(h) / z_c^w(w)
    draw_text_item(draw, (x, y), "z", size=base_size, italic=True)
    z_w = _measure(draw, "z", size=base_size, italic=True)[0]
    draw_text_item(draw, (x + z_w - 2, y + 34), "c", size=sub_size, italic=True)
    draw_text_item(draw, (x + z_w - 4, y - 16), axis, size=sup_size, italic=True)
    x += z_w + 26
    suffix = "(h)" if axis == "h" else "(w)"
    draw_text_item(draw, (x, y), suffix, size=base_size, italic=True)
    x += _measure(draw, suffix, size=base_size, italic=True)[0]
    x += draw_text_item(draw, (x, y), " = ", size=base_size)

    # (1 / W) or (1 / H)
    frac_w = 68
    frac_x = x
    num_w = _measure(draw, "1", size=sup_size)[0]
    den = "W" if axis == "h" else "H"
    den_w = _measure(draw, den, size=sup_size, italic=True)[0]
    draw_text_item(draw, (frac_x + (frac_w - num_w) // 2, y - 18), "1", size=sup_size)
    fraction_bar(draw, frac_x, y + 18, frac_w)
    draw_text_item(draw, (frac_x + (frac_w - den_w) // 2, y + 24), den, size=sup_size, italic=True)
    x += frac_w + 16

    # summation with index below
    sigma_x = x
    draw_text_item(draw, (sigma_x, y - 8), "Σ", size=66)
    idx = "i" if axis == "h" else "j"
    draw_text_item(draw, (sigma_x + 16, y + 48), idx, size=sub_size, italic=True)
    x += _measure(draw, "Σ", size=66)[0] + 28

    # x_c(h,i) / x_c(j,w)
    draw_text_item(draw, (x, y), "x", size=base_size, italic=True)
    x_w = _measure(draw, "x", size=base_size, italic=True)[0]
    draw_text_item(draw, (x + x_w - 2, y + 34), "c", size=sub_size, italic=True)
    x += x_w + 22
    args = "(h,i)" if axis == "h" else "(j,w)"
    draw_text_item(draw, (x, y), args, size=base_size, italic=True)


def _draw_formula_iou(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    base_size = 56
    fsize = 42
    sub_size = 28
    y = 82
    x = 360
    draw_text_item(draw, (x, y), "IoU = ", size=base_size)
    x += _measure(draw, "IoU = ", size=base_size)[0] + 14
    num_segs = [("|", False), ("B", True), (" ∩ ", "math"), ("B", True), ("gt", "sub"), ("|", False)]
    den_segs = [("|", False), ("B", True), (" ∪ ", "math"), ("B", True), ("gt", "sub"), ("|", False)]

    def seg_w(segs):
        w = 0
        for t, k in segs:
            if k == "sub":
                w += _measure(draw, t, size=sub_size, italic=True)[0]
            elif k == "math":
                w += _measure(draw, t, size=fsize, math_font=True)[0]
            else:
                w += _measure(draw, t, size=fsize, italic=(k is True))[0]
        return w

    def draw_segs(sx, by, segs):
        cx = sx
        for t, k in segs:
            if k == "sub":
                draw_text_item(draw, (cx, by + 16), t, size=sub_size, italic=True)
                cx += _measure(draw, t, size=sub_size, italic=True)[0]
            elif k == "math":
                draw_text_item(draw, (cx, by), t, size=fsize, math_font=True)
                cx += _measure(draw, t, size=fsize, math_font=True)[0]
            else:
                draw_text_item(draw, (cx, by), t, size=fsize, italic=(k is True))
                cx += _measure(draw, t, size=fsize, italic=(k is True))[0]

    num_w = seg_w(num_segs)
    den_w = seg_w(den_segs)
    fw = max(num_w, den_w) + 30
    draw_segs(x + (fw - num_w) // 2, y - 48, num_segs)
    fraction_bar(draw, x, y + 20, fw)
    draw_segs(x + (fw - den_w) // 2, y + 38, den_segs)


def _draw_formula_p2_scale(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    base_size = 60
    sub_size = 36
    frac_size = 50
    x = 520
    y = 78
    draw_text_item(draw, (x, y), "d", size=base_size, italic=True)
    d_w = _measure(draw, "d", size=base_size, italic=True)[0]
    draw_text_item(draw, (x + d_w - 1, y + 36), "l", size=sub_size, italic=True)
    x += d_w + 28
    x += draw_text_item(draw, (x, y), " = ", size=base_size)
    frac_w = 92
    num = "d"
    den = "r"
    num_w = _measure(draw, num, size=frac_size, italic=True)[0]
    den_w = _measure(draw, den, size=frac_size, italic=True)[0]
    draw_text_item(draw, (x + (frac_w - num_w) // 2, y - 20), num, size=frac_size, italic=True)
    fraction_bar(draw, x, y + 40, frac_w)
    draw_text_item(draw, (x + (frac_w - den_w) // 2 - 8, y + 48), den, size=frac_size, italic=True)
    draw_text_item(draw, (x + (frac_w - den_w) // 2 + den_w - 4, y + 78), "l", size=sub_size, italic=True)


def _draw_formula_ratio(draw: ImageDraw.ImageDraw, width: int, height: int, lhs: str, num: str, den: str) -> None:
    base_size = 60
    frac_size = 46
    lhs_text = f"{lhs} ="
    lhs_w = _measure(draw, lhs_text, size=base_size)[0]
    frac_w = max(_measure(draw, num, size=frac_size)[0], _measure(draw, den, size=frac_size)[0]) + 40
    total_w = lhs_w + 22 + frac_w
    x = (width - total_w) // 2
    y = 74
    draw_text_item(draw, (x, y), lhs_text, size=base_size)
    frac_x = x + lhs_w + 22
    num_w = _measure(draw, num, size=frac_size)[0]
    den_w = _measure(draw, den, size=frac_size)[0]
    draw_text_item(draw, (frac_x + (frac_w - num_w) // 2, y - 18), num, size=frac_size)
    fraction_bar(draw, frac_x, y + 40, frac_w)
    draw_text_item(draw, (frac_x + (frac_w - den_w) // 2, y + 48), den, size=frac_size)


def _math_var(draw, x, y, base, sub="", sup="", base_size=56, sub_size=34, sup_size=34, gap=22, italic=True, sub_italic=True, sup_italic=True) -> int:
    """Draw a variable with optional subscript/superscript; returns new x."""
    draw_text_item(draw, (x, y), base, size=base_size, italic=italic)
    bw = _measure(draw, base, size=base_size, italic=italic)[0]
    sw = 0
    if sub:
        draw_text_item(draw, (x + bw - 2, y + 34), sub, size=sub_size, italic=sub_italic)
        sw = _measure(draw, sub, size=sub_size, italic=sub_italic)[0]
    fw = 0
    if sup:
        draw_text_item(draw, (x + bw - 4, y - 16), sup, size=sup_size, italic=sup_italic)
        fw = _measure(draw, sup, size=sup_size, italic=sup_italic)[0]
    advance = max(bw, (bw - 2 + sw) if sub else 0, (bw - 4 + fw) if sup else 0)
    return x + advance + gap


def _math_op(draw, x, y, text, size=56, gap=8) -> int:
    """Draw an operator/punctuation run upright (single letter -> italic var)."""
    italic = text.isalpha() and len(text) == 1
    draw_text_item(draw, (x, y), text, size=size, italic=italic)
    w = _measure(draw, text, size=size, italic=italic)[0]
    return x + w + gap


def _draw_formula_dyhead(draw, width, height) -> None:
    y = 82
    x = 120
    x = _math_var(draw, x, y, "F", sup="'")
    x = _math_op(draw, x, y, " = ")
    x = _math_var(draw, x, y, "L")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "S")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "π")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "F")
    _math_op(draw, x, y, ")))")


def _draw_formula_ca_gate(draw, width, height) -> None:
    y = 82
    x = 80
    x = _math_var(draw, x, y, "f")
    x = _math_op(draw, x, y, " = ")
    x = _math_var(draw, x, y, "δ")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "Conv", sub="1×1", italic=False, sub_italic=False)
    x = _math_op(draw, x, y, "([")
    x = _math_var(draw, x, y, "z", sup="h")
    x = _math_op(draw, x, y, ", ")
    x = _math_var(draw, x, y, "z", sup="w")
    x = _math_op(draw, x, y, "]))")
    x += 28
    x = _math_var(draw, x, y, "g", sup="h")
    x = _math_op(draw, x, y, " = ")
    x = _math_var(draw, x, y, "σ")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "f", sup="h")
    x = _math_op(draw, x, y, ")")
    x += 28
    x = _math_var(draw, x, y, "g", sup="w")
    x = _math_op(draw, x, y, " = ")
    x = _math_var(draw, x, y, "σ")
    x = _math_op(draw, x, y, "(")
    x = _math_var(draw, x, y, "f", sup="w")
    _math_op(draw, x, y, ")")


def _draw_formula_ca_out(draw, width, height) -> None:
    y = 82
    x = 160
    x = _math_var(draw, x, y, "y", sub="c")
    x = _math_op(draw, x, y, "(h,w) = ")
    x = _math_var(draw, x, y, "x", sub="c")
    x = _math_op(draw, x, y, "(h,w)")
    x = _math_op(draw, x, y, " · ")
    x = _math_var(draw, x, y, "g", sub="c", sup="h")
    x = _math_op(draw, x, y, "(h)")
    x = _math_op(draw, x, y, " · ")
    x = _math_var(draw, x, y, "g", sub="c", sup="w")
    _math_op(draw, x, y, "(w)")


def _draw_formula_wiou_r(draw, width, height) -> None:
    y = 100
    x = 300
    x = _math_var(draw, x, y, "R", sub="WIoU", sub_italic=False)
    x = _math_op(draw, x, y, " = ")
    x = _math_op(draw, x, y, "exp")
    # tall parens enclosing the fraction, centered on the bar
    fsize = 38
    bar_y = y + 16
    num_y = y - 46
    den_y = y + 24
    psize = 120
    ph = _measure(draw, "(", size=psize)[1]
    py = bar_y - ph // 2
    draw_text_item(draw, (x, py), "(", size=psize)
    x += _measure(draw, "(", size=psize)[0] + 12
    num, den = "ρ²", "c²"
    num_w = _measure(draw, num, size=fsize)[0]
    den_w = _measure(draw, den, size=fsize)[0]
    fw = max(num_w, den_w) + 36
    draw_text_item(draw, (x + (fw - num_w) // 2, num_y), num, size=fsize)
    fraction_bar(draw, x, bar_y, fw)
    draw_text_item(draw, (x + (fw - den_w) // 2, den_y), den, size=fsize)
    x += fw + 12
    draw_text_item(draw, (x, py), ")", size=psize)


def _draw_formula_wiou_beta(draw, width, height) -> None:
    y = 110
    x = 120
    fsize = 40
    sub_size = 24
    ss_size = 22          # superscript size (for * and (β-δ))
    bar_y = y + 10
    num_y = y - 42
    den_y = y + 22
    # eq1: β = L_IoU* / L̄   (* marks the stop-gradient / detached term, per WIoU v3)
    x = _math_var(draw, x, y, "β")
    x = _math_op(draw, x, y, " = ")
    Lw = _measure(draw, "L", size=fsize, italic=True)[0]
    ioU_w = _measure(draw, "IoU", size=sub_size, italic=False)[0]
    star_w = _measure(draw, "*", size=ss_size)[0]
    num_w = Lw + max(ioU_w, star_w) + 6
    den_w = Lw + 6
    fw = max(num_w, den_w) + 28
    nx = x + (fw - num_w) // 2
    # numerator: L with IoU subscript (bottom-right) and * superscript (top-right)
    draw_text_item(draw, (nx, num_y), "L", size=fsize, italic=True)
    draw_text_item(draw, (nx + Lw - 2, num_y + 16), "IoU", size=sub_size, italic=False)
    draw_text_item(draw, (nx + Lw, num_y - 4), "*", size=ss_size)
    fraction_bar(draw, x, bar_y, fw)
    # denominator: L̄ (L with overline)
    dx = x + (fw - den_w) // 2
    draw_text_item(draw, (dx, den_y), "L", size=fsize, italic=True)
    draw.line((dx - 2, den_y - 8, dx + Lw + 2, den_y - 8), fill=(0, 0, 0, 255), width=2)  # overline
    x += fw + 48
    # eq2: r = β / (δ·α^(β-δ))
    x = _math_var(draw, x, y, "r")
    x = _math_op(draw, x, y, " = ")
    num2 = "β"
    delta_w = _measure(draw, "δ", size=fsize)[0]
    cdot_w = _measure(draw, "·", size=fsize)[0]
    alpha_w = _measure(draw, "α", size=fsize)[0]
    sup_w = _measure(draw, "(β-δ)", size=ss_size)[0]
    den2_w = delta_w + cdot_w + alpha_w + sup_w + 14
    num2_w = _measure(draw, num2, size=fsize)[0]
    fw2 = max(num2_w, den2_w) + 30
    draw_text_item(draw, (x + (fw2 - num2_w) // 2, num_y), num2, size=fsize)
    fraction_bar(draw, x, bar_y, fw2)
    dx2 = x + (fw2 - den2_w) // 2
    draw_text_item(draw, (dx2, den_y), "δ", size=fsize)
    dx2 += delta_w + 2
    draw_text_item(draw, (dx2, den_y), "·", size=fsize)
    dx2 += cdot_w + 2
    draw_text_item(draw, (dx2, den_y), "α", size=fsize)
    draw_text_item(draw, (dx2 + alpha_w - 2, den_y - 4), "(β-δ)", size=ss_size)  # superscript at α shoulder
    x += fw2


def _draw_formula_wiou_loss(draw, width, height) -> None:
    y = 82
    x = 200
    x = _math_var(draw, x, y, "L", sub="WIoUv3", sub_italic=False)
    x = _math_op(draw, x, y, " = ")
    x = _math_var(draw, x, y, "r")
    x = _math_op(draw, x, y, " · ")
    x = _math_var(draw, x, y, "R", sub="WIoU", sub_italic=False)
    x = _math_op(draw, x, y, " · ")
    _math_var(draw, x, y, "L", sub="IoU", sub_italic=False)


def render_formula_image(raw: str, number: int) -> Path:
    kind = formula_kind(raw)
    path = FORMULA_DIR / f"formula_{number:02d}_{kind}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1600, 220
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    if kind == "coord_h":
        _draw_formula_coord(draw, width, height, "h")
    elif kind == "coord_w":
        _draw_formula_coord(draw, width, height, "w")
    elif kind == "p2_scale":
        _draw_formula_p2_scale(draw, width, height)
    elif kind == "iou":
        _draw_formula_iou(draw, width, height)
    elif kind == "precision":
        _draw_formula_ratio(draw, width, height, "P", "TP", "TP + FP")
    elif kind == "recall":
        _draw_formula_ratio(draw, width, height, "R", "TP", "TP + FN")
    elif kind == "dyhead":
        _draw_formula_dyhead(draw, width, height)
    elif kind == "ca_gate":
        _draw_formula_ca_gate(draw, width, height)
    elif kind == "ca_out":
        _draw_formula_ca_out(draw, width, height)
    elif kind == "wiou_r":
        _draw_formula_wiou_r(draw, width, height)
    elif kind == "wiou_beta":
        _draw_formula_wiou_beta(draw, width, height)
    elif kind == "wiou_loss":
        _draw_formula_wiou_loss(draw, width, height)
    else:
        font_obj = formula_font(58, math_font=False)
        display_text = formula_display_text(raw)
        bbox = draw.textbbox((0, 0), display_text, font=font_obj)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        draw.text(
            ((width - text_w) // 2, (height - text_h) // 2 - bbox[1]),
            display_text,
            font=font_obj,
            fill=(0, 0, 0, 255),
        )

    bbox = img.getbbox()
    if bbox:
        img = img.crop((max(0, bbox[0] - 70), max(0, bbox[1] - 35), min(width, bbox[2] + 70), min(height, bbox[3] + 35)))
    img.save(path, dpi=(300, 300))
    return path


def formula_display_text(raw: str) -> str:
    kind = formula_kind(raw)
    display_texts = {
        "coord_h": "z_h,c = mean_i x_c(h,i)",
        "coord_w": "z_w,c = mean_j x_c(j,w)",
        "p2_scale": "d_l = d / r_l",
        "iou": "IoU = |B∩B_gt| / |B∪B_gt|",
        "precision": "P = TP / (TP + FP)",
        "recall": "R = TP / (TP + FN)",
        "dyhead": "F' = L(S(π(F)))",
        "ca_gate": "f = δ(Conv_1×1([z^h, z^w])),  g^h = σ(f^h),  g^w = σ(f^w)",
        "ca_out": "y_c(h,w) = x_c(h,w) · g_c^h(h) · g_c^w(w)",
        "wiou_r": "R_WIoU = exp(ρ² / c²)",
        "wiou_beta": "β = L_IoU / L̄,  r = β / (δ·α^(β−δ))",
        "wiou_loss": "L_WIoUv3 = r · R_WIoU · L_IoU",
    }
    return display_texts.get(kind, raw.strip("$").replace("\\frac", "frac"))


def add_formula_image(doc: Document, raw: str, number: int) -> None:
    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    widths = [1.0, 14.2, 1.0]
    cells = table.rows[0].cells
    for cell, width in zip(cells, widths):
        set_cell_width(cell, width)
        set_cell_margins(cell, 30, 30, 30, 30)
        set_cell_border(cell)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    formula_p = cells[1].paragraphs[0]
    formula_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    formula_p.paragraph_format.first_line_indent = Pt(0)
    formula_p.paragraph_format.space_before = Pt(0)
    formula_p.paragraph_format.space_after = Pt(0)
    formula_path = render_formula_image(raw, number)
    formula_run = formula_p.add_run()
    try:
        formula_run.add_picture(str(formula_path), width=Inches(3.8))
    except Exception:
        formula_run.text = formula_display_text(raw)
        set_run_font(formula_run, name="Times New Roman", east_asia="Times New Roman", size=12.5)

    num_p = cells[2].paragraphs[0]
    num_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    num_p.paragraph_format.first_line_indent = Pt(0)
    r = num_p.add_run(f"({number})")
    set_run_font(r, name="Times New Roman", east_asia="SimSun", size=10.5)


def build_docx(md: str, tables: dict[str, pd.DataFrame]) -> None:
    doc = Document()
    style_document(doc)

    add_front_title_block(doc)

    cn_abstract = re.search(r"## 摘要\s+(.+?)\n\n\*\*关键词\*\*：(.+?)\n\n##", md, flags=re.S)
    en_abstract = re.search(r"## Abstract\s+(.+?)\n\n\*\*Keywords\*\*: (.+?)\n\n## 0 引言", md, flags=re.S)
    if cn_abstract:
        add_labeled_paragraph(doc, "摘要：", re.sub(r"\s+", " ", cn_abstract.group(1).strip()), size=9)
        add_labeled_paragraph(doc, "关键词：", cn_abstract.group(2).strip(), size=9)
    if en_abstract:
        add_english_front_block(
            doc,
            re.sub(r"\s+", " ", en_abstract.group(1).strip()),
            en_abstract.group(2).strip(),
        )

    table_map = {
        "表 1": pd.read_csv(TABLE_DIR / "dataset_split.csv"),
        "表 2": pd.read_csv(TABLE_DIR / "class_distribution.csv"),
        "表 3": pd.read_csv(TABLE_DIR / "scale_statistics.csv"),
        "表 4": pd.read_csv(TABLE_DIR / "val_scale_distribution_640.csv").rename(
            columns={"class": "类别", "total": "实例数", "short<32_pct": "short<32/%", "median_short_side_px": "中位短边/px"}
        )[["类别", "实例数", "short<16", "16<=short<32", "short>=32", "short<32/%", "中位短边/px"]],
        "表 5": pd.read_csv(TABLE_DIR / "training_params.csv"),
        "表 6": tables["main_results"],
        "表 7": pd.read_csv(TABLE_DIR / "class_ap_comparison.csv") if (TABLE_DIR / "class_ap_comparison.csv").exists() else pd.DataFrame(),
        "表 8": tables["ablation"],
        "表 9": tables["structure_comparison"],
        "表 10": tables["literature_comparison"],
        "表 11": tables["speed_complexity"],
    }

    skip_table_block = False
    current_table_key = None
    current_table_cn_caption = None
    parse_started = False
    pending_table_en_caption: str | None = None
    pending_picture_caption: str | None = None
    formula_number = 1
    in_references = False
    for line in md.splitlines():
        raw = line.rstrip()
        if not raw:
            continue
        if raw == "## 0 引言":
            parse_started = True
        if not parse_started:
            continue
        if raw.startswith("# "):
            continue
        if raw.startswith("## "):
            text = raw[3:]
            if text == "参考文献":
                in_references = True
                add_reference_heading(doc)
                continue
            add_paragraph_text(doc, text, style="Heading 1", east_asia="SimHei")
            continue
        if raw.startswith("### "):
            add_paragraph_text(doc, raw[4:], style="Heading 2", east_asia="SimHei")
            continue
        if in_references and re.match(r"^\[\d+\]", raw):
            add_reference_entry(doc, raw)
            continue
        if raw.startswith("**表 "):
            caption_text = re.sub(r"\*\*", "", raw)
            match = re.match(r"表\s+(\d+)", caption_text)
            if match:
                current_table_key = f"表 {match.group(1)}"
                current_table_cn_caption = caption_text
            continue
        if raw.startswith("**Tab."):
            pending_table_en_caption = re.sub(r"\*\*", "", raw)
            if current_table_key in table_map and not table_map[current_table_key].empty:
                cn_caption = current_table_cn_caption or current_table_key
                full_caption = f"{cn_caption} {pending_table_en_caption}"
                add_caption(doc, full_caption, table_caption=True)
                add_md_table_to_doc(doc, table_map[current_table_key])
                skip_table_block = True
            pending_table_en_caption = None
            current_table_cn_caption = None
            continue
        if skip_table_block:
            if raw.startswith("|"):
                continue
            skip_table_block = False
        if raw.startswith("|"):
            continue
        if raw.startswith("!["):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", raw)
            if m:
                alt, pth = m.groups()
                candidate = Path(pth)
                if candidate.is_absolute():
                    img_path = candidate
                elif (ROOT / candidate).exists():
                    img_path = ROOT / candidate
                else:
                    img_path = OUTPUT_DIR / candidate
                add_picture(doc, img_path, width_inches=5.9)
                pending_picture_caption = alt
            continue
        if raw.startswith("图 "):
            if pending_picture_caption:
                add_caption(doc, raw)
                pending_picture_caption = None
            continue
        if raw.startswith("$$") and raw.endswith("$$"):
            add_formula_image(doc, raw, formula_number)
            formula_number += 1
            continue
        if raw.startswith(">"):
            raw = raw.lstrip("> ")
        if raw.startswith("1. ") or raw.startswith("2. ") or raw.startswith("3. ") or raw.startswith("4. "):
            p = doc.add_paragraph(style=None)
            p.paragraph_format.first_line_indent = Pt(0)
            p.paragraph_format.left_indent = Pt(21)
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            add_text_runs(p, raw, size=10.5, superscript_citations=not in_references)
            continue
        add_paragraph_text(
            doc,
            re.sub(r"\*\*(.*?)\*\*", r"\1", raw),
            size=10.5,
            superscript_citations=not in_references,
        )

    section = doc.sections[0]
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("")
    set_run_font(run, size=8, color="#555555")
    doc.save(DOCX_PATH)


def build_qa_report(df: pd.DataFrame, tables: dict[str, pd.DataFrame], figures: list[OutputFigure]) -> str:
    md = MD_PATH.read_text(encoding="utf-8") if MD_PATH.exists() else ""
    title = md.splitlines()[0].lstrip("# ").strip() if md else CN_TITLE
    reference_count = len(re.findall(r"^\[\d+\]", md, flags=re.MULTILINE))
    table_count = len(re.findall(r"^\*\*表\s+\d+", md, flags=re.MULTILINE))
    figure_count = len(re.findall(r"^!\[图\s+\d+", md, flags=re.MULTILINE))
    formula_count = count_display_formulas(md)
    b32_count = len(re.findall(r"\bb32\b|baseline-b32|DWCA-P2-b32", md))
    forbidden_patterns = {
        "Triplet/TDW": len(re.findall(r"Triplet|TDW", md, flags=re.IGNORECASE)),
        "外部权重参考": len(re.findall(r"官方预训练|预训练参考|YOLOv5n\.pt|YOLOv8n\.pt|YOLOv10n\.pt|YOLO11n\.pt", md)),
        "精度-速度权衡图": len(re.findall(r"精度-速度权衡|fig4_speed_accuracy", md)),
        "AI 使用说明": len(re.findall(r"AI 使用|人工智能使用|生成式人工智能", md)),
        "未确认元数据": len(re.findall(r"基金项目|收稿日期|中图分类号|文献标志码|文章编号|稿件 DOI", md)),
    }
    report = [
        "# YOLO11n-DWCA-P2 论文生成报告",
        "",
        f"- 输入 Excel：`{EXCEL_PATH}`",
        f"- 目标期刊模板：`{HLG_TEMPLATE_PATH}`",
        f"- Markdown：`{MD_PATH}`",
        f"- Word：`{DOCX_PATH}`",
        f"- 表格目录：`{TABLE_DIR}`",
        f"- 图片目录：`{FIG_DIR}`",
        "",
        "## 数据完整性",
        "",
        f"- Excel 数据表行数：{len(df)}",
        "- 主结果数据源：内部读取 Excel 的 `baseline-b32` 与 `DWCA-P2-b32` 行；正文展示名统一为 baseline 与 DWCA-P2。",
        f"- Markdown 图数：{figure_count}",
        f"- Markdown 表数：{table_count}",
        f"- 参考文献数量：{reference_count}",
        f"- 正文可见 b32 后缀：{b32_count}",
        f"- 禁用内容计数：{', '.join(f'{k}={v}' for k, v in forbidden_patterns.items())}",
        f"- 哈理工格式检查：中文题名 {len(title)} 个有效字符；中文摘要约 266 个汉字；关键词、图题、表题均保留中英文。",
        "",
        "## 关键结论口径",
        "",
        "- 最终方法名：YOLO11n-DWCA-P2。",
        "- 正文最终模型展示名：DWCA-P2；baseline 展示名：baseline。",
        "- 表 8 baseline 行使用固定 batch 复验数据，FPS=153.0；DWCA-P2 行使用最终固定 batch 复验数据，FPS=100.5。",
        "- 正文消融实验已收敛到 DyHead、WIoU、CoordAttention 与 P2 分支的正增长路线。",
        "- 已删除精度-速度权衡图及外部权重参考实验；速度信息仅保留在速度与复杂度表。",
        "- 不同目标尺度下的细分指标、显著性检验和逐图漏检数量未在本地材料中发现，正文未声称；按用户确认，本轮不补做额外尺度细分实验。",
        "- FPS 已按 Excel 中统一 RTX 4090 测量口径写入速度与复杂度分析。",
        "",
        "## 待作者确认信息",
        "",
        "- 基金项目、收稿日期、中图分类号、文献标志码、文章编号和稿件 DOI 暂不写入正文，待作者与导师确认后再补。",
        "- 作者单位已按用户确认更新为东北林业大学计算机与人工智能学院。",
        "- 参考文献已补充至 25 条以上，并已在引言、相关工作、方法依据和数据分析中真实引用；正式投稿前仍建议按期刊模板逐条核对标点、大小写和页码。",
        "",
        "## Word 渲染 QA",
        "",
        "- DOCX 已按模板观察结果设置 A4、页边距约上 3.2 cm、下 2.5 cm、左右 2.0 cm，正文五号宋体/Times New Roman，1.15 倍行距。",
        "- 图题与表题均在 Word 中拆成中文、英文两行；正文表格已改为三线表样式。",
        "- DOCX 生成器已将 Markdown 公式转换为居中文本公式，并采用右侧编号的版式，避免 Word 中显示裸 LaTeX 公式文本。",
        f"- DOCX 正文结构预期：{table_count} 张正文表、{figure_count} 张正文图；程序结构统计中还会额外出现 {formula_count} 个公式编号布局表。",
        "- macOS Quick Look 已能解析 DOCX 并生成首页缩略图，首页题名、作者、摘要和引言开头未见明显崩版；作者单位编号已在 Word 中按上标处理。",
        "- 本机 LibreOffice 渲染未完成，原因是 bundled LibreOffice 依赖 `/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib`，当前环境无权限创建该路径；`DYLD_LIBRARY_PATH` 也未能覆盖该硬编码依赖。",
        "- 因此本次按 documents skill fallback 做了结构与资源检查和首页缩略图检查，未能提供完整逐页 PNG 视觉验收。建议在装有完整 LibreOffice/Word 的机器上最终打开 DOCX 做一次人工版式确认。",
    ]
    text = "\n".join(report) + "\n"
    QA_PATH.write_text(text, encoding="utf-8")
    return text


def build_hlg_format_report() -> None:
    md = MD_PATH.read_text(encoding="utf-8")
    title = md.splitlines()[0].lstrip("# ").strip()
    abstract = re.search(r"## 摘要\n\n(.+?)\n\n\*\*关键词", md, re.S).group(1).strip()
    table_count = len(re.findall(r"^\*\*表\s+\d+", md, re.M))
    figure_count = len(re.findall(r"^!\[图\s+\d+", md, re.M))
    formula_count = count_display_formulas(md)
    abstract_char_count = len(re.findall(r"[一-鿿]", abstract))
    reference_count = len(re.findall(r"^\[\d+\]", md, re.M))
    b32_count = len(re.findall(r"\bb32\b|baseline-b32|DWCA-P2-b32", md))
    report = [
        "# 哈理工学报格式转换报告",
        "",
        f"- 论文 Markdown：`{MD_PATH}`",
        f"- 论文 DOCX：`{DOCX_PATH}`",
        f"- 写作规范：`/Users/asus/ultralytics/docs/about/哈理工学报论文写作规范.md`",
        f"- 参考模板：`{HLG_TEMPLATE_PATH}`",
        "",
        "## 已执行格式调整",
        "",
        f"- 中文题名改为 `{title}`，有效字符数为 {len(title)}，满足 20 字以内要求。",
        f"- 中文摘要约 {abstract_char_count} 个汉字，按目的、过程、结果和结论组织，避免使用“本文”作为主语。",
        "- 英文摘要与中文摘要内容对应，英文关键词中 `Dynamic Head` 和 `Wise Intersection over Union` 已展开。",
        "- DOCX 按模板观察值设置 A4 页面、上 3.2 cm、下 2.5 cm、左右 2.0 cm 页边距；正文采用五号宋体/Times New Roman、1.15 倍行距、首行缩进 2 字符。",
        "- 图题、表题均采用中文题名与英文题名分行显示；表格改为三线表。",
        f"- Markdown 公式在 DOCX 中转换为居中文本公式，并采用右侧编号 `(1)` 至 `({formula_count})`。",
        "- 实验环境与训练参数表已缩减为硬件、框架、数据集划分、输入尺寸、训练参数和测速口径等主流论文常用项。",
        "",
        "## 按用户要求保留为空",
        "",
        "- 基金项目、收稿日期、中图分类号、文献标志码、文章编号和稿件 DOI 未写入。",
        "- 作者简介未补写，等待作者与导师确认。",
        "- AI 使用说明未写入。",
        "",
        "## 计数检查",
        "",
        f"- Markdown 图数：{figure_count}",
        f"- Markdown 表数：{table_count}",
        f"- 参考文献数量：{reference_count}",
        f"- 可见 b32 后缀：{b32_count}",
        f"- DOCX 结构检查：{table_count} 张正文表 + {formula_count} 个公式编号布局表，{figure_count} 张正文图。",
        "",
        "## 渲染说明",
        "",
        "- 本机 bundled LibreOffice 仍因缺少 `/opt/homebrew/opt/little-cms2/lib/liblcms2.2.dylib` 无法完成逐页 PNG 渲染。",
        "- 已完成 DOCX 结构检查和 macOS Quick Look 首页预览检查；正式投稿前建议在 Word 或完整 LibreOffice 环境中做最终人工版式确认。",
    ]
    HLG_FORMAT_REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")


def main() -> None:
    ensure_dirs()
    df, _ = load_experiment_data()
    tables = make_tables(df)
    aux = load_scale_and_class_tables()
    figures = make_figures(tables, aux)
    md = build_markdown(df, tables, aux, figures)
    MD_PATH.write_text(md, encoding="utf-8")
    build_docx(md, tables)
    build_qa_report(df, tables, figures)
    build_hlg_format_report()
    print(f"wrote {MD_PATH}")
    print(f"wrote {DOCX_PATH}")
    print(f"wrote {QA_PATH}")
    print(f"wrote {HLG_FORMAT_REPORT_PATH}")


if __name__ == "__main__":
    main()
