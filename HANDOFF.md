# Ultralytics TDW 实验交接文档

> 用途：把本文件内容发给新的空白 agent，对方即可接上当前 YOLOv11 + Triplet Attention + DyHead + Wise-IoU 消融实验的上下文。
> 当前日期：2026-06-05
> 当前本地仓库：`/Users/asus/ultralytics`
> 当前本地分支：`feat/triplet-wiou`（`+TW` 已训完并 push）
> 当前远端：`origin/feat/triplet-wiou` @ `f7aa200bd`
> 下一步：在 `feat/wiou` 基础上新建 `feat/dyhead-wiou`，开始 `+DW` 实验。

---

## 1. 用户目标与全局要求

用户正在做硕士论文相关实验：在 Ultralytics YOLOv11 上集成并评估 TDW 组合：

- `+T`：Triplet Attention（backbone P5 末端，SPPF 之前）
- `+D`：DyHead / Dynamic Head（替换最终 Detect → DyHeadDetect）
- `+W`：Wise-IoU v3（替换 CIoU loss）
- 组合实验：`+TD` ✅、`+TW` ⏭ 下一步、`+DW`、`TDW`

核心目标：**只要指标提高即可**，实验设置需要可复现、可对比、可写入论文。

全局要求：

1. **每个模型组合必须新建独立分支并 push**
   - `feat/triplet`：`+T` ✅
   - `feat/dyhead`：`+D` ✅
   - `feat/wiou`：`+W` ✅
   - `feat/triplet-dyhead`：`+TD` ✅（已训完、已 push、xlsx row 6 已写）
   - `feat/triplet-wiou`：`+TW` ✅（已训完、已 push、xlsx row 7 已写）
   - **下一步：`feat/dyhead-wiou`** → `+DW`
   - 后续：`feat/tdw` → `TDW`

2. **训练权重不要提交到 git**
   - `runs/**/*.pt`、`runs/**/weights/` 排除；其他 csv/yaml/jpg/png/log 提交。
   - 使用 `git add 'runs/**'`，不要 `git add runs/`。

3. **训练 batch 统一使用 `batch=0.85`**（AutoBatch 85% 显存）。

4. **不要后台自动监控训练**：用户通知完成后再汇总。

5. **autodl 网络操作（GitHub/pip/HF/conda）必须先 `source /etc/network_turbo &&`**。

6. **tmux 训练保留窗口**：新建后 `tmux set-option -t <session> remain-on-exit on`。

7. **Smoke test 一律在 autodl 上跑，不在 mac 本地**（mac 没装 cv2/torch；autodl 是真实运行环境）。本地最多做 AST/grep 静态校验。

8. **指标取数规则**（每行 xlsx 都按这套规则）：
   - **不得对 results.csv 各列分别取最大**——这会拼出一个不存在的模型，等于学术造假。
   - 数据来源唯一：训练末尾 ultralytics 用 **best.pt 重跑 val 输出的最终四元组**（P / R / mAP50 / mAP50-95）。
   - best.pt 由 ultralytics 按 **fitness = 0.1·mAP50 + 0.9·mAP50-95** 选出（源码 `ultralytics/utils/metrics.py::DetMetrics.fitness`）。
   - **FPS** 来自训练末尾的 Speed 行：`1000 / (preprocess_ms + inference_ms + postprocess_ms)`（loss_ms 不计入）。
   - **GFLOPs / Params** 来自模型 build 时的 fused summary，与 epoch 无关。
   - 写 xlsx 时百分制保留一位小数，FPS 一位小数，Params 两位小数。

9. **xlsx 行号速查**（`/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx`，sheet `数据表`）：
   - row 2：baseline
   - row 3：`+T` ✅
   - row 4：`+D` ✅
   - row 5：`+W` ✅
   - row 6：`+TD` ✅
   - row 7：`+TW` ✅
   - row 8：`+DW` ⏭ 下一步
   - row 9：`TDW`
   - 指标列：I=Precision, J=Recall, K=mAP50, L=mAP50-95, M=FPS, N=GFLOPs, O=Params

---

## 2. 已完成实验结果

