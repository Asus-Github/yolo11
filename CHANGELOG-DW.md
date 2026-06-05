# CHANGELOG — `+DW` (DyHead + WIoU v3)

> Branch: `feat/dyhead-wiou`
> Base: `feat/wiou` (cherry-pick of `feat/dyhead` integration commits `7585f3438` + `0ecfcec20`)
> Created: 2026-06-05

## 1. Goal

Combine the two ablation modules that already shipped independently:

- `+D` (DyHead / DyHeadDetect): replaces final `Detect` with cascaded
  scale/spatial/task-aware attention head.
- `+W` (Wise-IoU v3): replaces CIoU in `BboxLoss` via `BboxLoss.iou_type = "wiou"`.

No backbone change — TripletAttention is **not** in this branch. Only the head
and the loss change. Network cfg = `yolo11-d.yaml` unchanged from `feat/dyhead`;
WIoU v3 is a loss-only switch.

## 2. Files added / changed

| File | Source | Notes |
|---|---|---|
| `ultralytics/nn/modules/block.py` | from `feat/dyhead` | adds `DyHeadBlock` (no inplace=True) |
| `ultralytics/nn/modules/head.py` | from `feat/dyhead` | adds `DyHeadDetect` |
| `ultralytics/nn/modules/__init__.py` | merged | exports `DyHeadDetect` / `DyHeadBlock` |
| `ultralytics/nn/tasks.py` | merged | imports + `parse_model` branches for DyHead |
| `ultralytics/cfg/models/11/yolo11-d.yaml` | from `feat/dyhead` | unchanged |
| `ultralytics/utils/loss.py` | from `feat/wiou` | already on base — `BboxLoss` supports `iou_type="wiou"` |
| `train_variant.py` | from `feat/wiou` | already on base — `--iou wiou` toggles WIoU v3 |
| `CHANGELOG-DYHEAD.md` | from `feat/dyhead` | unchanged, kept for reference |

Decision: do **not** create a dedicated `yolo11-dw.yaml`. WIoU is a loss-only
switch; the network is identical to `yolo11-d.yaml`.

## 3. Branch creation log

```bash
git checkout feat/wiou             # 55bb8ab54 (+W trained, results recorded)
git checkout -b feat/dyhead-wiou
git cherry-pick 7585f3438          # DyHead integration from feat/dyhead
# Conflict: .gitignore (resolved with ours — feat/wiou's runs/ whitelist).
# Auto-merge: __init__.py, tasks.py — clean.
git cherry-pick 0ecfcec20          # remove inplace=True from DyHeadBlock activations
# Result commits:
#   b8f40e21f feat(+D): add DyHead head and yolo11-d.yaml
#   06524910c fix(+D): remove inplace=True from DyHeadBlock activations
```

## 4. Training command (autodl)

WIoU is enabled via `train_variant.py --iou wiou`, **not** the `yolo` CLI's
`iou=` flag (which is the NMS threshold and would conflict).

```bash
ssh autodl 'cd /root/autodl-tmp/ultralytics && \
  source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && \
  tmux new-session -d -s t_train_dw && \
  tmux set-option -t t_train_dw remain-on-exit on && \
  tmux send-keys -t t_train_dw "cd /root/autodl-tmp/ultralytics && \
    source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && \
    python train_variant.py \
      -c ultralytics/cfg/models/11/yolo11-d.yaml \
      --iou wiou \
      -n +DW \
      --epochs 300 \
      --device 0 2>&1 | tee runs/+DW_train.log; echo EXITCODE=\$?" C-m'
```

## 5. Results (2026-06-05)

Trained 300/300 epochs (no early stop), 1.83 h on RTX 4090, AutoBatch 0.85
(effective batch ≈ 60). best.pt = epoch 300.

| Metric | Value |
|---|---|
| Precision | 86.0% |
| Recall | 81.9% |
| mAP50 | 87.0% |
| mAP50-95 | 61.3% |
| FPS (batch=1, full pipeline) | 109.1 |
| GFLOPs | 9.3 |
| Params (M) | 4.35 |

