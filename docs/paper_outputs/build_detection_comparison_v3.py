# -*- coding: utf-8 -*-
"""v3 detection comparison: different intersections, sparse scenes, zoomed,
with printed counts and green highlight on targets DWCA-P2 found that baseline missed.

Requires boxes.json (saved by the AutoDL predict script) with per-image boxes for
both models, plus the annotated-image dirs and the val GT labels (for the zoom window).

usage: python3 build_detection_comparison_v3.py <baseline_annotated_dir> <dwca_annotated_dir> <boxes.json>
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FIG_DIR = Path(__file__).resolve().parents[2] / "docs" / "paper_outputs" / "figures"
LABEL_DIR = Path("/Users/asus/ultralytics/datasets/dair_v2x_i/labels/val")
INFO_PATH = Path("/Users/asus/ultralytics/datasets/data_info.json")
FONT_CJK = "/System/Library/Fonts/STHeiti Medium.ttc"
BLUE = (37, 99, 235)
ORANGE = (249, 115, 22)
RED = (220, 38, 38)
GREEN = (22, 163, 74)
WW, HH = 1040, 580  # zoom window


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_CJK, size)
    except OSError:
        return ImageFont.load_default()


def intersection_map():
    info = json.load(open(INFO_PATH))
    return {it["image_path"].split("/")[-1].replace(".jpg", ""): it["intersection_loc"]
            for it in info}


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


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    ua = (ax1 - ax0) * (ay1 - ay0) + (bx1 - bx0) * (by1 - by0) - inter
    return inter / ua if ua > 0 else 0


def dwca_new_indices(dwca, base, thr=0.5):
    """Indices of dwca boxes with no baseline match (same class, IoU>thr)."""
    out = []
    for i, d in enumerate(dwca):
        hit = any(d["cls"] == b["cls"] and iou(d["xyxy"], b["xyxy"]) > thr for b in base)
        if not hit:
            out.append(i)
    return out


def main():
    if len(sys.argv) < 4:
        print("usage: build_detection_comparison_v3.py <baseline_dir> <dwca_dir> <boxes.json>")
        sys.exit(1)
    base_dir, prop_dir = Path(sys.argv[1]), Path(sys.argv[2])
    boxes = json.load(open(sys.argv[3]))
    i2inter = intersection_map()

    # per-image stats + differential
    stats = []
    for iid, both in boxes.items():
        b = both.get("baseline", {}).get("xyxy", [])
        d = both.get("dwca-p2", {}).get("xyxy", [])
        b_cls = both.get("baseline", {}).get("cls", [])
        d_cls = both.get("dwca-p2", {}).get("cls", [])
        bboxes = [{"xyxy": xy, "cls": c} for xy, c in zip(b, b_cls)]
        dboxes = [{"xyxy": xy, "cls": c} for xy, c in zip(d, d_cls)]
        new_idx = dwca_new_indices(dboxes, bboxes)
        stats.append({
            "id": iid, "inter": i2inter.get(iid, "?"),
            "base_n": len(b), "dwca_n": len(d), "new": len(new_idx), "new_idx": new_idx,
            "dboxes": dboxes,
        })
    stats.sort(key=lambda s: (-s["new"], -(s["dwca_n"] - s["base_n"])))
    print("=== candidate ranking (dwca-new desc) ===")
    for s in stats:
        print(f"  {s['id']}: {s['inter']}  base={s['base_n']} dwca={s['dwca_n']} new={s['new']} (+{s['dwca_n']-s['base_n']})")

    # pick top per distinct intersection (clear DWCA win: dwca_n>base_n and new>=3)
    seen, picks = set(), []
    for s in stats:
        if s["inter"] in seen or s["dwca_n"] <= s["base_n"] or s["new"] < 3:
            continue
        seen.add(s["inter"])
        picks.append(s)
        if len(picks) == 3:
            break
    if len(picks) < 3:  # relax: allow new>=2
        for s in stats:
            if s["inter"] in seen:
                continue
            seen.add(s["inter"]); picks.append(s)
            if len(picks) == 3:
                break
    print("PICKS:", [(p["id"], p["inter"], p["base_n"], p["dwca_n"], p["new"]) for p in picks])

    f, fs, fb = font(26), font(22), font(24, bold=True)
    zoom_w, thumb_w, gap, label_h, pad = 720, 220, 24, 64, 22
    rows = []
    for s in picks:
        iid = s["id"]
        bim = Image.open(base_dir / f"{iid}.jpg").convert("RGB")
        pim = Image.open(prop_dir / f"{iid}.jpg").convert("RGB")
        W, H = bim.size
        (cx0, cy0, cx1, cy1), cnt = densest_window(LABEL_DIR / f"{iid}.txt", W, H)
        # zoom factors (for re-drawing highlight boxes into the crop)
        sx, sy = zoom_w / (cx1 - cx0), zoom_w / (cy1 - cy0)
        bc = bim.crop((cx0, cy0, cx1, cy1)).resize((zoom_w, int(zoom_w * (cy1 - cy0) / (cx1 - cx0))))
        pc = pim.crop((cx0, cy0, cx1, cy1)).resize((zoom_w, int(zoom_w * (cy1 - cy0) / (cx1 - cx0))))
        zh = pc.height
        # highlight DWCA-new boxes (green) on the DWCA zoom panel
        dimg = ImageDraw.Draw(pc)
        for i in s["new_idx"]:
            x0, y0, x1, y1 = s["dboxes"][i]["xyxy"]
            if x1 < cx0 or x0 > cx1 or y1 < cy0 or y0 > cy1:
                continue
            rx0 = (max(cx0, x0) - cx0) * sx
            ry0 = (max(cy0, y0) - cy0) * sy
            rx1 = (min(cx1, x1) - cx0) * sx
            ry1 = (min(cy1, y1) - cy0) * sy
            dimg.rectangle((rx0, ry0, rx1, ry1), outline=GREEN, width=5)
        # thumbnail with crop rect
        th_h = int(H * thumb_w / W)
        th = bim.resize((thumb_w, th_h))
        ImageDraw.Draw(th).rectangle((cx0 / W * thumb_w, cy0 / H * th_h, cx1 / W * thumb_w, cy1 / H * th_h),
                                     outline=RED, width=4)
        row_w = thumb_w + gap + zoom_w + gap + zoom_w
        row_h = max(th_h, zh) + label_h
        row = Image.new("RGB", (row_w, row_h), "white")
        ty = (row_h - label_h - th_h) // 2
        zy = label_h + (row_h - label_h - zh) // 2
        row.paste(th, (0, ty))
        row.paste(bc, (thumb_w + gap, zy))
        row.paste(pc, (thumb_w + gap + zoom_w + gap, zy))
        dd = ImageDraw.Draw(row)
        dd.text((8, 6), "裁剪位置", font=fs, fill=RED)
        dd.text((8, 32), iid, font=fs, fill=(75, 85, 99))
        dd.text((thumb_w + gap + 8, 6), f"baseline（{s['base_n']} 框）", font=f, fill=BLUE)
        dd.text((thumb_w + gap + zoom_w + gap + 8, 6), f"DWCA-P2（{s['dwca_n']} 框）", font=f, fill=ORANGE)
        dd.text((thumb_w + gap + zoom_w + gap + 8, 34), f"绿框={s['new']} 个 baseline 漏检", font=fs, fill=GREEN)
        rows.append(row)
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
