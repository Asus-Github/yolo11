# Ultralytics TDW 实验交接文档

> 用途：把本文件内容发给新的空白 agent，对方即可接上当前 YOLOv11 + Triplet Attention + DyHead + Wise-IoU 消融实验的上下文。
> 当前日期：2026-06-04
> 当前本地仓库：`/Users/asus/ultralytics`
> 当前本地分支：`feat/triplet-dyhead`
> 当前远端：`origin/feat/triplet-dyhead`

---

## 1. 用户目标与全局要求

用户正在做硕士论文相关实验：在 Ultralytics YOLOv11 上集成并评估 TDW 组合：

- `+T`：Triplet Attention（backbone P5 末端，SPPF 之前）
- `+D`：DyHead / Dynamic Head（替换最终 Detect → DyHeadDetect）
- `+W`：Wise-IoU v3（替换 CIoU loss）
- 组合实验：`+TD`、`+TW`、`+DW`、`TDW`

核心目标：**只要指标提高即可**，实验设置需要可复现、可对比、可写入论文。

全局要求：

1. **每个模型组合必须新建独立分支并 push**
   - `feat/triplet`：`+T` ✅
   - `feat/dyhead`：`+D` ✅
   - `feat/wiou`：`+W` ✅
   - `feat/triplet-dyhead`：`+TD` ⚙️ 训练中
   - 后续：`feat/triplet-wiou`、`feat/dyhead-wiou`、`feat/tdw`

2. **训练权重不要提交到 git**
   - `runs/**/*.pt`、`runs/**/weights/` 排除；其他 csv/yaml/jpg/png/log 提交。
   - 使用 `git add 'runs/**'`，不要 `git add runs/`。

3. **训练 batch 统一使用 `batch=0.85`** （AutoBatch 85% 显存）

4. **不要后台自动监控训练**：用户通知完成后再汇总。

5. **autodl 网络操作（GitHub/pip/HF/conda）必须先 `source /etc/network_turbo &&`**。

6. **tmux 训练保留窗口**：新建后 `tmux set-option -t <session> remain-on-exit on`。

7. **xlsx 行号速查**（`/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx`，sheet `数据表`）：
   - row 2：baseline
   - row 3：`+T` ✅
   - row 4：`+D` ✅
   - row 5：`+W` ✅
   - row 6：`+TD` ⏳
   - row 7：`+TW`
   - row 8：`+DW`
   - row 9：`TDW`
   - 指标列：I=Precision, J=Recall, K=mAP50, L=mAP50-95, M=FPS, N=GFLOPs, O=Params

8. **FPS 公式（与 +T/+W/+D 一致）**：`1000 / (preprocess_ms + inference_ms + postprocess_ms)`，从 `yolo` 训练末尾打印的 `Speed:` 行读出。

---

## 2. 已完成实验结果

| 行 | 变体 | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | `+T` | 85.6 | 80.5 | 85.9 | 60.2 | 244 | 6.4 | 2.6 |
| 4 | `+D` | 86.3 | 81.1 | 86.6 | 61.3 | 435 | 9.3 | 4.35 |
| 5 | `+W` | 86.4 | 80.3 | 86.0 | 60.2 | 200 | 6.4 | 2.6 |

`+D` 训练结果细节见 `CHANGELOG-DYHEAD.md` §9，per-class mAP 已记录。

---

## 3. `+TD` 当前进度（本会话工作）

### 3.1 分支创建

```bash
git checkout feat/dyhead              # 4390b1f (DyHead 已训完)
git checkout -b feat/triplet-dyhead
git cherry-pick 361fd0dba             # Triplet 集成 commit (来自 feat/triplet)
# 自动合并：__init__.py, tasks.py 干净
# HANDOFF.md 冲突，已用旧 .bak 替换、随后被本会话重写
```

### 3.2 已添加/修改文件（branch 上）

| 文件 | 来源 |
|---|---|
| `ultralytics/nn/modules/conv.py` | cherry-pick from `feat/triplet`（`ZPool` / `AttentionGate` / `TripletAttention`） |
| `ultralytics/nn/modules/__init__.py` | 自动合并，同时导出 `TripletAttention` 与 `DyHeadBlock`/`DyHeadDetect` |
| `ultralytics/nn/tasks.py` | 自动合并，含两个 `parse_model` 分支 |
| `ultralytics/cfg/models/11/yolo11-t.yaml` | cherry-pick |
| `ultralytics/cfg/models/11/yolo11-d.yaml` | 来自 `feat/dyhead` |
| `ultralytics/cfg/models/11/yolo11-td.yaml` | **新增**：yolo11-t backbone + 最后一层 `DyHeadDetect, [nc]` |
| `CHANGELOG-TD.md` | 新增日志 |

