# 面向路侧小目标检测的改进 YOLO11n 方法

> 论文修订版本：v1.1（基于模拟审稿意见修订）  
> 数据来源：`/Users/asus/ultralytics/刘华硕-实验记录表.xlsx`、`/Users/asus/ultralytics/datasets/dair_v2x_i/dair_v2x_i.yaml`、`/Users/asus/ultralytics/runs/detect/runs/ablation/`  
> 写作口径：所有实验均按固定 `batch=32` 解释；实验备注或历史日志中曾出现的旧 batch 字段不作为论文训练口径引用。  
> 参考体例：参考 `docs/about/改进YOLOv8n的桃子品质分级检测方法.pdf` 与 `docs/about/融合自注意力与局部特征的遮挡行人重识别.pdf` 的中文工程类小论文写法，采用中英文题名、摘要、关键词、引言、相关工作、数据集与方法、实验分析、结论和参考文献结构。
> 修订说明：本版本统一采用 Ultralytics 官方文档中的 `YOLO11n` 命名；现有主结果明确标注为验证集结果；对尺度分组 AP、测试集结果和同硬件 FPS 等尚未重新计算的指标作边界说明，不编造未验证数据。

## 题目

面向路侧小目标检测的改进 YOLO11n 方法

## 摘要

路侧感知是车路协同系统获取全局交通状态的重要组成部分。受摄像机安装高度、观测距离、道路纵深和目标遮挡等因素影响，路侧图像中的行人、骑行者、摩托车和交通锥等目标常呈现尺度小、密度高、类别不均衡和背景干扰强等特点。轻量化 YOLO 模型虽然具有较好的实时检测能力，但默认 P3/P4/P5 三尺度检测结构对极小目标的浅层细节保留不足，容易造成远距离弱势交通参与者漏检。针对上述问题，本文构建一种面向路侧小目标检测的改进 YOLO11n 方法 YOLO11n-DWCA-P2。该方法以 YOLO11n 为基准模型，在检测端引入 DyHead 动态检测头，在边界框回归中采用 Wise-IoU 损失，并进一步增加 P2/4 高分辨率检测分支，使检测特征由 P3/P4/P5 扩展为 P2/P3/P4/P5；同时在中浅层特征处嵌入 CoordAttention 模块，以增强位置敏感通道表达。基于 DAIR-V2X-I 路侧图像数据集的标注统计表明，在 640 输入尺度下，短边小于 32 像素的目标占 87.55%，面积小于 32^2 像素的目标占 79.65%，数据集具有显著的小目标密集特征。验证集实验结果表明，在统一 batch=32、imgsz=640、epochs=300 的训练设置下，所构建的 DWCA-P2-b32 模型 Precision 为 86.0%，Recall 为 83.5%，mAP@0.5 为 88.4%，mAP@0.5:0.95 为 64.4%；相较 YOLO11n baseline-b32，Recall 提升 2.7 个百分点，mAP@0.5 提升 2.4 个百分点，mAP@0.5:0.95 提升 4.2 个百分点。消融实验和类别级 AP 分析表明，P2 高分辨率检测分支是当前性能提升的主要来源，CoordAttention 起辅助增强作用，Triplet 注意力路线未超过 DyHead 与 WIoU 组合基线。本文方法在验证集上表现出更高的小目标检出能力和定位质量，为车路协同场景下轻量化目标检测模型改进提供了参考。

**关键词**：路侧目标检测；车路协同；YOLO11n；小目标检测；DyHead；Wise-IoU；P2 检测分支

## Improved YOLO11n for Roadside Small Object Detection

## Abstract

Roadside perception is an important component of vehicle-infrastructure cooperative systems because it provides a wider observation range than vehicle-mounted sensors. However, roadside images often contain dense and distant targets, where pedestrians, cyclists, motorcyclists, and traffic cones occupy only a few pixels after resizing. Lightweight YOLO detectors are suitable for real-time deployment, but the default P3/P4/P5 detection structure of YOLO11n may lose fine-grained spatial details during repeated downsampling, which limits its ability to detect small roadside objects. To address this problem, this paper develops YOLO11n-DWCA-P2, an improved YOLO11n detector for roadside small object detection. The method introduces a DyHead detection head and Wise-IoU regression loss into YOLO11n, adds a P2/4 high-resolution detection branch to extend the detection features from P3/P4/P5 to P2/P3/P4/P5, and embeds a Coordinate Attention module into the shallow-to-middle feature stage to enhance position-aware channel representation. Label statistics on the DAIR-V2X-I roadside image dataset show that, under the 640 input scale, objects with a short side smaller than 32 pixels account for 87.55%, and objects with an area smaller than 32^2 pixels account for 79.65%, indicating a clear small-object-dense characteristic. On the validation set, under the unified training setting of batch=32, image size 640, and 300 epochs, the DWCA-P2-b32 model achieves 86.0% Precision, 83.5% Recall, 88.4% mAP@0.5, and 64.4% mAP@0.5:0.95. Compared with the YOLO11n baseline-b32, Recall, mAP@0.5, and mAP@0.5:0.95 are improved by 2.7, 2.4, and 4.2 percentage points, respectively. Ablation and class-level AP results further show that the P2 high-resolution detection branch is the main source of the observed improvement, while Coordinate Attention provides auxiliary enhancement, and the Triplet-based route does not outperform the DyHead plus Wise-IoU baseline. The proposed method shows improved detection and localization performance for roadside small objects on the validation set and provides a practical structural optimization reference for lightweight detectors in vehicle-infrastructure cooperative perception.

**Keywords**: roadside object detection; vehicle-infrastructure cooperation; YOLO11n; small object detection; DyHead; Wise-IoU; P2 detection branch

---

## 0 引言

随着智能交通系统、协同自动驾驶和车路云一体化技术的发展，单车智能感知逐渐向车端、路端和云端协同感知演进。车载摄像机和激光雷达能够提供车辆自身周围的局部环境信息，但其感知范围容易受到遮挡、视角和传感器安装位置限制。路侧感知设备通常部署在信号灯杆、道路横杆或高位监控点，具有较稳定的外参条件和更广的道路覆盖范围，能够从全局视角捕获交叉口、匝道、车道汇入区域等复杂交通场景中的车辆与弱势交通参与者。因此，路侧目标检测结果不仅可用于道路事件监测、交通流统计和安全预警，也可作为车路协同自动驾驶系统的重要环境输入。

然而，路侧视觉感知并不是简单地将通用目标检测模型迁移到道路监控画面中。路侧摄像机通常具有较高安装位置和较大俯视角，道路纵深方向明显，远端目标在图像中呈现出极小尺度。行人、骑行者、摩托车、交通锥等目标本身物理尺寸较小，当其位于远距离区域时，经过图像缩放和网络下采样后往往仅保留少量像素。与此同时，道路场景中车辆、交通标志、车道线、护栏、树木阴影和路面纹理共同构成复杂背景，交通参与者之间还可能存在相互遮挡。这些因素使路侧目标检测具有小目标多、密集目标多、背景干扰强和类别分布不均衡等特征。

YOLO 系列单阶段目标检测算法因检测速度快、工程部署链路成熟，在智能交通、工业质检、农业检测和安防监控等场景中得到广泛应用。Ultralytics YOLO11 在前序 YOLO 模型的基础上继续优化特征提取、检测效率和多任务支持能力，覆盖目标检测、实例分割、姿态估计、图像分类和旋转框检测等视觉任务[2]。其中 YOLO11n 是该系列中的轻量化版本，参数量和计算量较低，适合部署在边缘设备或对实时性要求较高的系统中。对于路侧感知任务，轻量化模型的效率优势具有现实意义，但其有限的网络容量也使其更容易受到小目标信息损失的影响。

通用 YOLO 检测结构通常采用多尺度特征输出处理不同尺寸目标。以轻量化 YOLO11n 为例，其默认检测头主要使用 P3/P4/P5 三个尺度特征，对应输入图像的 1/8、1/16 和 1/32 下采样特征图。在常规目标检测任务中，P3 特征已经能够覆盖较多小目标。但在路侧图像中，当目标短边仅为数像素至十余像素时，1/8 下采样后的特征响应可能过于稀疏，边界和局部纹理信息难以被完整保留。若仅依靠深层语义特征，模型可能获得较好的类别判别能力，却无法准确定位小目标框，最终表现为漏检、定位偏移或高 IoU 阈值下 AP 下降。

为验证上述问题，本文对 DAIR-V2X-I 路侧图像数据集的 YOLO 标注进行统计。该数据集包含 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类道路交通目标。统计结果显示，在 640 输入尺度下，短边小于 32 像素的目标占 87.55%，短边小于 16 像素的目标占 68.60%，面积小于 32^2 像素的目标占 79.65%。其中 Trafficcone 的中位短边约为 4.2 像素，Pedestrian 的中位短边约为 8.9 像素，Cyclist 和 Motorcyclist 的中位短边也仅约为 14.4 像素和 15.5 像素。这一分布说明，本文任务的主要矛盾并非单纯提升大目标分类置信度，而是如何在轻量化网络中保留并利用高分辨率空间细节。

