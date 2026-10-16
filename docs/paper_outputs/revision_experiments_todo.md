# 修订实验 TODO（ARS Review Round 1 — Major Revision）

> 来源：`/ars-reviewer full` 模拟同行评审（2026-06-30），编辑决定 Major Revision。
> 本文档只收录**需要 GPU 执行的实验项**（纯文字修订不在此列，见编辑决定 Revision Roadmap）。
> 完成后请回到 `build_yolo11n_dwca_p2_paper.py` 更新对应表格数据并重生成 `.md`/`.docx`。

## 公共路径
- 数据集配置：`/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/dair_v2x_i.yaml`（已含 train/val/test 三路）
- 权重根目录：`/Users/asus/ultralytics/runs/detect/runs/ablation/`
- 关键 best.pt：
  - baseline-b32：`.../ablation/baseline-b32/weights/best.pt`
  - DWCA-P2-b32：`.../ablation/DWCA-P2-b32/weights/best.pt`
  - 中间消融（+D / +DW / DWCA / DW-P2）：`.../ablation/{+D,+DW,DWCA,DW-P2}/weights/best.pt`

---

## TODO-1 ｜ 测试集评测（关闭 R3 残留）— 优先级 高

- **对应审稿项**：R1-W3（test 集划分后从未使用）；R3-B 已加 val-only 声明，此项彻底消除"val 即 test"嫌疑。
- **做法**：用已有 best.pt 在 test split 上跑推理评测，**不重训**。
- **命令**（每个权重一条）：
  ```bash
  yolo val model=/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/weights/best.pt \
    data=/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/dair_v2x_i.yaml \
    split=test imgsz=640 batch=1 device=0
  yolo val model=/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/weights/best.pt \
    data=/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/dair_v2x_i.yaml \
    split=test imgsz=640 batch=1 device=0
  ```
- **可选**：中间消融行（+D/+DW/DWCA/DW-P2）best.pt 也都在，可一并跑 test，补全 Table 8 test 列。
- **产出**：Table 6 增加 test 行（baseline-b32 / DWCA-P2-b32 的 test P/R/mAP@0.5/mAP@0.5:0.95）；§2.1 的 val-only 声明相应改为"主表同时报告 val 与 test"。
- **状态**：⬜ pending

---

## TODO-2 ｜ baseline+P2 控制实验（R4 归因收官）— 优先级 最高

- **对应审稿项**：DA-M1 容量混淆 + R2 归因；P2 始终与 DyHead+WIoU 同现，从未单独验证"只加 P2"。
- **为什么最关键**：DWCA-P2 比 baseline 多 73% 参数 / 125% FLOPs，缺这一格则"涨的是 P2 设计 vs 涨的是参数量"无法区分——这是核心论点（贡献点 3）最大缺口。
- **前置**：新建 `docs/paper_inputs/model_yamls/yolo11-p2.yaml`（baseline + P2 检测头，**不含** DyHead/WIoU/CA）。最稳妥做法：复制 `yolo11-dwca-p2.yaml`，把 `DyHeadDetect` 改回 `Detect`、移除 CoordAttention 层、保留 P2 输出层。
- **训练命令**（与正文统一口径：batch=32、epochs=300、SGD、seed=42、nbs=64、close_mosaic=10、imgsz=640）：
  ```bash
  yolo train model=docs/paper_inputs/model_yamls/yolo11-p2.yaml \
    data=/Users/asus/ultralytics-paper-yolo11n-clean/docs/paper_inputs/dair_v2x_i.yaml \
    epochs=300 batch=32 imgsz=640 optimizer=SGD seed=42 nbs=64 close_mosaic=10 \
    pretrained=False device=0 project=runs/detect/runs/ablation name=baseline+P2
  ```
  > 注意：WIoU v3 仅用于改进模型；此对照行保持 baseline 的 CIoU，以隔离"P2 单独"效果。
- **测速**：训练后用统一口径 `yolo val ... split=test` 或 `yolo predict` 测 FPS（batch=1，FPS=1000/(preprocess+inference+postprocess)）。
- **产出**：Table 8 增加 "baseline+P2" 行（P/R/mAP@0.5/mAP@0.5:0.95/FPS/GFLOPs/Params）。
- **判定**：
  - 若 mAP@0.5:0.95 ≈ 63–64 → P2 单独即拿到大部分增益，"P2 主驱动"铁证。
  - 若 ≈ 61 → P2 需与 DyHead/WIoU 协同，结论改为"P2 与 DyHead/WIoU 协同主导"，更扎实。
- **状态**：⬜ pending（需先建 YAML）

---

## TODO-3 ｜ SAHI 切片推理（R4-c，可选）— 仅推理

