# 路侧交通小目标检测DWCA-P2方法

刘华硕^1^，任洪娥^1^

（1. 东北林业大学 计算机与人工智能学院，哈尔滨 150040）

## 摘要

针对路侧图像远距离交通目标尺度小、密度高和背景干扰强导致轻量化 YOLO 漏检的问题，提出 YOLO11n-DWCA-P2 小目标检测方法。该方法以 YOLO11n 为基准，采用 Dynamic Head（DyHead）动态检测头和 Wise Intersection over Union v3（Wise-IoU v3）回归损失，增加 P2/4 高分辨率检测分支，将检测特征由 P3/P4/P5 扩展为 P2/P3/P4/P5，并用 Coordinate Attention（CoordAttention）增强浅中层位置敏感表达。训练与测速均采用统一设置，以降低训练口径和硬件差异对比较结果的影响。DAIR-V2X-I 统计显示，640 输入尺度下短边小于 32 像素和面积小于 32² 像素²的目标分别占 87.55% 和 79.65%。实验结果表明，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 86.0%、83.5%、88.4% 和 64.4%，较 baseline 分别提高 0.3、2.7、2.4 和 4.2 个百分点，RTX 4090 上达到 100.5 FPS。消融结果表明，P2 分支是 Recall 和 mAP@0.5:0.95 提升的主要来源，DyHead 和 Wise-IoU v3 的组合构成稳定正向基线，CoordAttention 主要体现在 Precision 和 mAP@0.5 的补充增益上。该方法提升了路侧小目标检出能力和定位质量，可为车路协同视觉感知中的轻量化检测模型设计提供参考。

**关键词**：路侧目标检测；车路协同；YOLO11n；小目标检测；DyHead；Wise-IoU；P2 检测分支

## YOLO11n-DWCA-P2 for Roadside Traffic Small Object Detection

LIU Huashuo^1^, REN Honge^1^

(1. College of Computer and Artificial Intelligence, Northeast Forestry University, Harbin 150040, China)

## Abstract

Roadside images contain distant traffic objects with small scales, high density and strong background interference, which can cause missed detections in lightweight YOLO models. YOLO11n-DWCA-P2 was proposed for roadside small object detection. Based on YOLO11n, the method adopted a Dynamic Head detection head and Wise Intersection over Union version 3 regression loss, added a P2/4 high-resolution detection branch to extend the detection features from P3/P4/P5 to P2/P3/P4/P5, and used Coordinate Attention to enhance shallow and mid-level position-sensitive representation. Statistics on DAIR-V2X-I showed that objects with a short side smaller than 32 pixels and objects with an area smaller than 32² pixel² accounted for 87.55% and 79.65%, respectively, at the 640 input scale. Experiments showed that DWCA-P2 achieved 86.0% Precision, 83.5% Recall, 88.4% mAP@0.5 and 64.4% mAP@0.5:0.95. Compared with baseline, the four metrics increased by 0.3, 2.7, 2.4 and 4.2 percentage points, respectively, and the model reached 100.5 FPS on an RTX 4090. Ablation results indicate that the P2 branch is the main source of recall and localization improvement, while Coordinate Attention provides complementary gains in precision-oriented metrics. The method improves detection and localization for small roadside objects.

**Keywords**: roadside object detection; vehicle-infrastructure cooperation; YOLO11n; small object detection; Dynamic Head; Wise Intersection over Union; P2 detection branch

## 0 引言

随着智能交通系统、协同自动驾驶和车路云一体化技术的发展，单车智能感知逐渐向车端、路端和云端协同感知演进。车载摄像机和激光雷达能够提供车辆自身周围的局部环境信息，但感知范围容易受到遮挡、视角和传感器安装位置限制。路侧感知设备通常部署在信号灯杆、道路横杆或高位监控点，具有较稳定的外参条件和更广的道路覆盖范围，能够从全局视角捕获交叉口、匝道、车道汇入区域等复杂交通场景中的车辆与弱势交通参与者。因此，路侧目标检测结果不仅可用于道路事件监测、交通流统计和安全预警，也可作为车路协同自动驾驶系统的重要环境输入。

路侧视觉感知并不是简单地将通用目标检测模型迁移到道路监控画面中。路侧摄像机通常具有较高安装位置和较大俯视角，道路纵深方向明显，远端目标在图像中呈现出极小尺度。行人、骑行者、摩托车、交通锥等目标本身物理尺寸较小，当其位于远距离区域时，经过图像缩放和网络下采样后往往仅保留少量像素。道路场景中的车辆、交通标志、车道线、护栏、树木阴影和路面纹理共同构成复杂背景，交通参与者之间还可能存在相互遮挡。这些因素使路侧目标检测具有小目标多、密集目标多、背景干扰强和类别分布不均衡等特征。

目标检测经历了从两阶段候选区域方法到单阶段实时检测方法的发展。Fast R-CNN、Faster R-CNN 等方法通过候选区域和区域特征分类提升检测精度[1-2]，SSD、RetinaNet 和 EfficientDet 则推动了单阶段检测、多尺度特征、密集预测和类别不均衡处理的发展[3-5]。YOLO 系列进一步强调端到端实时检测能力，因检测速度快、工程部署链路成熟，在智能交通、工业质检、农业检测和安防监控等场景中得到广泛应用[6-10]。Ultralytics YOLO11 在前序 YOLO 模型的基础上继续优化特征提取、检测效率和多任务支持能力，覆盖目标检测、实例分割、姿态估计、图像分类和旋转框检测等视觉任务[11]。其中 YOLO11n 是该系列中的轻量化版本，参数量和计算量较低，适合部署在边缘设备或对实时性要求较高的系统中。对于路侧感知任务，轻量化模型的效率优势具有现实意义，但有限的网络容量也使其更容易受到小目标信息损失的影响。

通用 YOLO 检测结构通常采用多尺度特征输出处理不同尺寸目标。以轻量化 YOLO11n 为例，其默认检测头主要使用 P3/P4/P5 三个尺度特征，对应输入图像的 1/8、1/16 和 1/32 下采样特征图。在常规目标检测任务中，P3 特征已经能够覆盖较多小目标；但在路侧图像中，当目标短边仅为数像素至十余像素时，1/8 下采样后的特征响应可能过于稀疏，边界和局部纹理信息难以被完整保留。若仅依靠深层语义特征，模型可能获得较好的类别判别能力，却无法准确定位小目标框，最终表现为漏检、定位偏移或高 IoU 阈值下 AP 下降。

为验证上述问题，本文对 DAIR-V2X-I 路侧图像数据集的 YOLO 标注进行统计。该数据集包含 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类道路交通目标。统计结果显示，在 640 输入尺度下，短边小于 32 像素的目标占 87.55%，短边小于 16 像素的目标占 68.60%，面积小于 32² 像素²的目标占 79.65%。其中 Trafficcone 的中位短边约为 4.2 像素，Pedestrian 的中位短边约为 9.0 像素，Cyclist 和 Motorcyclist 的中位短边也仅约为 14.4 像素和 15.6 像素。这一分布说明，本文任务的主要矛盾并非单纯提升大目标分类置信度，而是如何在轻量化网络中保留并利用高分辨率空间细节。

围绕小目标检测问题，已有研究通常从多尺度特征融合、注意力机制、检测头优化和边界框损失函数等方面改进模型。FPN、PAN 和 BiFPN 等多尺度融合结构能够将浅层细节与深层语义结合，提高不同尺度目标的表达能力[5,12-13]；SNIP 与切片辅助推理等方法从尺度归一化或保持局部高分辨率角度改善小目标检测[14-15]；注意力机制可增强关键区域或通道的响应，抑制背景噪声[16-19]；动态检测头能够根据尺度、空间位置和任务类型调整检测特征[20]；IoU 系列损失函数则直接影响边界框回归质量[21-23]。上述方向并非互相排斥，但在轻量化模型中盲目叠加模块可能带来冗余计算，也可能因功能重叠导致收益有限。因此，针对路侧小目标场景，需要通过实验确定真正有效的结构改进路径。