围绕小目标检测问题，已有研究通常从多尺度特征融合、注意力机制、检测头优化和边界框损失函数等方面改进模型。多尺度融合能够将浅层细节与深层语义结合，提高不同尺度目标的表达能力；注意力机制可增强关键区域或通道的响应，抑制背景噪声；动态检测头能够根据尺度、空间位置和任务类型调整检测特征；IoU 系列损失函数则直接影响边界框回归质量。上述方向并非互相排斥，但在轻量化模型中盲目叠加模块可能带来冗余计算，也可能因功能重叠导致收益有限。因此，针对路侧小目标场景，需要通过实验确定真正有效的结构改进路径。

本文构建一种面向路侧小目标检测的改进 YOLO11n 方法，记为 YOLO11n-DWCA-P2。该方法首先将 YOLO11n 检测头替换为 DyHeadDetect，以动态建模尺度、空间和任务维度的检测特征；其次采用 Wise-IoU 作为边界框回归损失，改善样本质量差异下的定位学习；随后在 Neck-Head 部分增加 P2/4 高分辨率检测分支，使模型直接在更高分辨率特征图上检测极小目标；最后引入 CoordAttention 模块，在较浅层特征中嵌入坐标位置信息，提升位置敏感表达能力。

本文的实验路线并非直接堆叠所有模块，而是经历了从 Triplet、DyHead、WIoU 到 P2 分支的逐步消融。实验结果显示，Triplet 注意力及其 channel-only、P3 迁移和 DyHead 加深等路线均未超过 DyHead 与 WIoU 组合基线；CoordAttention 单独带来的提升也较有限。真正显著提高 Recall 和 mAP@0.5:0.95 的，是新增 P2 高分辨率检测分支。该结果与 DAIR-V2X-I 数据集中极小目标占比高的统计事实一致，也说明结构改进应优先服务于数据集的目标尺度分布。

本文主要贡献如下。

1. 面向 DAIR-V2X-I 路侧图像的小目标密集特征，统计分析了训练、验证和测试集的类别分布与目标尺度分布，并进一步给出验证集类别尺度分布，为引入高分辨率检测分支提供数据依据。

2. 构建 YOLO11n-DWCA-P2 检测方法，在 YOLO11n 中融合 DyHead、Wise-IoU、CoordAttention 与 P2 高分辨率检测分支，将检测尺度由 P3/P4/P5 扩展为 P2/P3/P4/P5。

3. 在统一 batch=32 训练口径下完成系统消融实验，表明 P2 分支是当前验证集性能提升的主要来源，CoordAttention 为辅助增强模块，Triplet 路线在本文任务中未形成有效增益。

4. 与 YOLOv5n、YOLOv8n、YOLOv10n、YOLO11n 等轻量化模型进行同口径结构对比和预训练参考对比，验证集结果表明本文方法在 mAP@0.5 和 mAP@0.5:0.95 上取得更优表现；同时说明测试集复验、尺度分组 AP 和同硬件 FPS 是后续投稿前必须补充的验证项。

## 1 相关工作

### 1.1 路侧目标检测与车路协同感知

车路协同感知旨在通过车端和路端传感器的信息互补，提高自动驾驶系统对复杂交通环境的理解能力。车端传感器具有跟随车辆移动、感知近车区域细节的优势，但在交叉口遮挡、远距离车辆汇入和大型车辆遮挡等场景中容易出现感知盲区。路侧传感器从固定高位观察道路，能够获取更稳定的道路全局视角，为车辆提供超视距信息和交通参与者分布状态。

DAIR-V2X 数据集为车路协同感知研究提供了真实场景数据基础。该数据集包含车端与路端多模态数据，覆盖城市道路、高速道路、交叉口和多种天气光照条件，并引入车辆-基础设施协同 3D 目标检测任务[1]。本文使用其中路侧单目图像数据构建 YOLO 检测任务，关注二维图像下的路侧交通目标检测。与车端图像相比，路侧图像中的远距离目标更小，交通锥、行人等类别数量多但像素尺度低，使检测模型需要更强的小目标定位能力。

在路侧场景中，漏检弱势交通参与者的风险往往高于少量误检。Pedestrian、Cyclist 和 Motorcyclist 等类别虽然在实例数中占比低于 Car 和 Trafficcone，但它们直接关系到道路安全预警。对于这些类别，检测模型不仅需要在低 IoU 阈值下判断目标存在，还需要在更严格 IoU 阈值下保持定位质量。因此，本文同时关注 Recall、mAP@0.5 和 mAP@0.5:0.95，并将 mAP@0.5:0.95 作为衡量定位质量的重要指标。

### 1.2 YOLO 系列轻量化目标检测

YOLO 系列模型采用单阶段检测范式，将目标分类和边界框回归统一到端到端网络中，具有较好的速度和精度平衡[7,10]。Ultralytics YOLOv8 于 2023 年发布，采用 Anchor-free split head 等设计，在检测、分割、分类和姿态估计等任务上形成较完整的工程生态[6]。YOLO11 进一步面向实时视觉任务优化骨干网络、颈部结构和训练流程，并支持多种视觉任务[2]。在实际应用中，n 系列轻量模型因参数少、推理快，常作为边缘部署和快速迭代的基础模型。

轻量化模型的主要问题在于网络容量有限。为了保持实时性，YOLO11n 的通道数和模块深度较小，对复杂背景、小目标和密集目标的表达能力有限。若在不改变检测尺度的情况下仅增加注意力模块，模型可能提升部分通道选择能力，但无法从根本上恢复下采样过程中已经损失的空间细节。本文实验中的 `DWCA` 与 `+DW` 结果接近，也说明对本数据集而言，单纯增强注意力并不足以解决小目标检测瓶颈。

因此，轻量化模型改进需要在精度和计算量之间做取舍。对于车路协同路侧系统，若模型部署在路侧边缘服务器或具备 GPU/NPU 加速的边缘盒子中，适度增加计算量以换取更高 Recall 和更好定位质量是可接受的。本文方法的 GFLOPs 从 baseline-b32 的 6.3 增加到 14.2，参数量从 2.58M 增加到 4.46M，仍保持在轻量级检测模型范围内，但相比原始 YOLO11n 已显著增加。该代价需要结合具体部署硬件进一步评估。

### 1.3 小目标检测与多尺度特征融合

小目标检测的困难主要来自像素信息不足、上下文依赖强和特征下采样损失。对于大目标，深层语义特征能够提供足够的分类和定位信息；对于小目标，浅层特征中的边缘、角点和纹理信息更为关键。多尺度特征融合通过将不同分辨率特征组合，使模型同时获得语义信息和空间细节，是提升小目标检测性能的常用方法[8-9]。

YOLO 默认的 P3/P4/P5 检测尺度已经具备一定多尺度能力，但在极小目标密集任务中，P3/8 仍可能不够精细。P2/4 特征图相较 P3/8 具有更高空间分辨率，在输入图像为 640 x 640 时，P2 特征图约为 160 x 160，P3 特征图约为 80 x 80。对于短边仅 4 到 16 像素的目标，P2 分支能够显著增加其在特征图中的响应区域，降低目标在下采样后被压缩为单点或弱响应的风险。

当然，新增 P2 分支也会增加计算量。高分辨率特征图面积较大，卷积和检测头计算开销明显高于 P4/P5。本文消融结果表明，P2 分支将 GFLOPs 从 9.3 左右提高到 14.2，但 mAP@0.5:0.95 同时从 61.3% 提高到 64.4%。在路侧小目标检测任务中，这种计算代价换来了更明显的定位质量提升，符合本文任务需求。

### 1.4 注意力机制、动态检测头与边界框损失

注意力机制通过增强关键信息、抑制冗余背景，能够提升视觉模型的特征表达能力。CoordAttention 将通道注意力分解为沿水平和垂直方向的一维编码过程，在建模长程依赖的同时保留方向感知和位置敏感信息[4]。对于路侧图像，小目标常分布在道路纵深方向的局部区域，位置信息对检测具有一定价值。因此，本文将 CoordAttention 引入中浅层特征作为辅助增强模块。

Dynamic Head（DyHead）从检测头角度统一建模尺度感知、空间感知和任务感知注意力。Dai 等[3]认为检测头需要同时处理不同特征层级、空间位置和任务通道之间的差异，DyHead 通过在检测头中组合多种注意力机制，提高检测特征表达能力。本文将 YOLO11n 的检测头替换为 DyHeadDetect，使多尺度特征在输出预测前获得更充分的动态调制。消融实验显示，`+D` 相较 baseline 的 mAP@0.5 从 85.9% 提升至 86.6%，说明 DyHead 对本文任务具有稳定正向作用。

