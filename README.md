# 成都行业问题模型回答快照 · B01–B06

**English abstract.** This dataset contains 1,686 saved model answers to 234 author-designed questions across six Chengdu-related batches collected between September 29 and October 16, 2026. It preserves question wording, within-batch repetitions, model identifiers, timestamps, search observations and source order, with entity names pseudonymized and street-number-level addresses masked to district/street level. Public scripts reproduce the published B01 counts. Each batch is a single-day snapshot; these records are model outputs and do not establish rankings, factual accuracy or commercial performance. Data: CC BY 4.0. Code: MIT.

作者为王涛（Taomir），ORCID：[0009-0004-5104-1811](https://orcid.org/0009-0004-5104-1811)。本包只包含 B01–B06；这是已有采样记录的本机整理版，构建日为 2026-10-22。公开内容包含题集、代号化后的回答、来源域名与标题、复算代码和摘要承诺。未包含原始 API 请求、完整响应、请求头、账号、请求标识或私有代号表。

## 批次与模型

| 编号 | 名称 | 采样日 | 题数 | 每题每平台次数 | 有效回答 | 平台 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| B01 | 成都住宅（综合与细分需求） | 2026-09-29 | 50 | 5 | 250 | 豆包 |
| B02 | 成都进销存软件与服务商 | 2026-10-15 | 40 | 3 | 360 | 豆包、DeepSeek、千问 |
| B03 | 成都婚纱摄影 | 2026-10-15 | 40 | 3 | 360 | 豆包、DeepSeek、千问 |
| B04 | 成都留学咨询 | 2026-10-16 | 40 | 3 | 360 | 豆包、DeepSeek、千问 |
| B05 | 成都汽车贴膜 | 2026-10-13 | 36 | 6（同日 3+3） | 216 | 豆包 |
| B06 | 成都高新南改善住宅 | 2026-10-10 | 28 | 5 | 140 | 豆包 |

合计 234 道题、1,686 条有效回答、0 条记录状态为失败的回答。B06 有 16 道点名题，其余五批均为 0。模型标识如下，逐批信息以 `batches.csv` 为准。

- 豆包（`doubao`）：`doubao-seed-2-0-lite-260215`
- DeepSeek（`deepseek`）：`deepseek-v4-flash`
- 千问（`qianwen`）：`qwen3.6-flash-2026-04-16`

模型、平台和原始协议并不完全相同。未显式设置的参数沿用平台默认值；B01 原协议显式设置温度为 0，不能概括为全部参数均使用默认值。这里保留已有运行结果，没有重新采样。

## 联网字段怎么读

`web_search_requested` 表示请求配置，`web_search_observed` 表示保存记录中的观测证据。`true`、`false`、`null` 分别表示观察到、明确未观察到、记录不足以判断。来源列表或回答自称“搜索”不单独证明发生了搜索调用。

| 批次 | 豆包：观察到 / 总数 | DeepSeek：观察到 / 总数 | 千问 |
| --- | ---: | ---: | --- |
| B01 | 0 / 250 | — | — |
| B02 | 120 / 120 | 87 / 120 | 120 条均未知 |
| B03 | 120 / 120 | 92 / 120 | 120 条均未知 |
| B04 | 120 / 120 | 79 / 120 | 120 条均未知 |
| B05 | 216 / 216 | — | — |
| B06 | 140 / 140 | — | — |

各批均请求联网。B01 的旧调用计数字段为正，但 250 条的传输验证均为 false，状态均明确记录未观察到搜索；导出以明确的传输验证与状态为准，故 B01 为 250 条 false。其余批次依据保存的调用计数；千问缺少可判定的调用计数，保留 null，没有填成 0 或 false。

## 文件与字段

`batches.csv` 每批一行；`data/Bxx/questions.csv` 保留题号、分类、代号化题面和原点名题标记；`data/Bxx/answers.jsonl` 每行一条回答，按题号、平台、轮次排序。`round` 为批内原轮次，B05 的 1–6 对应同日两组各三次。

回答包含 `batch_id`、`record_id`、`question_id`、`platform`、`model`、`sampled_at`、`round`、两个联网字段、`answer_text`、`sources`、`status`、`finish_reason`。时间均转为 Asia/Shanghai，使用带 `+08:00` 的 ISO 8601。`record_id` 是公开记录编号。

`sources` 保留原列表顺序与重复项，每项为 `order`、`url`、`title`、`kind`、`published_at`。`kind=citation` 直接来自原记录的 `citation_items` / `citations` 列表，`kind=search_result` 直接来自 `search_results` 列表。结构化引用不等于已核查页面支持了回答中的某句话，正文 Markdown 链接也不会另计为结构化引用。有两种列表时，按原引用列表在前、搜索结果列表在后的顺序导出；同一页面重复出现仍逐项保留。网址统一为 HTTPS 可注册域名；品牌自有域名改为代号域名。B02 有 1 个来源指向本地文档路径，无法形成公开网站域名，故 url 为 null，标题仍保留并代号化。

`published_at` 仅取保存来源项的 `published_at`、`publish_time` 或内嵌 `original.publish_time`；搜索结果的 `page_age` 在这些输入中均为空。保存的中文日期带 CST 标记，按该协议的中国标准时间转为带 `+08:00` 的 ISO 8601；日期若只有年月日则只保留日期。没有日期或仅有不能确定绝对时间的表述时为 null，不从采样日、标题年份或现在的网页补齐。该值表示来源元数据所报日期，不证明真实首发时间，原记录中晚于采样日的日期也照实保留。

| 平台 | citation | search_result | published_at 非空 | published_at null |
| --- | ---: | ---: | ---: | ---: |
| 豆包 | 3,348 | 0 | 3,343 | 5 |
| DeepSeek | 0 | 5,600 | 0 | 5,600 |
| 千问 | 0 | 0 | 0 | 0 |

共 8,948 个来源项。缺少来源项不单独证明未联网。URL 已收敛到可注册域名，因此无法恢复逐页去重或原主机名口径。

`status=valid` 沿用采样记录或表示成功保存了非空回答，不表示回答事实已经核查。回答中自然语言描述搜索故障的内容仍按原记录保留。结束原因缺失时为 null；B01 全部缺失，不猜测补齐。

## 代号化与复算边界

实体采用 `〔B01-E017-a〕` 格式。E 编号按本批题号、平台、轮次顺序中的首次出现位置分配；同一实体的不同写法使用不同字母，长写法优先替换。代号不跨批关联，实体数量也不等于被推荐品牌的数量；字典还包含开发商、学校、配套机构和只在自有域名中出现的实体。

保留地名、媒体和平台、政府机构及通用词。按作者确认的实体语境验收，短写法出现在地名、媒体名称或普通表达中时保留。人名和联系方式使用对应中文占位符。网址只保留域名，路径、参数和子域名均不公开。**代号化用于避免直接点名，不保证不可识别**；区位、地址、产品描述及题目上下文仍可能让读者识别实体。

门牌地址已隐去到区/街道级：回答正文和来源标题中的门牌号、附号、楼栋、单元、楼层、房号及紧随门牌的写字楼、商场名称统一替换为 `〔门牌已隐去〕`，区、街道和路名保留；地铁线路、证照文号和楼盘规划层数等非地址数字不处理。该规则在 `scripts/anonymize.py` 中于代号化之后确定性执行。

仅 `data/B01/public-names.csv` 公开 14 个已在原文章中点名的项目与代号的关系，并保存文章正则命中的写法字母、代号集合及冻结期望值。其余对应关系保存在公开目录之外。

公开复算只需 Python 3.11 或更新版本，无第三方依赖、无网络调用。在本目录运行：

```bash
python3 -B scripts/recompute_b01.py
python3 -B scripts/validate.py
```

未提供私有代号表时，品牌与已知人名的残留检查显示 null，表示未检查；结构、条数、联系方式、敏感标记和发布清单检查仍可在公开包上运行。

复算沿用原口径：先移除正文中的 Markdown 链接，再按原文章正则对应的写法代号计数，一份回答最多计 1 次。新增的其他简称不会混入文章计数。结果为汇总指标 **一致 56 / 不一致 0**，文章数字 **一致 24 / 不一致 0**；逐项结果在 `proofs/recompute-b01.json`。包含于长名称的原正则命中仍按原口径计数，没有为匹配期望值修改题集、回答或文章。

## 指纹与时间戳如何核对

`proofs/raw-roots.csv` 保存 6 个原始数据根摘要、取值范围及已有清单核验状态。根算法为 SHA-256：先按相对路径排序，再将每个文件的 `sha256 + 两个空格 + 相对路径 + LF` 拼接，对整个 UTF-8 字节串求摘要。

- B02、B03、B05、B06 使用既有清单中的 raw 项根。四份实际批次清单中，三份核验为 0 差异；B03 有 **348 个额外文件**，主要是渲染工作区的浏览器缓存，raw 项根仍一致。此次没有清理或重写来源目录。
- B01 的两个输入为散文件。本包另算这两个原始文件的根；它们的单文件摘要与 2026-10-15 归档中的成员记录一致。该归档的散文件组还有一个成员，因此本包的双文件根不等于归档散文件组根。B01 辅助图表目录清单的 raw 集合为空，虽核验 0 差异，也不能当作 B01 原始回答的根。该辅助清单不代表 B01 的原始回答已完整归档。
- B04 无既有清单，按相同算法在私有目录计算，未向原目录写文件。**B04 不在 2026-10-15 归档内**，不把本次生成的根追溯为当时已归档。

`proofs/archive-20261015-r2.sha256` 保存原归档文件摘要；`.ots` 是原凭据的副本，并仅对副本做了升级。原归档内容不包含在本包。升级副本包含 Bitcoin 区块头证明；升级成功与独立验证区块头是两件事，本机构建未声称已经完成独立链验证。

每份私有代号表首行含 32 字节随机盐；文件整体的 SHA-256 写入 `proofs/code-table-commitments.csv`。发布文件的摘要清单为 `proofs/release-sha256.txt`，按相对路径排序，排除 Git 元数据、该清单自身及它的 `.ots`，避免自引用。2026-10-28 隐去门牌后清单已重算，旧时间戳回执对不上新清单，已改名为 `proofs/release-sha256.txt.old.ots` 保留（它对应的是改动前的清单，不能用来证明当前文件）；当前清单的 `.ots` 尚待重新联网盖章，盖章前本包不含当前清单的时间戳回执。

```bash
shasum -a 256 -c proofs/release-sha256.txt
ots info proofs/archive-20261015-r2.ots
# 重新盖章后再运行：ots info proofs/release-sha256.txt.ots
```

公开数据由 `scripts/anonymize.py`、原始数据和固定私有代号表确定性生成。尽调时可向第三方出示原始文件、私有路径配置、代号表、已有清单及原归档；对方可重跑下列命令，逐字节核对导出文件、盐表承诺、raw 根和 10-15 的归档凭据。路径配置逐批提供 `path`、`default_platform`、公开名称与根摘要等字段，配置本身不公开。

```bash
python3 -B scripts/anonymize.py --sources /private/source-map-v1.json --tables /private/code-tables --output /tmp/rebuilt-dataset
python3 -B scripts/validate.py --tables /private/code-tables
```

私有路径配置仅包含本版六批。重新导出生成批次表、data 文件、raw 根表和代号表承诺；README、许可、引用文件、`.zenodo.json` 及原归档凭据作为固定发布文件一同核对。私有表不在公开包内，所以公开脚本自身无法重新识别全部实体或证明私有输入的归档成员关系。

## 使用局限

- 每批都是单日快照；同批重复是同一批次内的重复，不构成跨时点的独立观察。B05 的 3+3 次来自同一天的两批。
- 各批的平台组合、模型与原协议存在差异；联网请求、实际调用与来源列表须分别解读。不能把千问的未知状态写成未联网。
- 题集由作者为研究和行业观察设计，不代表真实用户提问的分布。点名题与开放题保留各自标记，比较时应分别处理。
- 本包保存模型当时说过的话；回答中的排名、比例、资质、价格或其他主张均未因此变成经核实的事实。本数据不是排名，也不评价品牌，不支持推断成交、转化或购买意向。
- 来源仅保留域名，无法用公开包恢复逐页链接。代号化和固定种子抽查不能保证不可识别，也不能证明所有可能的名称写法都已穷尽。

## 许可与引用

数据文件及随附数据说明采用 CC BY 4.0，`scripts/` 下代码采用 MIT，完整适用范围见 `LICENSE`。引用作者写王涛（Taomir），机器可读信息见 `CITATION.cff`。本机包未填写远程仓库地址或 DOI。
