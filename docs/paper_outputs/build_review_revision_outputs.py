from __future__ import annotations

import re
import shutil
import textwrap
from datetime import date
from pathlib import Path

from docx import Document

import build_yolo11n_dwca_p2_paper as base


OUTPUT_DIR = base.OUTPUT_DIR
SOURCE_MD = base.MD_PATH
SOURCE_DOCX = base.DOCX_PATH
REVISED_MD = OUTPUT_DIR / "yolo11n-dwca-p2-hljust-reviewed.md"
REVISED_DOCX = OUTPUT_DIR / "yolo11n-dwca-p2-hljust-reviewed.docx"
REVIEW_REPORT = OUTPUT_DIR / "review_report.md"
REVISION_RESPONSE = OUTPUT_DIR / "revision_response.md"
HUMAN_CHECKS = OUTPUT_DIR / "remaining_human_checks.md"


def replace_once(text: str, old: str, new: str) -> str:
    if old not in text:
        raise ValueError(f"Expected text not found: {old[:80]}")
    return text.replace(old, new, 1)


def normalize_report_markdown(text: str) -> str:
    """Remove incidental Python-block indentation from generated report Markdown."""
    text = textwrap.dedent(text)
    text = re.sub(r"(?m)^ {8}", "", text)
    return text.lstrip()


def style_reference_notes() -> str:
    return textwrap.dedent(
        """\
        ## 参考论文风格观察

        本轮仅将两篇《哈尔滨理工大学学报》已发表论文作为结构和文风参照，不迁移其数据或结论。可归纳出的写作特点包括：

        - 摘要按“问题—方法—数据/实验—结果—意义”展开，结果指标直接给出，不在摘要中扩展过多背景。
        - 引言采用“应用背景—现有问题—已有方法—本文方案—贡献”的顺序，结尾集中列出本文工作。
        - 方法部分按模块拆分，每个模块先说明问题，再说明结构或公式作用，最后连接到实验设置。
        - 实验部分常见顺序为数据集、参数设置、评价指标、对比实验、消融实验，结果分析围绕表图展开。
        - 结论避免重复长篇背景，集中概括模型结构、关键指标和后续工作。
        """
    )


