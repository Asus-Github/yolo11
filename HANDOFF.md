# Agent Handoff — WIoU 集成 + 训练同步

> 给下一位 agent：本文档是当前会话的全局快照。读完即可无缝接手。
> 用户 = 刘华硕，研究方向 YOLOv11 + Triplet Attention + DyHead + Wise-IoU (TDW) 三模块消融实验，用于硕士论文。

---

## 1. 当前进行中的任务

**目标**：跑 +W（仅替换 IoU 损失为 Wise-IoU v3）消融实验，结果同步到本地 xlsx。

**实时状态**（截至 2026-06-04 11:46）：
- autodl 上 tmux 会话 `w_train` 内训练进行中
- 已到 epoch 5/300，首次 val: mAP50=0.309（正常前期值）
- 用户**已说不需要后台监控**，等用户通知训练结束再动作
- ~17s/epoch，预计 ~85min 完成全部 300 epoch

**训练命令**（autodl tmux `w_train`）：
```bash
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
cd /root/autodl-tmp/ultralytics
python train_variant.py -c yolo11n.yaml --iou wiou -n +W
```

**输出路径**：`/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+W/`
- `results.csv` — 每 epoch 指标
- `weights/best.pt`, `weights/last.pt`
- `args.yaml`, 各种曲线 png

---

## 2. 训练结束后必做事项（按顺序）

### 2.1 autodl 端整理 runs（排除大权重文件）
当前 `.gitignore` 已配置：`!runs/**` 白名单，但 `runs/**/*.pt` 和 `runs/**/weights/` 被排除。
所以正常 `git add runs/` 即可，weights 目录不会进 git。

```bash
ssh autodl
cd /root/autodl-tmp/ultralytics
git add runs/
git commit -m "exp(+W): WIoU ablation results (300 epochs, dair_v2x_i)"
# push 用 ssh.github.com:443（普通 22 端口被墙）
git push origin feat/wiou
```

### 2.2 本地拉取
```bash
cd /Users/asus/ultralytics
git pull origin feat/wiou
```

### 2.3 用户手动处理权重（用户明确要求）
**不要替用户决定权重归档策略**。用户原话：
> 不要采用 B+c 了，训练完成后同步到本地我手动处理吧

只需用 scp 把权重单独拉到本地（不入 git）：
```bash
scp -r autodl:/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/+W/weights /Users/asus/ultralytics/runs/detect/runs/ablation/+W/
```

### 2.4 解析指标 + 更新 xlsx
xlsx：`/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx`（在 .gitignore 中，仅本地）

**目标行**：`数据表` sheet，**row 5**（序号=4，组别=+W）

**列映射**（已确认 r1 表头）：
- I (9) Precision|%
- J (10) Recall|%
- K (11) mAP@0.5|%（注意冒号是中文「：」）
- L (12) mAP@0.5:0.95|%
- M (13) FPS
- N (14) GFLOPs — 已预填 6.4，无需改
- O (15) Params|M — 已预填 2.6，无需改

**数据来源**：`runs/detect/runs/ablation/+W/results.csv` 最后一行
- 列名：`metrics/precision(B)`, `metrics/recall(B)`, `metrics/mAP50(B)`, `metrics/mAP50-95(B)`
- xlsx 用百分比，所以 `value * 100` 保留 1-3 位小数

**FPS 单独跑**（results.csv 没有 FPS）：
```bash
ssh autodl "cd /root/autodl-tmp/ultralytics && source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && python -c \"
from ultralytics import YOLO
m = YOLO('runs/detect/runs/ablation/+W/weights/best.pt')
r = m.val(data='ultralytics/cfg/datasets/dair_v2x_i.yaml', imgsz=640, batch=1, device=0)
# r.speed: {'preprocess', 'inference', 'postprocess', 'loss'} ms
total_ms = r.speed['preprocess'] + r.speed['inference'] + r.speed['postprocess']
print(f'FPS={1000/total_ms:.2f}')
\""
```

