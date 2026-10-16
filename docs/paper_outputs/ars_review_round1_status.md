# ARS Review Round 1 — 编辑决定与修订状态

> 评审技能：`academic-paper-reviewer` v1.10.0，`full` 模式（7 Agent）
> 评审日期：2026-06-30
> 手稿：`docs/paper_outputs/yolo11n-dwca-p2-hljust.md`（路侧交通小目标检测DWCA-P2方法）
> 目标期刊：哈尔滨理工大学学报
> 本文件 = 编辑决定摘要 + 修订执行状态 + 回复信骨架。5 份完整评审报告见会话记录。

## 1. 编辑决定

**Major Revision（大修）**

IRON RULE #4 触发：Devil's Advocate 命中 CRITICAL（C1，幸存者偏误/归因混淆），决定不可为 Accept。

### 评审人建议汇总

| Reviewer | 角色 | Recommendation | Confidence | 加权分 |
|---|---|---|---:|---:|
| EIC | 主编 | Minor Revision | 4 | 76.7 |
| R1 | 方法学 | Major Revision | 4 | 57.85 |
| R2 | 领域 | Major Revision | 4 | 68.5 |
| R3 | 跨学科 | Minor Revision | 4 | 74.2 |
| DA | 魔鬼代言人 | 不评分；1 CRITICAL + 5 MAJOR | — | — |

### 共识
- **CONSENSUS-5**：尺度统计 → P2 必要性论证是真实贡献；CA 增益边际、在 mAP@0.5:0.95 上无贡献。
- **CONSENSUS-4**：对比仅限 vanilla YOLO，缺真正小目标方法；Table 9 非容量匹配。
- **CONSENSUS-4**：baseline 数值在表 6/8 与表 9 间不一致，§3.4 混用。

---

## 2. Required Revisions 状态（截至本次辅导结束）

| # | 审稿项 | 状态 | 本次处理 |
|---|---|---|---|
| **R1** | baseline 口径统一（表 6/8 vs 表 9，§3.4 混用） | ✅ **已关闭** | 表 9 baseline 行改用 b32（85.7/80.8/86.0/60.2/6.3/2.6）；§1.4、§3.4 增益改按 b32 重算（86.0→86.6、60.2→61.3）；§5.4 "3.5→4.2 个百分点"；`.py` `structure_groups` 改 `"YOLOv11n"`→`"baseline-b32"` |
| **R2** | 幸存者偏误 / CA "稳定正向基线" 措辞 | ✅ **已关闭**（A2） | 摘要/贡献点 3/结论加"的组合"；§4.3 删暗示句+"呈正向收敛"。Triplet 非最终方法组件，不恢复（合理范围界定）。+W 行不补（§3.6 已披露 WIoU 对 mAP@0.5:0.95 无增益） |
| **R3** | test 集划分后从未使用 | ⚠️ **部分关闭** | §2.1 加 val-only 声明（best epoch 也在 val 选定、test 留作未来评估）。**彻底关闭待 TODO-1（test 评测）** |
| **R4** | 对比公平性 / 容量混淆 | ⚠️ **部分关闭** | 2a（容量说明句）/2b（预训练披露）作者选择不做（表 9 已含 GFLOPs/Params 列，容量非隐藏；预训练属不同口径）。**彻底关闭待 TODO-2（baseline+P2 控制实验）** |
| **R5** | DAIR-V2X 3D→2D 转换说明 | ✅ **已关闭**（降为 Minor） | 核验 `dair_v2x_i.yaml`：用户使用 2D 标注转 YOLO，无 3D→2D 投影。§2.1 写明"2D 边界框标注转 YOLO 格式（不涉及 3D 到 2D 投影）"+ Barrowlist 量化（验证集 24 实例） |
| **R6** | 单 seed 无方差 | ⚠️ **作者选择不处理；轻微残留** | 论文保留单 seed 值与"补充增益"软措辞；**未添加"已验证"硬声称**。回复信防御："P2 主增益远超噪声、CA 辅助、多 seed 列未来工作"。本层级单 seed 常见，非决定性 |

### 已落地文字修订（`.md` + `.py` 同步）
- R1：4 处（§1.4、§3.4、Table 9 行、§5.4）
- R2：4 处（摘要、贡献点 3、结论、§4.3）
- R3：§2.1 val-only 声明
- R5：§2.1 2D 标注说明 + Barrowlist 量化
- 公式补全：§3.4 DyHead 复合注意力（F'=L(S(π(F)))）/ §3.5 CA 门控+输出 / §3.6 WIoU v3 三式（R_WIoU、β、r、L，据 [3][4] + Ultralytics 源码核验）；.py formula_kind/display_text 扩展

### 待 GPU 实验（见 `revision_experiments_todo.md`）
- **TODO-2**（优先）：baseline+P2 控制实验 → 关闭 R4 容量混淆（核心论点防御）
- **TODO-1**：test 评测 → 彻底关闭 R3
- **TODO-5**：检测可视化（EIC-W4/R3-S4）→ 定性证据，AutoDL 暂无卡 pending
- TODO-3 SAHI / TODO-4 容量匹配：可选

---

## 3. 回复信骨架（DA 挑战 → 回应）

| DA 指控 | 回应 |
|---|---|
| C1 幸存者偏误（删 Triplet 负向行） | Triplet 不在最终方法 DWCA-P2 中，是探索阶段失败方向；论文对最终方法自身组件（DyHead/WIoU/CA/P2）的系统消融完整保留（Table 8）。已删 §4.3 暗示句。范围界定，非选择性报告。 |
| M1 容量混淆（P2 vs 参数量） | TODO-2 实验回答：补 baseline+P2 行，证明 P2 单独即拿到大部分增益。 |
| M2 +W 行（WIoU 单独无增益） | 已修：摘要/贡献点 3/结论改为"+DW 组合构成基线"；§3.6 原本就披露 WIoU 对 mAP@0.5:0.95 无增益。 |
| M3 预训练对比被删 | 预训练与从头训练是不同口径；scratch vs scratch 才公平；本文方法若预训练同样提升。不纳入主对比。 |
| M4 CA 两路径不一致 | CA 定位辅助模块，§6.2 已讨论注意力无法创造细节。小幅变化在单 seed 下的局限由 R6 处理。 |
| M5 单数据集过度泛化 | §6.3 已坦承单数据集局限，未来工作列跨场景验证。 |

---

## 4. 复审前清单（re-review 前须完成）

- [ ] TODO-2：baseline+P2 控制实验 → Table 8 补行
- [ ] TODO-1：test 评测 → Table 6 补 test 行
- [ ] 重生成 `.docx`（`.md` 已改，`.docx` 待同步）
- [ ] 核验 R1 全文数值自洽（已核验：无 85.9/60.9 残留）
- [ ] R6：准备回复信防御（无需改正文）

## 5. 文件改动清单
- `docs/paper_outputs/yolo11n-dwca-p2-hljust.md`（R1/R2/R3/R5 文字修订）
- `docs/paper_outputs/build_yolo11n_dwca_p2_paper.py`（同步修订 + Table 9 数据源改 b32）
- `docs/paper_outputs/revision_experiments_todo.md`（新建，GPU 实验清单）
- `docs/paper_outputs/ars_review_round1_status.md`（本文件）