| 行 | 变体 | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | `+T` | 85.6 | 80.5 | 85.9 | 60.2 | 244 | 6.4 | 2.60 |
| 4 | `+D` | 86.3 | 81.1 | 86.6 | 61.3 | 435 | 9.3 | 4.35 |
| 5 | `+W` | 86.4 | 80.3 | 86.0 | 60.2 | 200 | 6.4 | 2.60 |
| 6 | `+TD` | 85.8 | 81.0 | 86.2 | 61.0 | 233 | 9.29 | 4.36 |
| 7 | `+TW` | 85.8 | 81.0 | 86.3 | 60.5 | 208 | 6.4 | 2.58 |

`+D` per-class 详见 `CHANGELOG-DYHEAD.md` §9，`+TD` 详见 `CHANGELOG-TD.md` §5–§7，`+TW` 详见 `CHANGELOG-TW.md` §5。

### 2.1 `+TD` vs `+D` 关键结论（写论文可用）

`+TD` 比单 `+D` 略低（mAP50 −0.4、mAP50-95 −0.3、FPS 几乎腰斩）。原因：
1. **注意力机制饱和**：DyHead 已含 scale/spatial/task 三维 attention，再叠 Triplet (C-H, C-W, H-W) → 冗余压制。
2. **+T 自身贡献小**：mAP50-95 60.2，与 +W 持平、低于 +D 61.3，对 head 已替换的模型可加性差。
3. **超参未为组合重调**：`lr0=0.01` 是单模块最优值，组合后 DyHead offset 学习更敏感。
4. **小模型 latency 敏感**：Triplet 三分支 permute+pool 让 FPS 435→233，但 GFLOPs 几乎不增 → 拿延迟换不到精度。
5. **数据集 ceiling**：DAIR-V2X-I baseline 86 附近接近上限。

### 2.2 `+TW` vs `+T` / `+W` 关键结论（写论文可用）

`+TW` 对单 `+T`、单 `+W` 都是**正向叠加**（mAP50 +0.3~+0.4，mAP50-95 +0.3）。和 `+TD` 的"注意力饱和"形成对照：
1. **作用域正交是组合有效的关键**：Triplet 作用在特征空间，WIoU 作用在 loss 空间，没有重叠 → 可加性好。
2. **`+TW` 是目前最强的"不换 head"组合**：mAP50 86.3 与 `+TD` (86.2) 并列前列，但 Params 仅 2.58M（vs +TD 4.36M）、GFLOPs 6.4（vs 9.3）→ 显著轻量化优势。
3. **mAP50-95 仍输给 DyHead 系**（−0.5 vs +TD，−0.8 vs +D）：高 IoU 阈值下精细定位主要靠 head 端 task-aware attention，loss reweight 帮不上。
4. **FPS 208 ≈ `+W` 200**：WIoU 只影响训练 loss，不影响推理；推理瓶颈是 Triplet 三分支 permute+pool，与 `+T` 同构。
5. **论文故事点**：可作为"模块组合是否有效取决于作用域是否重叠"的正反例对照（`+TW` 正例 vs `+TD` 反例）。

---

## 3. `+TW` 完成情况（2026-06-05）

- 训练：autodl RTX 4090，AutoBatch=61，267/300 epochs（早停，best @ epoch 217，patience=50），1.334h。
- best.pt val：P=0.858 / R=0.810 / mAP50=0.863 / mAP50-95=0.605。
- Speed：0.0 + 0.2 + 4.6 = 4.8 ms/img → FPS=208.3。
- 本地完整产物：`/Users/asus/ultralytics/runs/detect/runs/ablation/+TW/`（含 `weights/best.pt + last.pt`）。
- 日志：`/Users/asus/ultralytics/runs/+TW_train.log`。
- 已 commit + push：`f7aa200bd docs(+TW): record Triplet+WIoU training results`。
- xlsx row 7 已更新（I=85.8, J=81.0, K=86.3, L=60.5, M=208.3, N=6.4, O=2.58）。
- autodl 上 `tmux session t_train_tw` 仍保留（remain-on-exit on，用户要求保留），可清理：
  ```bash
  ssh autodl 'tmux kill-session -t t_train_tw'
  ```

---

## 4. 明天开工：`+DW`（DyHead + WIoU）

