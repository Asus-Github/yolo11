# CHANGELOG — feat/dwca

> 分支基于：`feat/dwca-p2`
> 创建日期：2026-06-10
> 实验编号：12c（DWCA）

---

## 改动摘要

**分解消融：DyHead + WIoU + CoordAttention，去掉 P2 小目标检测头。**

该实验用于回答：DWCA-P2 的提升中，CoordAttention 在不引入 P2/4 高分辨率检测分支时是否有独立贡献。

## 与 DWCA-P2 的差异

| 项目 | DWCA-P2 | DWCA |
|---|---|---|
| Triplet | ❌ | ❌ |
| CoordAttention | ✅ P3 后 | ✅ P3 后 |
| P2 检测头 | ✅ | ❌ 移除 |
| DyHead | ✅ 2 blocks | ✅ 2 blocks |
| WIoU | ✅ | ✅ |
| Detect 输入 | P2/P3/P4/P5 | P3/P4/P5 |

## 与 +DW 的差异

| 项目 | +DW | DWCA |
|---|---|---|
| Backbone | YOLO11 原版 | YOLO11 + CoordAttention at P3 end |
| Head | DyHeadDetect(P3/P4/P5) | DyHeadDetect(P3/P4/P5) |
| Loss | WIoU v3 | WIoU v3 |

因此 DWCA 是严格的 CA 单变量消融：在 +DW 基础上只增加 CoordAttention。

## 文件改动

| 文件 | 操作 | 说明 |
|---|---|---|
| `ultralytics/cfg/models/11/yolo11-dwca.yaml` | 新增 | 三尺度 DyHead + CoordAttention 配置，移除 P2 分支 |

## 关键结构

```text
Backbone: YOLO11 + CoordAttention at P3 end
Head:
  P5 → P4 → P3 (top-down)
  P3 → P4 → P5 (bottom-up)
  DyHeadDetect([P3, P4, P5]) — 3 scale inputs, 2 blocks
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
- `project=runs/ablation name=DWCA`

> WIoU 实验禁止直接 `yolo train`。必须使用 Python 入口在 `model.train(...)` 前设置 `BboxLoss.iou_type = "wiou"`，并在 smoke/正式日志中确认该值。

## AutoDL 复现命令

```bash
# tmux: t_train_dwca
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
print(f'[DWCA] BboxLoss.iou_type = {BboxLoss.iou_type}')
model = YOLO('ultralytics/cfg/models/11/yolo11-dwca.yaml')
model.train(
    data=str(runtime), epochs=300, imgsz=640, batch=0.85, nbs=64,
    device='0', workers=8, optimizer='SGD', lr0=0.01, cos_lr=True,
    weight_decay=0.0005, project='runs/ablation', name='DWCA',
    seed=42, pretrained=True, amp=True, cache=False, patience=50,
    exist_ok=True, plots=True,
)
PY
```

建议实际长训时放入 tmux 并 `tee runs/DWCA_train.log`。

## 预期与判据

| 指标 | +DW | DWCA-P2 | DWCA 预期 | 判读 |
|---|---:|---:|---:|---|
| mAP50 | 87.0 | 88.2 | 87.1~87.5 | 若高于 +DW，CA 有独立贡献 |
| mAP50-95 | 61.3 | 64.4 | 61.5~62.2 | 若明显低于 DWCA-P2，P2 是主增益来源 |
| GFLOPs | 9.3 | 14.2 | 约 9.3~9.5 | 若收益接近 +DW 但计算量低，适合作轻量对照 |

## 论文用途

- 若 DWCA > +DW：说明 CoordAttention 是比 Triplet 更正交的轻量注意力补充。
- 若 DWCA ≈ +DW 但 DW-P2 明显提升：说明 DWCA-P2 的主要贡献来自 P2 小目标检测头。
- 若 DWCA 与 DW-P2 均低于 DWCA-P2：说明 CoordAttention 与 P2 分支存在协同增益。

## 训练结果（2026-06-10）

- 训练状态：300 epochs completed；best epoch=267。
- WIoU 确认：正式日志中已打印 `[DWCA] BboxLoss.iou_type = wiou`。
- best.pt fused summary：168 layers，4,357,526 parameters，9.3 GFLOPs。
- 指标：P=86.8%，R=81.4%，mAP50=86.8%，mAP50-95=61.3%。
- 输出目录：`runs/detect/runs/ablation/DWCA/`；训练日志：`runs/DWCA_train.log`。

### 结果判读

| Variant | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| +DW | 86.0 | 81.9 | 87.0 | 61.3 | 9.3 | 4.35 |
| DWCA | 86.8 | 81.4 | 86.8 | 61.3 | 9.3 | 4.36 |
| DWCA-P2 | 86.1 | 83.3 | 88.2 | 64.4 | 14.2 | 4.46 |

DWCA 与 +DW 的 mAP50-95 基本持平，Precision 明显提高但 Recall 和 mAP50 略低；说明单独加入 CoordAttention 并没有带来稳定的高 IoU 定位增益。结合 DWCA-P2 的大幅提升，当前证据更支持：DWCA-P2 的核心收益主要来自 P2/4 高分辨率小目标分支，CoordAttention 更可能是轻量辅助或与 P2 形成协同，而不是单独主贡献。
