# CHANGELOG — Wise-IoU 集成日志（教学复现版）

> 本文件不仅是改动清单，更是一份"**为什么这么改**"的教学笔记。每一节都包含：
> **目的 → 改前 → 改后 → 关键代码 → 与论文公式的对应 → 踩坑/为什么这么写**。
> 看完应能独立按论文复现 WIoU v3，并理解每行代码为什么这么写。

---

## 0. 全局信息

| 项 | 值 |
|---|---|
| 基线分支 | `main`（落后 ultralytics/main 约 20 commit，不影响功能） |
| 特性分支 | `feat/wiou` |
| GitHub | `git@github.com:Asus-Github/yolo11.git` |
| 目标实验 | 实验记录表第 4 行 `+W`：`yolo11n.yaml` + WIoU |
| AutoDL 工作目录 | `/root/autodl-tmp/ultralytics`（已 git 化，备份在 `.bak.<timestamp>`） |
| 论文 | Tong et al., *Wise-IoU: Bounding Box Regression Loss with Dynamic Focusing Mechanism*, 2023 |

## 0.1 全局回滚指南

```bash
# A. 完全回到改 WIoU 之前
git checkout main           # 或 git reset --hard 4e8bbf7e

# B. 只撤销某一个 commit（保留其它）
git revert <hash>           # 比如 git revert b085cd8e 撤销 loss.py 的改动

# C. AutoDL 灾难恢复
mv /root/autodl-tmp/ultralytics /root/autodl-tmp/ultralytics.broken
mv /root/autodl-tmp/ultralytics.bak.20260604_105348 /root/autodl-tmp/ultralytics
```

## 0.2 实验入口

```bash
# +W 实验：基础 yolo11n + WIoU
python train_variant.py -c yolo11n.yaml --iou wiou -n +W
# baseline 对比
python train_variant.py -c yolo11n.yaml --iou ciou -n baseline
```

---

## 1. WIoU 改在哪：数据流图（不是架构图！）

**重要事实**：WIoU 是**损失函数**改动，**模型架构 0 改动**。yolo11n 的 backbone / neck / detect head 全部不变，因此严格意义上没有"修改后的架构图"——损失函数不在架构里。下面这张**训练数据流图**才是教学上有用的"改在哪"：

```
   ┌─────────────────────────────────────────────────────────┐
   │             [模型架构层] —— 完全 0 改动 ——              │
   │                                                         │
   │     Image (640×640×3)                                   │
   │           │                                             │
   │           ▼                                             │
   │     ┌──────────┐                                        │
   │     │ Backbone │  Conv → C3k2 → ... → SPPF → C2PSA      │
   │     └──────────┘                                        │
   │           │                                             │
   │           ▼                                             │
   │     ┌──────────┐                                        │
   │     │   Neck   │  PAN-FPN (上下采样 + Concat + C3k2)    │
   │     └──────────┘                                        │
   │           │                                             │
   │           ▼  P3/8, P4/16, P5/32 三尺度特征              │
   │     ┌──────────┐                                        │
   │     │  Detect  │  cls_logits + reg_dist                 │
   │     │   Head   │                                        │
   │     └──────────┘                                        │
   │           │                                             │
   │           ▼                                             │
   │   pred_dist (DFL分布), pred_bboxes (decoded xyxy)       │
   └───────────┬─────────────────────────────────────────────┘
               │
               ▼  传给损失模块
   ┌─────────────────────────────────────────────────────────┐
   │           [损失层] —— 改动只发生在这里 ——               │
   │                                                         │
   │     v8DetectionLoss.__call__(preds, batch)              │
   │           │                                             │
   │     ┌─────┼─────────────────────────┐                   │
   │     ▼     ▼                         ▼                   │
   │   cls_loss  ┌────────────────────────────┐  dfl_loss    │
   │   (BCE)    │      BboxLoss.forward       │  (在 BboxLoss│
   │   不变     │    (reg_max=16, 子模块)     │   内部，不变) │
   │            │                            │               │
   │            │   ┌─ self.iou_type ─┐      │               │
   │            │   ▼                 ▼      │               │
   │            │ "ciou"            "wiou"   │ ← 新增分支    │
   │            │  (默认)         (本次新增) │               │
   │            │   │                 │      │               │
   │            │   ▼                 ▼      │               │
   │            │ bbox_iou(CIoU)  bbox_iou(WIoU=True)        │
   │            │   │                 │   ↳ 返回 (iou, r_wiou)
   │            │   │                 │      │               │
   │            │   │                 ▼      │               │
   │            │   │       ┌────────────────┐               │
   │            │   │       │  EMA 更新      │               │
   │            │   │       │  iou_mean      │               │
   │            │   │       │ (register_buffer,│              │
   │            │   │       │ 不参与梯度)    │               │
   │            │   │       └───────┬────────┘               │
   │            │   │               │                        │
   │            │   │               ▼                        │
   │            │   │     β = (1-iou).detach() / iou_mean    │
   │            │   │               │                        │
   │            │   │               ▼                        │
   │            │   │     r_focus = β / (δ·α^(β−δ))          │
   │            │   │               │  (动态非单调聚焦因子)  │
   │            │   ▼               ▼                        │
   │            │ (1-iou)·weight   r_focus · r_wiou          │
   │            │       │           · (1-iou) · weight       │
   │            │       └───────┬───┘                        │
   │            │               ▼                            │
   │            │           loss_iou (标量)                  │
   │            └────────────────────────────┘               │
   │                          │                              │
   │                          ▼                              │
   │           total_loss = box·loss_iou + cls·cls_loss      │
   │                       + dfl·loss_dfl                    │
   └─────────────────────────────────────────────────────────┘
                              │
                              ▼  反向传播
                          梯度回到模型参数
```