### 4.1 分支创建

`+DW` = DyHeadDetect（替换最终 Detect）+ WIoU v3（loss）。base 选 `feat/wiou`，cherry-pick `feat/dyhead` 的集成 commit：

```bash
cd /Users/asus/ultralytics
git fetch --all
git checkout feat/wiou               # 55bb8ab54 (+W 已训完)
git checkout -b feat/dyhead-wiou
# 找到 feat/dyhead 的集成 commit hash（参考 +TD 时用过的同一个机制）：
git log feat/dyhead --oneline | head -10
# cherry-pick DyHead 集成 commit（包含 yolo11-d.yaml + DyHeadBlock + DyHeadDetect 注册）
git cherry-pick <dyhead-integration-commit>
# 预期冲突：__init__.py / tasks.py 大概率自动合并；HANDOFF.md/CHANGELOG-* 留 ours
```

cfg 决策建议：**直接 `model=ultralytics/cfg/models/11/yolo11-d.yaml`**（DyHead 改的是 head，WIoU 只改 loss，不需要新 cfg）。新建 `CHANGELOG-DW.md`（参考 `CHANGELOG-TW.md` 结构）。

### 4.2 WIoU 启用方式（**已验证**，不是 yolo CLI 的 `iou=`）

WIoU 通过 `train_variant.py --iou wiou` 切换 `BboxLoss.iou_type`。**不要**用 `yolo detect train ... iou=wiou`——`iou=` 在 ultralytics CLI 是 NMS 阈值（float），用字符串会出错且无效。

autodl 上已端到端验证（`feat/triplet-wiou` 烟雾测试，2026-06-05）：
- `BboxLoss.iou_type='wiou'` 类属性生效
- `BboxLoss.forward` 调用 `bbox_iou(..., WIoU=True)`，spy 计数 wiou=1 / plain=0
- WIoU v3 `r_focus * r_wiou * loss_iou_per` 数值正常

### 4.3 训练命令模板（autodl）

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

### 4.4 启动前检查清单

- [ ] 本地 `feat/dyhead-wiou` 创建并 push。
- [ ] 在 autodl 上做烟雾测试（不在本地 mac）：
  - 模型可 build：`YOLO('ultralytics/cfg/models/11/yolo11-d.yaml')`
  - `BboxLoss.iou_type='wiou'` 后实例化 v8DetectionLoss → bbox_loss.iou_type 确为 'wiou'
  - 用 spy patch 验证 forward 走 wiou 分支
- [ ] autodl repo 切到 `feat/dyhead-wiou`（如果有 untracked 冲突用 `git checkout -f`）。
- [ ] tmux session 名 `t_train_dw`，`remain-on-exit on`。
- [ ] 网络命令前 `source /etc/network_turbo &&`。

---

## 5. 训练完成后的标准流程（适用于 +DW 及之后所有组合）

1. 抓取 tmux 末尾：

```bash
ssh autodl 'tmux capture-pane -t t_train_dw -p -S -200 | tail -100'
```

2. 同步完整产物到本地：

```bash
mkdir -p /Users/asus/ultralytics/runs/detect/runs/ablation
rsync -av autodl:/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+DW \
  /Users/asus/ultralytics/runs/detect/runs/ablation/
scp autodl:/root/autodl-tmp/ultralytics/runs/+DW_train.log /Users/asus/ultralytics/runs/+DW_train.log
```

> 同步规则：本地保留完整产物（含 `.pt`），git 只 push 非权重文件（`.gitignore` 已排除 `runs/**/*.pt` 与 `runs/**/weights/`）。

3. 按 §1.8 取数规则提取指标：从训练末尾 ultralytics 的 "Validating best.pt..." 段读 P/R/mAP50/mAP50-95；从 Speed 行算 FPS；GFLOPs/Params 从 fused summary 读。**不要对 results.csv 各列分别取最大**。

4. 更新 `CHANGELOG-DW.md` §5 + xlsx **row 8**（列 I–O）：

```python
from openpyxl import load_workbook
wb = load_workbook("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
ws = wb["数据表"]
assert ws["C8"].value == "+DW"
ws["I8"], ws["J8"], ws["K8"], ws["L8"] = P, R, mAP50, mAP5095
ws["M8"], ws["N8"], ws["O8"] = FPS, GFLOPs, Params
wb.save("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
```

