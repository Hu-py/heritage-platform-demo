# HERISK 文物保护规划知识库

本地可用版本：PDF 页级证据图谱 + 既有专业关系导入 + 中英概念检索 + HERISK 建筑诊断关联。DeepSeek 抽取和生成接口已实现，但未配置密钥、未实际调用模型。不要把接口可用等同于生成内容已验证。

## 直接使用

1. 启动 `../heritage-platform/启动平台.command`。
2. 打开 http://127.0.0.1:8765/knowledge.html 。可输入中文或英文检索，查看原文证据、候选关系、检索关系图、文献目录，点击引用定位 PDF 物理页码。
3. 在主平台地图选择文物 → “规划反馈响应”，按照当前风险类别查看相关证据。顶部“规划知识库”可以进入独立工作台。
4. 图谱展示的是当前检索的相关子图；共现、词语匹配、查询扩展不表示已证明的因果或适用策略。

## 当前数据

- 48 份去重 PDF：新资料 44 份 + rag_workbench 4 份，867 页。
- 2,442 个页内检索片段；正文切分目标 1,400 字符、重叠 180 字符，不跨 PDF 页。
- 已排除学术论文参考文献段落的检索索引，完整原页仍保留。
- 44 个双语受控概念（保护原则、风险、策略、措施、材料、对象身份、规范、案例等）。
- 763 处文物及当前平台的一级/三级原始评分、属性和外部风险记录。
- rag_workbench 的 79 条候选关系：PDF SHA256 与旧缓存匹配，引用逐条匹配对应页；均保持待人工复核，未自动升级为知识事实。
- 首轮对 52 个低文本/仅水印页尝试 OCR；其中包含空白页。新资料的标准扫描页和扫描论文已补 OCR；既有 4 份资料按 SHA256 复用旧页缓存。OCR 仍可能有错字。
- 图数据：32,917 个节点、41,875 条边，主要是评价记录、出处和概念提及，**不是 41,875 条经过验证的保护规则**。

准确统计以 `reports/build.json` 为准。PDF、解析文本、数据库都在本地，未上传 GitHub，未放入网站 public 目录；仅由本机服务按已登记文献 ID 提供 PDF。

## A / B 架构

A 评价图：`site → HAS_ATTRIBUTE / HAS_ASSESSMENT / HAS_EXTERNAL_RISK → record → source`。
每处建筑的评价节点使用独立 ID，避免多个文物共用指标名称后覆盖分数。原始 JSON 字段和数组位置保留。现阶段来源是本地整理后的 `sites.json`，不是参考项目数据库中的 Excel 原始行号；没有伪造这部分血缘。

B 规划图：`document ← PART_OF ← passage → MENTIONS → bilingual concept`，以及带原文、页码、证据性质、条件的专业候选关系。

连接桥：`assessment → RETRIEVAL_HINT → risk concept → EXPANDS_QUERY_TO → strategy / measure concept`。桥接与扩展是可编辑的检索规则，不是“该建筑发生了这种损伤”或“该措施已证实有效”的断言。规则在 `ontology.json`。

## 为什么没有直接照搬参考项目

`reference/LLM-history-buildings/` 是用户指定 GitHub 仓库的本地浅克隆，保留来源与版本；没有执行其安装/导入脚本。该项目公开代码主要实现评价、证据来源、资料审核及图谱展示；PDF 上传要求人工摘录，没有完整的自动 PDF 专业知识抽取流程。线上 D1/R2 数据不包含在这份仓库克隆中，因此这不是其线上数据库的完整备份。没有发现该仓库根目录的统一开源许可，当前仅本地留存参考，未再次公开发布代码或资料。

用户补充的 `规划数据库/rag_workbench/` 更贴近本需求：DeepSeek 逐片段抽取、引用逐字校验、按类型精确别名融合、保留否定和条件。其 `../code/multi_pdf_rag.py`、`rag_knowledge_graph.py` 与部分模板缺失，无法原样重跑。本实现不依赖缺失模块，导入已生成声明并重新核验；原目录未修改。

## 中英文如何处理

- 不翻译覆盖原文。PDF 文件、物理页码、原文语言、OCR 方法、原句一起保存。
- 用中英文别名映射到稳定概念 ID，例如 `施工振动 / vibration → concept:vibration`。
- 检索结合中文双字词、英文词的 SQLite FTS5 BM25 和一跳概念图扩展。中文查询可以匹配英文片段，英文查询也能找到中文依据。
- 模型如需输出中文解释，原文引用仍保留原语言；翻译不能冒充原文证据。
- **这是受控词汇跨语言检索，不是跨语言向量模型。** 当前词表以本项目保护议题为范围；未覆盖的术语、复杂意译可能漏检。扩充 `ontology.json` 后重建即可。后续可增加 BGE-M3 等多语嵌入与重排序，需另行安装模型和做检索评测，当前没有假称已完成。

