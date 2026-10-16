# -*- coding: utf-8 -*-
"""Generate 4 module structure figures for §3.3-3.6 (PIL, fig2-style, no in-image titles, proper math labels)."""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = ROOT / "docs" / "paper_outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_TIMES = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"
FONT_TIMES_ITALIC = "/System/Library/Fonts/Supplemental/Times New Roman Italic.ttf"
FONT_ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_ARIAL_UNICODE = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"

PALETTE = {
    "blue": "#2563EB", "blue_o": "#1E40AF", "orange": "#F97316", "orange_o": "#9A3412",
    "green": "#A7F3D0", "green_o": "#047857", "purple": "#DDD6FE", "purple_o": "#6D28D9",
    "cyan": "#67E8F9", "cyan_o": "#0E7490", "yellow": "#FDE68A", "yellow_o": "#B45309",
    "concat": "#FED7AA", "concat_o": "#9A3412", "detect": "#FECACA", "detect_o": "#BE123C",
    "grey": "#94A3B8", "grey_o": "#475569", "light": "#E5E7EB", "muted": "#4B5563",
    "ink": "#111827", "bg": "#FFFFFF",
}


def hex_rgb(c: str):
    if not c.startswith("#"):
        c = PALETTE[c]
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def font(size, bold=False, italic=False, cjk=True):
    if cjk:
        cand = [FONT_CJK, FONT_ARIAL_UNICODE]
    elif italic:
        cand = [FONT_TIMES_ITALIC, FONT_ARIAL]
    elif bold:
        cand = [FONT_ARIAL_BOLD, FONT_ARIAL_UNICODE]
    else:
        cand = [FONT_ARIAL, FONT_ARIAL_UNICODE]
    for p in cand:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def tsize(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def box(d, xy, fill, outline, width=3, radius=14):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=hex_rgb(fill), outline=hex_rgb(outline), width=width)


def label(d, xy, s, f, fill="#111827", center=True):
    x, y = xy
    w, h = tsize(d, s, f)
    if center:
        d.text((x - w / 2, y - h / 2), s, font=f, fill=hex_rgb(fill))
    else:
        d.text((x, y), s, font=f, fill=hex_rgb(fill))


def var_label(d, xy, base, sub="", sup="", base_size=30, ss_size=20, italic=True, fill="#111827"):
    """Draw a math variable with proper subscript/superscript at xy (center of base)."""
    x, y = xy
    bf = font(base_size, italic=italic, cjk=False)
    sf = font(ss_size, italic=True, cjk=False)
    bw = tsize(d, base, bf)[0]
    d.text((x - bw / 2, y - tsize(d, base, bf)[1] / 2), base, font=bf, fill=hex_rgb(fill))
    bx = x - bw / 2
    if sub:
        sw = tsize(d, sub, sf)[0]
        d.text((bx + bw - 2, y + base_size * 0.35), sub, font=sf, fill=hex_rgb(fill))
    if sup:
        d.text((bx + bw - 2, y - base_size * 0.55), sup, font=sf, fill=hex_rgb(fill))


def arrow(d, p0, p1, color="#4B5563", width=3, head=11):
    d.line([p0, p1], fill=hex_rgb(color), width=width)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    d.polygon([p1, (p1[0] - head * ux + head * 0.5 * px, p1[1] - head * uy + head * 0.5 * py),
               (p1[0] - head * ux - head * 0.5 * px, p1[1] - head * uy - head * 0.5 * py)],
              fill=hex_rgb(color))


def grid_icon(d, xy, w, h, color, outline, cols=4, rows=4):
    """Draw a small feature-map grid icon."""
    x, y = xy
    d.rectangle([x, y, x + w, y + h], fill=hex_rgb(color), outline=hex_rgb(outline), width=2)
    cw, rh = w / cols, h / rows
    for i in range(1, cols):
        d.line([(x + i * cw, y), (x + i * cw, y + h)], fill=hex_rgb(outline), width=1)
    for j in range(1, rows):
        d.line([(x, y + j * rh), (x + w, y + j * rh)], fill=hex_rgb(outline), width=1)