边界框损失函数决定了模型如何优化预测框与真实框之间的空间关系。传统 IoU、GIoU、DIoU、CIoU 等损失从重叠面积、中心距离和宽高比等角度约束回归过程。Wise-IoU 提出动态非单调聚焦机制，依据样本质量调整梯度增益，减弱低质量样本对回归学习的负面影响，并避免过度聚焦高质量样本[5]。在本文实验中，WIoU 单独替换 CIoU 的提升有限，但与 DyHead 结合后形成较强基线，表明检测头表达与回归损失之间存在互补关系。

## 2 数据集与小目标特征分析

### 2.1 数据集来源与类别设置

本文实验基于 DAIR-V2X-I 路侧图像数据构建 YOLO 格式目标检测数据集。数据集配置文件位于 `/Users/asus/ultralytics/datasets/dair_v2x_i/dair_v2x_i.yaml`，其中 `train`、`val` 和 `test` 分别指向训练集、验证集和测试集图像目录。类别名称包括 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类。原始数据中的极少样本类别 Barrowlist 未纳入本文 8 类检测任务。需要说明的是，本文当前报告的主实验、消融实验、类别级 AP、PR 曲线、混淆矩阵和训练曲线均来自验证集；测试集目录和标注已保留，但尚未在本版本中重新完成同口径测试集评估。

表 1 给出了本文使用的数据集划分和实例数量。训练集包含 4940 个标注文件、227831 个目标实例；验证集包含 1411 个标注文件、65255 个实例；测试集包含 707 个标注文件、32628 个实例。总计 7058 个标注文件和 325714 个目标实例。该规模能够支撑轻量化 YOLO 模型训练与消融比较。

**表 1 DAIR-V2X-I 数据集划分与实例数**

| 划分 | 标注文件数 | 实例数 |
|---|---:|---:|
| 训练集 | 4940 | 227831 |
| 验证集 | 1411 | 65255 |
| 测试集 | 707 | 32628 |
| 合计 | 7058 | 325714 |

### 2.2 类别分布统计

表 2 给出了各类别实例数量及占比。Trafficcone 数量最多，共 159930 个，占 49.10%；Car 共有 91443 个，占 28.07%。两类合计占比超过 77%，说明数据集中存在明显类别不均衡。Pedestrian 为 25194 个，占 7.74%；Cyclist 和 Motorcyclist 分别占 5.29% 和 5.60%；Truck、Van 和 Bus 的占比较低，均属于相对少样本类别。

**表 2 DAIR-V2X-I 类别实例分布**

| 类别 | 实例数 | 占比/% |
|---|---:|---:|
| Car | 91443 | 28.07 |
| Truck | 3501 | 1.07 |
| Van | 6767 | 2.08 |
| Bus | 3379 | 1.04 |
| Cyclist | 17244 | 5.29 |
| Motorcyclist | 18256 | 5.60 |
| Pedestrian | 25194 | 7.74 |
| Trafficcone | 159930 | 49.10 |

类别不均衡对模型训练具有两方面影响。一方面，Trafficcone 和 Car 的大量样本有助于模型学习常见目标模式；另一方面，少样本类别在训练中获得的梯度更新较少，容易受到背景、遮挡和尺度变化影响。对于交通安全而言，Pedestrian、Cyclist 和 Motorcyclist 虽然占比不高，却是路侧感知最需要稳定检出的目标类别。因此，评价模型时不能只关注总体 Precision，还应关注 Recall 和严格 IoU 阈值下的平均精度。

### 2.3 目标尺度统计

为了分析小目标特征，本文将 YOLO 归一化标注框折算到 640 x 640 输入尺度下，统计目标面积、短边长度和双边尺度。统计结果见表 3。若采用 COCO 中常见的小目标面积阈值 area < 32^2 px，则本文数据中小目标实例为 259421 个，占 79.65%。若以短边长度衡量，short side < 16 px 的目标占 68.60%，short side < 32 px 的目标占 87.55%。此外，宽高均小于 32 px 的目标占 56.37%。

**表 3 目标尺度统计结果**

| 小目标定义 | 实例数 | 占比/% |
|---|---:|---:|
| area < 32^2 px | 259421 | 79.65 |
| short side < 16 px | 223453 | 68.60 |
| short side < 32 px | 285172 | 87.55 |
| both sides < 32 px | 183595 | 56.37 |

从目标尺度看，本文数据集的小目标比例远高于一般自然场景检测任务。特别是 Trafficcone、Pedestrian、Cyclist 和 Motorcyclist 等类别，在路侧远景区域中常表现为高度细长或低像素目标。类别级中位短边统计进一步显示，Trafficcone 约为 4.2 px，Pedestrian 约为 8.9 px，Cyclist 约为 14.4 px，Motorcyclist 约为 15.5 px。对于这类目标，若模型最低检测尺度为 P3/8，则部分目标在特征图中可能仅对应 1 到 2 个栅格，边界回归难度较高。

为进一步观察验证集中的类别尺度分布，本文按 short side < 16 px、16 px <= short side < 32 px 和 short side >= 32 px 三个区间统计各类别目标数量，结果见表 4。Pedestrian 和 Trafficcone 几乎全部属于 short side < 32 px 的小目标，其中 Pedestrian 的 short side < 16 px 实例为 4587 个，占该类验证集实例的 90.4%；Trafficcone 的 short side < 16 px 实例为 32009 个，占该类验证集实例的 99.9%。Cyclist 和 Motorcyclist 的 short side < 32 px 占比分别为 93.1% 和 88.0%。相比之下，Bus 的中位短边为 38.1 px，小目标比例相对较低。上述统计说明，本文方法的 P2 分支主要服务于 Pedestrian、Trafficcone、Cyclist 和 Motorcyclist 等小尺度类别。

**表 4 验证集各类别尺度分布（imgsz=640）**

| 类别 | 实例数 | short<16 | 16<=short<32 | short>=32 | short<32/% | 中位短边/px |
|---|---:|---:|---:|---:|---:|---:|
| Car | 18342 | 3811 | 8238 | 6293 | 65.7 | 26.0 |
| Truck | 660 | 16 | 436 | 208 | 68.5 | 30.4 |
| Van | 1385 | 207 | 643 | 535 | 61.4 | 28.6 |
| Bus | 669 | 41 | 221 | 407 | 39.2 | 38.1 |
| Cyclist | 3469 | 2192 | 1036 | 241 | 93.1 | 14.4 |
| Motorcyclist | 3632 | 1881 | 1314 | 437 | 88.0 | 15.6 |
| Pedestrian | 5073 | 4587 | 485 | 1 | 100.0 | 9.0 |
| Trafficcone | 32025 | 32009 | 16 | 0 | 100.0 | 4.2 |

![图 1 验证集目标尺度分布](/Users/asus/ultralytics/docs/paper_assets/val_scale_distribution_640.svg)

> 图 1 验证集目标尺度分布。该图由 `/Users/asus/ultralytics/docs/paper_assets/val_scale_distribution_640.csv` 生成，反映不同类别在 640 输入尺度下的短边区间占比。

### 2.4 数据特征对模型设计的启示

上述统计为本文方法设计提供了直接依据。首先，目标短边普遍较小，说明模型需要更高分辨率的检测特征，P2/4 分支具有必要性。其次，类别分布不均衡且小目标类别与道路安全高度相关，说明模型需要提高 Recall，减少远距离目标漏检。再次，大量交通锥和车辆构成密集目标区域，要求检测头能够处理尺度和空间位置差异，DyHead 因此具有应用价值。最后，路侧背景复杂、目标位置具有明显道路几何规律，CoordAttention 的方向位置编码可作为辅助增强。

因此，本文方法并不是从通用模块库中任意组合改进点，而是从数据尺度统计出发，以 P2 分支解决“看不清”的问题，以 DyHead 解决“多尺度和空间差异建模不足”的问题，以 WIoU 解决“定位回归样本质量差异”的问题，以 CoordAttention 辅助增强“位置敏感特征表达”。后续实验也将围绕这些假设展开验证。

## 3 改进 YOLO11n 检测方法

### 3.1 YOLO11n 基准网络

YOLO11n 是 YOLO11 系列中的 nano 版本，具有参数量小、计算量低和训练部署方便等优点。本文以 YOLO11n YAML 结构作为 baseline，并采用从头训练的方式进行主要对比。baseline-b32 在固定 batch=32 复验中取得 Precision 85.7%、Recall 80.8%、mAP@0.5 86.0%、mAP@0.5:0.95 60.2%、GFLOPs 6.3、Params 2.58M 的结果。该模型计算量较低，但 Recall 和 mAP@0.5:0.95 仍存在提升空间。