本文提出一种面向路侧小目标检测的改进 YOLO11n 方法，记为 YOLO11n-DWCA-P2。该方法首先将 YOLO11n 检测头替换为 DyHeadDetect，以动态建模尺度、空间和任务维度的检测特征；其次采用 Wise-IoU v3 作为边界框回归损失，改善样本质量差异下的定位学习；随后在 Neck-Head 部分增加 P2/4 高分辨率检测分支，使模型直接在更高分辨率特征图上检测极小目标；最后引入 CoordAttention 模块，在较浅层特征中嵌入坐标位置信息，提升位置敏感表达能力。

本文主要贡献如下。

1. 面向 DAIR-V2X-I 路侧图像的小目标密集特征，统计分析了数据集类别分布与目标尺度分布，说明该任务存在较强的高分辨率特征需求。
2. 提出 YOLO11n-DWCA-P2 检测方法，重点通过 P2 高分辨率分支将检测尺度由 P3/P4/P5 扩展为 P2/P3/P4/P5，并结合 DyHead、Wise-IoU v3 与 CoordAttention 形成面向路侧小目标的轻量化改进结构。
3. 在统一 batch=32 训练口径下完成系统消融实验，明确 DyHead 与 WIoU 的组合构成稳定正向基线，P2 分支是最终性能提升的主要来源，CoordAttention 为辅助增强模块，避免将改进效果简单归因于模块叠加。
4. 与 YOLOv5n、YOLOv8n、YOLOv10n、YOLO11n 等轻量化结构进行同口径从头训练对比，结果表明本文方法在 mAP@0.5 和 mAP@0.5:0.95 上取得更优表现。

## 1 相关工作

### 1.1 路侧目标检测与车路协同感知

车路协同感知旨在通过车端和路端传感器的信息互补，提高自动驾驶系统对复杂交通环境的理解能力。车端传感器具有跟随车辆移动、感知近车区域细节的优势，但在交叉口遮挡、远距离车辆汇入和大型车辆遮挡等场景中容易出现感知盲区。路侧传感器从固定高位观察道路，能够获取更稳定的道路全局视角，为车辆提供超视距信息和交通参与者分布状态。

DAIR-V2X 数据集为车路协同感知研究提供了真实场景数据基础。该数据集包含车端与路端多模态数据，覆盖城市道路、高速道路、交叉口和多种天气光照条件，并引入车辆-基础设施协同 3D 目标检测任务[24]。OPV2V、V2X-ViT 等研究进一步说明，车端与路端或车车协同信息能够缓解遮挡和视距限制，但协同感知质量仍依赖单视角检测器对基础目标的稳定识别[25-26]。本文使用 DAIR-V2X-I 路侧单目图像构建 YOLO 检测任务，关注二维图像下的路侧交通目标检测。与车端图像相比，路侧图像中的远距离目标更小，交通锥、行人等类别数量多但像素尺度低，使检测模型需要更强的小目标定位能力。

在路侧场景中，漏检弱势交通参与者的风险往往高于少量误检。Pedestrian、Cyclist 和 Motorcyclist 等类别虽然在实例数中占比低于 Car 和 Trafficcone，但它们直接关系到道路安全预警。对于这些类别，检测模型不仅需要在低 IoU 阈值下判断目标存在，还需要在更严格 IoU 阈值下保持定位质量。因此，本文同时关注 Recall、mAP@0.5 和 mAP@0.5:0.95，并将 mAP@0.5:0.95 作为衡量定位质量的重要指标。

### 1.2 YOLO 系列轻量化目标检测

YOLO 系列模型采用单阶段检测范式，将目标分类和边界框回归统一到端到端网络中，具有较好的速度和精度平衡[6-10]。YOLOv3 通过多尺度预测增强了对不同尺寸目标的适应性[7]，YOLOv4 和 YOLOv7 继续从训练策略、特征融合与实时检测效率方面改进模型[8-9]。Ultralytics YOLOv8 于 2023 年发布，采用 Anchor-free split head 等设计，在检测、分割、分类和姿态估计等任务上形成较完整的工程生态[27]。YOLO11 进一步面向实时视觉任务优化骨干网络、颈部结构和训练流程，并支持多种视觉任务[11]。在实际应用中，n 系列轻量模型因参数少、推理快，常作为边缘部署和快速迭代的基础模型。

轻量化模型的主要问题在于网络容量有限。为了保持实时性，YOLO11n 的通道数和模块深度较小，对复杂背景、小目标和密集目标的表达能力有限。若在不改变检测尺度的情况下仅增加注意力模块，模型可能提升部分通道选择能力，但无法从根本上恢复下采样过程中已经损失的空间细节。本文实验中的 DWCA 与 +DW 结果接近，也说明对本数据集而言，单纯增强注意力并不足以解决小目标检测瓶颈。

### 1.3 小目标检测与多尺度特征融合

小目标检测的困难主要来自像素信息不足、上下文依赖强和特征下采样损失。相关综述指出，提高输入或特征分辨率、增强尺度感知训练、引入上下文信息和改进数据增强是深度学习小目标检测中的主要改进方向[28]。SNIP 通过尺度归一化训练缓解目标尺度变化带来的学习困难[14]，切片辅助推理与微调等方法也从保持局部高分辨率信息的角度改善小目标检测[15]，说明小目标任务的关键瓶颈常与有效像素和特征分辨率有关。对于大目标，深层语义特征能够提供足够的分类和定位信息；对于小目标，浅层特征中的边缘、角点和纹理信息更为关键。多尺度特征融合通过将不同分辨率特征组合，使模型同时获得语义信息和空间细节，是提升小目标检测性能的常用方法[5,12-13]。

YOLO 默认的 P3/P4/P5 检测尺度已经具备一定多尺度能力，但在极小目标密集任务中，P3/8 仍可能不够精细。P2/4 特征图相较 P3/8 具有更高空间分辨率，在输入图像为 640 x 640 时，P2 特征图约为 160 x 160，P3 特征图约为 80 x 80。对于短边仅 4 到 16 像素的目标，P2 分支能够增加其在特征图中的响应区域，降低目标在下采样后被压缩为单点或弱响应的风险。

当然，新增 P2 分支也会增加计算量。高分辨率特征图面积较大，卷积和检测头计算开销明显高于 P4/P5。本文消融结果表明，P2 路线将 GFLOPs 提高到 14.2，但 mAP@0.5:0.95 同时从 +DW 的 61.3% 提高到 64.4%。在路侧小目标检测任务中，这种计算代价换来了更明显的定位质量提升，符合本文任务需求。

### 1.4 注意力机制、动态检测头与边界框损失

注意力机制通过增强关键信息、抑制冗余背景，能够提升视觉模型的特征表达能力。SENet、CBAM 和 ECA-Net 分别从通道重标定、通道-空间联合注意力和轻量通道交互角度改进卷积特征表达[17-19]。CoordAttention 将通道注意力分解为沿水平和垂直方向的一维编码过程，在建模长程依赖的同时保留方向感知和位置敏感信息[16]。对于路侧图像，小目标常分布在道路纵深方向的局部区域，位置信息对检测具有一定价值。因此，本文将 CoordAttention 引入中浅层特征作为辅助增强模块。

Dynamic Head（DyHead）从检测头角度统一建模尺度感知、空间感知和任务感知注意力。Dai 等[20]认为检测头需要同时处理不同特征层级、空间位置和任务通道之间的差异，DyHead 通过在检测头中组合多种注意力机制，提高检测特征表达能力。本文将 YOLO11n 的检测头替换为 DyHeadDetect，使多尺度特征在输出预测前获得更充分的动态调制。消融实验显示，+D 相较 baseline 的 mAP@0.5 从 86.0% 提升至 86.6%，说明 DyHead 对本文任务具有稳定正向作用。