# ---------- fig3: P2 branch fusion ----------
def draw_p2_fusion():
    W, H = 1500, 950
    img = Image.new("RGB", (W, H), hex_rgb("#FFFFFF"))
    d = ImageDraw.Draw(img)
    fc = font(28, cjk=True)
    fb = font(26, bold=True, cjk=True)
    fs = font(20, cjk=True)
    fm = font(24, italic=True, cjk=False)

    # Top-down FPN column, centered directly above concat: P5 -> P4 -> P3 -> (straight down) concat
    cx = 730
    bw = 260
    box(d, (cx - bw / 2, 80, cx + bw / 2, 150), "purple", "purple_o")
    label(d, (cx, 103), "P5", font(30, bold=True, cjk=False))
    label(d, (cx, 130), "20×20", fs)
    box(d, (cx - bw / 2, 220, cx + bw / 2, 290), "purple", "purple_o")
    label(d, (cx, 243), "P4", font(30, bold=True, cjk=False))
    label(d, (cx, 270), "40×40", fs)
    box(d, (cx - bw / 2, 360, cx + bw / 2, 430), "cyan", "cyan_o")
    label(d, (cx, 383), "P3", font(30, bold=True, cjk=False))
    label(d, (cx, 410), "80×80", fs)
    arrow(d, (cx, 150), (cx, 220), "purple_o")
    arrow(d, (cx, 290), (cx, 360), "cyan_o")
    label(d, (cx + bw / 2 + 20, 178), "上采样", fs, fill="#6D28D9")
    label(d, (cx + bw / 2 + 20, 318), "上采样", fs, fill="#0E7490")
    # P3 -> concat : straight vertical, no bend
    arrow(d, (cx, 430), (cx, 510), "cyan_o")
    label(d, (cx + bw / 2 + 20, 462), "上采样", fs, fill="#0E7490")

    # P2 shallow feature (left) feeding concat horizontally
    box(d, (110, 510, 470, 600), "green", "green_o")
    label(d, (290, 540), "P2 浅层特征", fb)
    label(d, (290, 575), "160×160", fs)
    grid_icon(d, (150, 615), 90, 70, "green", "green_o", 5, 4)
    arrow(d, (470, 555), (640, 555), "green_o")

    # concat node (directly below P3)
    box(d, (640, 510, 820, 600), "concat", "concat_o")
    label(d, (730, 555), "Concat", fb)

    # P2 detect head
    box(d, (640, 680, 820, 770), "detect", "detect_o")
    label(d, (730, 725), "P2 检测头", fb)
    arrow(d, (730, 600), (730, 680), "concat_o")
    arrow(d, (730, 770), (730, 830), "detect_o")
    box(d, (560, 830, 900, 895), "light", "muted")
    label(d, (730, 862), "极小目标检出（行人 / 交通锥）", fs)

    label(d, (W / 2, 925), "P2/4 线性投影为 P3/8 的 2 倍，面积响应约 4 倍", fs, fill="#4B5563")
    img.save(FIG_DIR / "fig3_p2_fusion.png", dpi=(300, 300))


