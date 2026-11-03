"""NV-CoT regression fixture: reviewed translations tied to native PDF block IDs.
Paragraph text is reused from the reviewed translation, never laid out across pages.
"""
import re
from pathlib import Path

def translations(root):
    fixture=root/'translation_revised.txt'
    if not fixture.exists():fixture=root/'work/translation_revised.txt'
    pages=[[x for x in p.strip().splitlines() if x] for p in fixture.read_text(encoding='utf-8').split('===PAGE===')]
    # page -> source block -> translation paragraph indices
    indices={
      1:{0:0,3:3,4:[4,5],28:9,29:10},
      2:{1:1,3:2,4:3,5:[4,5],6:6},
      3:{0:0,1:1,2:2,3:3,4:4,5:5,6:[6,7],7:8,8:9},
      4:{0:0,2:2,3:3,4:4,5:5,10:7,11:8,12:9,13:10,15:12,16:13,19:15,23:17},
      5:{0:0,2:2,3:3,4:5,5:6,17:9,18:10,19:11,20:12,24:14,25:15,29:17},
      6:{0:0,2:2,8:4,9:5,10:6,11:7,12:8,13:9,14:10,15:11,16:12,17:13},
      7:{0:[0,1],10:3,11:5,12:6,13:7,14:8},
      8:{12:7,13:8,14:9,15:10,16:11,17:12,18:13},
      9:{7:0,8:2,21:4,22:6,23:7,36:11,37:12,38:13,39:14,40:15},
      10:{8:0,9:2,53:[4,5],54:7,55:[8,9],56:10},
      11:{0:0,1:1,2:2,3:3},
      14:{8:9,9:10,10:11,11:[12,13,14],12:15},
      15:{0:0,1:[1,2],2:3,3:[4,5],4:6,5:[7,8,9,10],6:11,7:12,8:13,9:14},
      16:{0:0,1:1,42:2,43:4,44:5,45:[6,7]},
      17:{0:0,1:1,2:2,3:3,5:4,6:5,7:6,8:7,11:[8,9,10],12:11,13:12},
      18:{0:0,1:1,2:[2,3,4],3:[5,6,7,8]},
      19:{0:0,1:1,4:[2,3],5:4,6:5,7:6,10:7,11:8,12:9,13:10,16:11},
      20:{0:[0,1],1:2,2:3,3:4,6:5,7:6,8:7,9:8,12:9,13:10,14:11,15:12},
      21:{0:0,1:[1,2,3,4],2:[5,6],3:6,4:[7,8],5:[9,10],6:11},
      22:{0:[0,1],1:[2,3],2:[4,5],3:[6,7],4:7,5:[8,9,10,11]},
      23:{0:0,1:[1,2],2:[3,4],3:4,4:5},
    }
    out={}
    for pg,blocks in indices.items():
        for bid,idx in blocks.items():
            if not isinstance(idx,list):idx=[idx]
            out[f'p{pg}.b{bid}']='\n'.join(re.sub(r'^#{1,2} ','',pages[pg-1][j]) for j in idx)
    # Full citation entries, still attached to their original native text boxes.
    refs={int(m.group(1)):m.group(0) for p in pages for s in p if (m:=re.match(r'^\[(\d+)\].*',s))}
    for pg,bstart,nstart,count in [(11,4,1,14),(12,0,15,18),(13,0,33,17),(14,0,50,8)]:
        for j in range(count):out[f'p{pg}.b{bstart+j}']=refs[nstart+j]
    # Caption translations must contain only captions, not explanations or table data.
    out.update({
      'p1.b0':'以连续动作进行图像思考：\n数值视觉思维链',
      'p1.b2':'¹南洋理工大学　²中国科学技术大学　³新加坡国立大学　⁴微软研究院\n通讯作者：Beier Zhu <beier.zhu@ustc.edu.cn>',
      'p1.b27':'图 1：不同图像思考范式的比较。（a）基于文本的方法将定位区域表示为离散坐标词元，导致模态不匹配和语义碎片化。（b）基于图像块的方法直接对细粒度视觉词元进行推理，但受视觉骨干固定空间粒度的限制。（c）NV-CoT 在连续空间预测区域坐标，实现灵活、精确的定位。',
      'p1.b29':out['p1.b29'].replace('这种以区域为依据的视觉推理是 MLLM 的一项基础能力，并支撑着广泛的下游应用。','这种'),
      'p1.b30':'第 40 届神经信息处理系统大会（NeurIPS 2026）。',
      'p2.b0':'（a）定位精度　　　　　　（b）最终答案准确率',
      'p2.b1':'图 2：NV-CoT 在 SFT 和 RL 下的定位精度、答案准确率和收敛速度均优于基于文本的视觉 CoT 模型（Vis-CoT [2]、DeepEyes [1]）。基于 SFT 的模型在提供真实边界框的 Vis-CoT-363K 数据集 [2] 上评估；基于 RL 的模型在 DeepEyes-47K 数据集 [1] 上评估。为公平比较，我们仅将文本空间中的离散坐标目标替换为欧氏空间中的连续目标，其余训练配置全部保持不变。',
      'p2.b2':'以区域为依据的视觉推理是 MLLM 的一项基础能力，并支撑着广泛的下游应用。',
      'p7.b0':'表 1：高分辨率基准结果。最佳结果以粗体表示。NV-CoT 在 SFT 和 RL 下均持续提高性能。NV-CoT（SFT）使用 ℓ₁ 损失，NV-CoT（RL）使用拉普拉斯策略。DeepEyes-7B† 和 NV-CoT† 表示多步工具使用（多次放大）。为公平比较，其余视觉 CoT 方法均仅使用一次放大，因为部分基线不支持多次工具调用。',
      'p7.b10':'表 2：通用多模态基准上的性能比较。NV-CoT 在 MMMU-Pro、ChartQA 和 OCRBench v2 上均取得最佳性能。',
      'p8.b2':'表 3：纯文本推理基准上的性能。NV-CoT 在 MMLU 和 GSM8K 上保持与 Qwen2.5-VL-7B 相当的性能。',
      'p8.b3':'表 4：定位和计数基准上的性能比较。NV-CoT 在 RefCOCO 系列、COCO 检测和计数任务上均持续优于强基线。',
      'p8.b6':'表 5：坐标策略（高斯，ℓ₂²；拉普拉斯，ℓ₁）及不确定性参数化（共享 σ/α 与逐坐标 σ/α）消融。非共享 σ/α 由四个头预测逐坐标尺度（标准差）。拉普拉斯策略持续优于高斯策略，共享与逐坐标 σ/α 的结果相当。',
      'p9.b7':'图 3：α 的行为。成功轨迹的 α 小于失败轨迹，反映更高置信度。',
      'p9.b8':'表 6：Vis-CoT-363K 数据集上的边界框 IoU。NV-CoT 显著提高相对 Vis-CoT 的定位精度，且 ℓ₁ 损失优于 ℓ₂² 损失。',
      'p9.b21':'图 4：λ 的影响。λ=0.3 时性能达到峰值；所有 λ 取值下 NV-CoT 均优于基线。',
      'p9.b22':'Vis-CoT-363K 验证集上的边界框 IoU。表 6 表明，NV-CoT 显著提高相对 Vis-CoT 的定位准确率，其中 ℓ₁ 损失的 IoU 最佳。',
      'p9.b24':'这推广了公式（1）的共享方差形式。重要性比值变为：',
      'p10.b8':'图 5：RL 训练动态。平均奖励在训练中持续上升，而每条轨迹的工具调用次数在训练进度 60% 处达到峰值，随后下降。',
      'p10.b9':'表 7：文本与坐标动作的 RL 策略统计。裁剪 ε=0.2；梯度范数占比在各分支间归一化。',
      'p10.b53':'图 6：边界框可视化。相比骨干模型（蓝色），NV-CoT（红色）产生更准确的边界框，体现其定位能力的改善。',
      'p11.b3':'参考文献',
      'p16.b42':'图 7：更多边界框可视化结果。相比骨干模型（蓝色），NV-CoT（红色）产生更准确的边界框，体现其定位能力的改善。',
    })
    # Individual checklist answer and justification boxes remain separate.
    for pg in range(17,24):
        for k,v in list(out.items()):
            if k.startswith(f'p{pg}.'):
                out[k]=v.replace('## ','').replace('**','')
    return out

