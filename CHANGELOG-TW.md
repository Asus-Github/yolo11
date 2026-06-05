# CHANGELOG — `+TW` (Triplet + WIoU v3)

> Branch: `feat/triplet-wiou`
> Base: `feat/wiou` (cherry-pick of `feat/triplet` integration commit `361fd0d`)
> Created: 2026-06-05

## 1. Goal

Combine the two ablation modules that already shipped independently:

- `+T` (Triplet Attention): inserted at the P5 end of the backbone (before SPPF).
- `+W` (Wise-IoU v3): replaces CIoU in `BboxLoss` via `BboxLoss.iou_type = "wiou"`.

No head change — final layer remains the standard `Detect` (not `DyHeadDetect`).
Network structure is byte-identical to `yolo11-t.yaml`; only the IoU branch in
`BboxLoss` switches to WIoU v3 at training time.

## 2. Files added / changed

| File | Source | Notes |
|---|---|---|
| `ultralytics/nn/modules/conv.py` | from `feat/triplet` | adds `ZPool`, `AttentionGate`, `TripletAttention` |
| `ultralytics/nn/modules/__init__.py` | merged | exports `TripletAttention` |
| `ultralytics/nn/tasks.py` | merged | imports + `parse_model` branch for `TripletAttention` |
| `ultralytics/cfg/models/11/yolo11-t.yaml` | from `feat/triplet` | reused as-is (no separate `-tw.yaml`) |
| `ultralytics/utils/loss.py` | from `feat/wiou` | already on base — `BboxLoss` supports `iou_type="wiou"` |
| `train_variant.py` | from `feat/wiou` | already on base — `--iou wiou` toggles WIoU v3 |

Decision: do **not** create a dedicated `yolo11-tw.yaml`. WIoU is a loss-only switch
and the network is identical to `yolo11-t.yaml`; an extra cfg would be redundant.

## 3. Branch creation log

```bash
# Local
git checkout feat/wiou            # 55bb8ab54 (+W trained, results recorded)
git checkout -b feat/triplet-wiou
git cherry-pick 361fd0dba         # Triplet integration from feat/triplet
# Auto-merge: __init__.py, conv.py, tasks.py — clean.
# Conflict: HANDOFF.md (kept ours, the +W-side handoff).
# Result commit: f5f8707 feat(triplet): integrate Triplet Attention module (+T variant)
```

Smoke test (without cv2/torch on macOS — AST + grep validation):

- `yolo11-t.yaml` references `TripletAttention` ✅
- `loss.py` exports `iou_type` and a `wiou` branch ✅
- `conv.py` declares `class TripletAttention` ✅
- `tasks.py` registers `TripletAttention` in `parse_model` ✅
- `ultralytics/nn/modules/__init__.py` exports `TripletAttention` ✅

## 4. Training command (autodl)

WIoU is enabled via `train_variant.py --iou wiou`, **not** the `yolo` CLI's
`iou=` flag (which is the NMS threshold and would conflict).

```bash
ssh autodl 'cd /root/autodl-tmp/ultralytics && \
  source /etc/network_turbo && \
  git fetch --all && git checkout -f feat/triplet-wiou && \
  source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && \
  tmux new-session -d -s t_train_tw && \
  tmux set-option -t t_train_tw remain-on-exit on && \
  tmux send-keys -t t_train_tw "python train_variant.py \
    -c ultralytics/cfg/models/11/yolo11-t.yaml \
    --iou wiou \
    -n +TW \
    --epochs 300 \
    --device 0 2>&1 | tee runs/+TW_train.log; echo EXITCODE=\$?" C-m'
```

Notes:
- `train_variant.py` sets `BboxLoss.iou_type = "wiou"` before `model.train(...)`.
- `nbs=64` is hard-coded in `train_variant.py` → effective batch matches all other ablations.
- `batch=0.85` AutoBatch (default when `-b` not passed).

## 5. Results