- **对应审稿项**：R2-W1 / DA；回答"结构改进是否优于推理技巧"。
- **做法**：SAHI 切片推理跑 baseline-b32 best.pt，无需训练。
- **命令**（Python）：
  ```python
  from sahi import AutoDetectionModel
  from sahi.predict import predict
  predict(
      model_type="ultralytics",
      model_path="/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/weights/best.pt",
      source="<val 图像目录>",
      slice_height=320, slice_width=320,
      overlap_height_ratio=0.2, overlap_width_ratio=0.2,
      confidence_threshold=0.25, device="cuda:0",
      project="runs/sahi", name="baseline-b32-sahi",
  )
  ```
  随后按 val 标注计算 mAP（需自行写评测脚本对齐 Ultralytics 口径）。
- **产出**：Table 9 增加 "YOLO11n + SAHI" 行，与 DWCA-P2 比 mAP 与 FPS。
- **状态**：⬜ optional

---

## TODO-4 ｜ 容量匹配对照（R4，较低优先）— 可选

- **对应审稿项**：R1-W4（Table 9 非容量匹配）。
- **做法二选一**：
  - (a) 加宽 YOLO11n 到 ~4.5M 参数 / ~14 GFLOPs（无 P2），看纯容量提升能否到 64.4；或
  - (b) 对 DWCA-P2 的 P2 通道裁剪到 ~8 GFLOPs / ~3M 参数，看 mAP 是否仍领先 YOLOv8n。
- **状态**：⬜ optional（若 TODO-2 已能说清归因，此项可不做）

---

## TODO-5 ｜ 检测可视化对比（R3-S4 / EIC-W4）— 优先级 高（作者点名要）

- **对应审稿项**：EIC-W4 + R3-S4；表 7 称 Pedestrian mAP@0.5:0.95 +8.5、Trafficcone +8.0，但缺定性检测框对比图。小目标检测论文的最直观证据。**作者明确要求补这张图。**
- **已就位**：best.pt 与 DAIR-V2X-I 图像均在本地；Mac 无 torch，需 AutoDL 跑推理。已预选 3 张 Pedestrian/Trafficcone 密集且小目标多的验证集图（按标签 w*h 筛选）：
  - **009408**（81 实例，48 小目标）/ **008933**（83 实例，54 小目标）/ **010027**（66 实例，41 小目标）
- **命令**（AutoDL，按上面 3 张 ID；路径按 AutoDL 实际改）：
  ```bash
  # 把 3 张选定图拷到一个独立目录，或直接 source 指向 val 目录后按 ID 取
  for ID in 009408 008933 010027; do
    yolo predict model=<...>/baseline-b32/weights/best.pt \
      source=<数据集>/images/val/${ID}.jpg imgsz=640 conf=0.25 save=True project=runs/vis name=baseline
    yolo predict model=<...>/DWCA-P2-b32/weights/best.pt \
      source=<数据集>/images/val/${ID}.jpg imgsz=640 conf=0.25 save=True project=runs/vis name=dwca-p2
  done
  ```
- **回传**：把 `runs/vis/baseline/*` 与 `runs/vis/dwca-p2/*` 两个 annotated 目录同步回 Mac（含 .jpg）。
- **拼图（Mac，无需 torch）**：
  ```bash
  python3 docs/paper_outputs/build_detection_comparison.py <baseline_annotated_dir> <dwca_annotated_dir>
  ```
  → 生成 `figures/fig_detection_comparison.png`（3 行 × 2 列，baseline | DWCA-P2）。
- **选图建议**：跑完后人工挑 2–3 组"baseline 漏检而 DWCA-P2 检出"或"定位框更准"的行；若某 ID 不理想，可从次优候选 009021/008999/009153/008916 替换（改 `build_detection_comparison.py` 中 `IDS`）。
- **产出**：新图（检测效果对比），§5.2 补一段定性分析。
- **状态**：✅ **已完成（2026-07-02）**。AutoDL 推理（baseline-b32 + DWCA-P2-b32，conf=0.5）已跑完 3 张代表场景 009153/009408/009021，annotated 图回传后由 `build_detection_comparison.py` 拼成 `figures/fig_detection_comparison.png`，并作为图 11 插入 §5.7。DWCA-P2 在 conf=0.5 下检出框数较 baseline 分别多约 8/5/4（主要为 Pedestrian/Trafficcone）。

---

## 执行顺序建议
1. **TODO-2**（baseline+P2 控制）——最关键，决定核心论点能否立住。
2. **TODO-1**（test 评测）——最省力（仅推理），彻底关 R3。
3. **TODO-5**（检测可视化）——仅推理，EIC/R3 点名，直观支撑核心论点。
4. TODO-3 / TODO-4——视前述结果与篇幅决定。

## 完成后
- 把新数据写回 `docs/paper_outputs/tables/*.csv` 与 `build_yolo11n_dwca_p2_paper.py` 的数据字典。
- 重生成 `.md` / `.docx`，并更新 `paper_generation_report.md`。
- 进入 ARS re-review（Stage 3'）核验 R1–R6 是否落实。