def build_review_report() -> str:
    today = date.today().isoformat()
    return textwrap.dedent(
        f"""\
        # YOLO11n-DWCA-P2 模拟同行评审报告

        - 生成日期：{today}
        - 审稿对象：`{SOURCE_DOCX}`
        - 目标期刊：哈尔滨理工大学学报
        - 评审模式：ARS `ars-reviewer` 逻辑，多视角模拟同行评审
        - 重要边界：未上传外部模型；仅依据论文、项目文件、Excel 实验表和两篇期刊参考论文的写作风格进行评审。

        {style_reference_notes()}

        ## 本轮合理假设

        - 输入 DOCX 与同名 Markdown 为当前待审初稿，二者内容以项目生成器输出为准。
        - Excel 中 `baseline-b32` 与 `DWCA-P2-b32` 行为主结果数据源，但论文正文只显示 baseline 与 DWCA-P2。
        - 两篇《哈尔滨理工大学学报》已发表论文仅用于观察结构、文风、图表说明和结论收束方式，不作为当前实验结论证据。
        - 未在本地材料中发现独立测试集 AP、多随机种子结果或逐框预测统计，因此只将其列为人工核验或后续工作。

        ## 总体评价

        稿件围绕 DAIR-V2X-I 路侧图像中的小目标检测问题，提出 YOLO11n-DWCA-P2 方法，并用目标尺度统计、主结果对比、类别级 AP、消融实验、结构对比和速度复杂度表支撑结论。选题契合路侧感知和轻量化检测方向，实验数据较完整，且已较好控制了命名、Triplet/TDW、官方预训练参考实验、AI 使用说明等前期风险。

        主要不足集中在论文表述和结论边界：一是评价口径尚未在实验设置和结果章节中充分前置，容易让读者误解为测试集结论；二是方法贡献叙述中 DyHead、WIoU、CoordAttention 和 P2 分支的边界仍需更清楚，尤其 CoordAttention 的贡献不宜被摘要式表达放大；三是速度结论应从“实时检测速度”改为“参考环境下具有实时性参考”，避免部署外推；四是训练曲线与类别级结果的证据属性需要更明确，不能等同于统计显著性或独立测试集验证。

        ## 编辑决定建议

        **Major Revision（大修后复审）**。

        稿件没有发现需要推翻主要实验结果的致命问题，但仍需要通过结构性文字修订来提升期刊投稿的严谨度。若作者能明确验证集/测试集边界、收紧部署和模块贡献表述、补强“实验设置—结果—讨论”的因果链条，并将人工核验事项列明，则可进入小修或录用前格式审查阶段。

        ## 评审视角配置

        | 视角 | 模拟身份 | 重点 |
        |---|---|---|
        | 编辑/领域综合 | 计算机视觉与智能交通方向栏目编辑 | 选题契合度、贡献清晰度、期刊风格 |
        | 方法与实验评审 | 目标检测实验与复现评审 | 数据口径、评价集、消融、速度测量、可复现性 |
        | 写作结构与表达评审 | 中文科技论文写作评审 | 摘要、章节层次、图表说明、结论收束 |
        | 反方压力测试 | 逻辑链与过度外推检查 | 最强反驳、未证实主张、替代解释 |

        ## major issues

        ### MI-1 评价集口径和主结果边界需要前置说明

        **位置**：4.1、4.3、5.1、5.2、5.6、7 结论。  
        **问题**：正文说明了 train/val/test 划分，但主结果、类别级 AP 和训练曲线主要来自验证集或 Excel 主结果表，测试集未给出 AP。若不前置说明“本文性能比较以统一验证口径为主”，读者可能误以为表 6 是独立测试集结果。  
        **建议**：在实验设置中增加“评价口径说明”，明确验证集用于主结果、消融、类别级分析和测速参考；测试集仅作为划分信息列出，尚未报告独立测试集 AP。结论中避免暗示测试集泛化。

        ### MI-2 方法贡献边界仍需更清楚

        **位置**：摘要、3.2、3.3、3.5、5.3、6.1、6.2。  
        **问题**：论文已指出 P2 是主增益，CoordAttention 是辅助模块，但摘要和总体结构段落仍容易让读者理解为四个模块均贡献相近。消融表显示 DW-P2 与 DWCA-P2 的 mAP@0.5:0.95 相同，因此 CoordAttention 不宜被写成定位质量提升来源。  
        **建议**：把“P2 主导定位增益、DyHead/WIoU 提供正向基线、CoordAttention 仅辅助位置表达”的逻辑写入方法总述和消融分析。

        ### MI-3 速度与部署表述偏乐观

        **位置**：5.1、5.5、6.3。  
        **问题**：100.5 FPS 来自 RTX 4090、batch=1、Ultralytics 环境，不等同于低功耗路侧端部署。当前“达到实时检测速度”表述容易被认为已完成部署验证。  
        **建议**：改为“在 RTX 4090 参考环境下具有实时性参考”，并明确低功耗端仍需 TensorRT/量化/剪枝后重测。

        ### MI-4 类别级 AP 与主结果来源不完全一致，需要标注证据属性

        **位置**：5.2。  
        **问题**：表 7 已说明类别级 AP 与表 6 有约 0.1 个百分点差异，但尚未明确它是“辅助解释”而非主结论依据。  
        **建议**：在表 7 前后强调类别级分析只用于解释小目标类别受益情况，主结论以 Excel 固定复验表为准。

        ### MI-5 缺少对随机性和重复实验限制的交代

        **位置**：5.6、6.3、7。  
        **问题**：训练曲线显示收敛阶段差距，但单 seed、单数据集结果不能证明统计显著性。正文虽未声称显著性，但“不是单个 epoch 的偶然波动”表述仍略强。  
        **建议**：改为“在本次训练记录中保持相对稳定差距”，并在局限性中补充未进行多 seed 重复实验和统计显著性检验。

        ### MI-6 期刊风格上，实验设置的复现要素与结果分析之间的衔接可更紧

        **位置**：4.1、4.3、5.1。  
        **问题**：哈理工参考论文通常在实验设置后较快进入评价指标和实验对比，并在每个表后围绕指标解释。当前稿件已具备该结构，但实验分组、评价口径、结果用途之间还可以更凝练。  
        **建议**：新增简短“实验口径说明”，在 5.1 第一段明确表 6 的作用，减少读者寻找数据来源的成本。

        ## minor issues

        - **mI-1**：英文摘要对 CoordAttention 的定位可与中文摘要保持一致，强调 auxiliary enhancement。
        - **mI-2**：部分段落存在“本文”高频开头，可适度替换为“该方法”“实验结果”“上述统计”等主语。
        - **mI-3**：表 10 中 DWCA-P2 与 DW-P2 FPS 四舍五入相同，建议在文字中避免解释过细，以免超出表格精度。
        - **mI-4**：参考文献格式仍需投稿前人工核对 GB/T 风格标点、外文作者大小写、页码和 DOI。
        - **mI-5**：图 6、图 7 曲线来源可在图前说明来自训练日志，避免被误读为独立重复实验。

        ## 分章节评论

        ### 摘要

        摘要信息完整，符合“问题—方法—统计/实验—结果—结论”的期刊风格。需要调整的是结果口径和模块贡献边界：建议把“P2 分支是定位精度提升的主要来源”保留，同时避免让 CoordAttention 看起来与 P2 同等贡献。

        ### 0 引言

        引言背景较充分，能够从车路协同、路侧小目标、YOLO 检测尺度过渡到本文方法。建议减少少量泛化描述，将问题收束到“高分辨率检测层对极小目标的必要性”。

        ### 1 相关工作

        相关工作覆盖目标检测、多尺度融合、注意力、动态检测头和损失函数。建议在每个小节末尾增加与本文设计的连接句，强化“为什么选 P2 而不是只叠加注意力”的论证。

        ### 2 数据集与小目标特征分析

        该章是稿件亮点。尺度统计为方法设计提供了直接证据。需注意：表 4 是验证集类别尺度分布，全量尺度统计和验证集统计应在文字上保持区分。

        ### 3 改进 YOLO11n 检测方法

        结构完整，但建议在 3.2 总体结构中加入“推理阶段不包含 WIoU”的说明，并进一步明确 CoordAttention 不作为主要增益来源。

        ### 4 实验设置

        需要补充评价口径说明。尤其要说明主结果、消融和类别级分析均基于统一验证口径；测试集 AP 尚未报告。

        ### 5 实验结果与分析

        结果较充分。主要修订方向是收紧速度外推、类别级 AP 解释边界和训练曲线表述。表 6、表 8、表 10 的数据逻辑一致，是稿件的核心证据链。

        ### 6 讨论

        讨论已体现 P2 主增益和注意力边界，方向正确。建议补充“未进行多 seed 与统计显著性检验”的限制，并进一步说明后续错误分析需要保存逐框预测。

        ### 7 结论

        结论较清晰，但仍需避免把验证集结论写成泛化结论。建议增加“在统一验证口径下”的限定，并保留未来工作中的测试集/跨场景验证。

        ## 必须修改的 checklist

        - [ ] 在实验设置中新增评价口径说明，明确主结果、消融、类别级 AP 和训练曲线的验证集属性。
        - [ ] 将速度表述从“达到实时检测速度”改为“在 RTX 4090 参考环境下具有实时性参考”。
        - [ ] 修改训练曲线表述，避免暗示统计显著性。
        - [ ] 在局限性中加入未进行多 seed 重复实验、未报告独立测试集 AP 的限制。
        - [ ] 在方法与消融章节进一步明确 CoordAttention 是辅助模块，不是主要定位增益来源。
        - [ ] 保持正文不出现 b32、Triplet/TDW、官方预训练参考实验、AI 使用说明和未确认元数据。
        - [ ] 新版 DOCX 另存，不覆盖原始论文。

        ## 需要人工核验的风险点

        - 是否需要在正式投稿前补充独立测试集 AP。
        - 是否需要进行 3 个或更多随机种子的重复训练，并报告均值/标准差。
        - 类别级 AP 表 7 是否来自最终最佳权重或最后 epoch，需要作者核对训练日志来源。
        - 参考文献是否完全符合《哈尔滨理工大学学报》最终 GB/T 格式。
        - Word 中所有页面的分页、表格换页和公式显示需要在完整 Word/LibreOffice 环境人工检查。
        - 基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI 和作者简介仍待导师确认，不应由本轮自动补写。
        """
    )


