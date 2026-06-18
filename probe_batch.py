"""Auto-batch probe: ultralytics finds max batch at 85% GPU memory."""

from pathlib import Path

import yaml

from ultralytics import YOLO

ROOT = Path(".").resolve()
src = ROOT / "datasets/dair_v2x_i/dair_v2x_i.yaml"
cfg = yaml.safe_load(src.read_text())
cfg["path"] = str(ROOT / "datasets/dair_v2x_i")
out = ROOT / "datasets/dair_v2x_i/_runtime.yaml"
out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

m = YOLO("yolo11n.yaml")
# batch=0.85 lets ultralytics binary-search max batch at 85% GPU mem util
m.train(
    data=str(out),
    epochs=1,
    imgsz=640,
    batch=0.85,
    device=0,
    workers=8,
    optimizer="SGD",
    lr0=0.01,
    amp=True,
    project="runs/_probe",
    name="batch_probe",
    seed=42,
    exist_ok=True,
    plots=False,
)