LABELS={
'Abstract':'摘要','Guidelines:':'指南：','Model':'模型','Attr':'属性','Spatial':'空间','Overall':'总体',
'Gaussian policy':'高斯策略','Laplace policy':'拉普拉斯策略','Independent':'独立','loss':'损失',
'Action type':'动作类型','Text':'文本','tokens':'词元','Coordinate':'坐标','actions':'动作',
'Mean ratio':'比值均值','Std. ratio':'比值标准差','Clipped fraction':'裁剪比例','Gradient share':'梯度占比',
'Failure':'失败','Success':'成功','Baseline Performance':'基线性能','Bbox IoU':'边界框 IoU',
'Training progress':'训练进度','Mean reward':'平均奖励','Mean tool calls per trajectory':'每条轨迹平均工具调用数',
'Mean value':'均值','Mean of':'均值','Acc. (%)':'准确率（%）',
'pepper mill':'胡椒研磨器','camera':'相机','bottle':'瓶子',
'(a) Text-based visual CoT':'（a）基于文本的视觉 CoT',
'(b) Patch-based visual CoT':'（b）基于图像块的视觉 CoT',
'(c) Numerical visual CoT (ours)':'（c）数值视觉 CoT（本文）',
'model "6" as a discrete token':'将“6”建模为离散词元',
'fixed patch granularity and architectural modifications':'固定图像块粒度及架构修改',
'522.6 as a continuous value':'将 522.6 作为连续值',
'(a) Reinforcement Learning':'（a）强化学习','(b) Supervised Fine-Tuning':'（b）监督微调',
'Answer: [Yes]':'回答：[是]','Answer: [No]':'回答：[否]','Answer: [N/A]':'回答：[不适用]',
}
