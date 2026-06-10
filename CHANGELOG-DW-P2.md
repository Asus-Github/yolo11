# CHANGELOG — feat/dw-p2

> 分支基于：`feat/dwca-p2`
> 创建日期：2026-06-10
> 实验编号：12b（DW-P2）

---

## 改动摘要

**分解消融：DyHead + WIoU + P2 小目标检测头，去掉 CoordAttention。**

该实验用于回答：DWCA-P2 的大幅提升主要来自 P2/4 高分辨率检测头，还是来自 CoordAttention，或二者协同。

## 与 DWCA-P2 的差异

| 项目 | DWCA-P2 | DW-P2 |
|---|---|---|
| Triplet | ❌ | ❌ |
| CoordAttention | ✅ P3 后 | ❌ 移除 |
| P2 检测头 | ✅ | ✅ |
| DyHead | ✅ 2 blocks | ✅ 2 blocks |
| WIoU | ✅ | ✅ |
| Detect 输入 | P2/P3/P4/P5 | P2/P3/P4/P5 |

## 文件改动

| 文件 | 操作 | 说明 |
|---|---|---|
| `ultralytics/cfg/models/11/yolo11-dw-p2.yaml` | 新增 | 在 DWCA-P2 基础上删除 CoordAttention，保留 P2 分支 |

## 关键结构

```text
Backbone: 标准 YOLO11，无 Triplet，无 CoordAttention
Head:
  P5 → P4 → P3 → P2 (top-down)
  P2 → P3 → P4 → P5 (bottom-up)
  DyHeadDetect([P2, P3, P4, P5]) — 4 scale inputs, 2 blocks
Loss: WIoU v3
```

## 训练口径

必须与主消融实验一致：

- `epochs=300`
- `batch=0.85`
- `nbs=64`
- `imgsz=640`
- `optimizer=SGD`
- `seed=42`
- `pretrained=true`
- `cos_lr=true`
- `patience=50`
- `project=runs/ablation name=DW-P2`

> WIoU 实验禁止直接 `yolo train`。必须使用 Python 入口在 `model.train(...)` 前设置 `BboxLoss.iou_type = "wiou"`。

## AutoDL 复现命令

```bash
# tmux: t_train_dw_p2
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics

python - <<'PY'
from pathlib import Path
import sys, yaml
sys.path.insert(0, str(Path.cwd()))
from ultralytics import YOLO
from ultralytics.utils.loss import BboxLoss

cfg = yaml.safe_load(Path('datasets/dair_v2x_i/dair_v2x_i.yaml').read_text())
cfg['path'] = str(Path.cwd() / 'datasets/dair_v2x_i')
runtime = Path('datasets/dair_v2x_i/_runtime.yaml')
runtime.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))

BboxLoss.iou_type = 'wiou'
print(f'[DW-P2] BboxLoss.iou_type = {BboxLoss.iou_type}')
model = YOLO('ultralytics/cfg/models/11/yolo11-dw-p2.yaml')
model.train(
    data=str(runtime), epochs=300, imgsz=640, batch=0.85, nbs=64,
    device='0', workers=8, optimizer='SGD', lr0=0.01, cos_lr=True,
    weight_decay=0.0005, project='runs/ablation', name='DW-P2',
    seed=42, pretrained=True, amp=True, cache=False, patience=50,
    exist_ok=True, plots=True,
)
PY
```

建议实际长训时放入 tmux 并 `tee runs/DW-P2_train.log`。

## 预期与判据

| 指标 | +DW | DWCA-P2 | DW-P2 预期 | 判读 |
|---|---:|---:|---:|---|
| mAP50 | 87.0 | 88.2 | 87.7~88.1 | 若接近 DWCA-P2，P2 是主因 |
| mAP50-95 | 61.3 | 64.4 | 63.0~64.0 | 若明显高于 +DW，P2 有独立贡献 |
| Recall | 81.9 | 83.3 | 82.7~83.3 | P2 应主要提升小目标召回 |

## 论文用途

- 若 DW-P2 ≈ DWCA-P2：说明 P2 高分辨率分支是主要贡献，CA 是轻量辅助。
- 若 DW-P2 明显低于 DWCA-P2：说明 CA 与 P2 存在协同增益。