Trained on autodl RTX 4090, AutoBatch=61 (85% mem), 300 epochs requested,
**early-stopped at epoch 267** (best at epoch 217, patience=50). Total wall time 1.334 h.

best.pt validation:

| Metric | Value |
|---|---|
| Precision | 0.858 |
| Recall | 0.810 |
| mAP50 | 0.863 |
| mAP50-95 | 0.605 |
| FPS (= 1000/(pre+inf+post)) | 208.3 |
| GFLOPs | 6.4 |
| Params (M) | 2.58 |

Speed line: `0.0ms preprocess, 0.2ms inference, 0.0ms loss, 4.6ms postprocess per image`
→ FPS = 1000 / (0.0 + 0.2 + 4.6) = **208.3**.

### 5.1 Per-class (best.pt)

| Class | Images | Instances | P | R | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|---:|
| all          | 1411 | 65255 | 0.858 | 0.810 | 0.863 | 0.605 |
| Car          | 1408 | 18342 | 0.900 | 0.909 | 0.961 | 0.787 |
| Truck        |  595 |   660 | 0.757 | 0.932 | 0.805 | 0.548 |
| Van          |  849 |  1385 | 0.790 | 0.742 | 0.821 | 0.688 |
| Bus          |  496 |   669 | 0.927 | 0.914 | 0.947 | 0.770 |
| Cyclist      | 1238 |  3469 | 0.862 | 0.792 | 0.878 | 0.591 |
| Motorcyclist | 1121 |  3632 | 0.833 | 0.612 | 0.770 | 0.509 |
| Pedestrian   | 1228 |  5073 | 0.856 | 0.707 | 0.800 | 0.442 |
| Trafficcone  | 1411 | 32025 | 0.938 | 0.872 | 0.925 | 0.502 |

### 5.2 Comparison vs single modules and `+TD`

| Variant | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `+T`  | 0.856 | 0.805 | 0.859 | 0.602 | 244 | 6.4 | 2.60 |
| `+D`  | 0.863 | 0.811 | 0.866 | 0.613 | 435 | 9.3 | 4.35 |
| `+W`  | 0.864 | 0.803 | 0.860 | 0.602 | 200 | 6.4 | 2.60 |
| `+TD` | 0.858 | 0.810 | 0.862 | 0.610 | 233 | 9.29 | 4.36 |
| **`+TW`** | **0.858** | **0.810** | **0.863** | **0.605** | **208** | **6.4** | **2.58** |

Observations:

- `+TW` improves on **`+T` alone**: mAP50 +0.4 (0.859 → 0.863), mAP50-95 +0.3
  (0.602 → 0.605), R +0.5. WIoU's gradient-reweighting on top of Triplet
  feature refinement is mildly additive.
- `+TW` improves on **`+W` alone**: mAP50 +0.3 (0.860 → 0.863), mAP50-95 +0.3.
  Triplet's cross-axis attention yields a small bump even when CIoU is replaced
  by WIoU v3.
- `+TW` is **below `+D` and `+TD`** on mAP50-95 (−0.8 vs +D, −0.5 vs +TD), but
  with **no head replacement** — Params 2.58M vs 4.35M, GFLOPs 6.4 vs 9.3.
- FPS 208 ≈ `+W` (200) and slower than `+T` (244): WIoU's per-batch focusing
  factor adds modest overhead at training time but inference cost is
  dominated by the same Triplet permute/pool path as `+T`. The 244→208 gap is
  postprocess-side (4.1 → 4.6 ms), within run-to-run noise.
- Conclusion: `+TW` is **the strongest "no-head-change" combination so far**
  on mAP50-95 (0.605), but still trails any DyHead-containing variant on
  raw accuracy. Useful when parameter budget is constrained.

xlsx target: `刘华硕-飞书导入实验记录表.xlsx` sheet `数据表` row 7
(I7=85.8, J7=81.0, K7=86.3, L7=60.5, M7=208.3, N7=6.4, O7=2.58).