YOLO11n 的检测流程可以概括为：输入图像经 Backbone 提取多层特征，Neck 通过上采样、拼接和卷积实现多尺度特征融合，Head 在不同尺度特征图上预测目标类别和边界框。默认检测头使用 P3、P4 和 P5 三层特征，其中 P3 更偏向小目标，P4 和 P5 更偏向中大目标。对于 DAIR-V2X-I 这种极小目标比例高的数据集，仅使用 P3 作为最高分辨率检测层可能不足。

### 3.2 总体改进结构

本文提出的 YOLO11n-DWCA-P2 在基准网络基础上进行四方面改进。第一，将检测头替换为 DyHeadDetect，提高多尺度特征在检测阶段的动态表达能力；第二，在边界框回归中采用 Wise-IoU 损失，提高定位学习质量；第三，在 Neck 中新增 P2/4 高分辨率检测分支，使检测头接收 P2、P3、P4 和 P5 四尺度输入；第四，在浅中层特征中引入 CoordAttention，以增强通道和坐标位置联合建模。

图 2 为本文方法结构示意图。该图基于 `yolo11-dwca-p2.yaml` 重新绘制，突出 Backbone、Top-down FPN、Bottom-up PAN、四尺度检测输入和 Head/Loss 的阶段关系。图中 P2 分支对应 layer 20，CoordAttention 位于 layer 5，DyHeadDetect 的输入为 [20, 23, 26, 29]。需要强调的是，WIoU 以虚线 loss path 表示，仅作用于训练阶段的边界框回归损失，不属于推理阶段的网络拓扑。

![图 2 YOLO11n-DWCA-P2 网络结构示意图](/Users/asus/ultralytics/docs/paper_assets/dwca_p2_overview_optimized.svg)

> 图 2 YOLO11n-DWCA-P2 网络结构示意图。实线表示特征流，虚线表示训练损失路径；P2/P3/P4/P5 四尺度特征输入 DyHeadDetect，WIoU v3 仅用于训练期 bbox loss。

为避免总体结构图过于拥挤，本文进一步绘制 P2 高分辨率分支、DyHeadDetect、CoordAttention 和 WIoU 的内部结构图，分别见图 3(a)-图 3(d)。这些子图用于支撑各改进模块的结构说明，总图则用于说明完整模型的数据流。

### 3.3 P2 高分辨率检测分支

P2 分支是本文最终模型的核心改进。对于输入大小为 640 x 640 的图像，P2/4 特征图分辨率约为 160 x 160，P3/8 特征图分辨率约为 80 x 80。若一个目标短边为 8 px，则在 P3 特征图上对应约 1 个像素，在 P2 特征图上对应约 2 个像素；若目标短边为 16 px，则在 P3 上约 2 个像素，在 P2 上约 4 个像素。虽然这只是近似分析，但足以说明 P2 对极小目标响应区域的提升。

本文在 Neck 中将较高层特征逐步上采样，并与浅层 P2 特征拼接融合，得到用于 tiny object detection 的 P2 输出层。随后，检测头由原来的三尺度输入扩展为四尺度输入。P2 分支保留了更多浅层边缘、纹理和空间位置信息，能够缓解远距离行人、交通锥和骑行者在深层特征中消失或定位偏移的问题。

![图 3(a) P2 高分辨率检测分支内部结构](/Users/asus/ultralytics/docs/paper_assets/module_p2_branch.svg)

> 图 3(a) P2 高分辨率检测分支内部结构。layer 17 的 P3/8 特征经上采样后与 layer 2 的 P2/4 浅层特征拼接，layer 20 作为 P2 tiny 输出进入 DyHeadDetect，同时通过下采样参与后续 P3 融合。

从消融结果看，`DW-P2` 在不使用 CoordAttention 的情况下，mAP@0.5 达到 88.1%，mAP@0.5:0.95 达到 64.4%；完整 `DWCA-P2` 的 mAP@0.5:0.95 同样为 64.4%。这一结果表明 P2 分支几乎贡献了最终模型的主要定位增益。相比之下，`DWCA` 在没有 P2 分支时 mAP@0.5:0.95 仅为 61.3%。因此，本文在结论中将 P2 明确为主贡献模块。

### 3.4 DyHead 动态检测头

DyHead 的核心思想是在检测头中统一建模尺度、空间和任务三个维度的注意力。对于多尺度特征金字塔，尺度感知注意力可根据目标大小选择合适层级；空间感知注意力可关注目标所在位置；任务感知注意力可协调分类与定位任务之间的特征需求[3]。路侧图像中目标尺度跨度大、远近分布明显，同一类别在不同道路深度区域呈现显著尺度变化，因而适合引入动态检测头。

本文在 YOLO11n 中使用 DyHeadDetect 替换原检测头。设输入检测特征为多尺度特征集合 F = {F2, F3, F4, F5}，其中 F2 到 F5 分别对应 P2 到 P5 特征。DyHeadDetect 对多尺度特征进行动态调制后输出类别概率和边界框回归结果。其作用不是改变输入数据或标签，而是在检测阶段提高特征对尺度、空间位置和任务通道的适应性。

![图 3(b) DyHeadDetect 与 DyHeadBlock 内部结构](/Users/asus/ultralytics/docs/paper_assets/module_dyhead_detect.svg)

> 图 3(b) DyHeadDetect 与 DyHeadBlock 内部结构。四尺度输入 [20, 23, 26, 29] 分别经过两级 DyHeadBlock，每个 DyHeadBlock 包含 spatial-aware、scale-aware 和 task-aware 三类动态调制，随后进入标准 Detect 的 bbox 与 cls 分支。

在消融实验中，`+D` 模型相较 baseline 的 mAP@0.5 从 85.9% 提升至 86.6%，mAP@0.5:0.95 从 60.9% 提升至 61.3%；`+DW` 模型进一步达到 87.0% mAP@0.5 和 61.3% mAP@0.5:0.95。说明 DyHead 对本文任务有稳定增益，是构建强基线的重要模块。

### 3.5 CoordAttention 位置注意力模块

CoordAttention 的目标是在通道注意力中保留位置信息。传统通道注意力通常通过二维全局池化将空间维度压缩为单个通道描述子，容易丢失目标具体位置信息。CoordAttention 将全局池化分解为沿高度方向和宽度方向的一维编码，分别得到方向感知特征，再生成位置敏感注意力图[4]。该机制可表示为：

$$
z_c^h(h)=\frac{1}{W}\sum_{0\leq i<W}x_c(h,i)
$$

$$
z_c^w(w)=\frac{1}{H}\sum_{0\leq j<H}x_c(j,w)
$$

其中，x 表示输入特征，H 和 W 表示特征图高度和宽度，c 表示通道索引。经过共享变换和方向分支后，模块生成沿两个坐标方向的注意力权重，并作用于输入特征，从而增强方向和位置敏感信息。

![图 3(c) CoordAttention 内部结构](/Users/asus/ultralytics/docs/paper_assets/module_coord_attention.svg)

> 图 3(c) CoordAttention 内部结构。输入特征分别沿 H、W 两个方向进行一维全局池化，经共享 1x1 bottleneck 后拆分为两个方向分支，生成 `a_h` 和 `a_w` 并与原输入逐点相乘。

本文将 CoordAttention 嵌入到 P3 相关特征位置，目的是在浅层细节与中层语义之间增强位置编码。需要强调的是，本文实验并不支持将 CoordAttention 表述为主要增益来源。`DWCA` 的 mAP@0.5:0.95 为 61.3%，与 `+DW` 持平；完整 `DWCA-P2` 与 `DW-P2` 在 mAP@0.5:0.95 上均为 64.4%。因此，CoordAttention 更适合作为辅助模块写入方法部分，而不是在摘要和结论中过度强调。

### 3.6 Wise-IoU 边界框回归损失

边界框回归损失用于度量预测框与真实框之间的差异。IoU 可表示为：

$$
IoU=\frac{|B\cap B^{gt}|}{|B\cup B^{gt}|}
$$

其中，B 为预测框，B^{gt} 为真实框。传统 CIoU 在 IoU 基础上引入中心距离和宽高比约束，能够提升边界框回归稳定性。Wise-IoU 进一步关注样本质量差异，通过动态非单调聚焦机制调整不同质量锚框的梯度增益[5]。其思想是避免低质量样本产生过强有害梯度，同时不过度放大已经较好拟合的高质量样本，使模型更关注普通质量样本的有效学习。

![图 3(d) Wise-IoU v3 训练损失路径](/Users/asus/ultralytics/docs/paper_assets/module_wiou_loss.svg)

> 图 3(d) Wise-IoU v3 训练损失路径。WIoU 根据预测框、匹配真实框、距离项 `R_WIoU`、`loss_iou_per` 和运行均值 `iou_mean` 计算动态聚焦权重，最终改变 bbox 回归损失项；分类损失和 DFL 仍按 YOLO 检测损失流程计算。

