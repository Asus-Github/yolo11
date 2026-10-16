# Agent Handoff — TDW / DWCA-P2 消融与对比实验记录

> 给下一位 agent：本文档是当前会话全局快照。重点是继续 DWCA-P2 分解消融，并严格遵守 AutoDL/WIoU/tmux/同步硬性要求。
> 用户 = 刘华硕，研究方向 YOLOv11 + Triplet Attention + DyHead + Wise-IoU / DWCA-P2 消融实验，硕士论文。

---

## 1. 当前重点：DWCA-P2 分解消融进行中

DWCA-P2 已成为当前最强方案，需要用两个分解消融拆分 `CoordAttention` 与 `P2/4` 小目标检测头的贡献：

| 优先级 | 实验 | 分支 | YAML | 变量控制 | 当前状态 |
|---|---|---|---|---|---|
| P0 | DW-P2 | `feat/dw-p2` | `ultralytics/cfg/models/11/yolo11-dw-p2.yaml` | 去 CA，仅保留 P2 + DyHead + WIoU | ✅ 正式训练完成；best epoch=253；P=85.6%、R=83.5%、mAP50=88.1%、mAP50-95=64.4%；已写入 Excel；完整产物已同步本地；非权重产物已 push 到 `feat/dw-p2`（commit `17836f249`） |
| P1 | DWCA | `feat/dwca` | `ultralytics/cfg/models/11/yolo11-dwca.yaml` | 保留 CA，去 P2，仅三尺度 DyHead + WIoU | ✅ 正式训练完成；best epoch=267；P=86.8%、R=81.4%、mAP50=86.8%、mAP50-95=61.3%；已写入 Excel；完整产物已同步本地；非权重产物已 push 到 `feat/dwca`（commit `5a6736deb`） |

### 1.1 已完成的正式前校验

| 实验 | 结构校验 | 训练 smoke | 关键结果 |
|---|---|---|---|
| DW-P2 | ✅ 通过 | ✅ 1 epoch 通过 | `BboxLoss.iou_type=wiou`；`DyHeadDetect(P2,P3,P4,P5)`；strides `[4,8,16,32]`；`CA=0`；summary 约 `297 layers / 4.46M / 14.4 GFLOPs` |
| DWCA | ✅ 通过 | ✅ 1 epoch 通过 | `BboxLoss.iou_type=wiou`；`DyHeadDetect(P3,P4,P5)`；strides `[8,16,32]`；`CA=1`；summary 约 `249 layers / 4.37M / 9.5 GFLOPs` |

### 1.2 继续训练时常用命令

```bash
# 旧机器 DW-P2
ssh autodl
tmux attach -t t_train_dw_p2
tmux capture-pane -t t_train_dw_p2 -p | tail -60
tail -f /root/autodl-tmp/ultralytics/runs/DW-P2_train.log
nvidia-smi

# 新机器 DWCA
ssh -p 20327 root@connect.bjb1.seetacloud.com
tmux attach -t t_train_dwca
tmux capture-pane -t t_train_dwca -p | tail -60
tail -f /root/autodl-tmp/ultralytics/runs/DWCA_train.log
nvidia-smi
```

---

## 2. 已完成消融实验结果

