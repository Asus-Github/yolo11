"""Convert DAIR-V2X-I single-infrastructure dataset (JSON 2D boxes) to YOLO format.

Source layout:
    datasets/single-infrastructure-side-image/{frame_id}.jpg
    datasets/camera/{frame_id}.json   # list of objects with `type` and `2d_box`

Output layout (under <out_root>):
    images/{train,val,test}/{frame_id}.jpg
    labels/{train,val,test}/{frame_id}.txt
    dair_v2x_i.yaml
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import struct
from pathlib import Path

# Class mapping derived from scanning all JSONs (9 classes present in this dump).
CLASSES = [
    "Car",
    "Truck",
    "Van",
    "Bus",
    "Cyclist",
    "Motorcyclist",
    "Pedestrian",
    "Trafficcone",
    "Barrowlist",
]
CLASS_TO_ID = {name: i for i, name in enumerate(CLASSES)}


def jpeg_size(path: Path) -> tuple[int, int]:
    """Return (width, height) of a JPEG without external deps."""
    with path.open("rb") as f:
        data = f.read()
    i = 0
    while i < len(data) - 9:
        if data[i] == 0xFF and data[i + 1] in (0xC0, 0xC1, 0xC2):
            h = struct.unpack(">H", data[i + 5 : i + 7])[0]
            w = struct.unpack(">H", data[i + 7 : i + 9])[0]
            return w, h
        i += 1
    raise RuntimeError(f"cannot parse jpeg size: {path}")


def convert_one(json_path: Path, img_w: int, img_h: int) -> list[str]:
    """Return YOLO label lines for one frame."""
    objs = json.loads(json_path.read_text())
    lines: list[str] = []
    for obj in objs:
        cls_name = obj.get("type")
        if cls_name not in CLASS_TO_ID:
            continue
        box = obj["2d_box"]
        xmin = float(box["xmin"])
        ymin = float(box["ymin"])
        xmax = float(box["xmax"])
        ymax = float(box["ymax"])
        # clip and validate
        xmin = max(0.0, min(xmin, img_w))
        xmax = max(0.0, min(xmax, img_w))
        ymin = max(0.0, min(ymin, img_h))
        ymax = max(0.0, min(ymax, img_h))
        if xmax <= xmin or ymax <= ymin:
            continue
        xc = (xmin + xmax) / 2.0 / img_w
        yc = (ymin + ymax) / 2.0 / img_h
        w = (xmax - xmin) / img_w
        h = (ymax - ymin) / img_h
        cid = CLASS_TO_ID[cls_name]
        lines.append(f"{cid} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-images", default="/Users/asus/ultralytics/datasets/single-infrastructure-side-image")
    ap.add_argument("--src-labels", default="/Users/asus/ultralytics/datasets/camera")
    ap.add_argument("--out", default="/Users/asus/ultralytics/datasets/dair_v2x_i")
    ap.add_argument("--ratios", default="0.7,0.2,0.1", help="train,val,test")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--mode", choices=["copy", "symlink", "move"], default="symlink",
                    help="how to place images into images/{split}/")
    args = ap.parse_args()

    src_img = Path(args.src_images)
    src_lab = Path(args.src_labels)
    out = Path(args.out)

    train_r, val_r, test_r = (float(x) for x in args.ratios.split(","))
    assert abs(train_r + val_r + test_r - 1.0) < 1e-6

    # collect paired frame ids
    img_ids = {p.stem for p in src_img.glob("*.jpg")}
    lab_ids = {p.stem for p in src_lab.glob("*.json")}
    paired = sorted(img_ids & lab_ids)
    only_img = img_ids - lab_ids
    only_lab = lab_ids - img_ids
    print(f"paired: {len(paired)}  img-only: {len(only_img)}  json-only: {len(only_lab)}")

    rng = random.Random(args.seed)
    rng.shuffle(paired)
    n = len(paired)
    n_train = int(n * train_r)
    n_val = int(n * val_r)
    splits = {
        "train": paired[:n_train],
        "val": paired[n_train : n_train + n_val],
        "test": paired[n_train + n_val :],
    }

    # prep dirs
    for split in splits:
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)

    cls_counts = {c: 0 for c in CLASSES}
    for split, ids in splits.items():
        for fid in ids:
            jpg_src = src_img / f"{fid}.jpg"
            json_src = src_lab / f"{fid}.json"
            jpg_dst = out / "images" / split / f"{fid}.jpg"
            txt_dst = out / "labels" / split / f"{fid}.txt"

            try:
                w, h = jpeg_size(jpg_src)
            except Exception as e:
                print(f"[skip {fid}] {e}")
                continue

            lines = convert_one(json_src, w, h)
            for ln in lines:
                cid = int(ln.split(" ", 1)[0])
                cls_counts[CLASSES[cid]] += 1
            txt_dst.write_text("\n".join(lines))

            # place image
            if jpg_dst.exists() or jpg_dst.is_symlink():
                jpg_dst.unlink()
            if args.mode == "copy":
                shutil.copy2(jpg_src, jpg_dst)
            elif args.mode == "move":
                shutil.move(str(jpg_src), str(jpg_dst))
            else:
                jpg_dst.symlink_to(jpg_src.resolve())
        print(f"{split}: {len(ids)} frames")

    # yaml
    yaml_path = out / "dair_v2x_i.yaml"
    yaml_text = (
        f"# DAIR-V2X-I (single-infrastructure-side-image) -> YOLO\n"
        f"path: {out}\n"
        f"train: images/train\n"
        f"val: images/val\n"
        f"test: images/test\n\n"
        f"names:\n"
        + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES))
    )
    yaml_path.write_text(yaml_text)

    print("\nclass instance counts:")
    for c, k in cls_counts.items():
        print(f"  {c:14s} {k}")
    print(f"\nyaml written: {yaml_path}")


if __name__ == "__main__":
    main()