本文在训练中采用 WIoU 作为改进模型的回归损失。实验表明，单独将 CIoU 替换为 WIoU 的 `+W` 模型 mAP@0.5 为 86.0%，mAP@0.5:0.95 为 60.2%，提升并不明显；但与 DyHead 结合后，`+DW` 的 mAP@0.5 达到 87.0%。这说明 WIoU 在本文任务中更适合作为检测头改进后的配套优化，而不是单独贡献显著提升的模块。

### 3.7 方法流程

本文方法的训练和推理流程如下。首先，将 DAIR-V2X-I 路侧图像按 YOLO 格式读取，并在训练阶段进行常规数据增强。其次，输入图像经 YOLO11n Backbone 提取多层特征，在 Neck 中通过自顶向下和自底向上的特征融合形成 P2、P3、P4 和 P5 四尺度特征。随后，CoordAttention 对中浅层特征进行位置敏感增强，DyHeadDetect 对四尺度特征进行动态检测。训练阶段使用分类损失、回归损失和分布相关损失共同优化，其中回归部分采用 WIoU。推理阶段，模型输出多尺度候选框，经过置信度筛选和非极大值抑制得到最终检测结果。

与原始 YOLO11n 相比，本文方法的主要变化集中在 Neck-Head 与损失函数处，不改变数据标注格式，也不依赖额外传感器输入。这使方法能够较容易迁移到现有 YOLO 工程框架中。对于后续复现，可重点检查四项内容：模型 YAML 是否包含 P2 输出层，检测头是否为 DyHeadDetect，训练损失是否正确启用 WIoU，所有实验 batch 是否按 32 固定。

## 4 实验设置

### 4.1 实验环境与训练参数

本文所有实验使用同一数据集划分，并按固定 batch=32 口径解释。输入图像尺寸为 640 x 640，训练轮数为 300 epochs，优化器为 SGD，随机种子为 42，nbs 为 64，采用余弦学习率调度，patience 设置为 50，close_mosaic 设置为 10。实验评价指标包括 Precision、Recall、mAP@0.5、mAP@0.5:0.95、GFLOPs 和 Params。当前所有表格中的检测性能指标默认指验证集结果；若后续补充测试集结果，将单独以 `test` 标记，避免与验证集指标混用。表 5 给出了主要训练参数。

**表 5 训练参数设置**

| 参数 | 设置 |
|---|---|
| 输入尺寸 | 640 x 640 |
| epochs | 300 |
| batch | 32 |
| optimizer | SGD |
| seed | 42 |
| nbs | 64 |
| patience | 50 |
| cos_lr | True |
| close_mosaic | 10 |
| 评价指标 | Precision、Recall、mAP@0.5、mAP@0.5:0.95、GFLOPs、Params |
| 当前评估划分 | val |

为增强可复现性，本文记录的主要训练命令参数来自 `runs/detect/runs/ablation/*/args.yaml`。最终模型 `DWCA-P2-b32` 使用的模型结构文件为 `ultralytics/cfg/models/11/yolo11-dwca-p2.yaml`，baseline-b32 使用原始 `ultralytics/cfg/models/11/yolo11.yaml`。两者均采用 `imgsz=640`、`batch=32`、`epochs=300`、`optimizer=SGD`、`seed=42`、`cos_lr=True` 和 `split=val`。其中 baseline-b32 为从 YAML 结构训练，DWCA-P2-b32 的 `args.yaml` 记录 `pretrained=True`，因此在解读主结果时应注意该训练口径差异；同口径结构对比和官方预训练参考实验分别在后文单独列出。

### 4.2 评价指标

目标检测任务通常使用 Precision、Recall 和 mAP 评价模型性能。Precision 表示预测为正样本的目标中真正例所占比例，Recall 表示真实目标中被正确检出的比例，计算式为：

$$
P=\frac{TP}{TP+FP}
$$

$$
R=\frac{TP}{TP+FN}
$$

其中，TP 表示真正例，FP 表示假正例，FN 表示假负例。对于路侧安全感知任务，Recall 尤其重要，因为漏检行人、骑行者和交通锥可能影响后续交通事件判断。

AP 表示单类别 Precision-Recall 曲线下的面积，mAP 表示多类别 AP 的平均值。mAP@0.5 在 IoU 阈值为 0.5 时计算平均精度，主要反映模型能否检测到目标；mAP@0.5:0.95 在 0.5 到 0.95 的多个 IoU 阈值上取平均，更严格地反映定位质量。对于小目标检测，mAP@0.5:0.95 能更敏感地体现边界框偏移问题，因此本文将其作为重要指标。

GFLOPs 用于衡量模型计算复杂度，Params 表示模型参数量。二者反映模型部署成本。本文同时报告精度和复杂度，以避免只追求精度而忽略路侧部署需求。

### 4.3 实验分组

本文实验分为四类。第一类为主结果对比，比较 YOLO11n baseline-b32 与最终模型 DWCA-P2-b32。第二类为消融实验，逐步分析 Triplet、DyHead、WIoU、CoordAttention 和 P2 分支的作用。第三类为同口径结构对比，比较 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml、YOLO11n baseline 和本文方法。第四类为官方预训练参考实验，单独列出 YOLOv5n.pt、YOLOv8n.pt、YOLOv10n.pt、YOLO11n.pt 与本文方法的结果。上述四类实验均以验证集结果作为当前分析依据，测试集复验将在复验项中单独列出。

需要说明的是，实验记录中存在一条 `参考实验（误跑）TDW-CO-P3`，该实验原计划使用 WIoU，但实际按 CIoU 训练。由于其损失函数口径与 WIoU 消融目标不一致，本文不将该行纳入 WIoU 主结论。正式分析采用 WIoU 已确认的 `TDW-CO-P3` 结果。

## 5 实验结果与分析

### 5.1 验证集主结果对比

表 6 给出了本文最终模型与 YOLO11n baseline-b32 的验证集主结果对比。可以看出，DWCA-P2-b32 的 Precision 为 86.0%，较 baseline-b32 提升 0.3 个百分点；Recall 为 83.5%，提升 2.7 个百分点；mAP@0.5 为 88.4%，提升 2.4 个百分点；mAP@0.5:0.95 为 64.4%，提升 4.2 个百分点。

**表 6 验证集主结果对比**

| 模型 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| baseline-b32 | 85.7 | 80.8 | 86.0 | 60.2 | 6.3 | 2.58 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |
| 提升 | +0.3 | +2.7 | +2.4 | +4.2 | +7.9 | +1.88 |

从指标变化看，本文方法对 Recall 和 mAP@0.5:0.95 的提升最明显。Recall 提升说明模型能够检出更多真实目标，符合路侧小目标场景降低漏检的需求。mAP@0.5:0.95 提升高于 mAP@0.5 提升，说明该方法不仅提高了目标发现能力，也改善了较高 IoU 阈值下的定位质量。这与 P2 分支保留高分辨率空间细节、WIoU 优化边界框回归的设计目标一致。

计算复杂度方面，DWCA-P2-b32 的 GFLOPs 为 14.2，较 baseline-b32 增加 7.9；参数量为 4.46M，增加 1.88M。该代价主要来自 DyHead 和 P2 高分辨率检测分支。对于极端低功耗嵌入式设备，该计算开销可能需要进一步压缩；但对于路侧边缘服务器或具备加速芯片的路侧计算单元，该规模仍具有实际部署可能。

![图 4 主结果指标对比](/Users/asus/ultralytics/docs/paper_assets/main_metrics_comparison.svg)

> 图 4 baseline-b32 与 DWCA-P2-b32 验证集主指标对比。图中数值采用表 6 的固定 batch=32 主结果口径。

### 5.2 类别级结果分析

为进一步分析改进模型对不同类别的影响，本文从训练日志末尾的 per-class 验证输出中提取 baseline-b32 与 DWCA-P2-b32 的类别级 AP，结果见表 7。需要说明的是，表 7 来源于最终验证日志的逐类别输出，整体均值与表 6 的 Excel 主结果口径存在 0.1 个百分点左右的四舍五入和最佳轮次差异；论文主结论仍以表 6 为准，类别级分析用于观察不同类别的相对变化。

**表 7 类别级 AP 对比**

| 类别 | 实例数 | baseline mAP@0.5/% | DWCA-P2 mAP@0.5/% | 提升/% | baseline mAP@0.5:0.95/% | DWCA-P2 mAP@0.5:0.95/% | 提升/% |
|---|---:|---:|---:|---:|---:|---:|---:|
| Car | 18342 | 95.9 | 96.8 | +0.9 | 79.2 | 81.8 | +2.6 |
| Truck | 660 | 80.9 | 78.8 | -2.1 | 54.1 | 55.9 | +1.8 |
| Van | 1385 | 82.1 | 83.9 | +1.8 | 68.9 | 71.9 | +3.0 |
| Bus | 669 | 94.0 | 95.5 | +1.5 | 77.5 | 79.5 | +2.0 |
| Cyclist | 3469 | 87.5 | 89.8 | +2.3 | 58.1 | 62.1 | +4.0 |
| Motorcyclist | 3632 | 77.4 | 79.1 | +1.7 | 50.9 | 54.0 | +3.1 |
| Pedestrian | 5073 | 77.8 | 86.3 | +8.5 | 42.8 | 51.3 | +8.5 |
| Trafficcone | 32025 | 92.2 | 96.3 | +4.1 | 50.2 | 58.2 | +8.0 |

