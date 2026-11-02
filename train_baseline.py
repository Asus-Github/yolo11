"""YOLOv11n baseline on DAIR-V2X-I (CIoU, single-card).

Auto-resolves dataset path so the same script runs on Mac (CPU smoke test)
and on AutoDL 5090 without editing the YAML.
"""

import os
from pathlib import Path

import yaml

from ultralytics import YOLO

ROOT = Path(__file__).resolve().parent
SRC_YAML = ROOT / "datasets" / "dair_v2x_i" / "dair_v2x_i.yaml"
RUN_YAML = ROOT / "datasets" / "dair_v2x_i" / "_runtime.yaml"


def patch_dataset_yaml() -> Path:
    """Rewrite dataset yaml `path` to current absolute root."""
    cfg = yaml.safe_load(SRC_YAML.read_text())
    cfg["path"] = str(ROOT / "datasets" / "dair_v2x_i")
    RUN_YAML.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    return RUN_YAML


if __name__ == "__main__":
    data = patch_dataset_yaml()

    is_smoke = os.environ.get("SMOKE", "0") == "1"
    device = os.environ.get("DEVICE", "0")  # "cpu" on Mac, "0" on AutoDL

    model = YOLO("yolo11n.yaml")  # fresh weights from yaml; or "yolo11n.pt" to fine-tune

    model.train(
        data=str(data),
        epochs=2 if is_smoke else 300,
        imgsz=320 if is_smoke else 640,
        batch=4 if is_smoke else 32,
        device="cpu" if is_smoke else device,
        workers=2 if is_smoke else 8,
        optimizer="SGD",
        lr0=0.01,
        cos_lr=True,
        weight_decay=0.0005,
        project=str(ROOT / "runs" / "baseline"),
        name="yolo11n-baseline-smoke" if is_smoke else "yolo11n-baseline-v1",
        seed=42,
        amp=not is_smoke,
        cache=False,
        patience=50,
        exist_ok=True,
    )