边界框损失函数决定了模型如何优化预测框与真实框之间的空间关系。GIoU、DIoU 和 CIoU 等损失从重叠面积、中心距离和宽高比等角度约束回归过程[22-23]。Wise-IoU 提出动态非单调聚焦机制，依据样本质量调整梯度增益，减弱低质量样本对回归学习的负面影响，并避免过度聚焦高质量样本[21]。在本文正增长消融路线中，WIoU 与 DyHead 组合后形成没有 P2 分支时的较强基线，表明检测头表达与回归损失之间存在互补关系。

## 2 数据集与小目标特征分析

### 2.1 数据集来源与类别设置

本文实验基于 DAIR-V2X-I 路侧单目图像构建 YOLO 格式目标检测数据集，将其 2D 边界框标注转换为 YOLO 归一化中心坐标与宽高格式（不涉及 3D 到 2D 的投影转换）；配置文件中 train、val 和 test 分别指向训练集、验证集和测试集图像目录。类别名称包括 Car、Truck、Van、Bus、Cyclist、Motorcyclist、Pedestrian 和 Trafficcone 共 8 类。原始数据中的极少样本类别 Barrowlist（验证集仅 24 个实例）未纳入本文 8 类检测任务。

表 1 给出了本文使用的数据集划分和实例数量。训练集包含 4940 个标注文件、227831 个目标实例；验证集包含 1411 个标注文件、65255 个实例；测试集包含 707 个标注文件、32628 个实例。总计 7058 个标注文件和 325714 个目标实例。该规模能够支撑轻量化 YOLO 模型训练与消融比较。需要说明的是，本文所有定量评价指标均在验证集上计算，最佳训练轮次亦依验证集指标选定；测试集不参与模型选择与指标报告，留作后续跨场景泛化评估。

**表 1 DAIR-V2X-I 数据集划分与实例数**  
**Tab. 1 Dataset split and instance numbers of DAIR-V2X-I**

| 划分 | 标注文件数 | 实例数 |
|---|---:|---:|
| 训练集 | 4940 | 227831 |
| 验证集 | 1411 | 65255 |
| 测试集 | 707 | 32628 |
| 合计 | 7058 | 325714 |

### 2.2 类别分布统计

表 2 给出了各类别实例数量及占比。Trafficcone 数量最多，共 159930 个，占 49.10%；Car 共有 91443 个，占 28.07%。两类合计占比超过 77%，说明数据集中存在明显类别不均衡。Pedestrian 为 25194 个，占 7.74%；Cyclist 和 Motorcyclist 分别占 5.29% 和 5.60%；Truck、Van 和 Bus 的占比较低，均属于相对少样本类别。

**表 2 DAIR-V2X-I 类别实例分布**  
**Tab. 2 Category distribution of DAIR-V2X-I**

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

### 2.3 目标尺度统计

为了分析小目标特征，本文将 YOLO 归一化标注框折算到 640 x 640 输入尺度下，统计目标面积、短边长度和双边尺度。统计结果见表 3。若参考 COCO 数据集常用的小目标面积阈值 area < 32² px²[29]，本文数据中小目标实例为 259421 个，占 79.65%。若以短边长度衡量，short side < 16 px 的目标占 68.60%，short side < 32 px 的目标占 87.55%。此外，宽高均小于 32 px 的目标占 56.37%。

**表 3 目标尺度统计结果**  
**Tab. 3 Object scale statistics at imgsz=640**

| 小目标定义 | 实例数 | 占比/% |
|---|---:|---:|
| area < 32² px² | 259421 | 79.65 |
| short side < 16 px | 223453 | 68.60 |
| short side < 32 px | 285172 | 87.55 |
| both sides < 32 px | 183595 | 56.37 |

从目标尺度看，本文数据集的小目标比例远高于一般自然场景检测任务。特别是 Trafficcone、Pedestrian、Cyclist 和 Motorcyclist 等类别，在路侧远景区域中常表现为高度细长或低像素目标。类别级中位短边统计进一步显示，Trafficcone 约为 4.2 px，Pedestrian 约为 9.0 px，Cyclist 约为 14.4 px，Motorcyclist 约为 15.6 px。对于这类目标，若模型最低检测尺度为 P3/8，则部分目标在特征图中可能仅对应 1 到 2 个栅格，边界回归难度较高。

**表 4 验证集各类别尺度分布（imgsz=640）**  
**Tab. 4 Scale distribution by class on the validation set**

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

![图 1 验证集各类别短边尺度分布](figures/fig1_val_scale_distribution.png)

图 1 验证集各类别短边尺度分布。Fig. 1 Short-side scale distribution of each class on the validation set.

### 2.4 数据特征对模型设计的启示

上述统计为本文方法设计提供了直接依据。首先，目标短边普遍较小，说明模型需要更高分辨率的检测特征，P2/4 分支具有必要性。其次，类别分布不均衡且小目标类别与道路安全高度相关，说明模型需要提高 Recall，减少远距离目标漏检。再次，大量交通锥和车辆构成密集目标区域，要求检测头能够处理尺度和空间位置差异，DyHead 因此具有应用价值。最后，路侧背景复杂、目标位置具有明显道路几何规律，CoordAttention 的方向位置编码可作为辅助增强。

## 3 改进 YOLO11n 检测方法

### 3.1 YOLO11n 基准网络

YOLO11n 是 YOLO11 系列中的 nano 版本，具有参数量小、计算量低和训练部署方便等优点。本文以 YOLO11n YAML 结构作为 baseline，并采用从头训练的方式进行主要对比。baseline 在固定 batch=32 复验中取得 Precision 85.7%、Recall 80.8%、mAP@0.5 86.0%、mAP@0.5:0.95 60.2%、FPS 153.0、GFLOPs 6.3、Params 2.6M 的结果。该模型计算量较低，但 Recall 和 mAP@0.5:0.95 仍存在提升空间。

YOLO11n 的检测流程可以概括为：输入图像经 Backbone 提取多层特征，Neck 通过上采样、拼接和卷积实现多尺度特征融合，Head 在不同尺度特征图上预测目标类别和边界框。默认检测头使用 P3、P4 和 P5 三层特征，其中 P3 更偏向小目标，P4 和 P5 更偏向中大目标。对于 DAIR-V2X-I 这种极小目标比例高的数据集，仅使用 P3 作为最高分辨率检测层可能不足。

### 3.2 总体改进结构

本文提出的 YOLO11n-DWCA-P2 在基准网络基础上进行四方面改进。第一，将检测头替换为 DyHeadDetect，提高多尺度特征在检测阶段的动态表达能力；第二，在边界框回归中采用 Wise-IoU v3 损失，提高定位学习质量；第三，在 Neck 中新增 P2/4 高分辨率检测分支，使检测头接收 P2、P3、P4 和 P5 四尺度输入；第四，在浅中层特征中引入 CoordAttention，以增强通道和坐标位置联合建模。

图 2 为本文方法结构示意图。该图基于本文方法 YAML 结构重新绘制，突出 Backbone、Top-down FPN、Bottom-up PAN、四尺度检测输入和 Head/Loss 的阶段关系。图中 P2 分支对应 layer 20，CoordAttention 位于 layer 5，DyHeadDetect 的输入为 [20, 23, 26, 29]。WIoU v3 仅作用于训练阶段的边界框回归损失，不属于推理阶段的网络拓扑。

![图 2 YOLO11n-DWCA-P2 网络结构示意图](figures/fig2_dwca_p2_architecture_vertical.png)

图 2 YOLO11n-DWCA-P2 网络结构示意图。Fig. 2 Architecture of YOLO11n-DWCA-P2.

### 3.3 P2 高分辨率检测分支

P2 分支是本文最终模型的核心改进。对于输入大小为 640 x 640 的图像，P2/4 特征图分辨率约为 160 x 160，P3/8 特征图分辨率约为 80 x 80。若一个目标短边为 8 px，则在 P3 特征图上对应约 1 个像素，在 P2 特征图上对应约 2 个像素；若目标短边为 16 px，则在 P3 上约 2 个像素，在 P2 上约 4 个像素。虽然这只是近似分析，但足以说明 P2 对极小目标响应区域的提升。

