# CHANGELOG — Variant "+D" (DyHead)

> Branch: `feat/dyhead`
> Base: `main` (pre-experiment baseline) + `b603e7be3` (.gitignore allow `runs/` artifacts)
> Goal: Add **Dynamic Head (DyHead, Dai et al., CVPR 2021)** to YOLOv11n's Detect
> head and produce metrics for the **+D** ablation row.

---

## 1. Branch / file layout

| File | Action |
|---|---|
| `ultralytics/nn/modules/block.py` | append `DyHeadBlock` class |
| `ultralytics/nn/modules/head.py` | import `DyHeadBlock`; add `DyHeadDetect` class; export in `__all__` |
| `ultralytics/nn/modules/__init__.py` | re-export `DyHeadBlock`, `DyHeadDetect` |
| `ultralytics/nn/tasks.py` | import `DyHeadDetect`; include it in the Detect-family `frozenset` and `legacy` set |
| `ultralytics/cfg/models/11/yolo11-d.yaml` | new model config; replaces `Detect` with `DyHeadDetect` |

No baseline files are otherwise touched. The `.gitignore` change inherited from `b603e7be3`
keeps weights out of git but allows `results.csv`, `args.yaml`, plots, and logs under `runs/`.

---

## 2. Architecture (simplified DyHead)

DyHead applies three awareness modules **per FPN level** *before* the standard Detect cv2/cv3
branches. Following the convention in the manual, DCNv2 is replaced with a regular 3×3 conv to
keep dependencies minimal.

```
P3 ─┐                       per-level
P4 ─┼─► [DyHeadBlock × num_blocks] ─► Detect.cv2 / cv3
P5 ─┘
```

A single `DyHeadBlock` does:

```
x ─► (3×3 Conv + GroupNorm)               # 1) spatial-aware
  ─► × (AvgPool→1×1→ReLU→Hardsigmoid)     # 2) scale-aware (channel gate)
  ─► max(a1·x + b1,  a2·x + b2)           # 3) task-aware (DyReLU-B)
```

`(a1, b1, a2, b2)` are predicted from a global pool of the spatially+scale-attended feature
through a two-layer 1×1 conv. The last conv is initialized so the output starts at
`a1=1, b1=a2=b2=0`, i.e. the block is approximately identity at init — keeps early training
stable.

Per FPN level, channel counts differ (P3=64, P4=128, P5=256 for YOLO11n), so each level owns
its own DyHeadBlock weights. `num_blocks` (class attribute, default `2`) controls how many
DyHeadBlocks are cascaded per level.

---

## 3. Code: `DyHeadBlock` and `DyHeadDetect`

`DyHeadBlock` lives at the end of `ultralytics/nn/modules/block.py`. Key snippet:

```python
class DyHeadBlock(nn.Module):
    def __init__(self, c1):
        super().__init__()
        self.spatial_conv = nn.Conv2d(c1, c1, 3, padding=1)
        # GroupNorm groups must divide c1
        gn = max(1, min(16, c1))
        while c1 % gn != 0:
            gn -= 1
        self.gn = nn.GroupNorm(gn, c1)
        self.scale_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Conv2d(c1, 1, 1),
            nn.ReLU(inplace=True), nn.Hardsigmoid(inplace=True),
        )
        hidden = max(c1 // 4, 8)
        self.task_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(c1, hidden, 1), nn.ReLU(inplace=True),
            nn.Conv2d(hidden, c1 * 4, 1),
        )
        nn.init.zeros_(self.task_attn[-1].weight)
        with torch.no_grad():
            self.task_attn[-1].bias.zero_()
            self.task_attn[-1].bias[:c1] = 1.0  # a1 = 1
```

`DyHeadDetect` lives at the end of `ultralytics/nn/modules/head.py`:

```python
class DyHeadDetect(Detect):
    num_blocks: int = 2  # class attribute; not in __init__ to avoid parse_model arg ordering issues

    def __init__(self, nc=80, reg_max=16, end2end=False, ch=()):
        super().__init__(nc, reg_max, end2end, ch)
        self.dyhead = nn.ModuleList(
            nn.Sequential(*[DyHeadBlock(c) for _ in range(self.num_blocks)]) for c in ch
        )

    def forward(self, x):
        x = [self.dyhead[i](xi) for i, xi in enumerate(x)]
        return super().forward(x)
```

Why `num_blocks` is a class attribute, not a constructor arg: the parse_model path that
expands Detect-family modules injects `(reg_max, end2end, ch)` after `nc`, so the
`__init__` signature must remain `(nc, reg_max, end2end, ch)`. Subclassing + class attr is
the cleanest way to parameterize without forking parse_model.

