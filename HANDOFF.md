# Ultralytics TDW 实验交接文档

> 用途：把本文件内容发给新的空白 agent，对方即可接上当前 YOLOv11 + Triplet Attention + DyHead + Wise-IoU 消融实验的上下文。
> 当前日期：2026-06-04（晚）
> 当前本地仓库：`/Users/asus/ultralytics`
> 当前本地分支：`feat/triplet-dyhead`（`+TD` 已训完并 push）
> 当前远端：`origin/feat/triplet-dyhead` @ `6d75c2091`
> 下一步：在 `feat/wiou` 基础上新建 `feat/triplet-wiou`，开始 `+TW` 实验。

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
   - **下一步：`feat/triplet-wiou`** → `+TW`
   - 后续：`feat/dyhead-wiou` → `+DW`、`feat/tdw` → `TDW`

2. **训练权重不要提交到 git**
   - `runs/**/*.pt`、`runs/**/weights/` 排除；其他 csv/yaml/jpg/png/log 提交。
   - 使用 `git add 'runs/**'`，不要 `git add runs/`。

3. **训练 batch 统一使用 `batch=0.85`**（AutoBatch 85% 显存）。

4. **不要后台自动监控训练**：用户通知完成后再汇总。

5. **autodl 网络操作（GitHub/pip/HF/conda）必须先 `source /etc/network_turbo &&`**。

6. **tmux 训练保留窗口**：新建后 `tmux set-option -t <session> remain-on-exit on`。

7. **xlsx 行号速查**（`/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx`，sheet `数据表`）：
   - row 2：baseline
   - row 3：`+T` ✅
   - row 4：`+D` ✅
   - row 5：`+W` ✅
   - row 6：`+TD` ✅
   - row 7：`+TW` ⏭ 下一步
   - row 8：`+DW`
   - row 9：`TDW`
   - 指标列：I=Precision, J=Recall, K=mAP50, L=mAP50-95, M=FPS, N=GFLOPs, O=Params

8. **FPS 公式**：`1000 / (preprocess_ms + inference_ms + postprocess_ms)`，从 `yolo` 训练末尾打印的 `Speed:` 行读出。

---

## 2. 已完成实验结果

| 行 | 变体 | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 3 | `+T` | 85.6 | 80.5 | 85.9 | 60.2 | 244 | 6.4 | 2.60 |
| 4 | `+D` | 86.3 | 81.1 | 86.6 | 61.3 | 435 | 9.3 | 4.35 |
| 5 | `+W` | 86.4 | 80.3 | 86.0 | 60.2 | 200 | 6.4 | 2.60 |
| 6 | `+TD` | 85.8 | 81.0 | 86.2 | 61.0 | 233 | 9.29 | 4.36 |

`+D` per-class 详见 `CHANGELOG-DYHEAD.md` §9，`+TD` 详见 `CHANGELOG-TD.md` §5–§7。

### 2.1 `+TD` vs `+D` 关键结论（写论文可用）

`+TD` 比单 `+D` 略低（mAP50 −0.4、mAP50-95 −0.3、FPS 几乎腰斩）。原因：
1. **注意力机制饱和**：DyHead 已含 scale/spatial/task 三维 attention，再叠 Triplet (C-H, C-W, H-W) → 冗余压制。
2. **+T 自身贡献小**：mAP50-95 60.2，与 +W 持平、低于 +D 61.3，对 head 已替换的模型可加性差。
3. **超参未为组合重调**：`lr0=0.01` 是单模块最优值，组合后 DyHead offset 学习更敏感。
4. **小模型 latency 敏感**：Triplet 三分支 permute+pool 让 FPS 435→233，但 GFLOPs 几乎不增 → 拿延迟换不到精度。
5. **数据集 ceiling**：DAIR-V2X-I baseline 86 附近接近上限。

---

## 3. `+TD` 完成情况（2026-06-04 收尾）