## 重建与命令行

在项目根目录运行（本机 Poppler 与 Tesseract 已可用）：

```sh
/opt/anaconda3/bin/python heritage-knowledge/scripts/extract_documents.py
/opt/anaconda3/bin/python heritage-knowledge/scripts/enrich_metadata.py
/opt/anaconda3/bin/python heritage-knowledge/cli.py build
/opt/anaconda3/bin/python heritage-knowledge/cli.py search '施工振动 砖木建筑 监测'
/opt/anaconda3/bin/python heritage-knowledge/cli.py search 'authenticity minimum intervention'
/opt/anaconda3/bin/python heritage-knowledge/cli.py plan G-2 --risk development
/opt/anaconda3/bin/python heritage-knowledge/cli.py export /tmp/herisk-graph.json
/opt/anaconda3/bin/python -m unittest discover -s heritage-knowledge/tests -v
```

将新 PDF 放入 `规划数据库/文物保护规划响应_PDF资料下载包/已下载PDF/` 的对应类别子目录。可在原来源清单 CSV 补充题名、URL、发布者和年份；重跑解析、元数据与构建步骤。以文件 SHA256 去重，同内容不同路径不会重复入库；改变文献会生成新记录。页缓存依文件校验值复用，不复用不同内容的旧结果。数据库先在临时文件构建，完成后原子替换。

`data/documents.json` 是文献清单；`data/extracted/` 保存页级文本；`data/knowledge.sqlite` 是完整数据库；`reports/` 保存核查报告。用脚本导出全量图数据，不建议在浏览器一次画全部节点。

## 启用 DeepSeek（尚未执行）

创建 `heritage-knowledge/.env.local`，按 `.env.example` 设置：

```dotenv
DEEPSEEK_API_KEY=在本机填写你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-flash
```

密钥只在服务端读取，不发送给浏览器，不应提交 GitHub。模型名可配置。接口按 [DeepSeek Chat Completions 官方文档](https://api-docs.deepseek.com/api/create-chat-completion/)实现，使用 JSON 输出；模型计费、额度由你的账号承担。

按查询小批量抽取专业关系：

```sh
/opt/anaconda3/bin/python heritage-knowledge/cli.py enrich '施工振动 监测 保护措施' --limit 8
/opt/anaconda3/bin/python heritage-knowledge/cli.py plan G-2 --risk development --generate
```

前者发送最多 8 个检索片段，逐段缓存模型输出，校验实体、原句、条件与类型后保存为待复核声明；重建会恢复可验证的缓存。后者只发送当前建筑诊断和最多 8 条检索证据，生成有引用的结构化策略草案。网页中也可主动点击生成按钮。未配置时仅检索，按钮明确显示待配置。

模型输出校验：拒绝未知引用 ID、原文不存在的引句、无证据策略、越出类型范围的抽取。**程序只校验引用定位和文字匹配，不证明引文足够支持策略、不证明法规适用性，也不替代专家。** 未现场验证的高敏感性不能写成病害已发生；不自动生成法定边界、许可结论或工程参数。

## 来源适用性与质量

- 每份资料 `validity=not_verified`，未宣称截至今天仍有效；原来源清单的“现行”属于来源题名，使用时仍需核查最新版本。
- GB 55035-2023 的 PDF 物理第 5 页（1.0.2）写有文物建筑及文物保护单位除外。对本平台文物对象的规划证据检索默认过滤该文件；一般检索保留并醒目标注适用范围。正式使用仍需核对对象身份与条款。
- DG/TJ08-108-2025 文件仅为批准实施通知，不是标准全文，单独标注、降权，不据此生成技术要求。
- 法规、国际准则、学术论文、既有专题资料分类保存；研究案例的效果不能无条件推广到不同材料或地区。
- 不同语言的同一文件、案例未做语义级去重；当前只按 PDF 字节哈希去重。
- 图表、表格、跨页条款可能受解析顺序影响；索引不跨页，跨页论证可能漏检，原 PDF 可用于复核。
- 公开下载不等于可再分发；PDF、全文缓存、生成数据库默认不进入 GitHub。
