# -*- coding: utf-8 -*-
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "docs" / "paper_outputs" / "figures"
OUT_PATH = FIG_DIR / "fig2_dwca_p2_architecture_compact.png"

FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ARIAL_UNICODE = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

PALETTE = {
    "blue": "#2563EB",
    "orange": "#F97316",
    "green": "#A7F3D0",
    "green_o": "#047857",
    "purple": "#DDD6FE",
    "purple_o": "#6D28D9",
    "cyan": "#67E8F9",
    "cyan_o": "#0E7490",
    "yellow": "#FDE68A",
    "yellow_o": "#B45309",
    "concat": "#FED7AA",
    "concat_o": "#9A3412",
    "detect": "#FECACA",
    "detect_o": "#BE123C",
    "grey": "#94A3B8",
    "light": "#E5E7EB",
    "muted": "#4B5563",
    "ink": "#111827",
    "bg": "#FFFFFF",
}


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def font(size: int, bold: bool = False, cjk: bool = True) -> ImageFont.ImageFont:
    candidates = []
    if cjk:
        candidates.append(FONT_CJK)
    candidates.extend([FONT_ARIAL_BOLD if bold else FONT_ARIAL, FONT_ARIAL_UNICODE])
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.ImageFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def centered(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, fnt: ImageFont.ImageFont, fill: str = PALETTE["ink"]) -> None:
    tw, th = text_size(draw, text, fnt)
    draw.text((xy[0] - tw / 2, xy[1] - th / 2), text, font=fnt, fill=hex_to_rgb(fill))


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str, width: int = 2, radius: int = 9) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=hex_to_rgb(fill), outline=hex_to_rgb(outline), width=width)