- 训练：autodl RTX 4090，300 epochs / 1.865h，AutoBatch=46。
- best.pt val：P=0.858 / R=0.810 / mAP50=0.862 / mAP50-95=0.610。
- Speed：0.0 + 0.2 + 4.1 = 4.3 ms/img → FPS=232.6。
- 本地完整产物：`/Users/asus/ultralytics/runs/detect/runs/ablation/+TD/`（含 `weights/best.pt + last.pt`）。
- 日志：`/Users/asus/ultralytics/runs/+TD_train.log`。
- 已 commit + push：`6d75c2091 docs(+TD): record Triplet+DyHead training results`。
- xlsx row 6 已更新（I=85.8, J=81.0, K=86.2, L=61.0, M=232.6, N=9.29, O=4.36）。
- autodl 上 `tmux session t_train_td` 仍保留（remain-on-exit），可清理：
  ```bash
  ssh autodl 'tmux kill-session -t t_train_td'
  ```

---

## 4. 明天开工：`+TW`（Triplet + WIoU）

### 4.1 分支创建

`+TW` = Triplet Attention（backbone）+ WIoU v3（loss）。base 选 `feat/wiou`，再 cherry-pick `feat/triplet` 的集成 commit：

```bash
cd /Users/asus/ultralytics
git fetch --all
git checkout feat/wiou               # 55bb8ab54 (+W 已训完)
git checkout -b feat/triplet-wiou
# 把 Triplet 集成合进来。注意 feat/wiou 上的 commit 51b228aa3 已经被 8b14edf0d revert，
# 所以需要重新 cherry-pick feat/triplet 的原始集成 commit：
git log feat/triplet --oneline | head -10        # 找到 Triplet 的集成 commit hash
git cherry-pick <triplet-integration-commit>     # 应当是 361fd0dba（+TD 时用过的同一个）
# 预期冲突：__init__.py / tasks.py 大概率自动合并；HANDOFF.md/CHANGELOG-* 可能冲突 → 留 ours
```

随后新增 cfg：

- 复制 `ultralytics/cfg/models/11/yolo11-t.yaml` → `yolo11-tw.yaml`（其实结构与 yolo11-t 完全相同，
  WIoU 只是 loss 替换，不改网络结构；为了命名一致性可以新建一份只改注释，**也可直接复用 yolo11-t.yaml**）。
- 决策建议：**直接 `model=ultralytics/cfg/models/11/yolo11-t.yaml`**，配合 `iou=wiou`，避免冗余 cfg。
- 新建 `CHANGELOG-TW.md`（参考 `CHANGELOG-TD.md` 结构）。

### 4.2 WIoU 启用方式

`feat/wiou` 已经把 `BboxLoss` 接通 `iou_type`，启用方式是训练命令加 `iou=wiou`（注意：不是 `iou=0.7`，
那个是 NMS 阈值；WIoU 通过 `iou_type` 参数控制，源码里见 commits `b085cd8e` 和 `789ac209`）。
**操作前先确认 cherry-pick 后 `BboxLoss` 还认识 `wiou` 类型**（grep `iou_type` / `wiou` 验证）。

### 4.3 训练命令模板（autodl）

```bash
ssh autodl 'cd /root/autodl-tmp/ultralytics && \
  git fetch --all && git checkout -f feat/triplet-wiou && \
  source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && \
  tmux new-session -d -s t_train_tw && \
  tmux set-option -t t_train_tw remain-on-exit on && \
  tmux send-keys -t t_train_tw "yolo detect train \
    model=ultralytics/cfg/models/11/yolo11-t.yaml \
    data=/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml \
    epochs=300 imgsz=640 batch=0.85 \
    device=0 workers=8 \
    project=runs/ablation name=+TW \
    optimizer=SGD lr0=0.01 iou=wiou 2>&1 | tee runs/+TW_train.log; echo EXITCODE=\$?" C-m'
```

> 注意：`iou=wiou` 是字符串，不要写成 `iou=0.7`。NMS IoU 阈值用 ultralytics 默认即可（不要在命令里再传 `iou=0.7`，避免和 `iou_type` 字段冲突；实际看 `feat/wiou` 训练命令的写法）。

### 4.4 启动前检查清单

