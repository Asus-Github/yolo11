# AutoDL + Comate Remote-SSH 训练工作流手册（小白零基础版）

> **场景**：本地 Mac + Comate IDE → AutoDL 远程 RTX 4090 → 训练 YOLOv11n-TDW → 拉回结果。
> **配套手册**：先看 `刘华硕-三模块集成详细手册.md`（在本地完成代码改动）。
> **创建时间**：2026-05-28

---

## 〇、整体流程鸟瞰图

```
[本地 Mac + Comate]
   │  ① 在本地完成三模块代码改动（按集成手册）
   │  ② git push 到 Gitee 私有仓库（或直接 SCP 上传）
   ↓
[AutoDL 4090 实例]
   │  ③ 通过 SSH 拉代码 / 数据
   │  ④ 安装环境（实际只需 pip install -e . 即可）
   │  ⑤ 跑训练（tmux 后台 + 自动关机保护）
   │  ⑥ 训练完导出 best.pt + results.csv
   ↓
[本地 Mac]
   │  ⑦ rsync 拉回权重和实验结果
   │  ⑧ 关闭 AutoDL 实例（停止计费）
```

**关键省钱原则**：

- AutoDL **关机后还会按"硬盘"收费**（约 0.001 元/GB/h），但停止计费 GPU
- 长期不用：**保留环境但删除大数据**，或迁移到 OSS
- 4090 单卡训练 YOLOv11n-TDW 约 **4-6 小时/300epoch**，单组 ~10 元

---

## 一、AutoDL 账号准备 + 选卡

### 1.1 注册 + 实名

1. 浏览器打开 https://www.autodl.com/
2. 注册 → 实名认证（必做，否则不能租 GPU）
3. 充值 50-100 元（够你跑 8 组消融实验 + 对比实验）

### 1.2 选机器（**重要：选对镜像省 1 小时配置**）

进入"算力市场" → 选 **"按量计费"**（按小时计费，停机不收 GPU 费）

**GPU 推荐**：

- 北京/上海/重庆区任选，**RTX 4090 24GB**，约 1.58-1.88 元/h
- **避开"自如卡"**（部分共享卡，跑大模型可能掉速）

**镜像推荐**（选错就要重装环境）：

```
框架：PyTorch
版本：PyTorch 2.3.0 (或 2.1.0/2.2.0 都行)
Python：3.10 / 3.11
CUDA：12.1 (或 11.8)
```

**直接用 AutoDL 官方镜像**，不要选社区镜像。Ultralytics 在这个组合下 0 配置可跑。

**硬盘**：

- 系统盘：默认 50GB（够用，不要扩）
- 数据盘：**不需要额外买**，使用 `/root/autodl-tmp` 即可（默认 50GB，够装 DAIR-V2X-I）

### 1.3 启动后获取 SSH 信息

实例创建成功后，**控制台** → **快速使用** → **SSH 登录指令**，会看到类似：

```
ssh -p 12345 root@connect.bjb1.seetacloud.com
密码：xxxxxxxxxx
```

记下三件事：

- 端口（如 12345）
- 主机名（如 `connect.bjb1.seetacloud.com`）
- 密码（点眼睛图标查看）

---

## 二、本地 Mac 准备 SSH

### 2.1 配置 SSH config（让连接更方便）