| 序号 | 组别 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M | 备注 |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | baseline | 85.9 | 80.8 | 85.9 | 60.9 | 6.4 | 2.60 | YOLOv11n 原版 |
| 2 | +T | 85.6 | 80.5 | 85.9 | 60.2 | 6.4 | 2.60 | 仅加 Triplet |
| 3 | +D | 86.3 | 81.1 | 86.6 | 61.3 | 9.3 | 4.35 | 仅加 DyHead |
| 4 | +W | 86.4 | 80.3 | 86.0 | 60.2 | 6.4 | 2.60 | 仅换 WIoU |
| 5 | +TD | 85.8 | 81.0 | 86.2 | 61.0 | 9.3 | 4.36 | Triplet + DyHead |
| 6 | +TW | 85.8 | 81.0 | 86.3 | 60.5 | 6.4 | 2.58 | Triplet + WIoU |
| 7 | +DW | 86.0 | 81.9 | 87.0 | 61.3 | 9.3 | 4.35 | DyHead + WIoU，强基线 |
| 8 | TDW | 86.8 | 80.8 | 86.5 | 60.9 | 9.3 | 4.36 | Triplet + DyHead + WIoU |
| 9 | TDW-CO | 86.2 | 81.4 | 86.7 | 61.2 | 9.3 | 4.36 | channel-only Triplet |
| 10 | TDW-CO-P3 | 86.5 | 81.4 | 86.7 | 61.1 | 9.4 | 4.35 | Triplet channel-only 移至 P3，未超 +DW |
| 11 | TDW-CO-D3 | 86.1 | 81.3 | 86.3 | 61.1 | 10.9 | 5.24 | DyHead 2→3 blocks，未带来收益 |
| 12 | DWCA-P2 | 86.1 | 83.3 | 88.2 | 64.4 | 14.2 | 4.46 | **当前最强：CA + P2 head + DyHead + WIoU（AutoBatch=25）** |
| 13 | DWCA | 86.8 | 81.4 | 86.8 | 61.3 | 9.3 | 4.36 | CA-only（去 P2），与 +DW 基本持平 |
| 14 | DW-P2 | 85.6 | 83.5 | 88.1 | 64.4 | 14.2 | 4.45 | P2-only（去 CA），几乎复现 DWCA-P2 |
| 15 | DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 | batch=32 固定复验；best epoch=234；EarlyStopping at 284/300；WIoU v3；nbs=64 |
| 16 | baseline-b32 | 85.7 | 80.8 | 86.0 | 60.2 | 6.3 | 2.58 | batch=32 固定复验；main 分支；YAML=`yolo11.yaml`；pretrained=false；CIoU/default；best epoch=243；EarlyStopping at 293/300；nbs=64 |

### 2.1 关键结论

- **DWCA-P2 是当前主方案**：相比 +DW，mAP50 +1.2、mAP50-95 +3.1、Recall +1.4，但 GFLOPs 从 9.3 升至 14.2。
- Triplet 方向基本停止：+T、TDW、TDW-CO、TDW-CO-P3 均未超过 +DW，说明 Triplet 与 DyHead 空间注意力可能冗余。
- TDW-CO-D3 说明单纯加深 DyHead 也无收益。
- DWCA（CA-only，去 P2）=86.8/81.4/86.8/61.3，基本与 +DW 持平：CA 单独提升有限，主要表现为 Precision 提高但 Recall/mAP50 没有超过 +DW。
- DW-P2（P2-only，去 CA）=85.6/83.5/88.1/64.4，几乎复现 DWCA-P2 的 mAP50-95；最终说明 DWCA-P2 的主收益来自 P2/4 高分辨率小目标分支，CA 更像轻量精度调节或边际协同项。

---

## 3. 已完成对比实验结果

### 3.1 官方预训练参考表（不与同口径消融混比）

| 序号 | 模型 | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M | 状态 |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 10 | YOLOv5n.pt | 87.3 | 81.4 | 87.0 | 62.3 | 7.8 | 2.65 | ✅ 已完成 |
| 11 | YOLOv8n.pt | 87.2 | 82.1 | 87.3 | 62.8 | 8.1 | 3.01 | ✅ 已完成 |
| 12 | YOLOv10n.pt | 85.2 | 81.3 | 86.9 | 63.5 | 6.5 | 2.27 | ✅ 已完成；官方预训练参考中 mAP50-95 最高 |
| 18 | YOLOv11n.pt | 86.4 | 81.6 | 87.0 | 62.3 | 6.3 | 2.58 | ✅ 已完成；仅作预训练参考 |