**写入 xlsx 模板代码**：
```python
import openpyxl, csv
xlsx_path = '/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx'
csv_path = '/Users/asus/ultralytics/runs/detect/runs/ablation/+W/results.csv'
with open(csv_path) as f:
    rows = list(csv.DictReader(f))
last = rows[-1]
P  = float(last['         metrics/precision(B)'].strip()) * 100  # key 含空格，strip
R  = float(last['            metrics/recall(B)'].strip()) * 100
m50= float(last['             metrics/mAP50(B)'].strip()) * 100
m95= float(last['          metrics/mAP50-95(B)'].strip()) * 100
FPS = ...  # 上一步 benchmark 得到
wb = openpyxl.load_workbook(xlsx_path)
ws = wb['数据表']
ws.cell(5, 9, round(P, 2))
ws.cell(5, 10, round(R, 2))
ws.cell(5, 11, round(m50, 2))
ws.cell(5, 12, round(m95, 2))
ws.cell(5, 13, round(FPS, 1))
wb.save(xlsx_path)
```
注意：results.csv 的列名前有空格（pandas/csv reader 默认会保留），先 print 看真实 key。

### 2.5 更新 CHANGELOG-WIOU.md
在「Section 6 — Smoke Test 结果」后追加「Section 7 — +W 完整训练结果」，记录：
- 起止时间、epoch 数、是否 early stop
- 最终 P/R/mAP50/mAP50-95
- 与 baseline-v2 对比（baseline-v2: epoch 266 早停, mAP50=0.857, mAP50-95=0.601）
- 是否观察到训练曲线异常

---

## 3. 关键背景知识（必读）

### 3.1 项目结构
- 仓库根：`/Users/asus/ultralytics`（Mac，开发）↔ `/root/autodl-tmp/ultralytics`（autodl RTX 4090，训练）
- 远程 git：`git@github.com:Asus-Github/yolo11.git`（已设为 public）
- 当前分支：`feat/wiou`
- 数据集：`/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/`（4940 train + 1411 val）

### 3.2 WIoU 集成（已完成，无需再改）
**核心文件改动**：
1. `ultralytics/utils/metrics.py` — `bbox_iou` 加 `WIoU=True` 分支，返回 `(iou, r_wiou)`
2. `ultralytics/utils/loss.py` — `BboxLoss` 加 `iou_type` 类属性切换；`iou_mean` 用 `register_buffer`（自动跟随 .to(device)）
3. `train_variant.py` — `--iou wiou` 参数通过 `BboxLoss.iou_type = args.iou` 切换

**WIoU v3 公式**：
- `r_wiou = exp(rho²/c²)` — c² 必须 detach（防止梯度作弊），clamp(max=10) 防 fp16 溢出
- `r_focus = β / (δ * α^(β-δ))`，α=1.9, δ=3.0（论文 Table 6）
- `β = L_iou / L_iou_mean`（每个 anchor 的相对难度）
- `loss = r_focus * r_wiou * (1-iou) * weight`

**Smoke test 已通过 5/5（autodl 4090，AMP 安全）**

### 3.3 网络配置坑（autodl）
- HTTPS clone/fetch：开 `source /etc/network_turbo`（学术加速只代理 HTTP/HTTPS）
- SSH push：`/etc/network_turbo` 不代理 SSH，必须用 `ssh.github.com:443` 端口绕过墙
- autodl 已配 `safe.directory` 解决 dubious ownership

### 3.4 .gitignore 规则
- `runs/` 不在 ignore；用 `!runs/**` 白名单 + `runs/**/*.pt` + `runs/**/weights/` 排除大文件
- `*.xlsx` 在 ignore（用户实验记录表只在本地）
- `docs/about/*.pdf|.doc(x)` 在 ignore（用户隐私文档）

