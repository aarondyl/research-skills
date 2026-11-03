# 工具用法与数据约定

依赖 Python、PyMuPDF（已验证 1.26.7）、numpy；用当前可用运行时，缺依赖时安装到任务虚拟环境。无需固定 Aaron 用户路径。`scripts/mirror.py` 提供保守的通用解析、试排与检查入口；翻译由助手完成，脚本本身不调用远程模型。

```text
python scripts/mirror.py parse --source paper.pdf --out job
python scripts/mirror.py render --source paper.pdf --out job --manifest job/manifest.json --fonts <font-directory>
```

parse 生成 layout.json 与 manifest.template.json。先阅读原文与 layout，完善术语表，再将模板逐条变为 manifest.json。模板绑定 source_sha256，防止错用另一篇论文；每条有 id、action、translation、style、font_size、line_height。action 必须明确改为 translate 或 preserve；preserve 需 reason。不得为逃避翻译把正文标 preserve。

style 允许七种用户要求的元素类型；heading_level 要结合原式确认后写入布局或通过 style 表达。模板正文继承源字号、行高起点 1.12；标题和图注使用本技能目标。复杂混合公式块不要直接整块覆盖：在任务副本中拆分结构/扩展脚本，保留公式对象，然后运行独立公式检查。通用脚本会拒绝含明显数学字体或与图片重叠的块，以防未经分析删损；这不是论文未完成时停止工作的理由，应精修或列出无法完成的具体区域。

默认字体目录需有 simsun.ttc、simhei.ttf、times.ttf、cambria.ttc、msyhbd.ttc；其他系统在脚本任务副本里映射字体。字号、行距可逐条指定；bbox 默认原框，可在检查周围障碍物后明确指定本页局部微调。不会自动把标题扩大到整栏。

脚本对每个块试排成功才删除源文字，保留非文字对象，并检查图片、页尺寸、框外像素与逐页截图。quality.json 的 auto_checks_passed 不代表语义、图内 OCR、公式或视觉全通过。拒绝项写入报告，原文保留。输出 translated.pdf 是待审校产物，验收后再命名交付。

完整 NV-CoT 专用引擎、样式映射、翻译缓存、OCR 检查、阅读器及局部 restyle 工具在 assets/nv-cot/。遇到需要复杂修复的版式可参考其实现，但不要沿用论文 ID 或硬编码坐标。原引擎个别路径是历史实现，通用新论文优先用本脚本和明确 manifest。