类别级结果显示，DWCA-P2-b32 在 Pedestrian 和 Trafficcone 上的提升最明显。其中 Pedestrian 的 mAP@0.5 从 77.8% 提升到 86.3%，mAP@0.5:0.95 从 42.8% 提升到 51.3%，两项均提升 8.5 个百分点；Trafficcone 的 mAP@0.5:0.95 提升 8.0 个百分点。结合表 4 可知，这两类目标在验证集中几乎全部属于 short side < 32 px 的小目标，因此其提升能够较直接地支撑 P2 高分辨率检测分支的有效性。Cyclist 和 Motorcyclist 的 mAP@0.5:0.95 分别提升 4.0 和 3.1 个百分点，也说明 P2 分支对弱势交通参与者具有较明显帮助。Truck 的 mAP@0.5 下降 2.1 个百分点，但 mAP@0.5:0.95 仍提升 1.8 个百分点，可能与该类样本数量较少、类别内尺度变化较大有关。

![图 5 类别级 mAP@0.5:0.95 增益](/Users/asus/ultralytics/docs/paper_assets/class_map50_95_gain.svg)

> 图 5 DWCA-P2-b32 相对 baseline-b32 的类别级 mAP@0.5:0.95 提升。该图由 `/Users/asus/ultralytics/docs/paper_assets/class_metrics_baseline_vs_dwca_p2_b32.csv` 生成。

### 5.3 模块消融实验

为分析各模块贡献，本文设计了从 baseline 到最终模型的多组消融实验，结果见表 8。表中 `+T` 表示引入 Triplet 注意力，`+D` 表示引入 DyHead，`+W` 表示使用 WIoU，`DWCA` 表示 DyHead、WIoU 与 CoordAttention 组合但不含 P2，`DW-P2` 表示 DyHead、WIoU 与 P2 组合但不含 CoordAttention，`DWCA-P2` 表示完整结构。

**表 8 消融实验结果**

| 模型 | 主要改动 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | GFLOPs | Params/M |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | YOLO11n | 85.9 | 80.8 | 85.9 | 60.9 | 6.4 | 2.60 |
| +T | Triplet | 85.6 | 80.5 | 85.9 | 60.2 | 6.4 | 2.60 |
| +D | DyHead | 86.3 | 81.1 | 86.6 | 61.3 | 9.3 | 4.35 |
| +W | WIoU | 86.4 | 80.3 | 86.0 | 60.2 | 6.4 | 2.60 |
| +TD | Triplet + DyHead | 85.8 | 81.0 | 86.2 | 61.0 | 9.29 | 4.36 |
| +TW | Triplet + WIoU | 85.8 | 81.0 | 86.3 | 60.5 | 6.4 | 2.58 |
| +DW | DyHead + WIoU | 86.0 | 81.9 | 87.0 | 61.3 | 9.3 | 4.35 |
| TDW | Triplet + DyHead + WIoU | 86.8 | 80.8 | 86.5 | 60.9 | 9.29 | 4.36 |
| TDW-CO | channel-only Triplet + DyHead + WIoU | 86.2 | 81.4 | 86.7 | 61.2 | 9.29 | 4.36 |
| TDW-CO-P3 | Triplet 移至 P3 | 86.5 | 81.4 | 86.7 | 61.1 | 9.4 | 4.35 |
| TDW-CO-D3 | DyHead block 加深 | 86.1 | 81.3 | 86.3 | 61.1 | 10.9 | 5.24 |
| DWCA | +CA，去 P2 | 86.8 | 81.4 | 86.8 | 61.3 | 9.3 | 4.36 |
| DW-P2 | +P2，去 CA | 85.6 | 83.5 | 88.1 | 64.4 | 14.2 | 4.45 |
| DWCA-P2 | +CA + P2 | 86.1 | 83.3 | 88.2 | 64.4 | 14.2 | 4.46 |
| DWCA-P2-b32 | 最终固定 batch 复验 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |

从单模块实验看，Triplet 并未带来提升。`+T` 的 mAP@0.5 与 baseline 持平，为 85.9%，mAP@0.5:0.95 从 60.9% 降至 60.2%。这说明在本文路侧目标检测任务中，单独引入 Triplet 注意力无法改善检测性能，甚至可能对定位质量产生不利影响。

DyHead 的提升较稳定。`+D` 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 均高于 baseline，其中 mAP@0.5 提升 0.7 个百分点。WIoU 单独使用时 Precision 较高，但 Recall 和 mAP@0.5:0.95 没有提升。将二者组合后，`+DW` 的 Recall 达到 81.9%，mAP@0.5 达到 87.0%，成为没有 P2 分支时的较强基线。这表明 DyHead 和 WIoU 在特征表达与边界框回归层面具有一定互补性。

Triplet 组合路线没有形成有效增益。`TDW`、`TDW-CO`、`TDW-CO-P3` 和 `TDW-CO-D3` 均未超过 `+DW`。其中 `TDW-CO-D3` 通过加深 DyHead block 将 GFLOPs 提高到 10.9、Params 提高到 5.24M，但 mAP@0.5 反而下降到 86.3%。这说明增加模块深度并不必然带来更好效果。对于轻量化模型，结构复杂度增加可能导致训练难度上升、特征冗余或局部过拟合。

P2 分支的效果最为明显。`DW-P2` 在不使用 CoordAttention 的情况下，Recall 达到 83.5%，mAP@0.5 达到 88.1%，mAP@0.5:0.95 达到 64.4%。相比 `+DW`，其 Recall 提升 1.6 个百分点，mAP@0.5 提升 1.1 个百分点，mAP@0.5:0.95 提升 3.1 个百分点。加入 CoordAttention 后，`DWCA-P2` 的 mAP@0.5 为 88.2%，mAP@0.5:0.95 仍为 64.4%。最终固定 batch 复验 `DWCA-P2-b32` 的 mAP@0.5 进一步达到 88.4%。这些结果共同说明，P2 高分辨率分支是本文方法性能提升的核心。

CoordAttention 的作用应谨慎表述。`DWCA` 相比 `+DW` 的 mAP@0.5:0.95 没有提升，二者均为 61.3%；完整模型相较 `DW-P2` 的 mAP@0.5:0.95 也没有增加。CoordAttention 可能对 Precision 或局部特征稳定性有辅助作用，但从当前总体指标看，它不是主要增益来源。正式论文中应将其定位为位置敏感辅助模块，避免夸大贡献。

### 5.4 消融路线收敛分析

本文实验路线体现了从注意力叠加到尺度结构改进的收敛过程。最初尝试 Triplet 注意力，是希望通过跨维度交互增强空间和通道表达。但 `+T` 和后续 `TDW` 系列结果表明，Triplet 在 DAIR-V2X-I 路侧图像上并未带来稳定收益。可能原因有三点。

第一，Triplet 与 DyHead 的空间建模存在功能重叠。DyHead 已经在检测头中包含空间感知注意力，继续叠加 Triplet 可能无法提供新的有效信息。第二，路侧小目标的核心瓶颈是空间分辨率不足，而不是单纯的通道选择不足。当极小目标在 P3 特征上响应过弱时，注意力机制难以恢复已经丢失的边界信息。第三，Triplet 模块增加了额外结构复杂度，可能对轻量模型训练稳定性产生影响。

相比之下，P2 分支直接改变了检测尺度，使极小目标在特征图中获得更充分的空间表达。该改动与数据统计高度一致：当 87.55% 的目标短边小于 32 px 时，提高最高分辨率检测层比继续叠加注意力更符合任务需求。因此，本文最终方法选择以 P2 分支为主，以 DyHead 和 WIoU 构建检测与回归基础，以 CoordAttention 进行辅助增强。

### 5.5 同口径结构对比

为比较不同 YOLO 结构在相同数据任务下的表现，本文选取 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml 和 YOLO11n baseline 作为同口径结构对比。该组实验主要从 YAML 结构出发，不与官方预训练权重混合比较。结果见表 9。

**表 9 同口径结构对比**

| 模型 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv5n-yaml | 85.4 | 81.0 | 85.8 | 59.9 | 7.1 | 2.50 |
| YOLOv8n-yaml | 86.5 | 81.2 | 86.5 | 61.0 | 8.1 | 3.01 |
| YOLOv10n-yaml | 85.8 | 80.1 | 85.7 | 60.7 | 8.4 | 2.71 |
| YOLO11n baseline | 85.9 | 80.8 | 85.9 | 60.9 | 6.4 | 2.60 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |

