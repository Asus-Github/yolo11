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

_To be filled after training completes._

| Metric | Value |
|---|---|
| Precision | TBD |
| Recall | TBD |
| mAP50 | TBD |
| mAP50-95 | TBD |
| FPS (= 1000/(pre+inf+post)) | TBD |
| GFLOPs | TBD |
| Params (M) | TBD |

xlsx target: `刘华硕-飞书导入实验记录表.xlsx` sheet `数据表` row 7 (cells I7–O7).