# ---------- fig4: DyHead internal (structural) ----------
def draw_dyhead():
    W, H = 1500, 900
    img = Image.new("RGB", (W, H), hex_rgb("#FFFFFF"))
    d = ImageDraw.Draw(img)
    fb = font(26, bold=True, cjk=True)
    fs = font(20, cjk=True)
    fcjk = font(24, cjk=True)

    # Left: multi-scale input feature maps (stacked grids)
    label(d, (170, 130), "多尺度特征输入", fcjk)
    scales = [("F2", "purple", 150, 5), ("F3", "cyan", 110, 4), ("F4", "orange", 80, 3), ("F5", "grey", 55, 2)]
    y0 = 175
    for name, col, sz, n in scales:
        grid_icon(d, (110, y0), sz, sz, col, col + "_o", n, n)
        label(d, (110 + sz + 35, y0 + sz / 2), name, font(28, bold=True, italic=True, cjk=False))
        y0 += sz + 18

    # Middle: three attention stages (vertical cascade)
    stages = [
        ("尺度感知 π", "blue", "按目标尺度跨层加权"),
        ("空间感知 S", "orange", "可变形卷积定位目标"),
        ("任务感知 L", "green", "动态激活协调分类 / 回归"),
    ]
    sx = 560
    sy = 150
    for i, (name, col, desc) in enumerate(stages):
        y = sy + i * 200
        box(d, (sx, y, sx + 380, y + 130), col, col + "_o")
        label(d, (sx + 190, y + 45), name, fb)
        label(d, (sx + 190, y + 85), desc, fs)
        if i < 2:
            arrow(d, (sx + 190, y + 130), (sx + 190, y + 200), "#4B5563")
    # input arrow to first stage
    arrow(d, (300, 360), (560, 215), "#4B5563")

    # Right: output
    box(d, (1080, 360, 1330, 460), "detect", "detect_o")
    var_label(d, (1205, 410), "F", sup="'", base_size=40, ss_size=26)
    arrow(d, (940, 285), (1080, 410), "#4B5563")
    arrow(d, (1205, 460), (1205, 530), "detect_o")
    box(d, (1060, 530, 1350, 600), "light", "muted")
    label(d, (1205, 565), "类别概率 + 边界框", fs)

    label(d, (W / 2, 700), "三级注意力级联：按尺度选层 → 按空间定位 → 按任务分通道", fs, fill="#4B5563")
    label(d, (W / 2, 735), "本文以 DyHeadDetect 替换 YOLO11n 原 Detect 头", fs, fill="#4B5563")
    img.save(FIG_DIR / "fig4_dyhead.png", dpi=(300, 300))


# ---------- fig5: CoordAttention internal ----------
def draw_ca():
    W, H = 1500, 900
    img = Image.new("RGB", (W, H), hex_rgb("#FFFFFF"))
    d = ImageDraw.Draw(img)
    fb = font(25, bold=True, cjk=True)
    fs = font(20, cjk=True)
    fcjk = font(24, cjk=True)
    fmath = font(27, italic=True, cjk=False)

    # input (top center) — single line, centered
    box(d, (600, 70, 900, 140), "light", "muted")
    label(d, (750, 105), "输入特征 x", fcjk)

    # two 1D pooling branches — operation only, centered
    box(d, (180, 220, 560, 300), "cyan", "cyan_o")
    label(d, (370, 260), "高度方向池化", fb)
    box(d, (940, 220, 1320, 300), "yellow", "yellow_o")
    label(d, (1130, 260), "宽度方向池化", fb)
    arrow(d, (680, 140), (370, 220), "#4B5563")
    arrow(d, (820, 140), (1130, 220), "#4B5563")

    # shared concat + 1x1 conv, then split along direction
    box(d, (590, 370, 910, 450), "concat", "concat_o")
    label(d, (750, 410), "拼接 + 1×1 Conv", fb)
    arrow(d, (370, 300), (680, 370), "#4B5563")
    arrow(d, (1130, 300), (820, 370), "#4B5563")

    # two DIRECTION-SPECIFIC sigmoid gates (g^h along height, g^w along width) — not interchangeable
    box(d, (180, 520, 560, 600), "purple", "purple_o")
    label(d, (370, 560), "Sigmoid 门控（高度方向）", fb)
    box(d, (940, 520, 1320, 600), "purple", "purple_o")
    label(d, (1130, 560), "Sigmoid 门控（宽度方向）", fb)
    arrow(d, (680, 450), (370, 520), "#4B5563")
    arrow(d, (820, 450), (1130, 520), "#4B5563")

    # output: y = x · g^h · g^w — single line, centered
    box(d, (560, 670, 940, 750), "detect", "detect_o")
    label(d, (750, 710), "y = x · gʰ · gʷ", fmath)
    arrow(d, (370, 600), (680, 670), "#4B5563")
    arrow(d, (1130, 600), (820, 670), "#4B5563")

    label(d, (W / 2, 805), "方向编码保留位置信息，门控回乘生成位置敏感注意力", fs, fill="#4B5563")
    label(d, (W / 2, 840), "本文嵌入 P3 相关浅中层特征位置", fs, fill="#4B5563")
    img.save(FIG_DIR / "fig5_coordattention.png", dpi=(300, 300))


