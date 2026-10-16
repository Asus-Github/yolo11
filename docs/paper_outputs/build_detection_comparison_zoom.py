# -*- coding: utf-8 -*-
"""Zoomed baseline-vs-DWCA-P2 detection comparison.

Like build_detection_comparison.py, but each row crops both images to the
densest small-target (Pedestrian/Trafficcone) window and adds a full-image
thumbnail with a red rectangle showing the crop location. Overwrites
figures/fig_detection_comparison.png (the figure referenced by the paper).
The un-zoomed version is kept as fig_detection_comparison_full.png.

usage: python3 build_detection_comparison_zoom.py <baseline_annotated_dir> <dwca_annotated_dir>
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIG_DIR = Path(__file__).resolve().parents[2] / "docs" / "paper_outputs" / "figures"
LABEL_DIR = Path("/Users/asus/ultralytics/datasets/dair_v2x_i/labels/val")
FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"
# Dense small-target val scene (single representative row, no differential overlay).
IDS = ["000024"]
BLUE = (37, 99, 235)
ORANGE = (249, 115, 22)
RED = (220, 38, 38)
WW, HH = 1000, 560  # zoom window (~half of a 1920x1080 frame)


def font(size):
    try:
        return ImageFont.truetype(FONT_CJK, size)
    except OSError:
        return ImageFont.load_default()


def densest_window(label_path, W, H, ww=WW, hh=HH, step=80):
    pts = []
    for line in open(label_path):
        p = line.split()
        if len(p) >= 5 and p[0] in ("6", "7"):
            pts.append((float(p[1]) * W, float(p[2]) * H))
    if not pts:
        return (0, 0, min(ww, W), min(hh, H)), 0
    best = (0, 0, 0)
    for x0 in range(0, max(1, W - ww + 1), step):
        for y0 in range(0, max(1, H - hh + 1), step):
            c = sum(1 for cx, cy in pts if x0 <= cx <= x0 + ww and y0 <= cy <= y0 + hh)
            if c > best[0]:
                best = (c, x0, y0)
    _, x0, y0 = best
    return (x0, y0, min(W, x0 + ww), min(H, y0 + hh)), best[0]


def main():
    if len(sys.argv) < 3:
        print("usage: build_detection_comparison_zoom.py <baseline_dir> <dwca_dir>")
        sys.exit(1)
    base_dir, prop_dir = Path(sys.argv[1]), Path(sys.argv[2])
    f = font(26)
    fs = font(22)
    thumb_w, zoom_w, gap, label_h, pad = 240, 720, 24, 40, 22
    rows = []
    for id_ in IDS:
        bp, pp = base_dir / f"{id_}.jpg", prop_dir / f"{id_}.jpg"
        if not bp.exists() or not pp.exists():
            print(f"[skip] {id_}")
            continue
        bim = Image.open(bp).convert("RGB")
        pim = Image.open(pp).convert("RGB")
        W, H = bim.size
        (cx0, cy0, cx1, cy1), cnt = densest_window(LABEL_DIR / f"{id_}.txt", W, H)
        cw, ch = cx1 - cx0, cy1 - cy0
        zh = int(zoom_w * ch / cw)
        bc = bim.crop((cx0, cy0, cx1, cy1)).resize((zoom_w, zh))
        pc = pim.crop((cx0, cy0, cx1, cy1)).resize((zoom_w, zh))
        # full-image thumbnail with red crop rectangle
        th_h = int(H * thumb_w / W)
        th = bim.resize((thumb_w, th_h))
        td = ImageDraw.Draw(th)
        td.rectangle((cx0 / W * thumb_w, cy0 / H * th_h, cx1 / W * thumb_w, cy1 / H * th_h),
                     outline=RED, width=4)
        row_w = thumb_w + gap + zoom_w + gap + zoom_w
        row_h = max(th_h, zh) + label_h
        row = Image.new("RGB", (row_w, row_h), "white")
        ty = (row_h - label_h - th_h) // 2
        zy = label_h + (row_h - label_h - zh) // 2
        row.paste(th, (0, ty))
        row.paste(bc, (thumb_w + gap, zy))
        row.paste(pc, (thumb_w + gap + zoom_w + gap, zy))
        d = ImageDraw.Draw(row)
        d.text((8, 8), "裁剪位置", font=fs, fill=RED)
        d.text((thumb_w + gap + 8, 8), "baseline（放大）", font=f, fill=BLUE)
        d.text((thumb_w + gap + zoom_w + gap + 8, 8), "DWCA-P2（放大）", font=f, fill=ORANGE)
        rows.append(row)
        print(f"[ok] {id_}: crop=({cx0},{cy0})-({cx1},{cy1}) size={cw}x{ch} small_in_window={cnt}")
    if not rows:
        print("no rows"); sys.exit(1)
    rw, rh = rows[0].width, rows[0].height
    sheet = Image.new("RGB", (rw, rh * len(rows) + pad * (len(rows) + 1)), "white")
    y = pad
    for r in rows:
        sheet.paste(r, (0, y))
        y += rh + pad
    out = FIG_DIR / "fig_detection_comparison.png"
    sheet.save(out, dpi=(300, 300))
    print(f"wrote {out} {sheet.size}")


if __name__ == "__main__":
    main()