### 3.2 YAML/scratch 同口径结构对比表

| 序号 | 模型 | 模型/YAML | P/% | R/% | mAP50/% | mAP50-95/% | GFLOPs | Params/M | 状态 |
|---:|---|---|---:|---:|---:|---:|---:|---:|---|
| 13 | YOLOv11n baseline | `yolo11n.yaml` | 85.9 | 80.8 | 85.9 | 60.9 | 6.4 | 2.60 | ✅ baseline |
| 15 | YOLOv8n-yaml | `yolov8n.yaml` | 86.5 | 81.2 | 86.5 | 61.0 | 8.1 | 3.01 | ✅ 已完成 |
| 16 | YOLOv5n-yaml | `yolov5n.yaml` | 85.4 | 81.0 | 85.8 | 59.9 | 7.1 | 2.50 | ✅ 已完成 |
| 17 | YOLOv10n-yaml | `yolov10n.yaml` | 85.8 | 80.1 | 85.7 | 60.7 | 8.4 | 2.71 | ✅ 已完成 |

结论：论文建议拆成两张表：`YAML/scratch 同口径结构对比表` 与 `官方预训练参考表`，不要把官方 `.pt` 与同口径消融混比。

---

## 4. AutoDL / 项目硬性要求（必须保留）

### 4.1 网络与 tmux

- ⭐ **必须在 tmux 会话内部执行 `source /etc/network_turbo` 后再启动训练**；只在外层 ssh shell 开学术加速不够。
- HTTPS clone/fetch/pip/HF 前需要：`source /etc/network_turbo &&`。
- SSH push 使用 `ssh.github.com:443`，默认 22 端口可能不可用。
- tmux 长训必须设置：`tmux set-option -t <name> remain-on-exit on`；训练结束后也不要 kill/清理 tmux，用户需要回看训练记录。
- tmux 建议开启：`tmux set-option -g mouse on`、`tmux set-window-option -g history-limit 100000`。

### 4.2 训练前校验

- ⭐ **正式 300 epochs 长训前必须先检查模型结构并跑 smoke**。
- 必须确认：YAML 引用正确、模块位置正确、检测尺度正确、参数量/GFLOPs 符合预期、数据路径正确。
- ⭐ WIoU 实验禁止直接 `yolo train`；必须使用 Python 入口，在 `model.train(...)` 前设置并打印：`BboxLoss.iou_type = "wiou"`。
- 日志中必须能看到类似：`[DW-P2] BboxLoss.iou_type = wiou` 或 `[DWCA] BboxLoss.iou_type = wiou`。

### 4.3 统一训练口径

- 当前消融实验统一：`epochs=300`, `batch=0.85`, `nbs=64`, `imgsz=640`, `optimizer=SGD`, `seed=42`, `pretrained=true`, `cos_lr=true`, `patience=50`。
- `DWCA-P2-b32` 是固定 batch 复验：`epochs=300`, `batch=32`, `nbs=64`, `imgsz=640`, `optimizer=SGD`, `seed=42`, `pretrained=true`, `cos_lr=true`, `patience=50`；用于评估 AutoBatch→固定 batch 的影响，不覆盖主表原 `DWCA-P2` 结果。
- 输出目录统一：`project=/root/autodl-tmp/ultralytics/runs/ablation name=<实验名>`。
- 数据集：`/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/`（4940 train + 1411 val，8 类）。
- AutoDL 主仓库：`/root/autodl-tmp/ultralytics`；本地仓库：`/Users/asus/ultralytics`。

### 4.4 分支与同步