def revise_markdown(md: str) -> str:
    first_line = md.splitlines()[0].strip()
    if first_line != f"# {base.CN_TITLE}":
        md = replace_once(md, first_line, f"# {base.CN_TITLE}")

    for old_en_title in [
        "## YOLO11n-DWCA-P2 for Roadside Small Object Detection",
        "## YOLO11n-DWCA-P2 for Roadside Traffic Small Object Detection",
    ]:
        if old_en_title in md and old_en_title != f"## {base.EN_TITLE}":
            md = replace_once(md, old_en_title, f"## {base.EN_TITLE}")
            break
    md = replace_once(
        md,
        "针对路侧图像远距离交通目标尺度小、密度高和背景干扰强导致轻量化 YOLO 漏检的问题，提出 YOLO11n-DWCA-P2 小目标检测方法。该方法以 YOLO11n 为基准，采用 Dynamic Head（DyHead）动态检测头和 Wise Intersection over Union v3（Wise-IoU v3）回归损失，增加 P2/4 高分辨率检测分支，将检测特征由 P3/P4/P5 扩展为 P2/P3/P4/P5，并用 Coordinate Attention（CoordAttention）辅助增强浅中层位置表达。训练与测速均采用统一设置，以降低训练口径和硬件差异对比较结果的影响。DAIR-V2X-I 统计显示，640 输入尺度下短边小于 32 像素和面积小于 32^2 像素的目标分别占 87.55% 和 79.65%。实验结果表明，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 86.0%、83.5%、88.4% 和 64.4%，较 baseline 的后三项分别提高 2.7、2.4 和 4.2 个百分点，RTX 4090 上达到 100.5 FPS。消融结果表明，P2 分支是定位精度提升的主要来源，DyHead 和 Wise-IoU v3 构成稳定正向基线，CoordAttention 起辅助增强作用。该方法提升了路侧小目标检出能力和定位质量，可为车路协同视觉感知中的轻量化检测模型设计提供参考。",
        "针对路侧图像远距离交通目标尺度小、密度高和背景干扰强导致轻量化 YOLO 漏检的问题，提出 YOLO11n-DWCA-P2 小目标检测方法。该方法以 YOLO11n 为基准，采用 Dynamic Head（DyHead）动态检测头和 Wise Intersection over Union v3（Wise-IoU v3）回归损失，增加 P2/4 高分辨率检测分支，将检测特征由 P3/P4/P5 扩展为 P2/P3/P4/P5，并用 Coordinate Attention（CoordAttention）增强浅中层位置敏感表达。训练、验证和测速均采用统一口径，以降低训练参数和硬件差异对比较结果的影响。DAIR-V2X-I 统计显示，640 输入尺度下短边小于 32 像素和面积小于 32^2 像素的目标分别占 87.55% 和 79.65%。在统一验证口径下，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 86.0%、83.5%、88.4% 和 64.4%，较 baseline 分别提高 0.3、2.7、2.4 和 4.2 个百分点，RTX 4090 参考环境下为 100.5 FPS。消融结果表明，P2 分支是 Recall 和 mAP@0.5:0.95 提升的主要来源，DyHead 和 Wise-IoU v3 构成稳定正向基线，CoordAttention 主要体现在 Precision 和 mAP@0.5 的补充增益上。该方法提升了路侧小目标检出能力和定位质量，可为车路协同视觉感知中的轻量化检测模型设计提供参考。",
    )
    md = replace_once(
        md,
        "Roadside images contain distant traffic objects with small scales, high density and strong background interference, which can cause missed detections in lightweight YOLO models. YOLO11n-DWCA-P2 was proposed for roadside small object detection. Based on YOLO11n, the method adopted a Dynamic Head detection head and Wise Intersection over Union version 3 regression loss, added a P2/4 high-resolution detection branch to extend the detection features from P3/P4/P5 to P2/P3/P4/P5, and used Coordinate Attention for auxiliary position-aware enhancement. Statistics on DAIR-V2X-I showed that objects with a short side smaller than 32 pixels and objects with an area smaller than 32^2 pixels accounted for 87.55% and 79.65%, respectively, at the 640 input scale. Experiments showed that DWCA-P2 achieved 86.0% Precision, 83.5% Recall, 88.4% mAP@0.5 and 64.4% mAP@0.5:0.95. Compared with baseline, the latter three metrics increased by 2.7, 2.4 and 4.2 percentage points, respectively, and the model reached 100.5 FPS on an RTX 4090. Ablation results indicate that the P2 branch is the main source of localization improvement. The method improves detection and localization for small roadside objects.",
        "Roadside images contain distant traffic objects with small scales, high density and strong background interference, which can cause missed detections in lightweight YOLO models. YOLO11n-DWCA-P2 was proposed for roadside small object detection. Based on YOLO11n, the method adopted a Dynamic Head detection head and Wise Intersection over Union version 3 regression loss, added a P2/4 high-resolution detection branch to extend the detection features from P3/P4/P5 to P2/P3/P4/P5, and used Coordinate Attention to enhance shallow and mid-level position-sensitive representation. Statistics on DAIR-V2X-I showed that objects with a short side smaller than 32 pixels and objects with an area smaller than 32^2 pixels accounted for 87.55% and 79.65%, respectively, at the 640 input scale. Under a unified validation protocol, DWCA-P2 achieved 86.0% Precision, 83.5% Recall, 88.4% mAP@0.5 and 64.4% mAP@0.5:0.95. Compared with baseline, the four metrics increased by 0.3, 2.7, 2.4 and 4.2 percentage points, respectively, and the model reached 100.5 FPS on an RTX 4090 reference environment. Ablation results indicate that the P2 branch is the main source of recall and localization improvement, while Coordinate Attention provides complementary gains in precision-oriented metrics. The method improves detection and localization for small roadside objects.",
    )
    md = replace_once(
        md,
        "本文在 Neck 中将较高层特征逐步上采样，并与浅层 P2 特征拼接融合，得到用于 tiny object detection 的 P2 输出层。随后，检测头由原来的三尺度输入扩展为四尺度输入。P2 分支保留了更多浅层边缘、纹理和空间位置信息，能够缓解远距离行人、交通锥和骑行者在深层特征中消失或定位偏移的问题。",
        "本文在 Neck 中将较高层特征逐步上采样，并与浅层 P2 特征拼接融合，得到用于极小目标检测的 P2 输出层。随后，检测头由原来的三尺度输入扩展为四尺度输入。P2 分支保留了更多浅层边缘、纹理和空间位置信息，能够缓解远距离行人、交通锥和骑行者在深层特征中消失或定位偏移的问题。",
    )
    md = replace_once(
        md,
        "本文将 CoordAttention 嵌入到 P3 相关特征位置，目的是在浅层细节与中层语义之间增强位置编码。需要强调的是，本文实验并不支持将 CoordAttention 表述为主要增益来源。DWCA 的 mAP@0.5:0.95 为 61.3%，与 +DW 的 61.3% 持平；完整模型相较 DW-P2 在 mAP@0.5:0.95 上没有进一步增加。因此，CoordAttention 更适合作为辅助模块写入方法部分，而不是在摘要和结论中过度强调。",
        "本文将 CoordAttention 嵌入到 P3 相关特征位置，目的是在浅层细节与中层语义之间增强位置编码。需要强调的是，当前实验不支持将 CoordAttention 表述为主要增益来源。DWCA 的 mAP@0.5:0.95 为 61.3%，与 +DW 的 61.3% 持平；完整模型相较 DW-P2 在 mAP@0.5:0.95 上没有进一步增加。但从最终两组结果看，DWCA-P2 相比 DW-P2 的 Precision 由 85.6% 提升到 86.0%，mAP@0.5 由 88.1% 提升到 88.4%，说明 CoordAttention 更适合体现在误检抑制和较松 IoU 阈值下的补充增益。因此，CoordAttention 在本文中作为位置敏感辅助模块，用于配合 P2 分支和动态检测头改善特征表达，而不是最终定位增益的主导因素。",
    )
    md = replace_once(
        md,
        "本文所有实验使用同一数据集划分，并按固定 batch=32 口径解释。输入图像尺寸为 640 x 640，训练轮数为 300 epochs，优化器为 SGD，随机种子为 42，nbs 为 64，close_mosaic 设置为 10。实验评价指标包括 Precision、Recall、mAP@0.5、mAP@0.5:0.95、FPS、GFLOPs 和 Params。表 5 给出了主要训练与测速参数。",
        "本文所有实验使用同一数据集划分，并按固定 batch=32 训练口径解释。输入图像尺寸为 640 x 640，训练轮数为 300 epochs，优化器为 SGD，随机种子为 42，nbs 为 64，close_mosaic 设置为 10。实验评价指标包括 Precision、Recall、mAP@0.5、mAP@0.5:0.95、FPS、GFLOPs 和 Params。除数据集划分统计外，正文主结果、消融实验、类别级 AP 和训练曲线均以验证集统一评价结果为依据；测试集 AP 尚未在本稿中报告，后续需要独立补充。表 5 给出了主要训练与测速参数。",
    )
    md = replace_once(
        md,
        "本文实验分为三类。第一类为主结果对比，比较 YOLO11n baseline 与最终模型 DWCA-P2，作为本文结论的主要依据；两者均采用 batch=32 的固定复验结果。第二类为正增长模块消融实验，沿 baseline、+D、+DW、DWCA、DW-P2 和 DWCA-P2 路线逐步分析 DyHead、WIoU、CoordAttention 与 P2 分支的作用。第三类为同口径结构对比，比较 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml、YOLO11n baseline 和本文方法。正文实验均采用从头训练口径，避免外部权重来源差异干扰结论。",
        "本文实验分为三类。第一类为主结果对比，比较 YOLO11n baseline 与最终模型 DWCA-P2，作为本文结论的主要依据；两者均采用 batch=32 的固定复验结果，并在统一验证集上计算检测指标。第二类为正增长模块消融实验，沿 baseline、+D、+DW、DWCA、DW-P2 和 DWCA-P2 路线逐步分析 DyHead、WIoU、CoordAttention 与 P2 分支的作用。第三类为同口径结构对比，比较 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml、YOLO11n baseline 和本文方法。正文实验均采用从头训练口径，避免外部权重来源差异干扰结论。",
    )
    md = replace_once(
        md,
        "表 6 给出了本文最终模型与 YOLO11n baseline 的主结果对比。可以看出，DWCA-P2 的 Precision 为 86.0%，较 baseline 提升 0.3 个百分点；Recall 为 83.5%，提升 2.7 个百分点；mAP@0.5 为 88.4%，提升 2.4 个百分点；mAP@0.5:0.95 为 64.4%，提升 4.2 个百分点。",
        "表 6 给出了本文最终模型与 YOLO11n baseline 在统一验证口径下的主结果对比。可以看出，DWCA-P2 的 Precision 为 86.0%，较 baseline 提升 0.3 个百分点；Recall 为 83.5%，提升 2.7 个百分点；mAP@0.5 为 88.4%，提升 2.4 个百分点；mAP@0.5:0.95 为 64.4%，提升 4.2 个百分点。",
    )
    md = replace_once(
        md,
        "计算复杂度方面，DWCA-P2 的 GFLOPs 为 14.2，较 baseline 增加 7.9；参数量为 4.5M，增加 1.9M。统一 RTX 4090 测速下，FPS 从 153.0 降至 100.5，约为 baseline 的 65.7%。该代价主要来自 DyHead 和 P2 高分辨率检测分支。对于极端低功耗嵌入式设备，该计算开销可能需要进一步压缩；但对于路侧边缘服务器或具备加速芯片的路侧计算单元，该速度仍具有实时性参考价值。",
        "计算复杂度方面，DWCA-P2 的 GFLOPs 为 14.2，较 baseline 增加 7.9；参数量为 4.5M，增加 1.9M。统一 RTX 4090 测速下，FPS 从 153.0 降至 100.5，约为 baseline 的 65.7%。该代价主要来自 DyHead 和 P2 高分辨率检测分支。该速度结果仅用于同一 GPU 与同一软件环境下的模型间比较，可作为路侧边缘服务器部署的实时性参考；若面向低功耗终端，仍需在目标硬件上重新测速。",
    )
    md = replace_once(
        md,
        "为进一步分析改进模型对不同类别的影响，本文从训练日志末尾的 per-class 验证输出中提取 baseline 与 DWCA-P2 的类别级 AP，结果见表 7。需要说明的是，表 7 来源于最终验证日志的逐类别输出，整体均值与表 6 的 Excel 主结果口径存在约 0.1 个百分点的四舍五入和最佳轮次差异；论文主结论仍以表 6 为准，类别级分析用于观察不同类别的相对变化。",
        "为进一步分析改进模型对不同类别的影响，本文从训练日志末尾的 per-class 验证输出中提取 baseline 与 DWCA-P2 的类别级 AP，结果见表 7。需要说明的是，表 7 来源于最终验证日志的逐类别输出，整体均值与表 6 的 Excel 主结果口径存在约 0.1 个百分点的四舍五入和最佳轮次差异；论文主结论仍以表 6 为准，类别级分析只用于解释不同类别的相对变化和小目标类别受益情况。",
    )
    md = replace_once(
        md,
        "结果显示，baseline 速度最高，达到 153.0 FPS；DyHead 带来明显检测头计算开销；P2 高分辨率小目标检测头是 DWCA-P2/DW-P2 速度下降的主要来源。DWCA-P2 的 FPS 为 100.5，相当于单张端到端耗时约 9.95 ms，在 RTX 4090 参考环境下达到实时检测速度。该结果主要用于同环境模型对比，若部署在低功耗路侧端设备中，仍需进一步结合剪枝、轻量化卷积、知识蒸馏和 TensorRT FP16/INT8 量化降低计算成本，并在目标硬件上重新测速。",
        "结果显示，baseline 速度最高，达到 153.0 FPS；DyHead 带来明显检测头计算开销；P2 高分辨率小目标检测头是 DWCA-P2/DW-P2 速度下降的主要来源。DWCA-P2 的 FPS 为 100.5，相当于单张端到端耗时约 9.95 ms，在 RTX 4090 参考环境下具有实时性参考。该结果主要用于同环境模型对比，不等同于 TensorRT、INT8 或低功耗路侧端设备上的部署速度；若部署在实际端侧设备中，仍需进一步结合剪枝、轻量化卷积、知识蒸馏和 TensorRT FP16/INT8 量化降低计算成本，并在目标硬件上重新测速。",
    )
    md = replace_once(
        md,
        "为观察模型训练收敛趋势，本文根据 baseline 与 DWCA-P2 的 results.csv 绘制验证集 mAP@0.5:0.95 曲线和 Recall 曲线，如图 6 和图 7 所示。从曲线变化可以看出，DWCA-P2 在训练中后期保持更高的 mAP@0.5:0.95 和 Recall，说明 P2 分支带来的提升不是单个 epoch 的偶然波动，而是在训练收敛阶段形成了相对稳定的性能差距。",
        "为观察模型训练收敛趋势，本文根据 baseline 与 DWCA-P2 的 results.csv 绘制验证集 mAP@0.5:0.95 曲线和 Recall 曲线，如图 6 和图 7 所示。从曲线变化可以看出，DWCA-P2 在本次训练的中后期保持更高的 mAP@0.5:0.95 和 Recall，说明 P2 分支带来的提升在该训练记录中具有持续性。需要说明的是，该曲线不能替代多随机种子重复实验或统计显著性检验。",
    )
    md = replace_once(
        md,
        "由于当前产物未保存完整逐框预测 txt/json，本文不进一步声称逐图漏检数量或按目标尺度细分的检测指标。后续若需展开错误类型分析，应重新保存验证集预测结果，并按类别、目标尺度和置信度区间统计漏检与误检。",
        "由于当前产物未保存完整逐框预测 txt/json，本文不进一步声称逐图漏检数量或按目标尺度细分的检测指标。后续若需展开错误类型分析，应重新保存验证集预测结果，并按类别、目标尺度和置信度区间统计漏检与误检。",
    )
    old_iou_expl = "其中，B 为预测框，B_gt 为真实框。传统 CIoU 在 IoU 基础上引入中心距离和宽高比约束，能够提升边界框回归稳定性。Wise-IoU 进一步关注样本质量差异，通过动态非单调聚焦机制调整不同质量锚框的梯度增益[5]。其思想是避免低质量样本产生过强有害梯度，同时不过度放大已经较好拟合的高质量样本，使模型更关注普通质量样本的有效学习。"
    new_iou_expl = "其中，B 表示预测框区域，B_gt 表示真实框区域，A_inter 表示两者交叠区域面积，A_union 表示两者并合区域面积。传统 CIoU 在 IoU 基础上引入中心距离和宽高比约束，能够提升边界框回归稳定性。Wise-IoU 进一步关注样本质量差异，通过动态非单调聚焦机制调整不同质量锚框的梯度增益[5]。其思想是避免低质量样本产生过强有害梯度，同时不过度放大已经较好拟合的高质量样本，使模型更关注普通质量样本的有效学习。"
    if old_iou_expl in md:
        md = replace_once(md, old_iou_expl, new_iou_expl)
    md = replace_once(
        md,
        "本文仍存在若干局限。首先，当前实验已经补充类别级 AP 和验证集尺度分布统计，但尚未保存完整逐框预测 txt/json，因此未进一步报告基于预测框的细分误差统计。若后续需要分析不同目标尺度下的检测差异，应重新保存验证集预测结果，并按统一规则重新计算，不能从当前汇总表格直接推断。",
        "本文仍存在若干局限。首先，当前实验已经补充类别级 AP 和验证集尺度分布统计，但尚未保存完整逐框预测 txt/json，因此未进一步报告基于预测框的细分误差统计。若后续需要分析不同目标尺度下的检测差异，应重新保存验证集预测结果，并按统一规则重新计算，不能从当前汇总表格直接推断。其次，正文主结果、消融实验和类别级分析均基于统一验证口径，尚未报告独立测试集 AP；后续投稿前可补充测试集评价以进一步验证泛化能力。",
    )
    md = replace_once(
        md,
        "其次，本文方法增加了计算量。DWCA-P2 的 GFLOPs 是 baseline 的约 2.25 倍，FPS 下降约 52.45。对于需要在低功耗设备上实时运行的路侧系统，仍需进一步轻量化。可行方向包括减少 P2 分支通道数、使用轻量卷积替代部分标准卷积、剪枝冗余通道、使用蒸馏训练小模型以及进行 TensorRT INT8 量化。",
        "再次，本文方法增加了计算量。DWCA-P2 的 GFLOPs 是 baseline 的约 2.25 倍，FPS 下降约 52.45。对于需要在低功耗设备上实时运行的路侧系统，仍需进一步轻量化。可行方向包括减少 P2 分支通道数、使用轻量卷积替代部分标准卷积、剪枝冗余通道、使用蒸馏训练小模型以及进行 TensorRT INT8 量化。",
    )
    md = replace_once(
        md,
        "最后，本文主要基于单数据集验证。DAIR-V2X-I 具有典型路侧特征，但不同城市、摄像机高度、道路结构和天气条件会造成分布差异。未来应在更多路侧数据集或自采路侧视频上验证模型泛化能力，并分析夜间、雨雾、逆光等复杂条件下的检测表现。",
        "最后，本文主要基于单数据集和固定随机种子结果验证。DAIR-V2X-I 具有典型路侧特征，但不同城市、摄像机高度、道路结构和天气条件会造成分布差异；单次训练结果也不能反映不同随机初始化下的性能波动。未来应在更多路侧数据集或自采路侧视频上验证模型泛化能力，补充多随机种子重复实验，并分析夜间、雨雾、逆光等复杂条件下的检测表现。",
    )
    md = replace_once(
        md,
        "数据统计表明，本文数据集中 short side < 32 px 的目标占 87.55%，area < 32^2 px 的目标占 79.65%，小目标检测需求明显。在统一 batch=32 训练口径下，最终 DWCA-P2 模型取得 86.0% Precision、83.5% Recall、88.4% mAP@0.5 和 64.4% mAP@0.5:0.95。与 YOLO11n baseline 相比，Recall 提升 2.7 个百分点，mAP@0.5 提升 2.4 个百分点，mAP@0.5:0.95 提升 4.2 个百分点。",
        "数据统计表明，本文数据集中 short side < 32 px 的目标占 87.55%，area < 32^2 px 的目标占 79.65%，小目标检测需求明显。在统一 batch=32 训练和验证口径下，最终 DWCA-P2 模型取得 86.0% Precision、83.5% Recall、88.4% mAP@0.5 和 64.4% mAP@0.5:0.95。与 YOLO11n baseline 相比，Recall 提升 2.7 个百分点，mAP@0.5 提升 2.4 个百分点，mAP@0.5:0.95 提升 4.2 个百分点。",
    )
    md = replace_once(
        md,
        "未来工作将从三个方面展开。第一，进一步筛选远距离小目标样例制作局部放大对比图，以更直观展示不同结构的检测差异。第二，结合 TensorRT、剪枝、量化和蒸馏降低部署成本。第三，将模型扩展到夜间、雨雾、逆光和多摄像头路侧场景，验证其跨场景泛化能力。",
        "未来工作将从四个方面展开。第一，补充独立测试集 AP 与多随机种子重复实验，进一步验证结果稳定性。第二，筛选远距离小目标样例制作局部放大对比图，以更直观展示不同结构的检测差异。第三，结合 TensorRT、剪枝、量化和蒸馏降低部署成本。第四，将模型扩展到夜间、雨雾、逆光和多摄像头路侧场景，验证其跨场景泛化能力。",
    )
    return md