### 3.3 `yolo11-td.yaml` 关键设计

- backbone 与 `yolo11-t.yaml` 完全相同（`TripletAttention` 在 layer 9，SPPF 之前）。
- head PAN-FPN 不变。
- 最后一层：`[[17, 20, 23], 1, DyHeadDetect, [nc]]`（索引随 `+T` 的 +1 偏移自然对齐）。

### 3.4 本地 commit

```text
69a3bde2 feat(+TD): add yolo11-td.yaml combining Triplet Attention backbone + DyHeadDetect head
b53004af feat(triplet): integrate Triplet Attention module (+T variant)   ← cherry-picked
4390b1f4 docs(+D): record DyHead training results (mAP50 86.6, mAP50-95 61.3)
0ecfcec2 fix(+D): remove inplace=True from DyHeadBlock activations
7585f343 feat(+D): add DyHead (Dynamic Head) detection head and yolo11-d.yaml
```

已 push 到 `origin/feat/triplet-dyhead`。

### 3.5 autodl 状态（训练中）

- repo：`/root/autodl-tmp/ultralytics`，分支 `feat/triplet-dyhead`（已 force-checkout，runs/+D 文件保留为已跟踪文件）。
- smoke test：`YOLO("ultralytics/cfg/models/11/yolo11-td.yaml")` 构建成功，参数量 4,395,106（n scale）。
- AutoBatch 实测 batch=46，GFLOPs ≈ 9.288，Params ≈ 4.36M。
- tmux session：`t_train_td`（`remain-on-exit on`，与之前的 `t_train_d` 并存）。
- 训练命令：

```bash
yolo detect train \
  model=ultralytics/cfg/models/11/yolo11-td.yaml \
  data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
  epochs=300 imgsz=640 batch=0.85 \
  device=0 workers=8 \
  project=runs/ablation name=+TD \
  optimizer=SGD iou=0.7 lr0=0.01
```

- 启动方式（已执行）：

```bash
ssh autodl 'cd /root/autodl-tmp/ultralytics && tmux new-session -d -s t_train_td && tmux set-option -t t_train_td remain-on-exit on && tmux send-keys -t t_train_td "source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && cd /root/autodl-tmp/ultralytics && yolo detect train model=ultralytics/cfg/models/11/yolo11-td.yaml data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml epochs=300 imgsz=640 batch=0.85 device=0 workers=8 project=runs/ablation name=+TD optimizer=SGD iou=0.7 lr0=0.01 2>&1 | tee runs/+TD_train.log; echo EXITCODE=\$?" C-m'
```

- 日志：`/root/autodl-tmp/ultralytics/runs/+TD_train.log`
- 产物：`/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+TD/`
- 当前最新状态：`Epoch 1/300` 已启动，batch 46，AutoBatch 通过，AMP ✅。
- 检查命令：

```bash
ssh autodl 'tmux capture-pane -t t_train_td -p | tail -40; nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader'
```

---

## 4. `+D` 训练已完成（上一会话产物）

详见 `CHANGELOG-DYHEAD.md` §9。要点：

- 300 epochs，1.847h，RTX 4090，AutoBatch=46。
- best.pt val: P=0.863 / R=0.811 / mAP50=0.866 / mAP50-95=0.613。
- xlsx row 4 已填，commit `4390b1f4` 已 push。

---

## 5. 历史关键问题 & 修复（保留）

### 5.1 `.gitignore` runs 白名单

不要 `runs/` blanket，保留：

```gitignore
!runs/**
runs/**/*.pt
runs/**/weights/
```

### 5.2 DyHead 首次训练 inplace 报错

`DyHeadBlock` 的 `nn.ReLU(inplace=True)` / `nn.Hardsigmoid(inplace=True)` 破坏 autograd。已在 `0ecfcec` 移除 inplace。

### 5.3 tmux 自动销毁

`tmux new -d 'cmd'` 默认结束销毁，需要 `set-option remain-on-exit on`。

### 5.4 autodl GitHub 卡住 = 忘开学术加速

`source /etc/network_turbo && <network cmd>`。

### 5.5 autodl 上 git checkout 被 runs/ 阻挡

本会话发生过：本地把 `runs/detect/runs/ablation/+D/*` commit 后 push，autodl 上同名文件是 untracked，导致 `git checkout feat/triplet-dyhead` 被阻拦。解决：`git checkout -f feat/triplet-dyhead` 强制切换（这些文件本就是从 autodl rsync 过来的，丢失也能重建）。