---

## 4. parse_model wiring

In `ultralytics/nn/tasks.py`:

```python
elif m in frozenset(
    {Detect, DyHeadDetect, WorldDetect, YOLOEDetect, Segment, Segment26,
     YOLOESegment, YOLOESegment26, Pose, Pose26, OBB, OBB26}
):
    args.extend([reg_max, end2end, [ch[x] for x in f]])
    ...
    if m in {Detect, YOLOEDetect, Segment, Segment26, YOLOESegment, YOLOESegment26,
             Pose, Pose26, OBB, OBB26, DyHeadDetect}:
        m.legacy = legacy
```

This mirrors how `Detect` is already handled. The `isinstance(m, Detect)` checks elsewhere in
the file (build / loss / inference) automatically pick up `DyHeadDetect` because it is a Detect
subclass.

---

## 5. Model config: `ultralytics/cfg/models/11/yolo11-d.yaml`

Backbone + neck identical to `yolo11.yaml`. Only the final head line changes:

```yaml
- [[16, 19, 22], 1, DyHeadDetect, [nc]] # DyHeadDetect(P3, P4, P5)
```

Note: `[nc]` only — `num_blocks` is set on the class, not via yaml args.

---

## 6. Smoke test (autodl)

Run on the training machine after pulling `feat/dyhead`:

```bash
git fetch origin && git checkout feat/dyhead && git pull
python - <<'PY'
import torch
from ultralytics import YOLO
m = YOLO('ultralytics/cfg/models/11/yolo11-d.yaml', task='detect')
m.model.eval()
y = m.model(torch.zeros(1, 3, 640, 640))
print('build OK; output type:', type(y).__name__)
PY
```

Expected: model builds, forward returns a tuple/dict (eval mode) without error.

---

## 7. Training command (autodl, tmux)

```bash
tmux new -s train_d
tmux set-option remain-on-exit on
yolo detect train \
  model=ultralytics/cfg/models/11/yolo11-d.yaml \
  data=VisDrone.yaml \
  epochs=100 imgsz=640 batch=0.85 \
  device=0 workers=8 \
  project=runs/detect name=plus_D \
  iou=ciou
```

`iou=ciou` — keep the same loss as baseline/+T so the +D row isolates the head change.

---

## 8. Reproduction steps after training completes

1. `scp` weights and `runs/detect/plus_D/results.csv` back to local.
2. Manually drop weights into local artifact dir (not committed).
3. `git add 'runs/**'` (use glob — `runs/` blanket is removed in `.gitignore`); commit and push.
4. Update §9 of this CHANGELOG with the final metrics.
5. Update row 4 (the +D row) of `刘华硕-飞书导入实验记录表.xlsx`, columns I–O.

---

## 9. Results

Training completed on autodl (RTX 4090), 300 epochs, AutoBatch (`batch=0.85`, actual batch=46),
SGD, `iou=0.7`, `lr0=0.01`, dataset `dair_v2x_i`, imgsz 640. Total wall time ≈ 1.847 h.

Final metrics from `best.pt` validation (`runs/detect/runs/ablation/+D`):

| Metric | +D |
|---|---|
| Precision | 86.3 |
| Recall | 81.1 |
| mAP@0.5 | 86.6 |
| mAP@0.5:0.95 | 61.3 |
| FPS (full pipeline) | 435 |
| GFLOPs | 9.3 |
| Params (M) | 4.35 |

Speed (per image, RTX 4090, val): preprocess 0.1 ms / inference 1.6 ms / postprocess 0.6 ms.
FPS computed as `1000 / (pre + inference + post)` to stay consistent with `+T` / `+W` rows in
`刘华硕-飞书导入实验记录表.xlsx`.

Per-class mAP50 highlights (val): Car 0.959, Bus 0.953, Trafficcone 0.924, Cyclist 0.885,
Van 0.824, Truck 0.814, Pedestrian 0.792, Motorcyclist 0.775.

Comparison vs prior ablations (mAP50 / mAP50-95):

| Variant | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params (M) |
|---|---:|---:|---:|---:|---:|---:|---:|
| +T (Triplet) | 85.6 | 80.5 | 85.9 | 60.2 | 244 | 6.4 | 2.6 |
| +W (WIoU)    | 86.4 | 80.3 | 86.0 | 60.2 | 200 | 6.4 | 2.6 |
| **+D (DyHead)** | **86.3** | **81.1** | **86.6** | **61.3** | **435** | 9.3 | 4.35 |

DyHead 在 mAP50 / mAP50-95 / Recall 上均优于 `+T` 与 `+W`，代价是参数量约 +67%、FLOPs 约 +45%。
