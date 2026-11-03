# NV-CoT 已验收回归示例

论文：Thinking with Images as Continuous Actions。已验收版本是中文镜像的局部字体优化版，不是早期重新排版的 HTML/PDF。

历史工作目录：D:/Documents(文档)/Codex/2026-11-01/ban。
最终 PDF：outputs/NV-CoT_字体优化/NV-CoT_中文镜像_字体优化.pdf。
基线目录：outputs/NV-CoT_mirror，含 original.pdf、layout.json、translations.json、quality.json。

最终实测：23 页，612×792 pt；23 个标题和 7 个图注调整；一级 12.5 pt 真粗体，3.2/3.3 均 10.75 pt；图注一般 8.5 pt/1.20，Figure 6 为 8.25 pt/1.10；30 区域均原目标字号排入，溢出 0。局部调整框外逐页像素变化 0。Figure 1 按 (a)/(b)/(c) 换行；Figure 2 图注仍在右侧，其框内顶部 6 pt 留白。此论文没有独立三级标题。

保留在 assets/nv-cot/ 的脚本是本次真实工作产物，含论文专用修复；不是通用解析器。pipeline.py 的 FORMULAS、compile_jobs、图 2 标签坐标、p5 分式修复及 typography.py 的 ID/边界规则均不得套用其他论文。finalize.py、inspect_raster.py、typography_report.py 还含历史工作目录约定，应先复制到任务工作目录再检查路径。不要直接运行其默认路径覆盖用户已验收文件。

复现最终局部调整（输入为基线目录，输出必须是新目录）：

```text
python assets/nv-cot/restyle.py --base <baseline-directory> --out <new-output-directory>
```

要求 PyMuPDF 1.26.7、numpy 及 C:/Windows/Fonts 中原字体。此命令不需联网翻译。历史最初输入在 Zotero 临时拖放目录，重现时应使用持久 original.pdf，避免依赖临时路径。

历史全文镜像仍记录了图内 OCR 候选、极小标签及行内数学审校限制；用户认可最终字体版不意味着这些问题已全部消除。将历史基线结果与新运行结果分开，不能把这里的数字当作新论文验收结果。