- [ ] 本地 `feat/triplet-wiou` 创建并 push。
- [ ] 本地 smoke test：`python3 -c "from ultralytics import YOLO; YOLO('ultralytics/cfg/models/11/yolo11-t.yaml')"` 能 build。
- [ ] 验证 `BboxLoss` 在该分支支持 `iou_type='wiou'`（grep）。
- [ ] autodl repo 切到 `feat/triplet-wiou`（如果有 untracked 冲突用 `git checkout -f`）。
- [ ] tmux session 名 `t_train_tw`，记得 `remain-on-exit on`。
- [ ] 网络命令前 `source /etc/network_turbo &&`。

---

## 5. 训练完成后的标准流程（适用于 +TW 及之后所有组合）

1. 抓取 tmux 末尾：

```bash
ssh autodl 'tmux capture-pane -t t_train_tw -p | tail -80'
```

2. 同步完整产物到本地：

```bash
mkdir -p /Users/asus/ultralytics/runs/detect/runs/ablation
rsync -av autodl:/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+TW \
  /Users/asus/ultralytics/runs/detect/runs/ablation/
scp autodl:/root/autodl-tmp/ultralytics/runs/+TW_train.log /Users/asus/ultralytics/runs/+TW_train.log
```

> 同步规则：本地保留完整产物（含 `.pt`），git 只 push 非权重文件（`.gitignore` 已排除 `runs/**/*.pt` 与 `runs/**/weights/`）。

3. 计算 FPS = `1000/(pre+inf+post)`（`Speed:` 行）。

4. 更新 `CHANGELOG-TW.md` §5 + xlsx **row 7**（列 I–O）：

```python
from openpyxl import load_workbook
wb = load_workbook("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
ws = wb["数据表"]
assert ws["C7"].value == "+TW"
ws["I7"], ws["J7"], ws["K7"], ws["L7"] = P, R, mAP50, mAP5095
ws["M7"], ws["N7"], ws["O7"] = FPS, GFLOPs, Params
wb.save("/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx")
```

5. 提交：

```bash
git add CHANGELOG-TW.md 'runs/**'
git status        # 确认无 .pt 进暂存区
git commit -m "docs(+TW): record Triplet+WIoU training results"
git push origin feat/triplet-wiou
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

`+TW` 训完后：

1. `feat/dyhead-wiou` → `+DW`：base `feat/wiou`，cherry-pick DyHead 集成 + cfg `yolo11-d.yaml` + `iou=wiou`。
2. `feat/tdw` → `TDW`：base `feat/triplet-dyhead`，cherry-pick `feat/wiou` 的 `BboxLoss` 改动（commits `b085cd8e` + `789ac209`），用 `yolo11-td.yaml` + `iou=wiou`。

每个组合：独立 branch + push；训练命名 `runs/ablation/+TW`、`+DW`、`TDW`。

---

## 8. 关键文件速查

本地：

```text
/Users/asus/ultralytics/CHANGELOG-DYHEAD.md
/Users/asus/ultralytics/CHANGELOG-TRIPLET.md     (在 feat/triplet 分支上)
/Users/asus/ultralytics/CHANGELOG-WIOU.md        (在 feat/wiou 分支上)
/Users/asus/ultralytics/CHANGELOG-TD.md          (本分支，已写完结果)
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-d.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-t.yaml
/Users/asus/ultralytics/ultralytics/cfg/models/11/yolo11-td.yaml
/Users/asus/ultralytics/ultralytics/nn/modules/conv.py     (TripletAttention)
/Users/asus/ultralytics/ultralytics/nn/modules/block.py    (DyHeadBlock)
/Users/asus/ultralytics/ultralytics/nn/modules/head.py     (DyHeadDetect)
/Users/asus/ultralytics/ultralytics/nn/tasks.py
/Users/asus/ultralytics/runs/detect/runs/ablation/+TD      (本地完整产物，含 weights/)
/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx       (本地，不提交)
```

autodl：

```text
/root/autodl-tmp/ultralytics                           (待 checkout 到 feat/triplet-wiou)
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
- 更新 xlsx 时严格按行号：`+TW` 是 row 7。
- 后续组合实验必须新建独立 branch 并 push。
- 在接收到每个需求时先分析合理性，遇到不明白的地方一定要交互，不可瞎编。
- 对每个模块的更改需要日志记录（CHANGELOG-*.md）方便复现。
- autodl 训练统一用 tmux，方便用户实时观察。
- 本地 macOS 用 `python3`，不要用 `python`。