- 消融实验分支：`feat/<改进名>`；对比实验分支：`feat/compare-<模型名>`。
- 若 AutoDL 主仓库有未跟踪训练产物，优先用 git worktree 隔离分支，避免切分支污染或覆盖历史产物。
- ⭐ 每次 AutoDL 训练结束后，必须在对应实验分支提交训练产物并 push：`runs/<实验名>_train.log` + `runs/detect/runs/ablation/<实验名>/` 下非 `.pt` 文件。
- ⭐ push 后必须同步到本地 Mac：从 AutoDL 复制完整训练目录和日志，**包括 `.pt` 权重和 `weights/` 目录**，用于本地完整归档。
- 不提交权重到 git：`.pt`、`weights/` 只在 git commit/push 时排除；AutoDL → Mac 同步时不要排除。若 runs 被 `.gitignore` 忽略，可用 `git add -f` 添加非权重产物。

---

## 5. 当前分支 / 文件 / 日志位置

| 项目 | 位置 |
|---|---|
| DW-P2 分支 | `feat/dw-p2`（配置 commit `9bc7db29`；结果 commit `17836f249` 已 push） |
| DW-P2 AutoDL worktree | `/root/autodl-tmp/worktrees/ultralytics-dw-p2` |
| DW-P2 tmux | `t_train_dw_p2` |
| DW-P2 正式日志 | `/root/autodl-tmp/ultralytics/runs/DW-P2_train.log` |
| DW-P2 输出目录 | `/root/autodl-tmp/ultralytics/runs/ablation/DW-P2/` |
| DW-P2 smoke 日志 | `/root/autodl-tmp/worktrees/ultralytics-dw-p2/runs/DW-P2_smoke.log` |
| DWCA 分支 | `feat/dwca`（GitHub 已有 commit `c35cf3cbb`；新机器因 GitHub fetch 卡顿，当前用本地 `feat/dwca-p2` 底座 + scp 传入 DWCA YAML/CHANGELOG 运行） |
| DWCA 新机器 SSH | `ssh -p 20327 root@connect.bjb1.seetacloud.com` |
| DWCA 新机器 worktree | `/root/autodl-tmp/worktrees/ultralytics-dwca-local` |
| DWCA tmux | `t_train_dwca` |
| DWCA 正式日志 | `/root/autodl-tmp/ultralytics/runs/DWCA_train.log` |
| DWCA 输出目录 | `/root/autodl-tmp/ultralytics/runs/ablation/DWCA/` |
| DWCA smoke tmux/log | `t_smoke_dwca`；`/root/autodl-tmp/worktrees/ultralytics-dwca-local/runs/DWCA_smoke.log` |
| DWCA-P2-b32 分支 | `feat/dwca-p2` |
| DWCA-P2-b32 tmux | `t_train_dwca_p2_b32` |
| DWCA-P2-b32 正式日志 | `/root/autodl-tmp/ultralytics/runs/DWCA-P2-b32_train.log` |
| DWCA-P2-b32 输出目录 | `/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/` |
| baseline-b32 分支 | `main` |
| baseline-b32 AutoDL worktree | `/root/autodl-tmp/worktrees/ultralytics-baseline-b32` |
| baseline-b32 tmux | `t_train_baseline_b32` |
| baseline-b32 正式日志 | `/root/autodl-tmp/worktrees/ultralytics-baseline-b32/runs/baseline-b32_train.log` |
| baseline-b32 输出目录 | `/root/autodl-tmp/worktrees/ultralytics-baseline-b32/runs/detect/runs/ablation/baseline-b32/` |
| Excel 表格 | `/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx` |

---

## 6. 待办事项