# ---------- fig6: WIoU v3 focusing curve ----------
def draw_wiou_curve():
    W, H = 1500, 850
    img = Image.new("RGB", (W, H), hex_rgb("#FFFFFF"))
    d = ImageDraw.Draw(img)
    fs = font(20, cjk=True)
    fb = font(24, bold=True, cjk=True)

    alpha, delta = 1.9, 3.0
    def r(b):
        return b / (delta * alpha ** (b - delta))

    px0, py0, px1, py1 = 130, 110, 1380, 700
    bmin, bmax = 0.05, 5.0
    rmax = 1.5
    def xy(b, rv):
        x = px0 + (b - bmin) / (bmax - bmin) * (px1 - px0)
        y = py1 - rv / rmax * (py1 - py0)
        return x, y

    # region shading
    b_peak = 1 / math.log(alpha)
    def shade(b_lo, b_hi, color):
        x0, _ = xy(b_lo, 0); x1, _ = xy(b_hi, 0)
        d.rectangle([x0, py0, x1, py1], fill=hex_rgb(color))
    shade(bmin, 0.8, "#F1F5F9")
    shade(0.8, 2.6, "#ECFDF5")
    shade(2.6, bmax, "#FEF2F2")

    # axes
    d.line([(px0, py0), (px0, py1), (px1, py1)], fill=hex_rgb("#111827"), width=3)
    label(d, (px1 + 20, py1), "β = L_IoU* / L̄", fs, center=False)
    label(d, (px0 - 80, py0 - 30), "r", fs, center=False)
    for bt in [0, 1, 2, 3, 4, 5]:
        x, _ = xy(bt, 0)
        d.line([(x, py1), (x, py1 + 8)], fill=hex_rgb("#111827"), width=3)
        label(d, (x, py1 + 22), str(bt), fs)
    for rt in [0, 0.5, 1.0, 1.5]:
        _, y = xy(0, rt)
        d.line([(px0 - 8, y), (px0, y)], fill=hex_rgb("#111827"), width=3)
        label(d, (px0 - 45, y), f"{rt:.1f}", fs, center=False)

    # curve
    pts = [xy(b, r(b)) for b in [bmin + i * (bmax - bmin) / 300 for i in range(301)]]
    d.line(pts, fill=hex_rgb("#BE123C"), width=4, joint="curve")
    xp, yp = xy(b_peak, r(b_peak))
    d.ellipse([xp - 8, yp - 8, xp + 8, yp + 8], fill=hex_rgb("#BE123C"))
    label(d, (xp + 18, yp - 22), f"峰值 β≈{b_peak:.2f}, r≈{r(b_peak):.2f}", fs, fill="#BE123C", center=False)

    label(d, (xy(0.4, 0)[0], py0 + 18), "高质量样本", fs, fill="#475569")
    label(d, (xy(1.6, 0)[0], py0 + 18), "普通质量样本", fs, fill="#047857")
    label(d, (xy(3.8, 0)[0], py0 + 18), "离群低质量样本", fs, fill="#BE123C")

    label(d, (W / 2, 760), "r 在普通质量样本处取峰值，高质量与离群样本的梯度增益均被抑制（非单调）", fs, fill="#4B5563")
    label(d, (W / 2, 795), "α=1.9, δ=3.0（文献[5]）", fs, fill="#4B5563")
    img.save(FIG_DIR / "fig6_wiou_focusing.png", dpi=(300, 300))


def main():
    draw_p2_fusion()
    draw_dyhead()
    draw_ca()
    draw_wiou_curve()
    print("wrote fig3_p2_fusion.png, fig4_dyhead.png, fig5_coordattention.png, fig6_wiou_focusing.png")


if __name__ == "__main__":
    main()
