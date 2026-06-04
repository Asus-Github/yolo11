"""Smoke test: 1 epoch baseline on DAIR-V2X-I, batch=16."""
from pathlib import Path
import yaml
import torch
from ultralytics import YOLO

print("=" * 60)
print(f"torch: {torch.__version__}  cuda: {torch.version.cuda}")
print(f"gpu  : {torch.cuda.get_device_name(0)}")
print("=" * 60)

ROOT = Path(".").resolve()
src = ROOT / "datasets/dair_v2x_i/dair_v2x_i.yaml"
cfg = yaml.safe_load(src.read_text())
cfg["path"] = str(ROOT / "datasets/dair_v2x_i")
out = ROOT / "datasets/dair_v2x_i/_runtime.yaml"
out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

m = YOLO("yolo11n.yaml")
m.train(
    data=str(out),
    epochs=1, imgsz=640, batch=16, device=0,
    workers=8, optimizer="SGD", lr0=0.01, amp=True,
    project="runs/_smoke", name="s1", seed=42,
    exist_ok=True, plots=False,
)