- [x] `DW-P2` 正式训练已完成：best epoch=253，P=85.6%、R=83.5%、mAP50=88.1%、mAP50-95=64.4%；Excel 已更新；完整产物已同步本地（包括 `.pt`）；非权重产物已 push 到 GitHub `feat/dw-p2`（commit `17836f249`）。
- [x] `DWCA` 正式训练已完成：best epoch=267，P=86.8%、R=81.4%、mAP50=86.8%、mAP50-95=61.3%；Excel 已更新；完整产物已同步本地（包括 `.pt`）；非权重产物已 push 到 GitHub `feat/dwca`（commit `5a6736deb`）。
- [x] 已根据 `DW-P2` 与 `DWCA` 结果更新论文结论：DWCA-P2 收益主要来自 P2/4 高分辨率小目标分支，CA 单独贡献有限。
- [x] `DWCA-P2-b32` 固定 batch=32 复验已完成：best epoch=234，EarlyStopping at 284/300，P=86.0%、R=83.5%、mAP50=88.4%、mAP50-95=64.4%；WIoU v3、batch=32、nbs=64 均已确认；Excel 已追加；完整产物已同步本地（包括 `.pt`）；非权重产物已 push 到 `feat/dwca-p2`（commit `59517946`）。
- [x] `baseline-b32` 固定 batch=32 复验已完成：main 分支 YAML=`yolo11.yaml`，pretrained=false，CIoU/default；best epoch=243，EarlyStopping at 293/300，P=85.7%、R=80.8%、mAP50=86.0%、mAP50-95=60.2%；Excel 已追加；完整产物已同步本地（包括 `.pt`）；非权重产物已 push 到 `main`（commit `623fc138`）。
- [ ] 所有实验结束后，整理“消融表”“YAML/scratch 同口径结构对比表”“官方预训练参考表”三套论文口径。

---

## 7. DWCA / DW-P2 归档状态

- DWCA GitHub：`feat/dwca` 已 push commit `5a6736deb`，包含 `runs/DWCA_train.log` 和 `runs/detect/runs/ablation/DWCA/` 下非权重产物。
- DWCA 本地完整归档：`/Users/asus/ultralytics/runs/DWCA_train.log` 与 `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA/`，包含 `weights/best.pt`、`weights/last.pt`。
- DW-P2 本地完整归档：`/Users/asus/ultralytics/runs/DW-P2_train.log` 与 `/Users/asus/ultralytics/runs/detect/runs/ablation/DW-P2/`，包含 `weights/best.pt`、`weights/last.pt`。
- DW-P2 GitHub：`feat/dw-p2` 已 push commit `17836f249`，包含 `CHANGELOG-DW-P2.md`、`runs/DW-P2_train.log` 和 `runs/detect/runs/ablation/DW-P2/` 下非权重产物。
- Excel：第 24 行（DWCA）与第 25 行（DW-P2）已更新；第 26 行追加 `DWCA-P2-b32` 固定 batch=32 复验。
- DWCA-P2-b32 本地完整归档：`/Users/asus/ultralytics/runs/DWCA-P2-b32_train.log` 与 `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/`，包含 `weights/best.pt`、`weights/last.pt`。
- baseline-b32 本地完整归档：`/Users/asus/ultralytics/runs/baseline-b32_train.log` 与 `/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/`，包含 `weights/best.pt`、`weights/last.pt`。
- 注意：加载 DWCA / DWCA-P2 / DWCA-P2-b32 `best.pt` 时需使用含 `CoordAttention` 的 `feat/dwca-p2` 或对应 worktree 代码；DW-P2 不需要 CA。

---

**最后更新**：2026-06-12（baseline-b32 固定 batch=32 复验已完成并追加 Excel：main 分支 YAML=`yolo11.yaml`，pretrained=false，CIoU/default，best epoch=243，EarlyStopping at 293/300，P=85.7%、R=80.8%、mAP50=86.0%、mAP50-95=60.2%；完整产物已同步本地含 `.pt`，非权重产物已 push 到 `main`（commit `623fc138`）。DWCA-P2-b32 已完成并 push commit `59517946`：best epoch=234，P=86.0%、R=83.5%、mAP50=88.4%、mAP50-95=64.4%；固定 batch=32 不改变 DWCA-P2 主结论。WIoU 实验必须使用 Python 入口先设置并打印 `BboxLoss.iou_type="wiou"`，禁止直接 `yolo train`。）