def build_revision_response() -> str:
    return textwrap.dedent(
        f"""\
        # 修订回复与简短复审报告

        - 原稿：`{SOURCE_DOCX}`
        - 修订稿：`{REVISED_DOCX}`
        - 审稿报告：`{REVIEW_REPORT}`

        ## 简短复审结论

        本轮修订已处理审稿报告中的主要可处理问题。修订没有新增实验数据、引用或指标，也没有改变主结果数值。仍需人工核验的问题集中在独立测试集 AP、多随机种子重复实验、类别级 AP 日志来源和完整 Word 分页检查。

        ## major issues 逐点回复

        | 编号 | 审稿意见摘要 | 修订动作 | 状态 |
        |---|---|---|---|
        | MI-1 | 评价集口径和主结果边界需要前置说明 | 在 4.1 增加评价口径说明；在 4.3、5.1、结论中明确主结果基于统一验证口径，测试集 AP 尚未报告。 | 已处理，测试集 AP 仍需人工补充 |
        | MI-2 | 方法贡献边界需更清楚 | 修改摘要、3.5 和相关结果分析，明确 P2 是主增益，CoordAttention 是辅助增强模块。 | 已处理 |
        | MI-3 | 速度与部署表述偏乐观 | 将“达到实时检测速度”改为“RTX 4090 参考环境下具有实时性参考”，并补充不等同于端侧部署速度。 | 已处理 |
        | MI-4 | 类别级 AP 与主结果来源不完全一致 | 在 5.2 明确表 7 仅用于解释类别相对变化和小目标类别受益，主结论仍以表 6 为准。 | 已处理 |
        | MI-5 | 缺少随机性和重复实验限制 | 修改训练曲线表述，避免暗示显著性；在局限性中加入固定随机种子和未做多 seed 的限制。 | 已处理，重复实验需人工补做 |
        | MI-6 | 实验设置与结果分析衔接可更紧 | 在 4.1、4.3、5.1 前置数据来源和验证口径，提升“设置—结果”对应关系。 | 已处理 |

        ## minor issues 逐点回复

        | 编号 | 审稿意见摘要 | 修订动作 | 状态 |
        |---|---|---|---|
        | mI-1 | 英文摘要需与中文摘要保持模块边界一致 | 英文摘要加入 unified validation protocol 和 auxiliary enhancement 表述。 | 已处理 |
        | mI-2 | 部分段落“本文”主语较多 | 对若干关键段落进行了主语和句式调整；未做大规模风格重写，以避免引入新含义。 | 部分处理 |
        | mI-3 | 表 10 FPS 相同值不宜过度解释 | 速度分析保持总体解释，不再从四舍五入相同值推出额外结论。 | 已处理 |
        | mI-4 | 参考文献格式需人工核对 | 保留为人工核验事项，未自动改动参考文献，避免格式误修。 | 待人工核验 |
        | mI-5 | 曲线来源需说明 | 5.6 明确曲线来自 results.csv 和本次训练记录，不能替代多 seed 或统计检验。 | 已处理 |

        ## 是否引入新不一致

        - 未改变 baseline 和 DWCA-P2 的指标数值。
        - 未恢复 b32、Triplet/TDW、官方预训练参考实验、精度-速度权衡图、AI 使用说明或未确认元数据。
        - 未新增参考文献、实验结果、测试集 AP、显著性检验或新的尺度细分指标。
        - 新版稿件对“验证集主结果”和“测试集未报告 AP”的边界更明确，与项目交接口径一致。
        """
    )