打开 Mac 终端，编辑 SSH 配置：

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
nano ~/.ssh/config
```

追加以下内容（**把端口和主机名换成你的**）：

```
Host autodl
    HostName connect.bjb1.seetacloud.com
    User root
    Port 12345
    ServerAliveInterval 60
    ServerAliveCountMax 60
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
```

保存（`Ctrl+O` → 回车 → `Ctrl+X`）。

### 2.2 测试连接

```bash
ssh autodl
# 输入控制台的密码 → 看到 root@autodl-container-xxx:~# 即成功
```

### 2.3 配置 SSH 密钥（**强烈推荐，免每次输密码**）

```bash
# 在本地 Mac 终端执行（如果已有 ~/.ssh/id_rsa 跳过 keygen）
ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa
# 上传公钥到 AutoDL
ssh-copy-id autodl
# 之后 ssh autodl 不再需要密码
```

> **注意**：AutoDL 实例**关机重启后 IP 端口不变**，但**释放后再租新机器需重新 ssh-copy-id**。

---

## 三、Comate (VSCode) Remote-SSH 配置

> Comate 基于 VSCode 内核，**直接安装 VSCode 的 Remote-SSH 扩展即可**。

### 3.1 安装扩展

1. 打开 Comate
2. 左侧扩展商店搜索 **"Remote - SSH"**（微软官方，作者 Microsoft）
3. 点击 Install

### 3.2 连接服务器

1. `Cmd+Shift+P` → 输入 `Remote-SSH: Connect to Host` → 回车
2. 选择 `autodl`（来自你刚配置的 ~/.ssh/config）
3. 选择平台：**Linux**
4. 等待 30-60 秒（首次连接会装 VSCode Server）
5. 左下角变成 `SSH: autodl` 就成功了

### 3.3 打开远程项目

`File → Open Folder` → 输入 `/root/autodl-tmp` → OK

- 这是 AutoDL 的**数据盘目录**，重启后保留
- `/root` 也保留，但容量小（50GB）

---

## 四、首次环境部署（**全部在远程 Comate 终端执行**）

打开 Comate 内的终端：`Terminal → New Terminal`（自动连到远程）

### 4.1 启用学术加速（**关键，下载提速 10 倍**）

```bash
source /etc/network_turbo
# 一次性设置，仅本会话有效。每次新开 terminal 都要执行。
```

### 4.2 上传你的本地代码

#### 方案 A：通过 Gitee（推荐，可追溯版本）

**本地 Mac 终端**：

```bash
cd /Users/asus/ultralytics
# 如果还没初始化 git
git init && git add -A && git commit -m "init: TDW integration"
# 创建 Gitee 私有仓库 https://gitee.com/，加 remote
git remote add origin git@gitee.com:你的用户名/ultralytics-tdw.git
git push -u origin main
```

**远程 AutoDL（Comate 终端）**：

```bash
cd /root/autodl-tmp
git clone https://gitee.com/你的用户名/ultralytics-tdw.git ultralytics
cd ultralytics
```

#### 方案 B：直接 SCP 上传（不想用 git）

**本地 Mac 终端**：

```bash
# 排除大目录（runs/、datasets/）后打包上传
rsync -avz --progress \
  --exclude 'runs' --exclude 'datasets' --exclude '.git' \
  --exclude '__pycache__' --exclude '*.pyc' \
  /Users/asus/ultralytics/ \
  autodl:/root/autodl-tmp/ultralytics/
```

> **rsync 的好处**：之后改了代码，**重新执行同一行**会增量同步只传改动的文件，秒级完成。

### 4.3 安装 ultralytics（开发模式）

```bash
cd /root/autodl-tmp/ultralytics
pip install -e .
# AutoDL 镜像默认装好 PyTorch + CUDA，pip install -e . 只补依赖（约 1-2 分钟）
```

### 4.4 验证 GPU 可用

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 期望：True NVIDIA GeForce RTX 4090
```

### 4.5 验证三模块集成（烟雾测试）

```bash
python -c "from ultralytics import YOLO; m = YOLO('ultralytics/cfg/models/11/yolo11-tdw.yaml'); print('layers:', len(list(m.model.modules())))"
# 期望：layers 数字 + 无报错
```

---

## 五、数据集获取（DAIR-V2X-I）

### 5.1 推荐方案：直接在 AutoDL 上下载

DAIR-V2X 数据集由清华 AIR 发布，下载链接：

- 官方页：https://thudair.baai.ac.cn/index
- 注册后下载 **DAIR-V2X-I**（路侧子集，约 30GB）

**在 AutoDL 上下载**：

```bash
source /etc/network_turbo # 启用学术加速
cd /root/autodl-tmp
mkdir -p datasets/dair_v2x_i && cd datasets/dair_v2x_i
# 用 wget 或 axel 多线程下载（替换为你的实际链接）
wget -c "https://download.url/dair_v2x_i.zip"
unzip dair_v2x_i.zip
```

**网速预估**：学术加速下 **80-200 MB/s**，30GB 约 5-10 分钟。

