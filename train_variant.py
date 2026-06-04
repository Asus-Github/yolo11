"""通用变体训练脚本 — 用于 TDW 消融实验.

支持参数：
    --cfg / -c   模型 yaml 路径（默认 yolo11n.yaml = baseline）
    --iou        IoU 损失类型: ciou (默认) / wiou
    --name / -n  实验名（runs 子目录名）
    --batch / -b 物理 batch size，0 表示用 AutoBatch 探最大
    --epochs     训练轮数（默认 300）
    --patience   早停 patience（默认 50）
    --probe      只探最大 batch 不训练（用于探 TDW 极限）
    --device     GPU 设备（默认 0）

使用示例：
    # baseline 复现（无 TDW）
    python train_variant.py -c yolo11n.yaml --iou ciou -n baseline

    # 仅 Triplet
    python train_variant.py -c yolo11-t.yaml --iou ciou -n +T

    # Triplet + WIoU
    python train_variant.py -c yolo11-t.yaml --iou wiou -n +TW

    # 完整 TDW
    python train_variant.py -c yolo11-tdw.yaml --iou wiou -n TDW

    # 探最大 batch
    python train_variant.py -c yolo11-tdw.yaml --probe

设计要点：
- 所有变体的 nbs=64（有效 batch 统一）→ 确保消融对比公平
- 物理 batch 各取自身最大值（不浪费显存）
- ultralytics 自动用梯度累积补足
"""

import argparse
import sys
from pathlib import Path

import yaml

from ultralytics import YOLO


def patch_dataset_yaml(repo_root: Path) -> Path:
    """把 dair_v2x_i.yaml 的 path 改成当前实际路径，写入 _runtime.yaml。."""
    src = repo_root / "datasets/dair_v2x_i/dair_v2x_i.yaml"
    cfg = yaml.safe_load(src.read_text())
    cfg["path"] = str(repo_root / "datasets/dair_v2x_i")
    out = repo_root / "datasets/dair_v2x_i/_runtime.yaml"
    out.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--cfg", default="yolo11n.yaml", help="模型 yaml（默认 yolo11n.yaml）")
    ap.add_argument("--iou", choices=["ciou", "wiou"], default="ciou", help="IoU 损失类型（默认 ciou）")
    ap.add_argument("-n", "--name", required=True, help="实验名 / 子目录名")
    ap.add_argument("-b", "--batch", type=int, default=0, help="物理 batch；0 表示用 AutoBatch 探最大（默认 0）")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--patience", type=int, default=50)
    ap.add_argument("--device", default="0")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--probe", action="store_true", help="只跑 1 epoch 探最大 batch，不做完整训练")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent
    data_yaml = patch_dataset_yaml(repo_root)

    # batch 决策：probe 模式或用户没指定 → 让 ultralytics AutoBatch 选 85% 显存
    if args.probe or args.batch == 0:
        batch = 0.85
    else:
        batch = args.batch

    print(
        f"[train_variant] cfg={args.cfg}  iou={args.iou}  name={args.name}  "
        f"batch={batch}  epochs={args.epochs}  probe={args.probe}"
    )

    model = YOLO(args.cfg)

    train_kwargs = dict(
        data=str(data_yaml),
        epochs=1 if args.probe else args.epochs,
        imgsz=args.imgsz,
        batch=batch,
        nbs=64,  # 关键：统一有效 batch=64，不论物理 batch 多少
        device=args.device,
        workers=8,
        optimizer="SGD",
        lr0=0.01,
        cos_lr=True,
        weight_decay=0.0005,
        project="runs/baseline" if args.probe else "runs/ablation",
        name=f"_probe_{args.name}" if args.probe else args.name,
        seed=args.seed,
        amp=True,
        cache=False,
        patience=args.patience,
        exist_ok=True,
        plots=not args.probe,
    )

    # WIoU 切换：通过环境变量 / 配置告知 BboxLoss
    # 注：实际 WIoU 实现需要修改 ultralytics/utils/loss.py（后续做 TDW 集成时一并改）
    # 这里先用 box gain 作为占位，提醒未实现
    if args.iou == "wiou":
        # TODO: 完成 WIoU loss 集成后启用
        # from ultralytics.utils.loss import set_iou_type; set_iou_type("wiou")
        print("[warn] WIoU 当前未实现，请先完成 loss 集成。fallback 到 ciou。")

    model.train(**train_kwargs)


if __name__ == "__main__":
    sys.exit(main())
