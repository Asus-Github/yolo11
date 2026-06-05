# Agent Handoff — TDW 训练中

> 给下一位 agent：本文档是当前会话的全局快照。读完即可无缝接手。
> 用户 = 刘华硕，研究方向 YOLOv11 + Triplet Attention + DyHead + Wise-IoU (TDW) 三模块消融实验，硕士论文。

---

## 1. 当前进行中：**只有 `t_train_tdw` 一个 tmux 需要关注**

**autodl 上 tmux 状态**：
- `t_train_tdw` ← **唯一在跑的，需要分析这个**
- `t_train_dw`  ← 已完成，结果已 push 到 feat/dyhead-wiou，xlsx row 8 已填，CHANGELOG-DW.md §5 已写，可忽略
- `t_train_tw`  ← 已完成，结果已 push 到 feat/triplet-wiou（commit f7aa200b），xlsx row 7 已填，CHANGELOG-TW.md §5 已写，可忽略

**TDW 训练命令**（autodl tmux `t_train_tdw`）：
```bash
cd /root/autodl-tmp/ultralytics
source /root/miniconda3/etc/profile.d/conda.sh && conda activate base
python train_variant.py -c ultralytics/cfg/models/11/yolo11-td.yaml --iou wiou -n TDW --epochs 300 --device 0 2>&1 | tee runs/TDW_train.log
```
（注：网络结构 = `yolo11-td.yaml`，TDW = TD 网络 + WIoU 损失，不需要单独的 yolo11-tdw.yaml）

**TDW 模型规模**：4.36M params，9.29 GFLOPs，AutoBatch=46。
**输出路径**：`/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/TDW/`

---

## 2. 训练结束后必做事项（只针对 TDW）

### 2.1 检查训练完成
```bash
ssh autodl "tmux capture-pane -t t_train_tdw -p | tail -30"
```
确认 `EXITCODE=0` 和 best.pt 已生成。

### 2.2 push 到 feat/tdw（autodl）
autodl 当前在 `feat/tdw` 分支，runs/ 白名单已配置（权重排除）：
```bash
ssh autodl "cd /root/autodl-tmp/ultralytics && git add runs/detect/runs/ablation/TDW runs/TDW_train.log && git commit -m 'exp(TDW): full training results (300 epochs, dair_v2x_i)' && git push origin feat/tdw"
```

### 2.3 本地 pull + scp 权重
```bash
cd /Users/asus/ultralytics
git pull origin feat/tdw
mkdir -p runs/detect/runs/ablation/TDW/weights
scp -r autodl:/root/autodl-tmp/ultralytics/runs/detect/runs/ablation/TDW/weights/ runs/detect/runs/ablation/TDW/
```

### 2.4 FPS 基准（batch=1）
```bash
ssh autodl "cd /root/autodl-tmp/ultralytics && source /root/miniconda3/etc/profile.d/conda.sh && conda activate base && python -c \"
from ultralytics import YOLO
m = YOLO('runs/detect/runs/ablation/TDW/weights/best.pt')
r = m.val(data='/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/_runtime.yaml', imgsz=640, batch=1, device=0, verbose=False)
s = r.speed; total = s['preprocess'] + s['inference'] + s['postprocess']
print(f'TDW: total={total:.2f}ms FPS={1000/total:.1f}')
\""
```

### 2.5 写入 xlsx row 9（TDW）
xlsx：`/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx`，sheet `数据表`，**row 9**（序号=8，组别=TDW）。
列映射：I=P|%, J=R|%, K=mAP50|%, L=mAP50-95|%, M=FPS, N=GFLOPs(=9.29), O=Params|M(=4.36)

```python
import openpyxl
wb = openpyxl.load_workbook('/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx')
ws = wb['数据表']
ws.cell(9, 9, P); ws.cell(9, 10, R); ws.cell(9, 11, m50); ws.cell(9, 12, m95)
ws.cell(9, 13, FPS); ws.cell(9, 14, 9.29); ws.cell(9, 15, 4.36)
wb.save('/Users/asus/ultralytics/刘华硕-飞书导入实验记录表.xlsx')
```