### 3.5 用户偏好（已观察到）
- **直接动手**：不要每步问，能确定的就做
- **保留训练记录完整性**：runs/ 入 git
- **手动处理大件**：权重不替用户决定
- **教学型日志**：CHANGELOG-WIOU.md 是面向复现的，新改动要追加 section
- **简洁回复**：避免冗长总结，重点+下一步即可

### 3.6 后续待做实验（按顺序）
当前只完成 +W，剩余 7 组（按 xlsx 顺序）：
- baseline (row 2) — 已有 baseline-v2 (mAP50=0.857)，可直接填入
- +T (row 3) — 加 Triplet Attention
- +D (row 4) — 加 DyHead
- +TD (row 6) — Triplet+DyHead
- +TW (row 7) — Triplet+WIoU
- +DW (row 8) — DyHead+WIoU
- TDW (row 9) — 完整模型

T 和 D 模块**尚未集成代码**，开始下一步前需要先实现 yolo11-t.yaml / yolo11-d.yaml 和对应 backbone/head 修改。

---

## 4. 当前 git 状态
```
分支: feat/wiou
最近 commits:
  d3995f7 docs(changelog): add data-flow diagram and smoke test results
  bead106 exp: archive existing pre-WIoU baseline runs from autodl
  c97029e build(gitignore): allow runs/ artifacts (csv/yaml/jpg/png/log), keep weights out
  8509a6d docs: expand CHANGELOG-WIOU into a teaching-oriented reproduction log
  789ac20 feat(train_variant): wire --iou wiou to BboxLoss.iou_type
  b085cd8 feat(loss): BboxLoss switch iou_type, WIoU v3 with iou_mean buffer
  df8fffc feat(metrics): add WIoU branch returning (iou, r_wiou)
```

Mac 和 autodl 已同步，工作树干净（除非训练已写入新 runs/）。

---

## 5. 立即可执行的第一条命令（接手后）

如果用户说「训练好了」，第一步：
```bash
ssh autodl "tmux capture-pane -t w_train -p | tail -30"
```
确认 results.csv 已生成且 `EXITCODE=0`，再走 §2 流程。

如果用户说继续做 +T/+D 模块集成，去读：
- `/Users/asus/ultralytics/CHANGELOG-WIOU.md`（数据流图 + 改动模板）
- 用户给的 4 份手册（在 docs/about/，gitignored）

---

**最后更新**：2026-06-04 13:35

---

## 6. 进度更新（2026-06-04 13:35）

### +W 训练已完成（本分支专属）
- 早停 epoch 234 / 300（patience=50）
- best.pt val: P=86.4 / R=80.3 / mAP50=86.0 / mAP50-95=60.2 / FPS=200
- 已 push 到 GitHub feat/wiou，本地 pull + scp 权重完成
- xlsx row 5 已写入指标
- **重要教训**：tmux 默认 `new -d 'cmd'` 在 cmd 结束后销毁 session。下次必须用 `tmux set-option remain-on-exit on` 或 `cmd; bash`

### 分支结构（2026-06-04 已建立）
- `feat/wiou`（本分支）— WIoU 代码 + +W 训练结果
- `feat/triplet` — Triplet 代码 + +T 训练结果（独立分支，本分支不含 Triplet 代码）
- 后续 `feat/dyhead`、`feat/triplet-wiou`、`feat/triplet-dyhead`、`feat/dyhead-wiou`、`feat/tdw`

### +T 训练状态（在 autodl 上跑，但归属 feat/triplet 分支）
- autodl 当前仍 checkout 在 feat/wiou（运行进程不依赖 git 状态，不切换以免污染本地缓存）
- 训练完成后：scp +T 的 runs 到本地，**在本地切到 feat/triplet 后 commit**
- 不要让 +T 的 runs 进入本分支

### 关于 batch 一致性的统一约定
- 所有变体用 `batch=0.85`（AutoBatch），实际 batch 各异（baseline=64, +W=62, +T=61, ...）
- 论文 ablation table 加一列「Batch」列出实际值
- 影响 < 0.5% mAP，主结论不受影响