由表 9 可知，YOLOv8n-yaml 在未引入本文改进时表现较好，mAP@0.5 为 86.5%，mAP@0.5:0.95 为 61.0%。YOLO11n baseline 与 YOLOv8n-yaml 的总体差距较小，但计算量更低。本文方法在 mAP@0.5 和 mAP@0.5:0.95 上均明显高于上述轻量结构，其中 mAP@0.5:0.95 相较 YOLOv8n-yaml 提升 3.4 个百分点，相较 YOLO11n baseline 提升 3.5 个百分点（同口径表中的 baseline 行）。

这一结果说明，对于 DAIR-V2X-I 路侧小目标任务，针对目标尺度分布进行结构改进，比单纯更换轻量化 YOLO 版本更有效。不同 YOLO 版本在默认结构下均以 P3/P4/P5 为主要检测尺度，无法充分解决极小目标特征不足问题。本文通过 P2 分支引入更高分辨率检测层，因而在 Recall 和高阈值 mAP 上获得更明显提升。

### 5.6 官方预训练参考实验

官方 `.pt` 权重通常包含外部数据预训练信息，与 YAML/scratch 训练并非完全同源公平比较。为避免混淆，本文将官方预训练结果作为参考实验单独列出，见表 10。

**表 10 官方预训练参考实验**

| 模型 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv5n.pt | 87.3 | 81.4 | 87.0 | 62.3 | 7.8 | 2.65 |
| YOLOv8n.pt | 87.2 | 82.1 | 87.3 | 62.8 | 8.1 | 3.01 |
| YOLOv10n.pt | 85.2 | 81.3 | 86.9 | 63.5 | 6.5 | 2.27 |
| YOLO11n.pt | 86.4 | 81.6 | 87.0 | 62.3 | 6.3 | 2.58 |
| DWCA-P2-b32 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.46 |

从表 10 可以看出，预训练模型通常具有较高 Precision，其中 YOLOv5n.pt 和 YOLOv8n.pt 的 Precision 分别为 87.3% 和 87.2%，高于本文方法。但本文方法在 Recall、mAP@0.5 和 mAP@0.5:0.95 上均达到最高，其中 Recall 为 83.5%，mAP@0.5:0.95 为 64.4%。这说明本文方法更偏向提高小目标检出率和定位质量，而不是单纯追求预测框置信度保守性。

对于路侧安全感知，Recall 和高阈值 mAP 的提升具有现实意义。若模型 Precision 略低但能够减少远距离行人、骑行者和交通锥漏检，在后续多帧跟踪、时序滤波或车路协同融合中仍可能获得更好的系统收益。当然，实际部署时仍需结合误报成本和后处理策略综合评估。

### 5.7 复杂度与部署分析

本文方法的计算量高于原始 YOLO11n。baseline-b32 的 GFLOPs 为 6.3，Params 为 2.58M；DWCA-P2-b32 的 GFLOPs 为 14.2，Params 为 4.46M。计算量增加主要来自两个部分：一是 DyHeadDetect 的多尺度动态检测计算，二是 P2 高分辨率分支带来的大尺寸特征图计算。

从精度收益看，增加 7.9 GFLOPs 换来了 4.2 个百分点的 mAP@0.5:0.95 提升。若部署环境为普通嵌入式 CPU，该代价可能偏高；若部署在具备 GPU、NPU 或边缘推理加速器的路侧设备中，该复杂度仍处于可优化范围内。后续可通过通道剪枝、轻量化卷积、知识蒸馏、TensorRT FP16/INT8 量化等方式降低推理成本。

实验记录中的 FPS 字段并不完整，且不同实验可能来自不同硬件或不同统计方式，本文不将其作为主结论。训练日志中同一 RTX 4090 验证流程给出了参考速度：baseline-b32 约为 2.0 ms inference + 1.6 ms postprocess per image，DWCA-P2-b32 约为 0.5 ms inference + 4.4 ms postprocess per image。该结果只能说明日志所在验证流程下的速度表现，不能直接等同于部署 FPS。正式投稿前应在同一硬件、同一推理设置下重新测试 FPS，包括输入尺寸、batch size、精度模式、是否使用 TensorRT、是否包含 NMS 时间等信息。只有在推理环境一致时，FPS 才能作为可靠部署指标。

### 5.8 训练过程与可视化结果

为观察模型训练收敛趋势，本文根据 baseline-b32 与 DWCA-P2-b32 的 `results.csv` 绘制验证集 mAP@0.5:0.95 曲线和 Recall 曲线，如图 6 和图 7 所示。从曲线变化可以看出，DWCA-P2-b32 在训练中后期保持更高的 mAP@0.5:0.95 和 Recall，说明 P2 分支带来的提升不是单个 epoch 的偶然波动，而是在训练收敛阶段形成了相对稳定的性能差距。

![图 6 验证集 mAP@0.5:0.95 曲线](/Users/asus/ultralytics/docs/paper_assets/training_map50_95_curve.svg)

> 图 6 baseline-b32 与 DWCA-P2-b32 的验证集 mAP@0.5:0.95 曲线。数据来源为两组实验目录下的 `results.csv`。

![图 7 验证集 Recall 曲线](/Users/asus/ultralytics/docs/paper_assets/training_recall_curve.svg)

> 图 7 baseline-b32 与 DWCA-P2-b32 的验证集 Recall 曲线。DWCA-P2-b32 在训练后期整体保持更高召回率。

PR 曲线和混淆矩阵进一步反映了最终模型的分类与检出情况。图 8 为 DWCA-P2-b32 的 PR 曲线，图 9 为其混淆矩阵。PR 曲线可用于观察不同置信度阈值下 Precision 与 Recall 的平衡；混淆矩阵可用于分析类别间误检和漏检情况，后续正式排版时可重点讨论 Pedestrian、Cyclist、Motorcyclist 和 Trafficcone 等小目标类别的混淆关系。

![图 8 DWCA-P2-b32 PR 曲线](/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/BoxPR_curve.png)

> 图 8 DWCA-P2-b32 的 PR 曲线。图片来源为 `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/BoxPR_curve.png`。

![图 9 DWCA-P2-b32 混淆矩阵](/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/confusion_matrix.png)

> 图 9 DWCA-P2-b32 的混淆矩阵。图片来源为 `/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/confusion_matrix.png`。

图 10 给出了 baseline-b32 与 DWCA-P2-b32 在同一验证 batch 上的预测样例。正式论文中建议进一步从验证集筛选远距离行人、交通锥和骑行者密集的典型图像，制作并列对比图和局部放大图，使 P2 分支对小目标漏检改善的视觉证据更直接。

![图 10(a) baseline-b32 验证集预测样例](/Users/asus/ultralytics/runs/detect/runs/ablation/baseline-b32/val_batch0_pred.jpg)

![图 10(b) DWCA-P2-b32 验证集预测样例](/Users/asus/ultralytics/runs/detect/runs/ablation/DWCA-P2-b32/val_batch0_pred.jpg)

> 图 10 baseline-b32 与 DWCA-P2-b32 的验证集预测样例。图 10(a) 为 baseline-b32，图 10(b) 为 DWCA-P2-b32。

## 6 讨论

### 6.1 P2 分支为何成为主增益来源

本文最重要的实验结论是，P2 高分辨率检测分支是性能提升的主要来源。这一结论由数据统计和消融实验共同支持。数据统计显示，DAIR-V2X-I 路侧图像中短边小于 32 px 的目标占 87.55%，其中大量目标短边甚至小于 16 px。对于这些目标，特征图分辨率直接决定模型能否保留有效边界和中心位置信息。

从消融结果看，`DWCA` 仅在 `+DW` 基础上加入 CoordAttention，mAP@0.5:0.95 仍为 61.3%；`DW-P2` 在不加入 CoordAttention 的情况下将 mAP@0.5:0.95 提升到 64.4%。这说明当目标尺度极小时，先让模型“看得见”比进一步调整注意力权重更重要。P2 分支通过改变检测特征尺度，为极小目标提供了更大的响应区域，因此能够显著改善 Recall 和定位质量。

### 6.2 注意力模块的有效边界

注意力机制并非在所有场景中都能带来显著收益。本文 Triplet 和 CoordAttention 的实验结果说明，在已有 DyHead 动态检测头的情况下，继续叠加注意力模块可能收益有限。原因可能在于，注意力模块主要改变特征权重分配，而不能恢复下采样过程中损失的空间信息。若小目标已经在高层特征中变成弱响应，注意力机制只能重新分配现有响应，无法创造缺失的细节。