### 2.6 在 feat/tdw 创建 CHANGELOG-TDW.md §5（参考 CHANGELOG-DW.md 格式）
对比表只需对比目前已有的 7 个变体 + TDW，重点回答：**TDW 是否超过 +DW（mAP50=87.0, mAP50-95=61.3）**。

---

## 3. 当前已完成进度

### 3.1 已训练完成的 7 个变体（best.pt val on dair_v2x_i, 1411 imgs）

| Variant | P | R | mAP50 | mAP50-95 | FPS | GFLOPs | Params(M) | xlsx row | branch |
|---|---:|---:|---:|---:|---:|---:|---:|:-:|:-|
| baseline | — | — | 0.857 | 0.601 | — | 6.4 | 2.6 | 2 | — (用户已统计) |
| +T | 0.856 | 0.805 | 0.859 | 0.602 | 244 | 6.4 | 2.60 | 3 | feat/triplet |
| +D | 0.863 | 0.811 | 0.866 | 0.613 | 435 | 9.3 | 4.35 | 4 | feat/dyhead |
| +W | 0.864 | 0.803 | 0.860 | 0.602 | 200 | 6.4 | 2.60 | 5 | feat/wiou |
| +TD | 0.858 | 0.810 | 0.862 | 0.610 | 233 | 9.29 | 4.36 | 6 | feat/triplet-dyhead |
| +TW | 0.858 | 0.810 | 0.863 | 0.605 | 208 | 6.4 | 2.58 | 7 | feat/triplet-wiou |
| **+DW** | **0.860** | **0.819** | **0.870** | **0.613** | 109 | 9.3 | 4.35 | 8 | feat/dyhead-wiou |
| **TDW** | TBD | TBD | TBD | TBD | TBD | 9.29 | 4.36 | 9 | **feat/tdw** ← 训练中 |

baseline 用户已自行统计，不需要再跑。

### 3.2 TDW 关键观察点
- 当前最强是 +DW（mAP50 0.870, mAP50-95 0.613）
- +TD 比 +D 反而 mAP50-95 下降 0.3，提示 Triplet 在已有 DyHead 时增益不明显
- 关键问题：**TDW 能否超过 +DW？** 决定论文最终模型选择
- 若 TDW 不及 +DW，论文可能改用 +DW 作为最终模型，或重新论证 Triplet 必要性

---

## 4. 关键背景知识

### 4.1 项目结构
- 仓库根：`/Users/asus/ultralytics`（Mac 开发）↔ `/root/autodl-tmp/ultralytics`（autodl RTX 4090 训练）
- GitHub：`git@github.com:Asus-Github/yolo11.git`（public）
- 数据集：`/root/autodl-tmp/ultralytics/datasets/dair_v2x_i/`（4940 train + 1411 val, 8 类）

### 4.2 feat/tdw 分支构成
- base = feat/dyhead-wiou（含 DyHead + WIoU）
- cherry-pick = `b53004af0` (Triplet) + `69a3bde2d` (yolo11-td.yaml)
- 即 = WIoU loss + DyHead head + Triplet at P5 end + yolo11-td.yaml + 切换 `--iou wiou`

### 4.3 网络配置坑（autodl）
- HTTPS clone/fetch：`source /etc/network_turbo`
- SSH push：用 `ssh.github.com:443`（默认 22 被墙，已配在 ~/.ssh/config）
- tmux：必须 `tmux set-option -t <name> remain-on-exit on`，否则命令结束后 session 销毁

### 4.4 用户偏好
- **直接动手**：能确定的就做，不要每步问
- **简洁回复**：避免冗长总结，重点+下一步即可
- **保留训练记录完整性**：runs/ 入 git（除 weights）
- **手动处理大件**：权重不替用户决定归档策略

---

## 5. git 状态

**本地分支**：feat/tdw（4fec0d361），已 push 到 origin/feat/tdw
**autodl 分支**：feat/tdw，训练进行中，工作目录有 untracked: runs/+T_train.log, runs/+TD_train.log, runs/detect/runs/ablation/+T/, runs/detect/runs/ablation/+TD/（这些不属于本分支，训练完成后再决定是否清理）

---

**最后更新**：2026-06-05 12:21（TDW 训练已启动，epoch 1/300 进行中）
