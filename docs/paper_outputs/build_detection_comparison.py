# -*- coding: utf-8 -*-
"""Assemble a side-by-side baseline-vs-DWCA-P2 detection comparison figure.

Run order:
  1. On AutoDL (GPU), run `yolo predict` for baseline-b32 and DWCA-P2-b32 on the
     selected val images (see revision_experiments_todo.md TODO-5), save=True.
  2. Sync the two annotated-image folders back to the Mac.
  3. On Mac (no torch needed): python3 build_detection_comparison.py <baseline_dir> <dwca_dir>

The script matches images by the IDs in IDS and lays them out as labeled rows.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIG_DIR = Path(__file__).resolve().parents[2] / "docs" / "paper_outputs" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)
FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"

# Dense small-object val scenes (Pedestrian/Trafficcone heavy, distant).
# At conf=0.5 these show DWCA-P2 detecting more small targets than baseline.
IDS = ["009153", "009408", "009021"]

BLUE = (37, 99, 235)
ORANGE = (249, 115, 22)


def font(size):
    try:
        return ImageFont.truetype(FONT_CJK, size)
    except OSError:
        return ImageFont.load_default()


def find(d: Path, id_: str):
    for ext in (".jpg", ".png", ".jpeg"):
        p = d / f"{id_}{ext}"
        if p.exists():
            return p
    for p in d.glob(f"*{id_}*"):
        return p
    return None


def load(p: Path, target_h: int):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    return im.resize((int(w * target_h / h), target_h))


def main():
    if len(sys.argv) < 3:
        print("usage: build_detection_comparison.py <baseline_annotated_dir> <dwca_annotated_dir>")
        sys.exit(1)
    base_dir, prop_dir = Path(sys.argv[1]), Path(sys.argv[2])
    target_h, gap, label_h, pad = 560, 30, 44, 24
    f = font(28)
    rows = []
    for id_ in IDS:
        bp, pp = find(base_dir, id_), find(prop_dir, id_)
        if not bp or not pp:
            print(f"[skip] {id_}: baseline={bp} dwca={pp}")
            continue
        bim, pim = load(bp, target_h), load(pp, target_h)
        row = Image.new("RGB", (bim.width + gap + pim.width, target_h + label_h), "white")
        row.paste(bim, (0, label_h))
        row.paste(pim, (bim.width + gap, label_h))
        d = ImageDraw.Draw(row)
        d.text((12, 8), "baseline (YOLO11n)", font=f, fill=BLUE)
        d.text((bim.width + gap + 12, 8), "DWCA-P2 (本文)", font=f, fill=ORANGE)
        rows.append(row)
        print(f"[ok] {id_}")
    if not rows:
        print("no rows assembled (check dirs/IDs)"); sys.exit(1)
    row_h = rows[0].height
    sheet = Image.new("RGB", (rows[0].width, row_h * len(rows) + pad * (len(rows) + 1)), "white")
    y = pad
    for r in rows:
        sheet.paste(r, (0, y))
        y += row_h + pad
    out = FIG_DIR / "fig_detection_comparison.png"
    sheet.save(out, dpi=(300, 300))
    print(f"wrote {out} {sheet.size}")


if __name__ == "__main__":
    main()