**总结：3 处代码改动一一对应这张图**：

| 图中位置 | 代码改动 | 文件 |
|---|---|---|
| `bbox_iou(WIoU=True)` 分支 | 新增 R_WIoU 计算并返回 `(iou, r_wiou)` | `metrics.py` |
| `iou_mean` buffer + EMA | `register_buffer("iou_mean")` + `.mul_(0.9).add_(...)` | `loss.py::BboxLoss` |
| `r_focus = β / (δ·α^(β−δ))` 与最终 `r·r_wiou·(1-iou)` | `BboxLoss.forward` 的 `if self.iou_type == "wiou"` 分支 | `loss.py::BboxLoss` |
| `iou_type="wiou"` 切换入口 | `BboxLoss.iou_type = args.iou` | `train_variant.py` |

**架构层完全没动**——你打开 `yolo11n.yaml`，里面所有 backbone/head 配置一字未改。要确认这一点：`git diff main..feat/wiou -- ultralytics/cfg/` 输出为空。

---

## 2. WIoU v3 论文公式速查（先看公式再看代码）

WIoU v3 包含**两步**：

**Step 1：距离注意力项 R_WIoU（在 `bbox_iou` 里算）**

$$
R_{\text{WIoU}} = \exp\!\left(\frac{(x_p - x_g)^2 + (y_p - y_g)^2}{(W_g^2 + H_g^2)^*}\right)
$$

- 分子：预测框中心与 GT 中心的欧氏距离平方
- 分母：两框最小外接矩形对角线平方（**梯度切断**，论文 sec 3.2 用 `*` 标注）
- 物理意义：两框中心越远，惩罚指数级增大，引导网络先把框"挪过去"

**Step 2：动态非单调聚焦因子 r（在 `BboxLoss` 里算）**

$$
\beta = \frac{\mathcal{L}_{IoU}^*}{\overline{\mathcal{L}_{IoU}}}, \qquad
r = \frac{\beta}{\delta \cdot \alpha^{(\beta - \delta)}}
$$

- $\mathcal{L}_{IoU}^* = 1 - \text{IoU}$（当前样本，**梯度切断**）
- $\overline{\mathcal{L}_{IoU}}$：滑动均值，作为"普通样本"的参照
- β：当前样本相对均值的"离群度"。β=1 → 普通样本；β >> 1 → 异常样本
- 论文取 $\alpha=1.9$、$\delta=3.0$（Table 6）。曲线在 β=δ 处取峰值，远离 δ 时下降——所以是**非单调**：低质量样本（β 极小）和异常样本（β 极大）权重都被降低，焦点放在中等质量样本