### 5.2 备选方案：本地下载后 rsync 上传

如果你已经在本地下了：

```bash
# 本地 Mac
rsync -avz --progress /path/to/dair_v2x_i/ autodl:/root/autodl-tmp/datasets/dair_v2x_i/
# 30GB 走家里宽带（100Mbps）约 1 小时
```

### 5.3 准备 ultralytics 数据集 YAML

新建 `/root/autodl-tmp/ultralytics/ultralytics/cfg/datasets/dair_v2x_i.yaml`：

```yaml
# DAIR-V2X-I roadside vehicle detection
path: /root/autodl-tmp/datasets/dair_v2x_i # 数据集根目录
train: images/train
val: images/val
test: images/test # 可选

names:
  0: car
  1: truck
  2: van
  3: bus
  4: cyclist
  5: motorcyclist
  6: pedestrian
  7: tricyclist
```

> **前提**：你已经按 sequence_id 划分好 train/val/test 目录，每张图配一个 YOLO 格式的 .txt 标签。划分脚本在下一步会提供。

---

## 六、训练（**核心**）

### 6.1 用 tmux 防止 SSH 掉线导致训练中断

AutoDL 的 SSH 在你**关闭笔记本/网络断开**时会断连，**前台进程会被杀死**。**必须用 tmux**。

```bash
# 第一次安装 tmux（AutoDL 镜像自带，跳过即可）
which tmux || apt-get install -y tmux

# 创建一个会话
tmux new -s tdw

# 在 tmux 内执行训练
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics
python train_tdw.py

# 按 Ctrl+B 然后 D 退出 tmux（训练继续在后台跑）
# 关掉 Comate / Mac 都不影响

# 重新连回
tmux attach -t tdw
```

### 6.2 训练脚本（更新版，针对 4090 优化）

新建 `/root/autodl-tmp/ultralytics/train_tdw.py`：

```python
"""YOLOv11n-TDW on DAIR-V2X-I, RTX 4090 single-card."""

from ultralytics import YOLO
from ultralytics.utils.loss import BboxLoss

# 切换 IoU 类型
BboxLoss.iou_type = "wiou"  # baseline 时改 "ciou"

if __name__ == "__main__":
    model = YOLO("ultralytics/cfg/models/11/yolo11-tdw.yaml")

    model.train(
        data="ultralytics/cfg/datasets/dair_v2x_i.yaml",
        epochs=300,
        imgsz=640,
        batch=32,  # ★ 重要：8 组消融全部用 batch=32（控制变量），以最吃显存的 TDW 为基准
        device=0,
        workers=8,
        optimizer="SGD",
        lr0=0.01,
        cos_lr=True,
        weight_decay=0.0005,
        project="/root/autodl-tmp/runs/tdw",  # 保存到数据盘
        name="yolo11n-tdw-v1",
        seed=42,
        amp=True,  # 自动混合精度，4090 强烈推荐
        cache=False,  # 30GB 数据集太大不建议 cache=True
        patience=50,  # 连续 50 epoch 无提升提前停止
    )
```

### 6.3 监控训练（不用守着）

```bash
# 在另一个 tmux 窗口（Ctrl+B 然后 c 创建新窗口）查看 GPU
watch -n 5 nvidia-smi

# 看实时 loss 曲线
tail -f /root/autodl-tmp/runs/tdw/yolo11n-tdw-v1/results.csv
```

或者用 Comate 直接在 IDE 中打开 `results.csv` 看（Remote-SSH 模式下文件实时同步）。

### 6.4 训练完自动关机（**省钱必看**）

如果担心睡觉时训练完后还在白白计费 GPU：

```bash
# 进入 tmux
tmux new -s tdw_auto

# 执行训练 + 自动关机命令
cd /root/autodl-tmp/ultralytics
python train_tdw.py && /usr/bin/shutdown
```

`shutdown` 是 AutoDL 提供的脚本，**训练正常结束后自动关机**，停止 GPU 计费。

> **重要**：`shutdown` 只关 GPU 实例，**硬盘还在**，下次开机数据和代码都还在。

---

## 七、消融实验（8 组）批量跑法

### 7.1 一键启动 8 组实验的脚本