设输入图像短边尺度为 d，检测层下采样步长为 r_l，则该目标在第 l 个检测特征图上的近似线性投影尺度为

$$d_l=\frac{d}{r_l},$$

其中，P2 和 P3 的下采样步长分别为 4 和 8（即 r_{P2}=4、r_{P3}=8，表示相应特征图相对输入图像的下采样倍率）。因此，同一目标在 P2 上的线性投影约为 P3 的 2 倍，面积响应约为 4 倍。该尺度关系解释了为什么 P2 分支更适合承接远距离行人、交通锥和骑行者等极小目标的定位学习。

本文在 Neck 中将较高层特征逐步上采样，并与浅层 P2 特征拼接融合，得到用于 tiny object detection 的 P2 输出层。随后，检测头由原来的三尺度输入扩展为四尺度输入。P2 分支保留了更多浅层边缘、纹理和空间位置信息，能够缓解远距离行人、交通锥和骑行者在深层特征中消失或定位偏移的问题。

![图 3 P2 高分辨率分支融合示意](figures/fig3_p2_fusion.png)

图 3 P2 高分辨率分支融合示意。Fig. 3 P2 high-resolution branch fusion in the Neck.

从消融结果看，DW-P2 在不使用 CoordAttention 的情况下，mAP@0.5 达到 88.1%，mAP@0.5:0.95 达到 64.4%；完整 DWCA-P2 的 mAP@0.5:0.95 同样为 64.4%。这一结果表明 P2 分支贡献了最终模型的主要定位增益。相比之下，DWCA 在没有 P2 分支时 mAP@0.5:0.95 仅为 61.3%。因此，本文在结论中将 P2 明确为主贡献模块。

### 3.4 DyHead 动态检测头

DyHead 的核心思想是在检测头中统一建模尺度、空间和任务三个维度的注意力。对于多尺度特征金字塔，尺度感知注意力可根据目标大小选择合适层级；空间感知注意力可关注目标所在位置；任务感知注意力可协调分类与定位任务之间的特征需求[20]。路侧图像中目标尺度跨度大、远近分布明显，同一类别在不同道路深度区域呈现明显尺度变化，因而适合引入动态检测头。

本文在 YOLO11n 中使用 DyHeadDetect 替换原检测头。设输入检测特征为多尺度特征集合 F = {F2, F3, F4, F5}，其中 F2 到 F5 分别对应 P2 到 P5 特征。DyHeadDetect 对多尺度特征进行动态调制后输出类别概率和边界框回归结果。具体地，DyHead 依次施加尺度感知 π、空间感知 S 与任务感知 L 三种注意力，对多尺度特征 F 进行级联调制：

$$F'=L(S(\pi(F))),$$

其中，π 沿尺度维度计算跨层权重，使不同层级特征按目标尺度自适应融合；S 借助可变形卷积在空间维度关注目标位置；L 采用动态激活函数在任务通道间协调分类与回归特征。该级联调制不改变输入数据或标签，而是在检测阶段提高特征对尺度、空间位置和任务通道的适应性。

![图 4 DyHead 动态检测头结构示意](figures/fig4_dyhead.png)

图 4 DyHead 动态检测头结构示意。Fig. 4 DyHead dynamic head structure.

在消融实验中，+D 模型相较 baseline 的 mAP@0.5 从 86.0% 提升至 86.6%，mAP@0.5:0.95 从 60.2% 提升至 61.3%；+DW 模型进一步达到 87.0% mAP@0.5 和 61.3% mAP@0.5:0.95。说明 DyHead 对本文任务有稳定增益，是构建强基线的重要模块。

### 3.5 CoordAttention 位置注意力模块

CoordAttention 的目标是在通道注意力中保留位置信息。传统通道注意力通常通过二维全局池化将空间维度压缩为单个通道描述子，容易丢失目标具体位置信息。CoordAttention 将全局池化分解为沿高度方向和宽度方向的一维编码，分别得到方向感知特征，再生成位置敏感注意力图[16]。其沿高度和宽度方向的编码可分别表示为

$$z_c^h(h)=\frac{1}{W}\sum_{0\leq i<W}x_c(h,i),$$

$$z_c^w(w)=\frac{1}{H}\sum_{0\leq j<H}x_c(j,w),$$

其中，x 表示输入特征，H 和 W 表示特征图高度和宽度，c 表示通道索引。随后，将 zʰ 与 zʷ 沿通道拼接，经 1×1 卷积与非线性激活 δ 变换后沿方向拆分为两路，再由 Sigmoid 分别生成沿高度与宽度方向的方向门控 gʰ 与 gʷ；二者各自编码对应坐标轴的位置先验，不能由单一通道门控替代，这是 CoordAttention 能够保留方向位置敏感信息的关键：

$$f=\delta(\mathrm{Conv}_{1\times1}([z^h,z^w])),\quad g^h=\sigma(f^h),\quad g^w=\sigma(f^w),$$

$$y_c(h,w)=x_c(h,w)\cdot g_c^h(h)\cdot g_c^w(w),$$

其中，[·,·] 表示沿通道维度拼接，σ 为 Sigmoid 函数，fʰ、fʷ 为变换后沿高度与宽度方向的分支。最终输出 y_c(h,w) 将方向位置敏感的注意力权重作用回输入特征，从而增强方向和位置敏感信息。

![图 5 CoordAttention 结构示意](figures/fig5_coordattention.png)

图 5 CoordAttention 结构示意。Fig. 5 Coordinate attention structure.

本文将 CoordAttention 嵌入到 P3 相关特征位置，目的是在浅层细节与中层语义之间增强位置编码。需要强调的是，本文实验并不支持将 CoordAttention 表述为主要增益来源。DWCA 的 mAP@0.5:0.95 为 61.3%，与 +DW 的 61.3% 持平；完整模型相较 DW-P2 在 mAP@0.5:0.95 上没有进一步增加。因此，CoordAttention 更适合作为辅助模块写入方法部分，而不是在摘要和结论中过度强调。

### 3.6 Wise-IoU v3 边界框回归损失

边界框回归损失用于度量预测框与真实框之间的差异。IoU 可表示为

$$IoU=\frac{|B\cap B_{gt}|}{|B\cup B_{gt}|},$$

其中，B 为预测框，B_gt 为真实框，∩ 与 ∪ 分别表示区域的交集与并集。传统 CIoU 在 IoU 基础上引入中心距离和宽高比约束，能够提升边界框回归稳定性。Wise-IoU 进一步关注样本质量差异，通过动态非单调聚焦机制调整不同质量锚框的梯度增益[21]。其思想是避免低质量样本产生过强有害梯度，同时不过度放大已经较好拟合的高质量样本，使模型更关注普通质量样本的有效学习。具体地，设预测框与真实框中心距为 ρ、最小外接矩形对角线长度为 c，WIoU v3 首先构造距离注意力项

$$R_{WIoU}=\exp(\frac{\rho^2}{c^2}),$$

其中 c² 取停止梯度形式，使梯度仅经 ρ² 流动。记 L_IoU = 1 − IoU 为边界框回归损失，并以停止梯度形式 L_IoU* 参与聚焦计算；训练中以指数滑动平均维护其在批内的均值 L̄。以 L_IoU* 与 L̄ 之比定义锚框离群度 β，进而构造动态非单调聚焦因子 r：

$$\beta=\frac{L_{IoU}^{*}}{\overline{L}},\quad r=\frac{\beta}{\delta\,\alpha^{\beta-\delta}},$$

其中 α=1.9、δ=3.0 为文献[21]给出的超参数。WIoU v3 的最终回归损失为

$$\mathcal{L}_{WIoUv3}=r\cdot R_{WIoU}\cdot L_{IoU}.$$

当锚框为高质量样本（β 较小）时 r 较小，梯度增益被抑制；当为离群低质量样本（β 较大）时 r 亦被非单调衰减，避免过强有害梯度；而普通质量样本获得相对更大的梯度增益，从而更关注其有效学习。

