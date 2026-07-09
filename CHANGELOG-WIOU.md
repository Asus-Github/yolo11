# CHANGELOG — Wise-IoU 集成日志

> 本文件记录针对手册「刘华硕-三模块集成详细手册.md」中 **WIoU 部分**的实际落地改动。
> 用于回滚追溯。每条改动都对应一个 git commit，可用 `git log --oneline feat/wiou` 复核。

## 基本信息

- **基线分支**：`main`（落后 ultralytics/main 20 commit，commit `3000b7464`）
- **特性分支**：`feat/wiou`
- **远端仓库**：`git@github.com:Asus-Github/yolo11.git`
- **目标实验**：`+W`（基于 `yolo11.yaml` + WIoU 损失，对应实验记录表第 4 行）
- **AutoDL 部署路径**：`/root/autodl-tmp/ultralytics`（先 rsync 备份原目录再切到 git 管理）

## 与手册的偏差（已记录）

1. 手册 `bbox_iou` 加了 `scale: bool = False`——是死代码（两条 return 完全相同），**已删除**。
2. 手册 `BboxLoss.iou_type` 默认 `"wiou"`——会导致 baseline / +T / +D 等 CIoU 实验出错，**默认改为 `"ciou"`**，跑 WIoU 实验时显式置 `"wiou"`。
3. 手册 `wiou_alpha=1.9, wiou_delta=3.0`——与 WIoU v3 论文 Table 6 默认一致，保留并加注释说明出处。

## 改动文件清单

| #   | 文件                           | 操作                                                  | commit                                |
| --- | ------------------------------ | ----------------------------------------------------- | ------------------------------------- |
| 1   | `.gitignore`                   | 追加 `*.xlsx`                                         | (init commit)                         |
| 2   | `ultralytics/utils/metrics.py` | `bbox_iou` 加 `WIoU` 分支                             | feat: add WIoU branch in bbox_iou     |
| 3   | `ultralytics/utils/loss.py`    | `BboxLoss` 重写：支持 WIoU + register_buffer iou_mean | feat: BboxLoss supports WIoU v3       |
| 4   | `train_w.py`                   | 新建：+W 实验入口（yolo11.yaml + WIoU）               | feat: add +W ablation training script |

## 回滚方式

- 回滚到 main：`git checkout main && git branch -D feat/wiou`（或 `git reset --hard main`）
- 回滚单个 commit：`git revert <hash>`
- AutoDL 备份目录：`/root/autodl-tmp/ultralytics.bak.<timestamp>`

## 烟雾测试记录

(待补充：本地 CPU coco128 1-2 epoch 训练通过截图/日志摘要)