新建 `/root/autodl-tmp/ultralytics/run_ablation.sh`：

```bash
#!/bin/bash
set -e
source /etc/network_turbo
cd /root/autodl-tmp/ultralytics

declare -A configs=(
  ["baseline"]="yolo11.yaml ciou"
  ["t"]="yolo11-t.yaml ciou"
  ["d"]="yolo11-d.yaml ciou"
  ["w"]="yolo11.yaml wiou"
  ["td"]="yolo11-td.yaml ciou"
  ["tw"]="yolo11-t.yaml wiou"
  ["dw"]="yolo11-d.yaml wiou"
  ["tdw"]="yolo11-tdw.yaml wiou"
)

for name in baseline t d w td tw dw tdw; do
  read -r yaml iou <<< "${configs[$name]}"
  echo "=== Running: $name ($yaml + $iou) ==="
  python -c "
from ultralytics import YOLO
from ultralytics.utils.loss import BboxLoss
BboxLoss.iou_type = '$iou'
model = YOLO('ultralytics/cfg/models/11/$yaml')
model.train(
    data='ultralytics/cfg/datasets/dair_v2x_i.yaml',
    epochs=300, imgsz=640, batch=32, device=0, workers=8,
    optimizer='SGD', lr0=0.01, cos_lr=True, weight_decay=0.0005,
    project='/root/autodl-tmp/runs/ablation', name='$name',
    seed=42, amp=True, patience=50,
)
"
done

# 全部跑完自动关机
/usr/bin/shutdown
```

执行：

```bash
chmod +x run_ablation.sh
tmux new -s ablation
./run_ablation.sh
# Ctrl+B D 离开，回家睡觉
```

**4090 上 8 组 × 300 epoch ≈ 32-48 小时连续运行**，按 1.6 元/h 算约 60-80 元。

> **建议**：先只跑 `baseline` 和 `tdw` 两组（约 8-12 小时），看效果好再跑完整 8 组。

---

## 八、把结果拉回本地

### 8.1 同步整个 runs 目录回本地（recommended）

**本地 Mac 终端**：

```bash
mkdir -p /Users/asus/ultralytics/runs_remote
rsync -avz --progress \
  autodl:/root/autodl-tmp/runs/ \
  /Users/asus/ultralytics/runs_remote/
```

**只拉关键文件**（更快，权重 + 曲线 + csv）：

```bash
rsync -avz --progress \
  --include='*/' \
  --include='best.pt' --include='results.csv' \
  --include='results.png' --include='confusion_matrix.png' \
  --include='*.png' --include='*.jpg' \
  --exclude='*' \
  autodl:/root/autodl-tmp/runs/ \
  /Users/asus/ultralytics/runs_remote/
```

### 8.2 拉回代码改动（如果你在远程 IDE 里也改了代码）

```bash
# 本地 Mac
rsync -avz --progress \
  --exclude 'runs' --exclude 'datasets' --exclude '.git' \
  autodl:/root/autodl-tmp/ultralytics/ \
  /Users/asus/ultralytics/
```

或者在 Comate Remote 模式下：直接 git commit + push，本地 git pull。

---

## 九、关机 / 释放实例（**省钱关键**）

### 9.1 短期不用：**关机不释放**（保留数据盘 + 环境）

AutoDL 控制台 → 你的实例 → **关机**

- GPU 计费停止
- **硬盘按 0.001 元/GB/h 继续计费**（50GB 约 0.05 元/h，一天 1.2 元）
- 下次再开机数据和代码完整保留

### 9.2 长期不用（>1 周）：**释放并备份**

```bash
# 1. 把代码 push 到 Gitee（如果还没）
cd /root/autodl-tmp/ultralytics && git push

# 2. 把权重和结果传到阿里云 OSS / 百度网盘
#   AutoDL 内置 ossutil 工具，需先配置 AKSK
oss cp -r /root/autodl-tmp/runs/ oss://your-bucket/

# 3. 控制台 → 释放实例（彻底停止所有计费）
```

下次需要时：重新租机器 → 重装环境 → 拉代码 → 拉数据。

---

## 十、Comate 远程开发实用技巧

### 10.1 文件传输