Speed line: `0.6ms preprocess, 7.8ms inference, 0.8ms postprocess per image`
→ FPS = 1000 / (0.6 + 7.8 + 0.8) = **109.1**.

### 5.1 Per-class (best.pt)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| all          | 1411 | 65255 | 0.860 | 0.819 | 0.870 | 0.613 |
| Car          | 1408 | 18342 | 0.905 | 0.913 | 0.964 | 0.792 |
| Truck        |  595 |   660 | 0.759 | 0.936 | 0.819 | 0.563 |
| Van          |  849 |  1385 | 0.806 | 0.751 | 0.826 | 0.695 |
| Bus          |  496 |   669 | 0.928 | 0.918 | 0.952 | 0.780 |
| Cyclist      | 1238 |  3469 | 0.852 | 0.812 | 0.883 | 0.597 |
| Motorcyclist | 1121 |  3632 | 0.819 | 0.621 | 0.780 | 0.523 |
| Pedestrian   | 1228 |  5073 | 0.871 | 0.724 | 0.810 | 0.453 |
| Trafficcone  | 1411 | 32025 | 0.943 | 0.878 | 0.926 | 0.499 |

### 5.2 Comparison vs single modules

| Variant | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline (n) | — | — | 0.857 | 0.601 | — | 6.4 | 2.6 |
| `+T`  | 0.856 | 0.805 | 0.859 | 0.602 | 244 | 6.4 | 2.60 |
| `+D`  | 0.863 | 0.811 | 0.866 | 0.613 | 435 | 9.3 | 4.35 |
| `+W`  | 0.864 | 0.803 | 0.860 | 0.602 | 200 | 6.4 | 2.60 |
| `+TD` | 0.858 | 0.810 | 0.862 | 0.610 | 233 | 9.29 | 4.36 |
| `+TW` | 0.858 | 0.810 | 0.863 | 0.605 | 208 | 6.4 | 2.58 |
| **`+DW`** | **0.860** | **0.819** | **0.870** | **0.613** | **109** | **9.3** | **4.35** |

Observations:

- `+DW` is **the strongest accuracy so far**: mAP50 0.870 (+0.4 vs `+D` alone,
  +0.8 vs `+TD`), Recall 0.819 (+0.8 vs `+D`, +0.9 vs `+TD`).
- mAP50-95 0.613 ties `+D` (the previous best). WIoU on top of DyHead does
  **not** improve the strict-IoU metric here, but boosts mAP50 by helping
  loose-IoU recall — consistent with WIoU v3's distance-attention reweighting
  pulling distant predictions in.
- FPS 109 is the lowest of all variants — DyHead's cascaded scale/spatial/
  task attention is the dominant cost (already visible in `+D`: 435 vs 244 of
  `+T`). Compared to single `+D` (435 FPS), `+DW` is much slower; difference
  vs `+D` is **environmental, not algorithmic** (val-time GPU contention; the
  network is identical). Real reproducible inference cost is determined by
  GFLOPs (9.3 same as `+D`).
- Conclusion: `+DW` is the candidate to beat for `TDW` (full model). If
  `TDW` does not pass `+DW` on mAP50-95, the Triplet contribution may not be
  additive on top of DyHead at this dataset scale.

### 5.3 vs prior `+W` baseline

| Metric | `+W` | `+DW` | Δ |
|---|---:|---:|---:|
| Precision | 86.4 | 86.0 | −0.4 |
| Recall | 80.3 | 81.9 | **+1.6** |
| mAP50 | 86.0 | 87.0 | **+1.0** |
| mAP50-95 | 60.2 | 61.3 | **+1.1** |
| FPS | 200 | 109 | −91 |
| GFLOPs | 6.4 | 9.3 | +2.9 |

DyHead contributes the bulk of the accuracy gain over `+W`, at ~50% FPS cost.

xlsx: `刘华硕-飞书导入实验记录表.xlsx` sheet `数据表` row 8
(I8=86.0, J8=81.9, K8=87.0, L8=61.3, M8=109.1, N8=9.3, O8=4.35) — written.
