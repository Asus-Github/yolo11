# CHANGELOG — feat/tdw-co-p3

> 分支基于：`feat/tdw-co`（含 TripletAttention channel-only + DyHeadDetect + WIoU 全部基础设施）
> 创建日期：2026-06-09
> 实验编号：10（TDW-CO-P3）

---

## 改动摘要

**唯一改动**：将 `TripletAttention[no_spatial=True]` 从 P5 末端（原 layer 9）移至 P3 source 末端（新 layer 5）。

## 改动原理

| 项目 | TDW-CO（原方案） | TDW-CO-P3（本方案） |
|---|---|---|
| Triplet 位置 | P5 末端（20×20 @640） | P3 source 末端（80×80 @640） |
| 目标覆盖 | 大目标为主 | **小目标为主**（行人/骑行者） |
| 与 DyHead 关系 | P5 紧邻 SPPF/C2PSA，注意力堆叠 | P3 与 DyHead head 端空间注意力距离远，**机制正交** |
| 与 C2PSA 关系 | 紧邻 C2PSA（PSA 注意力），边际收益低 | 远离 C2PSA，无冗余 |

核心假设：DAIR-V2X-I 路侧场景小目标（远距行人/骑行者）主要由 P3/8 层检测，Triplet 在 P3 增强跨维通道交互可直接提升小目标 Recall。

## 文件改动

| 文件 | 操作 | 说明 |
|---|---|---|
| `ultralytics/cfg/models/11/yolo11-tdw-co-p3.yaml` | 新增 | 唯一改动文件 |

## YAML 层号对照（vs TDW-CO）

```
TDW-CO:                          TDW-CO-P3:
0  Conv P1/2                     0  Conv P1/2
1  Conv P2/4                     1  Conv P2/4
2  C3k2                          2  C3k2
3  Conv P3/8                     3  Conv P3/8
4  C3k2 (P3 source)             4  C3k2 (P3 source)
5  Conv P4/16                    5  ★ TripletAttention [True]  ← 从 layer 9 移到此处
6  C3k2 (P4 source)             6  Conv P4/16
7  Conv P5/32                    7  C3k2 (P4 source)
8  C3k2                          8  Conv P5/32
9  ★ TripletAttention [True]     9  C3k2
10 SPPF                          10 SPPF
11 C2PSA (P5 source)            11 C2PSA (P5 source)
```

Head 层 Concat 引用随之调整：P4 source 从 6→7，P3 source 从 4→5。

## 训练命令（AutoDL）

```bash
# tmux: t_train_tdw_co_p3
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics && /root/miniconda3/bin/yolo train \
  model=ultralytics/cfg/models/11/yolo11-tdw-co-p3.yaml \
  data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
  epochs=300 batch=0.85 imgsz=640 optimizer=SGD seed=42 pretrained=false \
  project=runs/ablation name=TDW-CO-P3 2>&1 | tee runs/TDW-CO-P3_train.log
```

注意：需在训练脚本中设置 `BboxLoss.iou_type = "wiou"`（与 TDW-CO 相同）。

## 预期指标

| 指标 | TDW-CO 实际 | TDW-CO-P3 预测 | 依据 |
|---|---|---|---|
| mAP50 | 86.7% | 86.9~87.2% | P3 增强小目标 Recall |
| mAP50-95 | 61.2% | 61.3~61.6% | 高 IoU 下小目标定位改善 |
| Recall | 81.4% | 81.6~82.0% | 小目标检出率提升 |
| GFLOPs | 9.29 | ~9.5 | P3 分辨率高，FLOPs 略增 |

## 通过判据

- mAP50 ≥ 86.9%（即 ≥ TDW-CO + 0.2）→ 方案有效
- 否则保留 TDW-CO 作为最佳 Triplet 方案

## 复现步骤

1. `git checkout feat/tdw-co-p3`
2. AutoDL 上同步分支：`git fetch origin && git checkout feat/tdw-co-p3`
3. 设置 WIoU：在训练前 `BboxLoss.iou_type = "wiou"`
4. 执行上方训练命令
5. 训练完成后采集 best epoch 指标