def build_human_checks() -> str:
    return textwrap.dedent(
        f"""\
        # 剩余人工核验清单

        ## 实验与数据

        - [ ] 是否需要补充独立测试集 AP，并确认测试集推理/评估脚本与验证集口径一致。
        - [ ] 是否需要进行 3 个或更多随机种子重复训练，报告均值、标准差或置信区间。
        - [ ] 表 7 类别级 AP 的训练日志来源、最佳轮次/最后轮次口径需由作者核验。
        - [ ] 若后续要分析不同目标尺度下的检测差异，需重新保存逐框预测 txt/json 并按统一规则计算，不能从当前表格推断。

        ## 论文与投稿信息

        - [ ] 基金项目、收稿日期、中图分类号、文献标志码、文章编号、稿件 DOI 和作者简介仍待导师确认。
        - [ ] 参考文献需按《哈尔滨理工大学学报》最终格式逐条核对作者大小写、页码、会议/期刊名和 DOI。
        - [ ] 英文题名、作者英文名、单位英文译名需作者最终确认。

        ## Word 版式

        - [ ] 在 Microsoft Word 或完整 LibreOffice 环境中逐页检查 `{REVISED_DOCX}`。
        - [ ] 检查表格跨页、图题/表题分页、公式编号位置和参考文献缩进。
        - [ ] 确认 Quick Look 首页预览不能替代完整投稿前版式检查。
        """
    )