def arrow(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], fill: str = PALETTE["ink"], width: int = 3) -> None:
    if len(points) < 2:
        return
    for start, end in zip(points[:-2], points[1:-1]):
        draw.line([start, end], fill=hex_to_rgb(fill), width=width)
    start, end = points[-2], points[-1]
    draw.line([start, end], fill=hex_to_rgb(fill), width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head_len = 10
    for delta in (math.pi * 0.82, -math.pi * 0.82):
        x = end[0] + head_len * math.cos(angle + delta)
        y = end[1] + head_len * math.sin(angle + delta)
        draw.line([end, (x, y)], fill=hex_to_rgb(fill), width=width)


def cx(box: tuple[int, int, int, int]) -> int:
    return (box[0] + box[2]) // 2


def cy(box: tuple[int, int, int, int]) -> int:
    return (box[1] + box[3]) // 2


def left(box: tuple[int, int, int, int]) -> tuple[int, int]:
    return (box[0], cy(box))


def right(box: tuple[int, int, int, int]) -> tuple[int, int]:
    return (box[2], cy(box))


def top(box: tuple[int, int, int, int]) -> tuple[int, int]:
    return (cx(box), box[1])


def bottom(box: tuple[int, int, int, int]) -> tuple[int, int]:
    return (cx(box), box[3])


def shape(channels: int, hw: int) -> str:
    return f"{channels} × {hw} × {hw}"


def style(name: str) -> tuple[str, str]:
    if name in {"Conv", "Upsample"}:
        return PALETTE["green"], PALETTE["green_o"]
    if name in {"C3k2", "SPPF"}:
        return PALETTE["purple"], PALETTE["purple_o"]
    if name == "C2PSA":
        return PALETTE["cyan"], PALETTE["cyan_o"]
    if name == "CoordAttention":
        return PALETTE["yellow"], PALETTE["yellow_o"]
    if name == "Concat":
        return PALETTE["concat"], PALETTE["concat_o"]
    if name == "Detect":
        return PALETTE["detect"], PALETTE["detect_o"]
    return "#F1F5F9", "#475569"


def block(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    name: str,
    sub: str,
    label_font: ImageFont.ImageFont,
    shape_font: ImageFont.ImageFont,
    *,
    accent: str | None = None,
) -> None:
    fill, outline = style(name)
    if accent:
        outline = accent
    rounded(draw, box, fill, outline, width=3 if accent else 2)
    centered(draw, (cx(box), cy(box) - 12), name, label_font)
    centered(draw, (cx(box), cy(box) + 15), sub, shape_font, PALETTE["muted"])


def dashed_section(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, fnt: ImageFont.ImageFont) -> None:
    x1, y1, x2, y2 = box
    dash, gap = 16, 10
    x = x1
    while x < x2:
        draw.line((x, y1, min(x + dash, x2), y1), fill=hex_to_rgb(PALETTE["grey"]), width=2)
        draw.line((x, y2, min(x + dash, x2), y2), fill=hex_to_rgb(PALETTE["grey"]), width=2)
        x += dash + gap
    y = y1
    while y < y2:
        draw.line((x1, y, x1, min(y + dash, y2)), fill=hex_to_rgb(PALETTE["grey"]), width=2)
        draw.line((x2, y, x2, min(y + dash, y2)), fill=hex_to_rgb(PALETTE["grey"]), width=2)
        y += dash + gap
    centered(draw, ((x1 + x2) / 2, y2 + 34), label, fnt)


def draw_compact_architecture(path: Path = OUT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    w, h = 1780, 1380
    img = Image.new("RGB", (w, h), hex_to_rgb(PALETTE["bg"]))
    draw = ImageDraw.Draw(img)

    title_font = font(42, bold=True)
    subtitle_font = font(21)
    section_font = font(27, bold=True)
    label_font = font(20, bold=True)
    shape_font = font(16)
    tiny_font = font(17)

    centered(draw, (w / 2, 54), "YOLO11n-DWCA-P2 网络结构示意图（紧凑版）", title_font)
    centered(draw, (w / 2, 98), "Compact reference-style architecture diagram of YOLO11n-DWCA-P2", subtitle_font, PALETTE["muted"])

    bw, bh = 150, 56
    backbone_x = 82
    neck_x0 = 615
    neck_dx = 162
    head_x = 1480

    backbone_top = 142
    backbone_gap = 73
    bb_w, bb_h = 176, 50

    bb_items = [
        ("input", "Input", shape(3, 640)),
        ("0", "Conv", shape(16, 320)),
        ("1", "Conv", shape(32, 160)),
        ("2", "C3k2", shape(64, 160)),
        ("3", "Conv", shape(64, 80)),
        ("4", "C3k2", shape(128, 80)),
        ("5", "CoordAttention", shape(128, 80)),
        ("6", "Conv", shape(128, 40)),
        ("7", "C3k2", shape(128, 40)),
        ("8", "Conv", shape(256, 20)),
        ("9", "C3k2", shape(256, 20)),
        ("10", "SPPF", shape(256, 20)),
        ("11", "C2PSA", shape(256, 20)),
    ]
    bb: dict[str, tuple[int, int, int, int]] = {}
    for i, (key, _, _) in enumerate(bb_items):
        y = backbone_top + i * backbone_gap
        bb[key] = (backbone_x, y, backbone_x + bb_w, y + bb_h)

    neck_specs = {
        "12": (0, 704, "Upsample", shape(256, 40)),
        "13": (1, 704, "Concat", shape(384, 40)),
        "14": (2, 704, "C3k2", shape(128, 40)),
        "15": (2, 558, "Upsample", shape(128, 80)),
        "16": (1, 558, "Concat", shape(256, 80)),
        "17": (0, 558, "C3k2", shape(64, 80)),
        "18": (0, 412, "Upsample", shape(64, 160)),
        "19": (1, 412, "Concat", shape(128, 160)),
        "20": (2, 412, "C3k2", shape(32, 160)),
        "21": (2, 520, "Conv", shape(32, 80)),
        "22": (3, 520, "Concat", shape(96, 80)),
        "23": (4, 520, "C3k2", shape(64, 80)),
        "24": (4, 680, "Conv", shape(64, 40)),
        "25": (3, 680, "Concat", shape(192, 40)),
        "26": (2, 830, "C3k2", shape(128, 40)),
        "27": (2, 962, "Conv", shape(128, 20)),
        "28": (1, 962, "Concat", shape(384, 20)),
        "29": (0, 962, "C3k2", shape(256, 20)),
    }
    n: dict[str, tuple[int, int, int, int]] = {}
    for key, (col, y, _, _) in neck_specs.items():
        x = neck_x0 + col * neck_dx
        n[key] = (x, y, x + bw, y + bh)

    det = {
        "P2": (head_x, cy(n["20"]) - 30, head_x + 190, cy(n["20"]) + 30),
        "P3": (head_x, cy(n["23"]) - 30, head_x + 190, cy(n["23"]) + 30),
        "P4": (head_x, cy(n["26"]) - 30, head_x + 190, cy(n["26"]) + 30),
        "P5": (head_x, cy(n["29"]) - 30, head_x + 190, cy(n["29"]) + 30),
    }

    bb_frame = (42, 120, 300, 1110)
    neck_frame = (520, 120, 1420, 1110)
    head_frame = (1440, 120, 1732, 1110)
    dashed_section(draw, bb_frame, "Backbone", section_font)
    dashed_section(draw, neck_frame, "Neck", section_font)
    dashed_section(draw, head_frame, "Head", section_font)

    for key, name, sub in bb_items:
        block(draw, bb[key], name, sub, label_font, shape_font, accent=PALETTE["yellow_o"] if key == "5" else None)
    for prev, curr in zip(bb_items[:-1], bb_items[1:]):
        arrow(draw, [bottom(bb[prev[0]]), top(bb[curr[0]])], PALETTE["muted"], 2)

    for key, (_, _, name, sub) in neck_specs.items():
        accent = PALETTE["blue"] if key in {"19", "20", "21"} else None
        block(draw, n[key], name, sub, label_font, shape_font, accent=accent)

    for lane, label_y in [("P2/4", 440), ("P3/8", 575), ("P4/16", 720), ("P5/32", 990)]:
        centered(draw, (neck_frame[0] + 35, label_y), lane, tiny_font, PALETTE["muted"])

    # Top-down path, arranged in a compact zig-zag like the reference figure.
    chain_edges = [
        ("12", "13", PALETTE["ink"], 3),
        ("13", "14", PALETTE["ink"], 3),
        ("14", "15", PALETTE["ink"], 3),
        ("15", "16", PALETTE["ink"], 3),
        ("16", "17", PALETTE["ink"], 3),
        ("17", "18", PALETTE["ink"], 3),
        ("18", "19", PALETTE["blue"], 4),
        ("19", "20", PALETTE["blue"], 4),
        ("20", "21", PALETTE["blue"], 4),
        ("21", "22", PALETTE["ink"], 3),
        ("22", "23", PALETTE["ink"], 3),
        ("23", "24", PALETTE["ink"], 3),
        ("24", "25", PALETTE["ink"], 3),
        ("25", "26", PALETTE["ink"], 3),
        ("26", "27", PALETTE["ink"], 3),
        ("27", "28", PALETTE["ink"], 3),
        ("28", "29", PALETTE["ink"], 3),
    ]
    for src, dst, color, width in chain_edges:
        sb, db = n[src], n[dst]
        if abs(cy(sb) - cy(db)) < 4:
            pts = [right(sb), left(db)] if sb[0] < db[0] else [left(sb), right(db)]
        elif abs(cx(sb) - cx(db)) < 4:
            pts = [bottom(sb), top(db)] if sb[1] < db[1] else [top(sb), bottom(db)]
        else:
            if db[1] < sb[1]:
                mid_y = db[3] + 18 if db[3] < sb[1] else cy(db)
                start = top(sb)
                end = right(db) if db[0] < sb[0] else left(db)
            else:
                mid_y = db[1] - 18 if sb[3] < db[1] else cy(db)
                start = bottom(sb)
                end = right(db) if db[0] < sb[0] else left(db)
            pts = [start, (cx(sb), mid_y), (end[0], mid_y), end]
        arrow(draw, pts, color, width)

    # Lateral / skip inputs are routed through separate left-side corridors to avoid crossings.
    arrow(draw, [right(bb["11"]), (385, cy(bb["11"])), (385, cy(n["12"])), left(n["12"])], PALETTE["ink"], 3)
    arrow(draw, [right(bb["7"]), (430, cy(bb["7"])), (430, n["13"][1] - 22), (cx(n["13"]), n["13"][1] - 22), top(n["13"])], PALETTE["ink"], 3)
    arrow(draw, [right(bb["5"]), (395, cy(bb["5"])), (395, n["16"][1] - 22), (cx(n["16"]), n["16"][1] - 22), top(n["16"])], PALETTE["orange"], 3)
    arrow(draw, [right(bb["2"]), (360, cy(bb["2"])), (360, n["19"][1] - 30), (cx(n["19"]), n["19"][1] - 30), top(n["19"])], PALETTE["blue"], 4)
    arrow(draw, [right(bb["11"]), (330, cy(bb["11"])), (330, n["28"][1] - 24), (cx(n["28"]), n["28"][1] - 24), top(n["28"])], PALETTE["ink"], 3)

    # PAN skip fusions stay inside the neck but use top corridors, not box centers.
    p3_skip_y = n["22"][1] - 28
    arrow(draw, [top(n["17"]), (cx(n["17"]), p3_skip_y), (cx(n["22"]), p3_skip_y), top(n["22"])], PALETTE["ink"], 3)
    arrow(draw, [right(n["14"]), (neck_x0 + 3 * neck_dx - 16, cy(n["14"])), (neck_x0 + 3 * neck_dx - 16, n["25"][1] - 28), (cx(n["25"]), n["25"][1] - 28), top(n["25"])], PALETTE["ink"], 3)

    det_labels = {
        "P2": ("Detect P2/4", "tiny · 160 × 160"),
        "P3": ("Detect P3/8", "small · 80 × 80"),
        "P4": ("Detect P4/16", "medium · 40 × 40"),
        "P5": ("Detect P5/32", "large · 20 × 20"),
    }
    for lane, box in det.items():
        name, sub = det_labels[lane]
        block(draw, box, "Detect", sub, label_font, shape_font, accent=PALETTE["blue"] if lane == "P2" else None)
        centered(draw, (cx(box), cy(box) - 12), name, label_font, PALETTE["ink"])

    arrow(draw, [right(n["20"]), (head_x - 36, cy(n["20"])), left(det["P2"])], PALETTE["blue"], 4)
    arrow(draw, [right(n["23"]), (head_x - 36, cy(n["23"])), left(det["P3"])], PALETTE["ink"], 3)
    arrow(draw, [right(n["26"]), (head_x - 36, cy(n["26"])), left(det["P4"])], PALETTE["ink"], 3)
    p5_bus_y = n["29"][3] + 34
    arrow(draw, [bottom(n["29"]), (cx(n["29"]), p5_bus_y), (head_x - 36, p5_bus_y), (head_x - 36, cy(det["P5"])), left(det["P5"])], PALETTE["ink"], 3)

    note = (1465, 1040, 1708, 1133)
    rounded(draw, note, "#FFF1F2", PALETTE["detect_o"], width=2, radius=12)
    centered(draw, (cx(note), note[1] + 25), "DyHeadDetect", label_font, PALETTE["detect_o"])
    centered(draw, (cx(note), note[1] + 52), "scale + spatial + task", tiny_font, PALETTE["muted"])
    centered(draw, (cx(note), note[1] + 77), "WIoU v3 · train-only", tiny_font, PALETTE["detect_o"])

    legend_y = 1160
    legend = [
        ("P2 high-resolution branch", PALETTE["blue"], 4),
        ("CoordAttention lateral", PALETTE["orange"], 3),
        ("FPN / PAN main path", PALETTE["ink"], 3),
    ]
    lx = 120
    for text, color, line_w in legend:
        draw.line((lx, legend_y, lx + 80, legend_y), fill=hex_to_rgb(color), width=line_w)
        draw.text((lx + 96, legend_y - 13), text, font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
        lx += 475

    module_y = 1210
    modules = [
        ("Conv / Upsample", PALETTE["green"], PALETTE["green_o"]),
        ("C3k2 / SPPF / C2PSA", PALETTE["purple"], PALETTE["purple_o"]),
        ("Concat", PALETTE["concat"], PALETTE["concat_o"]),
        ("Detect", PALETTE["detect"], PALETTE["detect_o"]),
        ("CoordAttention", PALETTE["yellow"], PALETTE["yellow_o"]),
    ]
    lx = 120
    for text, fill, outline in modules:
        rounded(draw, (lx, module_y, lx + 34, module_y + 24), fill, outline, width=2, radius=5)
        draw.text((lx + 44, module_y - 1), text, font=tiny_font, fill=hex_to_rgb(PALETTE["ink"]))
        lx += 320

    img.save(path, dpi=(300, 300))


if __name__ == "__main__":
    draw_compact_architecture()
    print(OUT_PATH)
