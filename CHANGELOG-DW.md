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

xlsx target: `刘华硕-飞书导入实验记录表.xlsx` sheet `数据表` row 8 (cells I8–O8).