![图 6 Wise-IoU v3 聚焦增益曲线](figures/fig6_wiou_focusing.png)

图 6 Wise-IoU v3 动态非单调聚焦增益 r 随 β 变化。Fig. 6 Wise-IoU v3 dynamic non-monotonic focusing gain r vs. β.

本文在训练中采用 WIoU v3 作为改进模型的回归损失。在正增长消融路线中，+DW 相较 +D 的 Recall 从 81.1% 提升到 81.9%，mAP@0.5 从 86.6% 提升到 87.0%，但 mAP@0.5:0.95 保持 61.3%。这说明 WIoU 在本文任务中更适合作为检测头改进后的配套优化，而不是主要定位增益来源；最终定位质量提升仍主要来自 P2 高分辨率检测分支。

### 3.7 方法流程

本文方法的训练和推理流程如下。首先，将 DAIR-V2X-I 路侧图像按 YOLO 格式读取，并在训练阶段进行常规数据增强。其次，输入图像经 YOLO11n Backbone 提取多层特征，在 Neck 中通过自顶向下和自底向上的特征融合形成 P2、P3、P4 和 P5 四尺度特征。随后，CoordAttention 对中浅层特征进行位置敏感增强，DyHeadDetect 对四尺度特征进行动态检测。训练阶段使用分类损失、回归损失和分布相关损失共同优化，其中回归部分采用 WIoU v3。推理阶段，模型输出多尺度候选框，经过置信度筛选和非极大值抑制得到最终检测结果。

与原始 YOLO11n 相比，本文方法的主要变化集中在 Neck-Head 与损失函数处，不改变数据标注格式，也不依赖额外传感器输入。对于后续复现，可重点检查四项内容：模型 YAML 是否包含 P2 输出层，检测头是否为 DyHeadDetect，训练损失是否正确启用 WIoU v3，所有主实验 batch 是否按 32 固定。

## 4 实验设置

### 4.1 实验环境与训练参数

本文所有实验使用同一数据集划分，并按固定 batch=32 口径解释。输入图像尺寸为 640 x 640，训练轮数为 300 epochs，优化器为 SGD，随机种子为 42，nbs 为 64，close_mosaic 设置为 10。实验评价指标包括 Precision、Recall、mAP@0.5、mAP@0.5:0.95、FPS、GFLOPs 和 Params。表 5 给出了主要训练与测速参数。

**表 5 训练与测速参数设置**  
**Tab. 5 Training and speed measurement settings**

| 参数 | 设置 |
|---|---|
| 硬件 | NVIDIA GeForce RTX 4090 24GB |
| 框架 | Python 3.12.3，Ultralytics 8.4.56，PyTorch 2.7.0+cu128 |
| 数据集划分 | 训练集/验证集/测试集=4940/1411/707 |
| 输入尺寸 | 640 x 640 |
| 训练参数 | epochs=300，batch=32，optimizer=SGD，seed=42 |
| 测速口径 | batch=1，FPS=1000/(preprocess+inference+postprocess) |

### 4.2 评价指标

目标检测任务通常使用 Precision、Recall 和 mAP 评价模型性能。Precision 表示预测为正样本的目标中真正例所占比例，Recall 表示真实目标中被正确检出的比例，计算式为

$$P=\frac{TP}{TP+FP},$$

$$R=\frac{TP}{TP+FN},$$

其中，TP 表示真正例，FP 表示假正例，FN 表示假负例。对于路侧安全感知任务，Recall 尤其重要，因为漏检行人、骑行者和交通锥可能影响后续交通事件判断。

AP 表示单类别 Precision-Recall 曲线下的面积，mAP 表示多类别 AP 的平均值。mAP@0.5 在 IoU 阈值为 0.5 时计算平均精度，主要反映模型能否检测到目标；mAP@0.5:0.95 在 0.5 到 0.95 的多个 IoU 阈值上取平均，更严格地反映定位质量。对于小目标检测，mAP@0.5:0.95 能更敏感地体现边界框偏移问题，因此本文将其作为重要指标。FPS 用于衡量统一测试环境下的端到端推理速度，GFLOPs 和 Params 分别反映计算复杂度与参数规模。

### 4.3 实验分组

本文实验分为三类。第一类为主结果对比，比较 YOLO11n baseline 与最终模型 DWCA-P2，作为本文结论的主要依据；两者均采用 batch=32 的固定复验结果。第二类为正增长模块消融实验，沿 baseline、+D、+DW、DWCA、DW-P2 和 DWCA-P2 路线逐步分析 DyHead、WIoU、CoordAttention 与 P2 分支的作用。第三类为同口径结构对比，比较 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml、YOLO11n baseline 和本文方法。正文实验均采用从头训练口径，避免外部权重来源差异干扰结论。

为保证结论边界清晰，本文正文只采用与最终方法直接相关的模块路线。

## 5 实验结果与分析

### 5.1 主结果对比

表 6 给出了本文最终模型与 YOLO11n baseline 的主结果对比。可以看出，DWCA-P2 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 分别为 86.0%、83.5%、88.4% 和 64.4%，较 baseline 分别提升 0.3、2.7、2.4 和 4.2 个百分点。

**表 6 主结果对比**  
**Tab. 6 Main comparison between baseline and the proposed method**

| 模型 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | FPS | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 85.7 | 80.8 | 86.0 | 60.2 | 153.0 | 6.3 | 2.6 |
| DWCA-P2 | 86.0 | 83.5 | 88.4 | 64.4 | 100.5 | 14.2 | 4.5 |

从指标变化看，本文方法在 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 上均有提升。其中 Recall 与 mAP@0.5:0.95 的增幅更大，说明该方法能够检出更多真实目标，并改善较高 IoU 阈值下的定位质量；Precision 与 mAP@0.5 的同步提升，则说明模型在降低漏检的同时没有显著放大误检。这与 P2 分支保留高分辨率空间细节、WIoU v3 优化边界框回归以及 CoordAttention 对位置敏感表达的补充增强作用相一致。

计算复杂度方面，DWCA-P2 的 GFLOPs 为 14.2，参数量为 4.5M。统一 RTX 4090 测速下，DWCA-P2 的 FPS 为 100.5，对应单张端到端耗时约 9.95 ms。额外计算主要来自 DyHead 和 P2 高分辨率检测分支。对于极端低功耗嵌入式设备，该计算开销可能需要进一步压缩；对于路侧边缘服务器或具备加速芯片的路侧计算单元，该速度可作为同环境实时性参考。

![图 7 主结果指标对比](figures/fig7_main_metrics.png)

图 7 baseline 与 DWCA-P2 主指标对比。Fig. 7 Main metric comparison between baseline and DWCA-P2.

### 5.2 类别级结果分析

为进一步分析改进模型对不同类别的影响，本文从训练日志末尾的 per-class 验证输出中提取 baseline 与 DWCA-P2 的类别级 AP，结果见表 7。需要说明的是，表 7 来源于最终验证日志的逐类别输出，整体均值与表 6 的 Excel 主结果口径存在约 0.1 个百分点的四舍五入和最佳轮次差异；论文主结论仍以表 6 为准，类别级分析用于观察不同类别的相对变化。

**表 7 类别级 AP 对比**  
**Tab. 7 Per-class AP comparison**

| 类别 | 实例数 | baseline mAP@0.5/% | DWCA-P2 mAP@0.5/% | baseline mAP@0.5:0.95/% | DWCA-P2 mAP@0.5:0.95/% | mAP@0.5:0.95提升/% |
|---|---:|---:|---:|---:|---:|---:|
| Car | 18342 | 95.9 | 96.8 | 79.2 | 81.8 | 2.6 |
| Truck | 660 | 80.9 | 78.8 | 54.1 | 55.9 | 1.8 |
| Van | 1385 | 82.1 | 83.9 | 68.9 | 71.9 | 3.0 |
| Bus | 669 | 94.0 | 95.5 | 77.5 | 79.5 | 2.0 |
| Cyclist | 3469 | 87.5 | 89.8 | 58.1 | 62.1 | 4.0 |
| Motorcyclist | 3632 | 77.4 | 79.1 | 50.9 | 54.0 | 3.1 |
| Pedestrian | 5073 | 77.8 | 86.3 | 42.8 | 51.3 | 8.5 |
| Trafficcone | 32025 | 92.2 | 96.3 | 50.2 | 58.2 | 8.0 |