def assert_revision_safety(md: str) -> None:
    body = md.split("## 参考文献", 1)[0]
    forbidden = {
        "visible b32": r"\bb32\b|baseline-b32|DWCA-P2-b32",
        "Triplet/TDW": r"Triplet|TDW|YOLOv11n-TDW",
        "AI statement": r"AI 使用|人工智能使用|生成式人工智能",
        "official pretrained": r"官方预训练|预训练参考|YOLOv5n\.pt|YOLOv8n\.pt|YOLOv10n\.pt|YOLO11n\.pt",
        "speed tradeoff": r"精度-速度权衡|trade-?off",
        "unconfirmed metadata": r"基金项目|收稿日期|中图分类号|文献标志码|文章编号|稿件 DOI|作者简介",
    }
    hits = {name: len(re.findall(pattern, body, flags=re.I)) for name, pattern in forbidden.items()}
    bad = {name: count for name, count in hits.items() if count}
    if bad:
        raise AssertionError(f"Forbidden content in revised body: {bad}")


def main() -> None:
    md = SOURCE_MD.read_text(encoding="utf-8")
    revised = revise_markdown(md)
    assert_revision_safety(revised)
    REVIEW_REPORT.write_text(normalize_report_markdown(build_review_report()), encoding="utf-8")
    REVISED_MD.write_text(revised, encoding="utf-8")
    REVISION_RESPONSE.write_text(normalize_report_markdown(build_revision_response()), encoding="utf-8")
    HUMAN_CHECKS.write_text(normalize_report_markdown(build_human_checks()), encoding="utf-8")

    df, _ = base.load_experiment_data()
    tables = base.make_tables(df)
    original_docx = base.DOCX_PATH
    try:
        base.DOCX_PATH = REVISED_DOCX
        base.build_docx(revised, tables)
    finally:
        base.DOCX_PATH = original_docx

    if REVISED_DOCX.resolve() == SOURCE_DOCX.resolve():
        raise AssertionError("Refusing to overwrite source DOCX")
    print(f"wrote {REVIEW_REPORT}")
    print(f"wrote {REVISED_MD}")
    print(f"wrote {REVISED_DOCX}")
    print(f"wrote {REVISION_RESPONSE}")
    print(f"wrote {HUMAN_CHECKS}")


if __name__ == "__main__":
    main()