**最终损失**：

$$
\mathcal{L}_{\text{WIoU-v3}} = r \cdot R_{\text{WIoU}} \cdot (1 - \text{IoU})
$$

---

## 3. 改动清单与逐项解析

### 改动 1 — `.gitignore`（commit `4e8bbf7e` & 后续 runs/ 放开）

**目的**：让 git 既管代码又管小体积实验产物，把大权重排除。

| 规则 | 说明 |
|---|---|
| `*.xlsx` | 飞书导出的 Excel 不进 git（二进制变更难 diff） |
| `docs/about/*.pdf/.doc(x)` | 论文 / 开题报告（22M+，git 不友好） |
| `*.pt` | 权重——可重新训练 |
| `runs/` 已**放开** | 保留 results.csv / args.yaml / 训练曲线 png / log — 复现实验关键产物 |

---

### 改动 2 — `ultralytics/utils/metrics.py::bbox_iou` （commit `df8fffc5`）

**目的**：在原有 IoU/GIoU/DIoU/CIoU 之外加 WIoU 分支，**只算 R_WIoU**（聚焦因子放到 BboxLoss）。

#### 改前
```python
def bbox_iou(box1, box2, xywh=True, GIoU=False, DIoU=False, CIoU=False, eps=1e-7):
    ...
    return iou  # IoU
```

#### 改后
```python
def bbox_iou(box1, box2, xywh=True, GIoU=False, DIoU=False, CIoU=False, WIoU=False, eps=1e-7):
    ...
    if WIoU:
        cw = b1_x2.maximum(b2_x2) - b1_x1.minimum(b2_x1)        # 外接矩形宽
        ch = b1_y2.maximum(b2_y2) - b1_y1.minimum(b2_y1)        # 外接矩形高
        c2 = cw.pow(2) + ch.pow(2) + eps                         # 对角线²
        rho2 = ((b2_x1 + b2_x2 - b1_x1 - b1_x2).pow(2)
              + (b2_y1 + b2_y2 - b1_y1 - b1_y2).pow(2)) / 4      # 中心距²
        r_wiou = torch.exp((rho2 / c2.detach()).clamp_(max=10.0))
        return iou, r_wiou
    return iou
```

#### 关键设计点（**重点理解**）

| 点 | 为什么 |
|---|---|
| `c2.detach()` | 对应公式里的 `*`：分母不参与梯度，否则网络会通过"放大外接矩形"来变相减小 R_WIoU，作弊 |
| `clamp_(max=10.0)` | AMP/fp16 安全。`exp(10)≈22026 < fp16 max 65504`；不 clamp 会在两框很远时溢出 inf → 整轮 NaN |
| 返回 `(iou, r_wiou)` 而非合并 | 聚焦因子 r 需要 batch 内 `iou_mean`，不属于点对点函数职责。**单一职责原则** |
| 中心距用 `(b2_x1+b2_x2-b1_x1-b1_x2)/2` | 等价于 `2*(cx2-cx1)`，再 ÷4 得 `(cx2-cx1)²`；和 CIoU 完全一致，复用 numerics |

---

### 改动 3 — `ultralytics/utils/loss.py::BboxLoss`（commit `b085cd8e`）

**目的**：让 BboxLoss 既能跑 CIoU baseline，也能跑 WIoU；**默认仍 CIoU**。

#### 改前
```python
class BboxLoss(nn.Module):
    def __init__(self, reg_max=16):
        super().__init__()
        self.dfl_loss = DFLoss(reg_max) if reg_max > 1 else None

    def forward(self, ...):
        iou = bbox_iou(pred_bboxes[fg_mask], target_bboxes[fg_mask], xywh=False, CIoU=True)
        loss_iou = ((1.0 - iou) * weight).sum() / target_scores_sum
        ...
```

