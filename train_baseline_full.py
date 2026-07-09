"""YOLOv11n baseline on DAIR-V2X-I, 300 epochs, batch=64.

Run with: python train_baseline_full.py
"""

from pathlib import Path

import yaml

from ultralytics import YOLO

ROOT = Path(".").resolve()
src = ROOT / "datasets/dair_v2x_i/dair_v2x_i.yaml"
cfg = yaml.safe_load(src.read_text())
cfg["path"] = str(ROOT / "datasets/dair_v2x_i")
out = ROOT / "datasets/dair_v2x_i/_runtime.yaml"
out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

model = YOLO("yolo11n.yaml")
model.train(
    data=str(out),
    epochs=300,
    imgsz=640,
    batch=64,
    device=0,
    workers=8,
    optimizer="SGD",
    lr0=0.01,
    cos_lr=True,
    weight_decay=0.0005,
    project="runs/baseline",
    name="yolo11n-baseline-v2",
    seed=42,
    amp=True,
    cache=False,
    patience=50,
    exist_ok=True,
    plots=True,
)