---

## 6. 训练完成后的标准流程（适用于 +TD 及之后所有组合）

1. 抓取 tmux 末尾：

```bash
ssh autodl 'tmux capture-pane -t t_train_td -p | tail -80'
```

2. 读 results.csv 末尾 + best.pt 的 val 指标（在 tmux 末尾日志里）。

3. 同步轻量产物到本地（不传权重）：

```bash
mkdir -p /Users/asus/ultralytics/runs/detect/runs/ablation
rsync -av --exclude='weights/' --exclude='*.pt' \
  autodl:/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+TD \
  /Users/asus/ultralytics/runs/detect/runs/ablation/
scp autodl:/root/autodl-tmp/ultralytics/runs/+TD_train.log /Users/asus/ultralytics/runs/+TD_train.log
```

4. 计算 FPS = `1000 / (pre + inf + post)`（从 tmux/log 中的 `Speed:` 行）。

5. 更新 `CHANGELOG-TD.md` §5 + xlsx row 6（列 I–O），用 openpyxl：

```python
from openpyxl import load_workbook
wb = load_workbook("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
ws = wb["数据表"]
assert ws["C6"].value == "+TD"
ws["I6"], ws["J6"], ws["K6"], ws["L6"] = P, R, mAP50, mAP5095
ws["M6"], ws["N6"], ws["O6"] = FPS, GFLOPs, Params
wb.save("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
```

6. 提交：

```bash
git add CHANGELOG-TD.md 'runs/**'
git commit -m "docs(+TD): record Triplet+DyHead training results"
git push origin feat/triplet-dyhead
```

---

## 7. 后续组合实验顺序

`+TD` 训完后建议：

1. `feat/triplet-wiou`：`+TW` —— yolo11-t.yaml + `iou=wiou`
2. `feat/dyhead-wiou`：`+DW` —— yolo11-d.yaml + `iou=wiou`
3. `feat/tdw`：`TDW` —— yolo11-td.yaml + `iou=wiou`

WIoU 注意：在 `feat/wiou` 上 `BboxLoss` 已支持 v3，训练命令通过 `iou=wiou` 启用。组合分支需要 cherry-pick `feat/wiou` 的 loss 改动（参考 commit `b085cd8e feat(loss): BboxLoss supports Wise-IoU v3` 与 `789ac209 feat(train_variant): wire --iou wiou to BboxLoss.iou_type`）。

每个组合：独立 branch + push；训练命名 `runs/ablation/+TW`、`+DW`、`TDW`。

---

## 8. 关键文件速查

本地：

```text
/Users/asus/ultralytics/CHANGELOG-DYHEAD.md
/Users/asus/ultralytics/CHANGELOG-TRIPLET.md     (在 feat/triplet 分支上)
/Users/asus/ultralytics/CHANGELOG-WIOU.md        (在 feat/wiou 分支上)
/Users/asus/ultralytics/CHANGELOG-TD.md          (本分支新增)
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-d.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-t.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-td.yaml
/Users/asus/ultralytics/ultralytics/nn/modules/conv.py     (TripletAttention)
/Users/asus/ultralytics/ultralytics/nn/modules/block.py    (DyHeadBlock)
/Users/asus/ultralytics/ultralytics/nn/modules/head.py     (DyHeadDetect)
/Users/asus/ultralytics/ultralytics/nn/tasks.py
/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx       (本地，不提交)
```

autodl：

```text
/root/autodl-tmp/ultralytics                    (feat/triplet-dyhead)
/root/autodl-tmp/ultralytics/runs/+TD_train.log
/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+TD
/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml
```

---

## 9. 给下一个 agent 的操作提醒

- 回复用户用中文。
- 不要问重复问题，直接按本文档继续。
- 对已有代码保持手术式修改，不要大范围重构。
- 不要提交 weights，不要把 `.pt` 加进 git。
- autodl 网络操作前必须 `source /etc/network_turbo &&`。
- 不要长期后台监控训练；用户说完成后再汇总。
- 更新 xlsx 时严格按行号：`+TD` 是 row 6。
- 后续组合实验必须新建独立 branch 并 push。
- 在接收到每个需求时先分析合理性，遇到不明白的地方一定要交互，不可瞎编。
- 对每个模块的更改需要日志记录（CHANGELOG-*.md）方便复现。
- autodl 训练统一用 tmux，方便用户实时观察。