类别级结果显示，DWCA-P2 在 Pedestrian 和 Trafficcone 上的提升最明显。其中 Pedestrian 的 mAP@0.5 从 77.8% 提升到 86.3%，mAP@0.5:0.95 从 42.8% 提升到 51.3%；Trafficcone 的 mAP@0.5:0.95 提升 8.0 个百分点。结合表 4 可知，这两类目标在验证集中几乎全部属于 short side < 32 px 的小目标，因此其提升能够较直接地支撑 P2 高分辨率检测分支的有效性。Cyclist 和 Motorcyclist 的 mAP@0.5:0.95 分别提升 4.0 和 3.1 个百分点，也说明 P2 分支对弱势交通参与者具有较明显帮助。Truck 的 mAP@0.5:0.95 提升 1.8 个百分点，但该类样本数量较少、类别内尺度变化较大，其低阈值 AP 波动仍需结合更多样本进一步核验。

![图 8 类别级 mAP@0.5:0.95 增益](figures/fig8_class_map_gain.png)

图 8 DWCA-P2 相对 baseline 的类别级 mAP@0.5:0.95 提升。Fig. 8 Per-class mAP@0.5:0.95 gain of DWCA-P2 over baseline.

### 5.3 模块消融实验

为分析各模块贡献，本文设计了从 baseline 到最终模型的正增长路线消融实验，结果见表 8。表中 +D 表示引入 DyHead，+DW 表示 DyHead 与 WIoU 组合，DWCA 表示 DyHead、WIoU 与 CoordAttention 组合但不含 P2，DW-P2 表示 DyHead、WIoU 与 P2 组合但不含 CoordAttention，DWCA-P2 表示完整结构。

**表 8 消融实验结果**  
**Tab. 8 Ablation study results**

| 模型 | 主要改动 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | FPS | GFLOPs | Params/M |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | YOLO11n | 85.7 | 80.8 | 86.0 | 60.2 | 153.0 | 6.3 | 2.6 |
| +D | DyHead | 86.3 | 81.1 | 86.6 | 61.3 | 120.8 | 9.3 | 4.3 |
| +DW | DyHead+WIoU | 86.0 | 81.9 | 87.0 | 61.3 | 123.4 | 9.3 | 4.3 |
| DWCA | DyHead+WIoU+CA | 86.8 | 81.4 | 86.8 | 61.3 | 119.5 | 9.3 | 4.4 |
| DW-P2 | DyHead+WIoU+P2 | 85.6 | 83.5 | 88.1 | 64.4 | 100.5 | 14.2 | 4.5 |
| DWCA-P2 | DyHead+WIoU+CA+P2 | 86.0 | 83.5 | 88.4 | 64.4 | 100.5 | 14.2 | 4.5 |

DyHead 的提升较稳定。+D 的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 均高于 baseline，其中 mAP@0.5 提升 0.7 个百分点。将 WIoU 与 DyHead 组合后，+DW 的 Recall 达到 81.9%，mAP@0.5 达到 87.0%，成为没有 P2 分支时的较强基线。这表明 DyHead 和 WIoU 在特征表达与边界框回归层面具有一定互补性。

P2 分支的效果最为明显。DW-P2 在不使用 CoordAttention 的情况下，Recall 达到 83.5%，mAP@0.5 达到 88.1%，mAP@0.5:0.95 达到 64.4%。相比 +DW，其 Recall 提升 1.6 个百分点，mAP@0.5 提升 1.1 个百分点，mAP@0.5:0.95 提升 3.1 个百分点。加入 CoordAttention 后，DWCA-P2 的 Precision 由 85.6% 提升到 86.0%，mAP@0.5 由 88.1% 提升到 88.4%，mAP@0.5:0.95 仍为 64.4%。这些结果共同说明，P2 高分辨率分支主导了 Recall 与定位质量提升，而 CoordAttention 在 Precision 和 mAP@0.5 上提供了补充增益。

CoordAttention 的作用应谨慎但不宜弱化。DWCA 相比 +DW 的 mAP@0.5:0.95 没有提升，二者均为 61.3%；完整模型相较 DW-P2 的 mAP@0.5:0.95 也没有增加，因此它不是最终定位质量提升的主导来源。但从最终模型与 DW-P2 的比较看，CoordAttention 使 Precision 从 85.6% 提升到 86.0%，mAP@0.5 从 88.1% 提升到 88.4%，说明该模块对误检抑制和位置敏感特征表达仍有积极作用。由于表 8 已同时列出 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95，消融分析以表格为主要依据，避免仅用单一指标图削弱对 CoordAttention 精度侧作用的呈现。

### 5.4 与其他检测方法的对比

本节从两个层面比较本文方法与其他检测方法：先在相同训练口径下与代表性轻量化 YOLO 结构对比（表 9），再与文献[30] 在 DAIR-V2X-I 上报告的多种方法作参考性对比（表 10）。同口径对比部分，本文选取 YOLOv5n-yaml、YOLOv8n-yaml、YOLOv10n-yaml 和 YOLO11n baseline，统一采用从头训练设置，结果见表 9。

**表 9 同口径结构对比**  
**Tab. 9 Comparison of lightweight YOLO structures trained from YAML**

| 模型 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|---:|
| YOLOv5n-yaml | 85.4 | 81.0 | 85.8 | 59.9 | 7.1 | 2.5 |
| YOLOv8n-yaml | 86.5 | 81.2 | 86.5 | 61.0 | 8.1 | 3.0 |
| YOLOv10n-yaml | 85.8 | 80.1 | 85.7 | 60.7 | 8.4 | 2.7 |
| YOLO11n baseline | 85.7 | 80.8 | 86.0 | 60.2 | 6.3 | 2.6 |
| DWCA-P2 | 86.0 | 83.5 | 88.4 | 64.4 | 14.2 | 4.5 |

由表 9 可知，YOLOv8n-yaml 在未引入本文改进时表现较好，mAP@0.5 为 86.5%，mAP@0.5:0.95 为 61.0%。YOLO11n baseline 与 YOLOv8n-yaml 的总体差距较小，但计算量更低。本文方法在 mAP@0.5 和 mAP@0.5:0.95 上均明显高于上述轻量结构，其中 mAP@0.5:0.95 相较 YOLOv8n-yaml 提升 3.4 个百分点，相较 YOLO11n baseline 提升 4.2 个百分点。

为进一步说明本文方法在 DAIR-V2X-I 上的竞争力，表 10 将本文 DWCA-P2 与文献[30] 报告的代表性方法进行对比。文献[30] 同样面向 DAIR-V2X-I 的改进 YOLO11（YOLO-FLC），在 10 类目标（含三轮车、手推车）、7058 张图像子集、batch=16、150 epoch 设置下报告了多种方法的结果；其中 YOLOv5n、YOLOv8n、YOLO11n 与本文表 9 的同口径模型重叠，故表 10 仅列出与本文结构差异较大的代表性方法（RT-DETR-r18、Mamba-YOLO-B 及其改进模型 YOLO-FLC，方法名右上角数字为参考文献编号）。本文 DWCA-P2 在 8 类、batch=32、300 epoch 设置下的 Precision、Recall、mAP@0.5 和 mAP@0.5:0.95 均高于表 10 所列方法，亦高于文献[30] 报告的全部方法。作为交叉印证，本文 YOLOv5n 的 mAP@0.5:0.95（59.9%，见表 9）与文献[30] 的 YOLOv5n（59.4%）接近，说明两者评测口径具有一定可比性。