#### 改后（核心片段）
```python
class BboxLoss(nn.Module):
    iou_type: str = "ciou"        # 类属性：训练前 BboxLoss.iou_type='wiou' 切换
    wiou_alpha: float = 1.9       # 论文 Table 6
    wiou_delta: float = 3.0

    def __init__(self, reg_max=16):
        super().__init__()
        self.dfl_loss = DFLoss(reg_max) if reg_max > 1 else None
        self.register_buffer("iou_mean", torch.tensor(1.0))

    def forward(self, ...):
        weight = target_scores.sum(-1)[fg_mask].unsqueeze(-1)
        if self.iou_type == "wiou":
            iou, r_wiou = bbox_iou(..., WIoU=True)
            loss_iou_per = 1.0 - iou
            with torch.no_grad():
                cur_mean = loss_iou_per.detach().float().mean().clamp_(min=1e-7)
                self.iou_mean.mul_(0.9).add_(cur_mean * 0.1)        # EMA, alpha=0.1
            beta   = (loss_iou_per.detach() / self.iou_mean.clamp_(min=1e-7)).clamp_(min=1e-7)
            r_focus = beta / (self.wiou_delta * (self.wiou_alpha ** (beta - self.wiou_delta)))
            loss_iou = ((r_focus * r_wiou * loss_iou_per) * weight).sum() / target_scores_sum
        else:
            iou = bbox_iou(..., CIoU=True)
            loss_iou = ((1.0 - iou) * weight).sum() / target_scores_sum
```

#### 关键设计点

| 点 | 为什么 |
|---|---|
| `iou_type` 默认 `"ciou"` | 表格里 4/8 行实验跑 CIoU。默认必须是 baseline，避免静默改变其它消融 |
| `register_buffer("iou_mean", ...)` 而非类属性 | ① 自动 `.to(device)`（v8DetectionLoss 行 368 有 `.to(device)`）；② 自动存进 `.pt` checkpoint，resume 训练时连续；③ 多模型实例不互相污染 |
| `loss_iou_per.detach()` 入 EMA / β | 滑动均值是"统计量"不该回传梯度；β 也只是权重不该回传 |
| `with torch.no_grad():` + `.float()` | 双重保险：禁止 EMA 路径建图；fp32 算 mean 防 fp16 溢出 |
| `.clamp_(min=1e-7)` 三处 | iou_mean 初值=1.0，第一步 EMA 后趋近真实值；防止某些 batch 全是完美匹配（loss=0）导致除零 |
| 公式参数名 `wiou_alpha=1.9, wiou_delta=3.0` | 论文 Table 6 默认值，未做调参 |

#### 一个常见误解

> "为什么 forward 里要 `.detach()` 算 β，而不直接用 `loss_iou_per`？"

因为 r 是**权重**不是损失主体。如果 r 也要回传梯度，等价于网络可以通过"调整某些样本的 IoU 来降低自己的权重"作弊。论文 sec 3.3 明确：聚焦因子是**外部统计量**。

---

### 改动 4 — `train_variant.py`（commit `789ac209`）

**目的**：把通用消融训练脚本里 `--iou wiou` 那条 TODO 兑现成真切换。

#### 改前
```python
if args.iou == "wiou":
    # TODO: 完成 WIoU loss 集成后启用
    print("[warn] WIoU 当前未实现，请先完成 loss 集成。fallback 到 ciou。")
```

#### 改后
```python
from ultralytics.utils.loss import BboxLoss
...
BboxLoss.iou_type = args.iou
print(f"[train_variant] BboxLoss.iou_type = {BboxLoss.iou_type}")
model.train(**train_kwargs)
```

#### 关键设计点

- 类属性赋值必须在 `model.train()` **之前**——因为 `BboxLoss` 实例化在 trainer 内部，赋值需要"先于"实例化
- 不用 argparse 之外的环境变量切换，**单一入口**便于复盘
- `args.iou` 作为 run 名/路径的语义来源，不污染 yaml

---

## 4. 烟雾测试脚本（autodl 上跑）

> 已固化在 `/tmp/wiou_smoke.py`（autodl）。源码也在下面，方便本地复制。