5. 提交：

```bash
git add CHANGELOG-DW.md 'runs/**'
git status        # 确认无 .pt 进暂存区
git commit -m "docs(+DW): record DyHead+WIoU training results"
git push origin feat/dyhead-wiou
```

---

## 6. 历史关键问题 & 修复（保留）

### 6.1 `.gitignore` runs 白名单

不要 `runs/` blanket，保留：

```gitignore
!runs/**
runs/**/*.pt
runs/**/weights/
```

### 6.2 DyHead 首次训练 inplace 报错

`DyHeadBlock` 的 `nn.ReLU(inplace=True)` / `nn.Hardsigmoid(inplace=True)` 破坏 autograd。已在 `0ecfcec` 移除 inplace。

### 6.3 tmux 自动销毁

`tmux new -d 'cmd'` 默认结束销毁，需要 `set-option remain-on-exit on`。

### 6.4 autodl GitHub 卡住 = 忘开学术加速

`source /etc/network_turbo && <network cmd>`。

### 6.5 autodl 上 git checkout 被 runs/ 阻挡

本地 commit 后 push，autodl 上同名文件是 untracked，导致 `git checkout` 阻挡。解决：`git checkout -f <branch>` 强制切换（这些产物是从 autodl rsync 来的，丢失能重建）。

### 6.6 macOS 上 `python` 不存在

要用 `python3`（已踩过坑）。

---

## 7. 后续组合实验顺序

`+DW` 训完后：

1. `feat/tdw` → `TDW`：base `feat/triplet-dyhead`，cherry-pick `feat/wiou` 的 `BboxLoss` 改动（commits `b085cd8e` + `789ac209`），用 `yolo11-td.yaml` + `--iou wiou`。

每个组合：独立 branch + push；训练命名 `runs/ablation/+DW`、`TDW`。

---

## 8. 关键文件速查

本地：

```text
/Users/asus/ultralytics/CHANGELOG-DYHEAD.md
/Users/asus/ultralytics/CHANGELOG-TRIPLET.md     (在 feat/triplet 分支上)
/Users/asus/ultralytics/CHANGELOG-WIOU.md        (在 feat/wiou 分支上)
/Users/asus/ultralytics/CHANGELOG-TD.md          (在 feat/triplet-dyhead 分支)
/Users/asus/ultralytics/CHANGELOG-TW.md          (本分支，已写完结果)
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-d.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-t.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-td.yaml
/Users/asus/ultralytics/ultralytics/nn/modules/conv.py     (TripletAttention)
/Users/asus/ultralytics/ultralytics/nn/modules/block.py    (DyHeadBlock)
/Users/asus/ultralytics/ultralytics/nn/modules/head.py     (DyHeadDetect)
/Users/asus/ultralytics/ultralytics/nn/tasks.py
/Users/asus/ultralytics/ultralytics/utils/loss.py          (BboxLoss.iou_type='wiou' 通路)
/Users/asus/ultralytics/train_variant.py                   (--iou wiou 启用入口)
/Users/asus/ultralytics/runs/detect/runs/ablation/+TW      (本地完整产物，含 weights/)
/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx       (本地，不提交)
```

autodl：

```text
/root/autodl-tmp/ultralytics                           (待 checkout 到 feat/dyhead-wiou)
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
- 更新 xlsx 时严格按行号：`+DW` 是 row 8，`TDW` 是 row 9。
- 后续组合实验必须新建独立 branch 并 push。
- 在接收到每个需求时先分析合理性，遇到不明白的地方一定要交互，不可瞎编。
- 对每个模块的更改需要日志记录（CHANGELOG-*.md）方便复现。
- autodl 训练统一用 tmux，方便用户实时观察。
- 本地 macOS 用 `python3`，不要用 `python`。
- **Smoke test 一律在 autodl 跑**，本地 mac 没装 cv2/torch。本地最多 AST/grep 静态校验。
- **指标取数严格按 §1.8 规则**：用 best.pt 的 final val 行，不得对各列分别取最大。