**表 10 与文献方法在 DAIR-V2X-I 上的对比**
**Tab. 10 Comparison with published methods on DAIR-V2X-I**
| 方法 | P/% | R/% | mAP@0.5/% | mAP@0.5:0.95/% |
|---|---:|---:|---:|---:|
| RT-DETR-r18^{[30]} | 85.5 | 78.9 | 85.1 | 59.9 |
| Mamba-YOLO-B^{[30]} | 85.6 | 79.1 | 85.2 | 61.1 |
| YOLO-FLC^{[30]} | 85.7 | 79.4 | 85.3 | 61.3 |
| DWCA-P2（本文） | 86.0 | 83.5 | 88.4 | 64.4 |

注：文献[30] 各行为其原始口径（10 类、7058 图、batch=16、150 epoch），本文 DWCA-P2 为本文口径（8 类、batch=32、300 epoch）。二者类别集合、数据划分与训练超参不完全一致，该表为同基准数据集上的参考性对比，严格同口径横评以表 9 为准。

这一结果说明，对于 DAIR-V2X-I 路侧小目标任务，针对目标尺度分布进行结构改进，比单纯更换轻量化 YOLO 版本更有效。不同 YOLO 版本在默认结构下均以 P3/P4/P5 为主要检测尺度，无法充分解决极小目标特征不足问题。本文通过 P2 分支引入更高分辨率检测层，因而在 Recall 和高阈值 mAP 上获得更明显提升。

### 5.5 速度与复杂度分析

表 11 给出了统一测速口径下的速度与复杂度结果。FPS 测量条件为 RTX 4090 24GB、Ultralytics 8.4.56、torch 2.7.0+cu128、DAIR-V2X-I val=1411、imgsz=640、batch=1，FPS=1000/(preprocess+inference+postprocess)，排除 loss。该口径能够用于本文各结构之间的速度比较，但仍不等同于 TensorRT、INT8 或特定边缘设备上的部署速度。

**表 11 速度与复杂度对比**
**Tab. 11 Speed and complexity comparison**

| 模型 | FPS | 单张耗时/ms | 相对baseline/% | GFLOPs | Params/M |
|---|---:|---:|---:|---:|---:|
| baseline | 153.0 | 6.5 | 100.0 | 6.3 | 2.6 |
| +DW | 123.4 | 8.1 | 80.7 | 9.3 | 4.3 |
| +D | 120.8 | 8.3 | 79.0 | 9.3 | 4.3 |
| DWCA | 119.5 | 8.4 | 78.1 | 9.3 | 4.4 |
| DWCA-P2 | 100.5 | 9.9 | 65.7 | 14.2 | 4.5 |
| DW-P2 | 100.5 | 10.0 | 65.7 | 14.2 | 4.5 |

结果显示，baseline 速度最高，达到 153.0 FPS；DyHead 带来明显检测头计算开销；P2 高分辨率小目标检测头是 DWCA-P2/DW-P2 速度下降的主要来源。DWCA-P2 的 FPS 为 100.5，相当于单张端到端耗时约 9.95 ms，在 RTX 4090 参考环境下达到实时检测速度。该结果主要用于同环境模型对比，若部署在低功耗路侧端设备中，仍需进一步结合剪枝、轻量化卷积、知识蒸馏和 TensorRT FP16/INT8 量化降低计算成本，并在目标硬件上重新测速。

### 5.6 训练过程分析

为观察模型训练收敛趋势，本文根据 baseline 与 DWCA-P2 的 results.csv 绘制验证集 mAP@0.5:0.95 曲线和 Recall 曲线，如图 9 和图 10 所示。从曲线变化可以看出，DWCA-P2 在训练中后期保持更高的 mAP@0.5:0.95 和 Recall，说明 P2 分支带来的提升不是单个 epoch 的偶然波动，而是在训练收敛阶段形成了相对稳定的性能差距。

![图 9 验证集 mAP@0.5:0.95 曲线](figures/fig9_training_map50_95.png)

图 9 baseline 与 DWCA-P2 的验证集 mAP@0.5:0.95 曲线。Fig. 9 Validation mAP@0.5:0.95 curves.

![图 10 验证集 Recall 曲线](figures/fig10_training_recall.png)

图 10 baseline 与 DWCA-P2 的验证集 Recall 曲线。Fig. 10 Validation Recall curves.

由于当前产物未保存完整逐框预测 txt/json，本文不进一步声称逐图漏检数量或按目标尺度细分的检测指标。后续若需展开错误类型分析，应重新保存验证集预测结果，并按类别、目标尺度和置信度区间统计漏检与误检。

### 5.7 定性检测效果对比

为直观验证改进对极小目标的提升，选取 1 张含远距离行人与交通锥的代表性场景（YiZhuang11North 路口），以 conf=0.5 分别用 baseline 与 DWCA-P2 推理，并对小目标密集区作局部放大对比，结果如图 11 所示。可以看出，DWCA-P2 较 baseline 检出更多远距离小目标，该场景检出框数由 24 增至 27。需说明的是，本文方法的整体优势主要体现在平均定位质量（mAP@0.5:0.95）和对极小目标召回的改善上（见表 6、表 7 的定量结果），此处为代表性场景的定性示意，未对全验证集按目标尺度进行系统的漏检/误检统计。

![图 11 baseline 与 DWCA-P2 检测效果对比（远距离小目标密集区局部放大；conf=0.5）](figures/fig_detection_comparison.png)

图 11 baseline 与 DWCA-P2 在代表性场景下的检测对比（左：裁剪位置缩略图；中：baseline 放大；右：DWCA-P2 放大；conf=0.5）。Fig. 11 Qualitative detection comparison between baseline and DWCA-P2 on a representative scene (left: crop locator; middle: baseline zoom; right: DWCA-P2 zoom; conf=0.5).

## 6 讨论

### 6.1 P2 分支为何成为主增益来源

本文最重要的实验结论是，P2 高分辨率检测分支是性能提升的主要来源。这一结论由数据统计和消融实验共同支持。数据统计显示，DAIR-V2X-I 路侧图像中短边小于 32 px 的目标占 87.55%，其中大量目标短边甚至小于 16 px。对于这些目标，特征图分辨率直接决定模型能否保留有效边界和中心位置信息。

从消融结果看，DWCA 仅在 +DW 基础上加入 CoordAttention，mAP@0.5:0.95 仍为 61.3%；DW-P2 在不加入 CoordAttention 的情况下将 mAP@0.5:0.95 提升到 64.4%。这说明当目标尺度极小时，先让模型“看得见”比进一步调整注意力权重更重要。另一方面，DWCA-P2 相比 DW-P2 的 Precision 由 85.6% 提升到 86.0%，mAP@0.5 由 88.1% 提升到 88.4%，说明 CoordAttention 更适合体现在误检抑制和较松 IoU 阈值下的检测稳定性改善。P2 分支通过改变检测特征尺度主导 Recall 与定位质量提升，CoordAttention 则对精度侧指标形成补充。

### 6.2 注意力模块的有效边界

注意力机制并非在所有场景中都能带来明显收益。本文 CoordAttention 的实验结果说明，在已有 DyHead 动态检测头的情况下，继续叠加位置注意力模块可能收益有限。原因可能在于，注意力模块主要改变特征权重分配，而不能恢复下采样过程中损失的空间信息。若小目标已经在高层特征中变成弱响应，注意力机制只能重新分配现有响应，无法创造缺失的细节。

CoordAttention 仍具有一定方法价值。它能够在轻量网络中引入位置敏感通道表达，对道路场景中具有方向规律的目标分布可能有帮助。结合消融结果，更合理的表述是：CoordAttention 作为辅助模块增强中浅层特征的位置表达，对 Precision 和 mAP@0.5 有补充增益，而最终 Recall 与 mAP@0.5:0.95 的主要提升仍由 P2 分支驱动。

### 6.3 局限性