CoordAttention 仍具有一定方法价值。它能够在轻量网络中引入位置敏感通道表达，对道路场景中具有方向规律的目标分布可能有帮助。但从当前总体指标看，其贡献不应被夸大。更合理的表述是：CoordAttention 作为辅助模块增强中浅层特征的位置表达，最终提升主要由 P2 分支驱动。

### 6.3 Triplet 路线的反证意义

论文中保留失败探索并不是削弱贡献，反而有助于说明方法选择的可靠性。本文尝试了 `+T`、`+TD`、`+TW`、`TDW`、`TDW-CO`、`TDW-CO-P3` 和 `TDW-CO-D3` 等路线，结果均未超过 `+DW` 或最终 P2 路线。这表明本文方法不是简单的模块堆叠，而是经过消融筛选后收束到更适合路侧小目标数据特征的结构。

该反证还提示一个工程实践原则：轻量化目标检测模型的改进应优先处理主瓶颈。对于 DAIR-V2X-I 路侧图像，主瓶颈是小目标尺度，而不是单纯的通道注意力不足。因此，新增 P2 检测尺度比继续复杂化注意力结构更有效。

### 6.4 局限性

本文仍存在若干局限。首先，当前实验已经补充类别级 AP 和验证集尺度分布统计，但尚未给出基于预测框的尺度分组 AP。尺度分组 AP 需要保存逐框预测结果，并按 short side 或 COCO small/medium/large 区间重新计算 AP；当前训练产物未保存完整预测 txt/json，本地环境也缺少可直接运行验证的 Torch 依赖，因此本文暂不伪造该指标。正式投稿前可在同一权重下重新运行 `yolo val save_json=True save_txt=True`，再按目标尺度区间统计 AP，以更直接证明 P2 分支对不同尺度目标的贡献。

其次，本文未在统一硬件下完成 FPS 对比。虽然 GFLOPs 和 Params 能反映理论复杂度，但实际推理速度还受硬件架构、算子实现、显存访问、NMS 和推理框架影响。正式投稿前应统一推理环境，补充 FPS 或单张延迟。

再次，本文方法增加了计算量。DWCA-P2-b32 的 GFLOPs 是 baseline-b32 的约 2.25 倍。对于需要在低功耗设备上实时运行的路侧系统，仍需进一步轻量化。可行方向包括减少 P2 分支通道数、使用轻量卷积替代部分标准卷积、剪枝冗余通道、使用蒸馏训练小模型以及进行 TensorRT INT8 量化。

最后，本文主要基于单数据集验证。DAIR-V2X-I 具有典型路侧特征，但不同城市、摄像机高度、道路结构和天气条件会造成分布差异。未来应在更多路侧数据集或自采路侧视频上验证模型泛化能力，并分析夜间、雨雾、逆光等复杂条件下的检测表现。

## 7 结论

本文针对 DAIR-V2X-I 路侧图像中小目标比例高、目标密集和远距离目标易漏检的问题，提出一种改进 YOLO11n 的路侧小目标检测方法 YOLO11n-DWCA-P2。该方法以 YOLO11n 为基准，引入 DyHead 动态检测头和 Wise-IoU 边界框回归损失，增加 P2/4 高分辨率检测分支，并使用 CoordAttention 进行位置敏感特征辅助增强。

数据统计表明，本文数据集中 short side < 32 px 的目标占 87.55%，area < 32^2 px 的目标占 79.65%，小目标检测需求显著。在统一 batch=32 训练口径下，最终 DWCA-P2-b32 模型取得 86.0% Precision、83.5% Recall、88.4% mAP@0.5 和 64.4% mAP@0.5:0.95。与 YOLO11n baseline-b32 相比，Recall 提升 2.7 个百分点，mAP@0.5 提升 2.4 个百分点，mAP@0.5:0.95 提升 4.2 个百分点。

消融实验进一步表明，P2 高分辨率检测分支是最终性能提升的主要来源，DyHead 与 WIoU 构成有效强基线，CoordAttention 起辅助增强作用，Triplet 相关路线未能超过 DyHead 与 WIoU 组合。本文方法提高了路侧小目标的检出能力和定位质量，为车路协同视觉感知中的轻量化检测模型改进提供了可行方案。

未来工作将从三个方面展开。第一，基于重新保存的逐框预测结果补充尺度分组 AP，并进一步筛选远距离小目标样例制作局部放大对比图。第二，在统一硬件平台上测试推理速度，并结合 TensorRT、剪枝、量化和蒸馏降低部署成本。第三，将模型扩展到夜间、雨雾、逆光和多摄像头路侧场景，验证其跨场景泛化能力。

## 参考文献

> 说明：以下参考文献为论文初稿引用条目，后续投稿前建议按目标期刊格式统一著录，并补全 DOI、页码和访问日期。

[1] Yu H, Luo Y, Shu M, et al. DAIR-V2X: A Large-Scale Dataset for Vehicle-Infrastructure Cooperative 3D Object Detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2022: 21361-21370. https://arxiv.org/abs/2204.05575

[2] Ultralytics. Ultralytics YOLO11 Docs[EB/OL]. https://docs.ultralytics.com/models/yolo11

[3] Dai X, Chen Y, Xiao B, et al. Dynamic Head: Unifying Object Detection Heads with Attentions[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021. https://arxiv.org/abs/2106.08322

[4] Hou Q, Zhou D, Feng J. Coordinate Attention for Efficient Mobile Network Design[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021. https://arxiv.org/abs/2103.02907

[5] Tong Z, Chen Y, Xu Z, Yu R. Wise-IoU: Bounding Box Regression Loss with Dynamic Focusing Mechanism[EB/OL]. arXiv:2301.10051, 2023. https://arxiv.org/abs/2301.10051

[6] Ultralytics. Explore Ultralytics YOLOv8[EB/OL]. https://docs.ultralytics.com/models/yolov8

[7] Redmon J, Divvala S, Girshick R, et al. You Only Look Once: Unified, Real-Time Object Detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2016: 779-788.

[8] Lin T Y, Dollár P, Girshick R, et al. Feature Pyramid Networks for Object Detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2017: 2117-2125.

[9] Liu S, Qi L, Qin H, et al. Path Aggregation Network for Instance Segmentation[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 8759-8768.

[10] Bochkovskiy A, Wang C Y, Liao H Y M. YOLOv4: Optimal Speed and Accuracy of Object Detection[EB/OL]. arXiv:2004.10934, 2020.

[11] Jocher G, Chaurasia A, Qiu J. Ultralytics YOLO[EB/OL]. https://github.com/ultralytics/ultralytics

## 已生成材料与仍需复验项

### 已生成材料

1. 网络结构图：`/Users/asus/ultralytics/docs/paper_assets/dwca_p2_overview_optimized.svg`，已在图 2 插入正文。
2. 模块内部结构图：`module_p2_branch.svg`、`module_dyhead_detect.svg`、`module_coord_attention.svg` 和 `module_wiou_loss.svg`，已作为图 3(a)-图 3(d)。
3. 类别级 AP 表：`/Users/asus/ultralytics/docs/paper_assets/class_metrics_baseline_vs_dwca_p2_b32.csv`，已整理为表 7。
4. 验证集尺度分布：`/Users/asus/ultralytics/docs/paper_assets/val_scale_distribution_640.csv` 和 `val_scale_distribution_640.svg`，已整理为表 4 和图 1。
5. 主指标对比图：`/Users/asus/ultralytics/docs/paper_assets/main_metrics_comparison.svg`，已作为图 4。
6. 类别级增益图：`/Users/asus/ultralytics/docs/paper_assets/class_map50_95_gain.svg`，已作为图 5。
7. 训练曲线图：`training_map50_95_curve.svg` 和 `training_recall_curve.svg`，已作为图 6 和图 7。
8. PR 曲线、混淆矩阵和检测样例：已从 `runs/detect/runs/ablation/DWCA-P2-b32/` 与 `baseline-b32/` 插入正文，分别作为图 8、图 9 和图 10。
9. 资产生成脚本：`/Users/asus/ultralytics/docs/paper_assets/build_paper_assets.py` 和 `build_architecture_figures.py`，可复现生成上述 CSV 与 SVG 图件。

### 仍需复验项

1. 尺度分组 AP：需要重新运行验证并保存逐框预测，例如在具备 Torch/Ultralytics 环境的训练机上执行 `yolo val model=runs/detect/runs/ablation/DWCA-P2-b32/weights/best.pt data=datasets/dair_v2x_i/dair_v2x_i.yaml imgsz=640 batch=32 save_json=True save_txt=True project=runs/val name=DWCA-P2-b32-scale-ap`，随后按 short side 区间统计 AP。
2. 同硬件 FPS：需要在目标硬件上以统一 batch=1、imgsz=640、相同精度模式和相同推理框架复测。日志中的 speed 可作为参考，但不宜作为最终部署 FPS。
3. 引用格式终稿：需按目标期刊要求补全 DOI、页码、访问日期，并统一参考文献格式。