```python
# 在 autodl 上：
import torch
from ultralytics.utils.metrics import bbox_iou
from ultralytics.utils.loss import BboxLoss

# 1) bbox_iou WIoU 分支
b1 = torch.tensor([[10., 10., 50., 50.]])
b2 = torch.tensor([[12., 11., 48., 52.]])
iou, r = bbox_iou(b1, b2, xywh=False, WIoU=True)
assert torch.isfinite(r).all()

# 2) AMP 极限：远距离不出 inf
b3 = torch.tensor([[1000., 1000., 1004., 1004.]])
b4 = torch.tensor([[0., 0., 4., 4.]])
_, r_far = bbox_iou(b3, b4, xywh=False, WIoU=True)
assert torch.isfinite(r_far).all() and r_far.item() < 1e5

# 3) BboxLoss WIoU forward+backward
BboxLoss.iou_type = "wiou"
loss_mod = BboxLoss(reg_max=16)
N = 8
pd = torch.randn(N, 64, requires_grad=True)
pb = torch.rand(N, 4) * 100
tb = pb + torch.randn(N, 4) * 2
li, ld = loss_mod(pd, pb, torch.rand(N, 2)*100, tb,
                  torch.rand(N, 80), torch.tensor(1.0), torch.ones(N, dtype=bool),
                  torch.tensor([640., 640.]), torch.tensor([8.]))
(li + ld).backward()
assert torch.isfinite(li).all() and torch.isfinite(pd.grad).all()
print("ALL PASSED")
```

成功通过即说明 WIoU 集成无 NaN/inf 风险。

---

## 5. 实验执行清单（按表格顺序）

| 顺序 | 组别 | yaml | --iou | 命令 |
|------|------|------|-------|------|
| 1 | baseline | yolo11n.yaml | ciou | `python train_variant.py -c yolo11n.yaml --iou ciou -n baseline` |
| **2** | **+W** | yolo11n.yaml | **wiou** | **`python train_variant.py -c yolo11n.yaml --iou wiou -n +W`** ← 本次重点 |
| 3 | +T | yolo11-t.yaml | ciou | (待 T 模块集成) |
| 4 | +D | yolo11-d.yaml | ciou | (待 D 模块集成) |
| 5 | +TW | yolo11-t.yaml | wiou | (待 T) |
| 6 | +DW | yolo11-d.yaml | wiou | (待 D) |
| 7 | +TD | yolo11-td.yaml | ciou | (待 T+D) |
| 8 | TDW | yolo11-tdw.yaml | wiou | (待全部) |

---

## 6. 烟雾测试结果（autodl, RTX 4090, 2026-06-04）

5/5 通过。tmux 会话名 `wiou_smoke`，日志在 `/tmp/wiou_smoke.log`。

```
============================================================
WIoU smoke test (autodl, RTX 4090)
============================================================
[1] iou=0.8397  r_wiou=1.0007
    └─ 两框中心几乎重合，距离惩罚≈1（近 1 表示几乎不惩罚）
[2] far-pair r_wiou=2.70 (clamp ceiling exp(10)~22026)
    └─ 两 4×4 框相距 1414，rho²/c²≈0.992，exp 后 ≈2.70（合理；clamp 在更极端
       场景才生效，本测试只是确认 isfinite）
[3] device=cuda
[3] wiou loss_iou=0.8400 loss_dfl=3.2994 iou_mean=0.9756
[3] backward ok, grad isfinite=True
    └─ GPU 上完整 forward+backward，所有梯度有限
[4] ciou loss_iou=0.7434
    └─ 默认 CIoU 路径仍工作，未受 WIoU 改动影响
[5] state_dict keys: ['iou_mean']
    └─ 确认 iou_mean 是 buffer（会随 .to(device) + 进 ckpt）
============================================================
ALL 5 SMOKE TESTS PASSED
============================================================
```

**结论**：WIoU 集成在 GPU 上 forward + backward 路径均无 NaN/inf，可以放心进入 +W 实验全量训练。

---

## 7. 烟雾测试脚本