本文仍存在若干局限。首先，当前实验已经补充类别级 AP 和验证集尺度分布统计，但尚未保存完整逐框预测 txt/json，因此未进一步报告基于预测框的细分误差统计。若后续需要分析不同目标尺度下的检测差异，应重新保存验证集预测结果，并按统一规则重新计算，不能从当前汇总表格直接推断。

其次，本文方法增加了计算量。DWCA-P2 的 GFLOPs 是 baseline 的约 2.25 倍，FPS 下降约 52.45。对于需要在低功耗设备上实时运行的路侧系统，仍需进一步轻量化。可行方向包括减少 P2 分支通道数、使用轻量卷积替代部分标准卷积、剪枝冗余通道、使用蒸馏训练小模型以及进行 TensorRT INT8 量化。

最后，本文主要基于单数据集验证。DAIR-V2X-I 具有典型路侧特征，但不同城市、摄像机高度、道路结构和天气条件会造成分布差异。未来应在更多路侧数据集或自采路侧视频上验证模型泛化能力，并分析夜间、雨雾、逆光等复杂条件下的检测表现。

## 7 结论

本文针对 DAIR-V2X-I 路侧图像中小目标比例高、目标密集和远距离目标易漏检的问题，提出一种改进 YOLO11n 的路侧小目标检测方法 YOLO11n-DWCA-P2。该方法以 YOLO11n 为基准，引入 DyHead 动态检测头和 Wise-IoU v3 边界框回归损失，增加 P2/4 高分辨率检测分支，并使用 CoordAttention 进行位置敏感特征辅助增强。

数据统计表明，本文数据集中 short side < 32 px 的目标占 87.55%，area < 32² px² 的目标占 79.65%，小目标检测需求明显。在统一 batch=32 训练口径下，最终 DWCA-P2 模型取得 86.0% Precision、83.5% Recall、88.4% mAP@0.5 和 64.4% mAP@0.5:0.95。与 YOLO11n baseline 相比，Recall 提升 2.7 个百分点，mAP@0.5 提升 2.4 个百分点，mAP@0.5:0.95 提升 4.2 个百分点。

消融实验进一步表明，P2 高分辨率检测分支是最终 Recall 与 mAP@0.5:0.95 提升的主要来源，DyHead 与 WIoU 的组合构成有效强基线，CoordAttention 则对 Precision 和 mAP@0.5 起辅助增强作用。本文方法提高了路侧小目标的检出能力和定位质量，为车路协同视觉感知中的轻量化检测模型改进提供了可行方案。

未来工作将从三个方面展开。第一，进一步筛选远距离小目标样例制作局部放大对比图，以更直观展示不同结构的检测差异。第二，结合 TensorRT、剪枝、量化和蒸馏降低部署成本。第三，将模型扩展到夜间、雨雾、逆光和多摄像头路侧场景，验证其跨场景泛化能力。

## 参考文献

[1] GIRSHICK R. Fast R-CNN[C]//Proceedings of the IEEE International Conference on Computer Vision. 2015: 1440.

[2] REN S, HE K, GIRSHICK R, et al. Faster R-CNN: Towards real-time object detection with region proposal networks[J]. IEEE Transactions on Pattern Analysis and Machine Intelligence, 2017, 39(6): 1137-1149.

[3] LIU W, ANGUELOV D, ERHAN D, et al. SSD: Single shot multibox detector[C]//European Conference on Computer Vision. Cham: Springer, 2016: 21-37.

[4] LIN T Y, GOYAL P, GIRSHICK R, et al. Focal loss for dense object detection[C]//Proceedings of the IEEE International Conference on Computer Vision. 2017: 2999.

[5] TAN M, PANG R, LE Q V. EfficientDet: Scalable and efficient object detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2020: 10778.

[6] REDMON J, DIVVALA S, GIRSHICK R, et al. You only look once: Unified, real-time object detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2016: 779.

[7] REDMON J, FARHADI A. YOLOv3: An incremental improvement[J/OL]. arXiv:1804.02767, 2018. https://arxiv.org/abs/1804.02767.

[8] BOCHKOVSKIY A, WANG C Y, LIAO H Y M. YOLOv4: Optimal speed and accuracy of object detection[J/OL]. arXiv:2004.10934, 2020. https://arxiv.org/abs/2004.10934.

[9] WANG C Y, BOCHKOVSKIY A, LIAO H Y M. YOLOv7: Trainable bag-of-freebies sets new state-of-the-art for real-time object detectors[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2023: 7464.

[10] JOCHER G, QIU J, CHAURASIA A. Ultralytics YOLO[EB/OL]. https://github.com/ultralytics/ultralytics, [2026-06-23].

[11] Ultralytics. Ultralytics YOLO11 docs[EB/OL]. https://docs.ultralytics.com/models/yolo11, [2026-06-23].

[12] LIN T Y, DOLLAR P, GIRSHICK R, et al. Feature pyramid networks for object detection[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2017: 936.

[13] LIU S, QI L, QIN H, et al. Path aggregation network for instance segmentation[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 8759.

[14] SINGH B, DAVIS L S. An analysis of scale invariance in object detection-SNIP[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 3578.

[15] AKYON F C, ALTINUC S O, TEMIZEL A. Slicing aided hyper inference and fine-tuning for small object detection[C]//2022 IEEE International Conference on Image Processing. Piscataway: IEEE, 2022: 966.

[16] HOU Q, ZHOU D, FENG J. Coordinate attention for efficient mobile network design[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021: 13708.

[17] HU J, SHEN L, SUN G. Squeeze-and-excitation networks[C]//Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition. 2018: 7132.

[18] WOO S, PARK J, LEE J Y, et al. CBAM: Convolutional block attention module[C]//European Conference on Computer Vision. Cham: Springer, 2018: 3-19.

[19] WANG Q, WU B, ZHU P, et al. ECA-Net: Efficient channel attention for deep convolutional neural networks[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2020: 11531.

[20] DAI X, CHEN Y, XIAO B, et al. Dynamic head: Unifying object detection heads with attentions[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2021: 7369.

[21] TONG Z, CHEN Y, XU Z, et al. Wise-IoU: Bounding box regression loss with dynamic focusing mechanism[J/OL]. arXiv:2301.10051, 2023. https://arxiv.org/abs/2301.10051.

[22] REZATOFIGHI H, TSOI N, GWAK J, et al. Generalized intersection over union: A metric and a loss for bounding box regression[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2019: 658.

[23] ZHENG Z, WANG P, LIU W, et al. Distance-IoU loss: Faster and better learning for bounding box regression[J]. Proceedings of the AAAI Conference on Artificial Intelligence, 2020, 34(7): 12993-13000.

[24] YU H, LUO Y, SHU M, et al. DAIR-V2X: A large-scale dataset for vehicle-infrastructure cooperative 3D object detection[C]//Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition. 2022: 21329.

[25] XU R, XIANG H, XIA X, et al. OPV2V: An open benchmark dataset and fusion pipeline for perception with vehicle-to-vehicle communication[C]//Proceedings of the IEEE International Conference on Robotics and Automation. 2022: 2583.

[26] XU R, XIANG H, TU Z, et al. V2X-ViT: Vehicle-to-everything cooperative perception with vision transformer[C]//European Conference on Computer Vision. Cham: Springer, 2022: 107-124.

[27] Ultralytics. Explore Ultralytics YOLOv8[EB/OL]. https://docs.ultralytics.com/models/yolov8, [2026-06-23].

[28] FENG Q, XU X, WANG Z. Deep learning-based small object detection: A survey[J]. Mathematical Biosciences and Engineering, 2023, 20(4): 6551-6590.

[29] LIN T Y, MAIRE M, BELONGIE S, et al. Microsoft COCO: Common objects in context[C]//European Conference on Computer Vision. Cham: Springer, 2014: 740-755.
[30] LIANG E, WEI D, LI F, et al. Object detection model of vehicle-road cooperative autonomous driving based on improved YOLO11 algorithm[J]. Scientific Reports, 2025, 15: 32348.
