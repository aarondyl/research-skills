from pathlib import Path
import json,shutil,hashlib
from PIL import Image,ImageOps,ImageDraw
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];out=HERE.parent if HERE.name=='system' else ROOT/'outputs/NV-CoT_mirror'
quality=json.loads((out/'quality.json').read_text(encoding='utf-8'))
raster=json.loads((out/'raster-review.json').read_text(encoding='utf-8'))
quality['raster_review_candidates']=raster
for p in quality['pages']:
    p['raster_review_candidates']=[r for r in raster if r['page']==p['page']]
    if p['raster_review_candidates']:p['status']='review'
(out/'quality.json').write_text(json.dumps(quality,ensure_ascii=False,indent=2),encoding='utf-8')
small=[(p['page'],x) for p in quality['pages'] for x in p['small_font_elements']]
overlaps=[(p['page'],x) for p in quality['pages'] for x in p['possible_box_overlaps']]
report=f'''# NV-CoT 中文镜像：架构修改与回归报告

## 结果与验收范围

输出是独立的 23 页中文版 PDF，每页保持原来的 612×792 pt 页面尺寸。对照阅读器的左右两侧均由 PDF.js 渲染 PDF；原 PDF 和中文 PDF 均内嵌，浏览器可离线打开。

这是一份保留原始版面的回归实现，不能宣称所有视觉文字均已完成无误的人工作业验收。未解决项单列如下。

## 根因

旧 work/build.py 只按页提取文字并拼接 HTML；work/make_pdf.py 与 work/render_revised.py 以固定页边距和游标 y 重新排布译文，再将新排版页面与原文合并。丢失了“译文—原文本对象—原始坐标”的关系。单独裁剪公式再按新宽度插入，会进一步改变公式位置和比例。表格也是重新创建，图片未出现在中文版的原始位置。仅靠提示词、CSS 或调整字号无法恢复这些信息。

## 新架构与文件清单

- system/pipeline.py：PyMuPDF 结构解析、原坐标替换、局部适配、像素和对象回归检查；同时导出 46 张原文/译文截图。
- system/mappings.py：NV-CoT 人工核对的语义段落与原生元素 ID 映射、图注和图内标签翻译。
- system/translation_revised.txt：可追踪的既有审校译文缓存。渲染不将其拼接成新文章。
- system/llm_adapter.py：可选的 JSON 聊天端点适配器，提供摘要上下文、统一术语和元素 ID；保护数学占位符并验证无丢失、重复或新增 ID。当前回归复用审校缓存，未调用付费远端服务。
- system/inspect_raster.py：OCR 识别图像载体中的自然语言候选，低可靠性内容只报告、不猜测、不重绘实验图像。
- system/viewer.js 与 system/package_viewer.py：将原版、中文版、PDF.js 和质量结果封装为单文件离线阅读器。
- layout.json：逐页尺寸、文本块与行/字体/方向/坐标、阅读顺序、图片摘要与位置、绘图对象、公式保护区域及表格候选。
- translations.json：每条译文关联原始 ID、源文、Bounding Box、替换方法、实际缩放比例和适配结果。
- quality.json、unmapped.json、ocr-candidates.json、raster-review.json：机器可读检查及审校记录。
- screenshots/：每页原文和译文截图；reader-preview.png：浏览器双 PDF 实际截图。

原始图片、曲线、箭头、网格、表格数字与独立公式均基于原 PDF 保留；文本删除采用 images=0、graphics=0 的文本专用处理，避免误删图像或绘图。删除区域内缩，防止 PDF 字符边界重叠造成相邻图例文字消失。Figure 2 的轮廓字采用 OCR 辅助检测并人工核对坐标，仅在轴标签处覆盖写入中文。

## 回归检查结果

- 页数：原文 {quality['page_count_source']} / 中文 {quality['page_count_translation']}。
- 所有页面尺寸一致：{quality['all_pages_same_size']}。
- 原始 32 个图片实例的摘要及坐标全部保留：{quality['all_source_images_preserved']}。
- 文本框溢出：{quality['total_overflows']}。
- 未映射原生自然语言文本块：{quality['total_unmapped']}（姓名、模型名、变量和基准名称按要求保留）。
- 替换区域及 3 像素抗锯齿边缘外的像素变化：{quality['total_outside_mask_changed_pixels']}。
- 15 个独立公式区域（含未编号 SFT 损失）的数学区域像素未变；公式中单独替换的自然语言说明从比较掩膜排除，数学符号不覆盖。
- 第 5 页归一化优势的行内分式采用原始矢量对象在原位恢复，该区域完整像素比对变化为 0，而非仅保留分数线。
- 新增 Unicode 替换字符：{sum(p['new_unicode_replacement_characters'] for p in quality['pages'])}。
- 潜在替换框显著重叠：{len(overlaps)}。这里是几何候选检查，不能替代全部视觉审校。
- 已对第 5 页原生分式拆块造成的两处重叠执行局部语义合并修复，子元素 ID 全部保留。
- 5 项契约测试通过：重叠正文合并且不合并公式、数学占位符往返、拒绝未知 ID、拒绝丢失或重复数学占位符。
- 每页均输出截图；对首页标题/作者/摘要/Figure 1、第二页 Figure 2、公式页、表格页做了可视复核。
- 浏览器测试结果详见 viewer-tests.json：离线载入、页码跳转、同步滚动、同步缩放、单双页布局、原文/译文切换、质量面板、PDF 下载与脚本错误检查。

## 尚未解决的问题

1. 第 16 页示例图的原始文档截图中，OCR 识别出 3 条候选：TABLE、LUNCH，以及疑似识别错误的 EOETATDAMACE。它们属于低分辨率图像载体内的文字，不是可编辑的图注。为防止改写原始视觉证据和误译，均保留并标记人工审核。**因此“所有图内英文均已替换”这一项尚未完全通过。** OCR 也不能证明不存在其他未检测出的微小图像文字。
2. 保持原位和原标签框后，有 {len(small)} 处有效字号低于 5 pt：{', '.join(x for _,x in small)}。均为微小图内标签，建议在阅读器中放大检查。未扩大遮盖区域侵入曲线或坐标数据。
3. 独立公式保留原始 PDF 对象；行内数学依赖译文中的 Unicode 和上下标转换，仍需人工核对每处索引、粗体向量及公式引用，不能以像素检查代替语义证明。
4. 原论文中的公式（2）交叉引用、公式（10）的 Y_A 符号及表 1 的增量不一致等疑点，仍保留原文，另见既有待审校项。未自行修正科学内容。
5. 构建期间 MuPDF 对部分原始字体发出 CFF/maxp 子集兼容警告。渲染后的保护区域像素检查未发现额外变化，但其他 PDF 引擎仍应进行字体兼容性复核。
6. 当前精确图区和保护区配置针对 NV-CoT 回归样本。另一篇论文会要求显式翻译清单或配置 LLM 端点，不会套用 NV-CoT 译文。扫描件、复杂旋转/跨栏表格和未被原生解析识别的公式，仍需额外版面检测及人工审校；没有宣称通用文档的全自动精确镜像已完成。

## 复现

需要 Python 3.12，按 system/requirements.txt 安装依赖。进入此目录后运行：

```powershell
python system/pipeline.py --source original.pdf --out .
python system/inspect_raster.py
python system/finalize.py
python system/package_viewer.py --out . --pdfjs-dir system/vendor
python system/test_core.py
```

finalize.py 将 raster-review.json 合并至质量状态并生成此报告，再封装阅读器。字体默认使用 Windows Fonts 中的宋体、黑体、Times 与 Cambria；可通过 PDF_TRANSLATION_FONT_DIR 指定含对应字体文件的目录。浏览器测试需安装 Playwright，运行 node system/test_viewer.cjs .，可用 PDF_TEST_BROWSER 指定浏览器路径。对不同论文先运行 --parse-only 检查 IR，随后用 --translations-file 指定按 ID 的翻译清单，或配置 --llm-url 与 --model；密钥仅从 PDF_TRANSLATION_API_KEY 环境变量读取。通用模式必须人工确认图区/表格和公式保护识别，不能直接视为通过验收。
'''
(out/'架构与审校报告.md').write_text(report,encoding='utf-8')
(out/'system/requirements.txt').write_text('PyMuPDF==1.26.7\nnumpy>=2.0\nPillow>=11\nrapidocr_onnxruntime==1.4.4\n',encoding='utf-8')
(out/'system/glossary.json').write_text(json.dumps({'multimodal large language model':'多模态大语言模型','visual chain-of-thought':'视觉思维链','grounding':'定位','bounding box':'边界框','patch':'图像块','token':'词元','supervised fine-tuning':'监督微调','reinforcement learning':'强化学习','importance ratio':'重要性比值','Gaussian policy':'高斯策略','Laplace policy':'拉普拉斯策略','reparameterization':'重参数化'},ensure_ascii=False,indent=2),encoding='utf-8')
# Contact sheet is an inspection aid, not a substitute for the full-resolution pages.
sheet=Image.new('RGB',(5*220,5*308),'#dce3e1');draw=ImageDraw.Draw(sheet)
for i in range(23):
    im=Image.open(out/'screenshots'/f'{i+1:02d}-translated.png');im.thumbnail((210,280));x=(i%5)*220+5;y=(i//5)*308+20;sheet.paste(im,(x,y));draw.text((x,y-16),str(i+1),fill='black')
sheet.save(out/'all-pages-preview.jpg',quality=90)
print('Report created. Small labels:',len(small),'Overlap candidates:',len(overlaps),'Raster review:',len(raster))