- **小文件**：Comate 内**直接拖拽**到资源管理器
- **大文件**：用 `rsync`，速度快十倍

### 10.2 端口转发（远程看 TensorBoard / Visdom）

Comate Remote-SSH 自动支持端口转发：

```bash
# 在远程启动 tensorboard
tensorboard --logdir /root/autodl-tmp/runs --port 6006
```

底部 PORTS 标签 → Forward Port → 输入 6006 → 本地浏览器打开 http://localhost:6006

### 10.3 Comate AI 在远程也能用

只要你在 Remote-SSH 模式下打开远程项目，Comate 的代码补全、生成、修改功能**完全可用**，跟本地无差。

### 10.4 SSH 长连接保活

`~/.ssh/config` 里已加 `ServerAliveInterval 60`，**每 60s 发一个心跳**，避免长时间不动断连。

---

## 十一、常见问题速查

| 问题                      | 原因               | 解决                                        |
| ------------------------- | ------------------ | ------------------------------------------- |
| `ssh: connection refused` | 实例关机了         | 控制台开机后重连                            |
| `pip install` 慢          | 没启用学术加速     | `source /etc/network_turbo`                 |
| 训练中断（SSH 掉线）      | 没用 tmux          | 重连后 `tmux attach -t tdw` 看是否还在跑    |
| `CUDA out of memory`      | batch 太大         | batch 改 16 或 8                            |
| 训练完忘了关机            | 充值了             | 控制台手动关机；下次用 `&& shutdown`        |
| Remote-SSH 连接超时       | 首次安装 server 慢 | 等 1-2 分钟，或重试                         |
| 数据集找不到              | path 写错          | 用绝对路径 `/root/autodl-tmp/datasets/...`  |
| 结果在哪                  | runs 路径          | `/root/autodl-tmp/runs/tdw/yolo11n-tdw-v1/` |

---

## 十二、推荐工作流（每天）

```
08:00  本地 Mac 用 Comate 写/改代码（baseline 测试用 CPU 即可）
       ↓
08:30  rsync 上传代码到 AutoDL（增量秒同步）
       或 git push → AutoDL 端 git pull
       ↓
09:00  Comate Remote-SSH 连上 AutoDL → 启动 tmux → 启动训练
       ↓
09:05  本地关掉 Comate / 出门上班，训练继续
       ↓
17:00  下班回来 ssh autodl + tmux attach 看进度
       ↓
22:00  训练完成（自动关机），4090 计费停止
       ↓
次日   rsync 拉回结果到本地分析
```

---

## 十三、自动化脚本路线图（**等你跑通一次手动后再做**）

如果以后想要"一行命令搞定全部"，可以做：

```python
# auto_train.py（构想，不在本期实现）
# 1. paramiko 建立 SSH 到 AutoDL
# 2. 自动 git pull / rsync 代码
# 3. 自动启动 tmux + 训练
# 4. 通过 webhook（飞书/钉钉/邮件）发送进度
# 5. 训练完自动 rsync 拉权重 + shutdown
```

但**强烈建议你先手动跑通一次完整流程**（baseline + tdw 两组），再考虑自动化。直接上手自动化反而排错难。

---

## 十四、本周建议清单

1. ⬜ 注册 AutoDL + 充值 50 元
2. ⬜ 配置本地 ~/.ssh/config
3. ⬜ Comate 装 Remote-SSH 扩展
4. ⬜ **本地** 先按集成手册改完代码 + 用 CPU 跑通 COCO128 烟雾测试
5. ⬜ 代码推到 Gitee 私有仓库
6. ⬜ 租 4090 1 小时（约 1.6 元）做"上传 + 安装 + 烟雾测试"演练
7. ⬜ 演练成功后释放，开始正式跑 baseline + tdw 两组
8. ⬜ 看结果是否符合预期（mAP@0.5 提升 ≥ 1.5%）
9. ⬜ 跑完整 8 组消融

---

**下一步问我**：

- 不会写 sequence-level 数据集划分脚本？
- AutoDL 选不到 4090？
- DAIR-V2X-I 下载链接找不到？
- Remote-SSH 连不上？

把卡点贴给我，我手把手帮你过。
