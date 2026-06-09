# CHANGELOG — feat/tdw-co-d3

> 分支基于：`feat/tdw-co`（含 TripletAttention channel-only + DyHeadDetect + WIoU 全部基础设施）
> 创建日期：2026-06-09
> 实验编号：11（TDW-CO-D3）

---

## 改动摘要

DyHead 级联块数从 2 增加到 3：新增 `DyHeadDetect3` 子类 + 对应 YAML。

## 改动原理

| 项目 | TDW-CO（原方案） | TDW-CO-D3（本方案） |
|---|---|---|
| DyHead blocks | 2 | **3** |
| 理论依据 | DyHead 原论文建议 6 块，YOLO 改进类普遍 1-2 | 2→3 是"低成本加深"的安全尝试 |
| DyHead 有效性 | +D 单独贡献 mAP50 +0.7，是当前最有效模块 | 加深有继续提升空间 |
| FPS 影响 | ~62 FPS | 预计下降 25~35%（路侧不敏感） |
| Params 增长 | 4.36M | +~0.3M |

## 文件改动

| 文件 | 操作 | 说明 |
|---|---|---|
| `ultralytics/nn/modules/head.py` | 修改 | 末尾新增 `DyHeadDetect3(DyHeadDetect)` 子类 |
| `ultralytics/nn/modules/__init__.py` | 修改 | 导出 `DyHeadDetect3` |
| `ultralytics/nn/tasks.py` | 修改 | import + `parse_model` frozenset 注册 |
| `ultralytics/cfg/models/11/yolo11-tdw-co-d3.yaml` | 新增 | 唯一区别：Detect 改为 `DyHeadDetect3` |

## 代码改动详情

### head.py（末尾追加）
```python
class DyHeadDetect3(DyHeadDetect):
    """DyHeadDetect with 3 cascaded blocks (default is 2)."""
    num_blocks: int = 3
```

### __init__.py
```python
from .head import (
    ...
    DyHeadDetect3,  # 新增
    ...
)
```

### tasks.py
- import 行新增 `DyHeadDetect3`
- `parse_model` 中的两处 frozenset/set 加入 `DyHeadDetect3`

### YAML 唯一差异
```yaml
# TDW-CO 原版:
- [[17, 20, 23], 1, DyHeadDetect, [nc]]   # 2 blocks
# TDW-CO-D3:
- [[17, 20, 23], 1, DyHeadDetect3, [nc]]  # 3 blocks
```

## 训练命令（AutoDL）

```bash
# tmux: t_train_tdw_co_d3
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics && /root/miniconda3/bin/yolo train \
  model=ultralytics/cfg/models/11/yolo11-tdw-co-d3.yaml \
  data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
  epochs=300 batch=0.85 imgsz=640 optimizer=SGD seed=42 pretrained=false \
  project=runs/ablation name=TDW-CO-D3 2>&1 | tee runs/TDW-CO-D3_train.log
```

注意：需在训练脚本中设置 `BboxLoss.iou_type = "wiou"`（与 TDW-CO 相同）。

## 预期指标

| 指标 | TDW-CO 实际 | +DW 实际 | TDW-CO-D3 预测 | 依据 |
|---|---|---|---|---|
| mAP50 | 86.7% | 87.0% | 86.9~87.2% | DyHead 加深提升多尺度感知 |
| mAP50-95 | 61.2% | 61.3% | 61.3~61.6% | 更多 block 精细化定位 |
| GFLOPs | 9.29 | 9.3 | ~10.0 | +1 block per level |
| Params | 4.36M | 4.35M | ~4.65M | +0.3M |

## 通过判据

- mAP50 ≥ 87.2%（即 ≥ +DW + 0.2）→ DyHead 加深有效，可考虑 D4
- mAP50 < 87.2% 且与 +DW 打平 → DyHead 已饱和，终止加深方向

## 复现步骤

1. `git checkout feat/tdw-co-d3`
2. AutoDL 上同步分支：`git fetch origin && git checkout feat/tdw-co-d3`
3. 设置 WIoU：在训练前 `BboxLoss.iou_type = "wiou"`
4. 执行上方训练命令
5. 训练完成后 `model.fuse()` 再测 FPS（DyHead 不可融合部分体现真实推理代价）
