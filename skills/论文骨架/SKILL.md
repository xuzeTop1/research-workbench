---
name: 论文骨架
version: 2.2.0
description: Deep-research gate, journal profiling, direction comparison, and domain-profile-aware outline building (CS, prespecified clinical, systematic review, observational). Hard-stops without a deep-research tool; gates G1-G3 are written in a tool-checkable format. Does NOT write paper content.
description_zh: 深度研究能力探针+期刊画像+现有方向对比+按领域档案搭骨架（CS/预注册临床/系统综述/观察性）。无深度研究工具一律硬中断；G1-G3 按 rw.py 可校验格式书写。不产出论文正文。
user-invocable: false
argument-hint: 输入选题方向和目标期刊（或说明"尚无目标期刊"）
---

# 论文骨架 — 研究·对比·大纲

本技能覆盖 Stage 1（深度研究）和 Stage 3（搭建骨架），被「写作工坊」调用。
骨架阶段的写作原则由「科研写作」提供，措辞与叙事强度由「反防御写作」提供。
**Domain profile first:** the rules in `skills/写作工坊/references/domain-profiles.md` override both whenever
they conflict (e.g. a prespecified clinical study never re-selects its main result).

**绝对不产出论文正文段落。** 所有输出为结构化规划信息。
结构模板细节见 `references/paper-structure-templates.md`。

---

## Stage 1: 深度研究

### 输入

「写作工坊」的启动问询结果：写作方向（一句话）+ 现有研究方向 + 当前材料 + 目标期刊（可为"未定"）+ 领域档案。
**缺一 → 不执行 Stage 1，退回工坊问询**（`python3 tools/rw.py check --stage research` 会列出缺项）。

### 第 0 步：深度研究能力探针（执行前必做，不可跳过、不可凭印象）

1. 列出当前 Agent 实际可见的技能/工具清单（不是"我记得有"，而是本轮上下文里可枚举的项）。
2. 判定是否存在**深度研究能力**，标准为：能多轮检索 + 跨来源交叉验证 + 输出带来源引用清单的
   综合报告（如 `deep-research` 类技能、专门的检索/综述子代理编排）。
   - 单次 `WebSearch`/`WebFetch` **不算**；**自己临时编排多轮 WebSearch 也不算**——
     多轮普通搜索的覆盖与交叉验证强度仍不如网页端 LLM 的 deep research（不会因轮数增加
     而升级为深研能力），一律按"无深研能力"处理。
   - A dedicated deep-research skill or tool that is actually visible in this session counts as `native`;
     record its name in `stages.research.source`.
3. 探针结论写入进度文件 `stages.research.deep_research_mode`，取值：
   `native`（有） / `absent`（无）；收到外部深研产物后改为 `external-handoff`。

### 无深度研究能力 → 硬中断（默认，不得自行降级）

`deep_research_mode = absent` 时：

- **停止**，不做任何自主搜索来"凑出"研究笔记，也不用模型记忆代替检索。
- 向用户输出下面这个中断块（原样给出，含可直接复制的交接 prompt）：

```
⛔ Stage 1 无法在本机/本 Agent 继续：未检测到深度研究工具

原因：选题定位与竞争格局需要多轮检索 + 交叉验证 + 可溯源引用，
      当前 Agent 无 deep research 工具（单次或多轮普通网页搜索都不能替代它），
      在这里继续下去只会产出"看起来很完整、实际不可靠"的笔记。

请外部平台完成一次 deep research（ChatGPT Deep Research / Gemini Deep Research /
Perplexity / 本机的其他带深研能力的 Agent），把结果原文贴回，或保存为
`deep-research-handoff.md` 后说"继续"。

拿到 handoff 文件之前，本工作流不会进入 Stage 2。
```

- 用户贴回或存好 `deep-research-handoff.md` 后：`deep_research_mode = external-handoff`，以该文件为来源继续
  （`rw.py` 会检查该文件确实存在）。

- **交接 prompt 模板**（交给用户复制出去用）：

```
研究主题：[主题一句话] ｜ 学科范围：[领域/子领域] ｜ 时间窗：近 [X] 年

请回答四件事，每条结论后面附来源（标题 + 出处/DOI 或 URL + 访问日期）：
1. 这个问题当前值得发表的理由是什么？谁在做、做到什么程度（列 8-15 项代表性工作）？
2. 明确未被解决或存在争议的子问题有哪些？各条给出支撑证据。
3. 主流方法公认的局限是什么？最好给出他人在 limitation/future work 中的原话出处。
4. 近 2 年 [目标期刊/会议] 上同主题发表了什么？（未定刊则列 2-3 个候选 venue 的偏好）

要求：区分"检索到的事实"与"你的推断"，推断单独标注；
找不到就写"未检索到"，不要给出无法核实的引用；不要编造 DOI、页码、论文标题。
```

- **唯一例外**：用户显式指令要求"就用 WebSearch（哪怕多轮）继续"时，可以降级执行，但必须在
  `research-notes.md` 顶部写 `⚠️ 降级模式：普通网页搜索，非 deep research，覆盖面与交叉验证
  强度不足，风险由作者承担`，且 `deep_research_mode = degraded-by-user-request`。
  Agent **不得**自行选择降级；多轮普通搜索的结果也不得冒充深研产物通过 G1——G1 仍要求每条
  gap 有可核实的来源支撑。

### 执行步骤（`native`、`external-handoff` 或用户显式降级后）

1. **期刊画像构建** — 检索目标期刊：Aims & Scope、文章类型、格式与字数/页数限制、
   参考文献体系与数量要求、近 1-2 年同主题文章标题、公开的审稿关注维度。
   目标期刊"未定" → 走「科研写作」第五节的候选期刊流程，等用户确认后再填画像。
   每个字段附来源；查不到写 `未检索到 — 请作者核实`，**禁止**填写估计的影响因子/分区。

2. **选题边界界定**：In scope / Out of scope / 交叉领域。

3. **创新点定位** — 基于深研结果识别：已充分研究的子问题（避开）、存在争议的空白（切入）、
   主流方法的公认局限（机会）。每条创新点必须挂上"来自 handoff/检索的哪条证据"。

4. **竞争格局分析**：主要竞品方法/系统列表，各自优劣与评测口径差异。

5. **与现有研究方向对比**（用户已有在研课题/已投论文/实验室主线时必须做）：

   | 维度 | 现有研究方向 | 本稿拟定位 | 关系 |
   |------|------------|-----------|------|
   | 问题 | | | 重叠 / 继承 / 偏离 / 冲突 |
   | 方法 | | | |
   | 数据与评测口径 | | | |
   | 目标读者/社区 | | | |

   外加两行结论：本稿是**延续**还是**转向**；转向的代价（需重做的实验、需补的相关工作、
   与既有投稿的自我重复/查重风险）。

### Stage 1 → Stage 2 门条件（三个都满足才允许进入实验设计）

| 门 | 判据（`rw.py check --stage design` 按下面模板的格式计算） | 不满足时 |
|----|------|---------|
| G1 已确认的相关问题 | 至少 1 条 gap，且**每条**带 URL 或 DOI + `accessed YYYY-MM-DD`（检索日期） | 停在 Stage 1，列出还缺哪条证据、要补什么检索 |
| G2 确切的下一步 | `Action:` 具体可执行动作（跑某基线/找某数据/核某文献/砍某主张，不是"继续调研"）+ `Resources:` + `Time estimate:`（含时长） | 停在 Stage 1，给出 2-3 个候选下一步让用户选 |
| G3 定位已对比 | 对比表 4 行（问题/方法/数据与评测口径/目标读者）全部填写 + `Decision: continuation` 或 `Decision: pivot`（转向需 `Pivot cost:`） | 停在 Stage 1，向用户提一个问询：现有方向是什么 |

**门禁未过就不要开始 Stage 2。** 编一个实验方案比承认还没研究清楚伤害更大。
有 shell 时运行 `python3 tools/rw.py check --stage design` 并原样转述结果；全部通过后才
`python3 tools/rw.py advance --to design`。无 shell 时按上表逐条人工核对并说明是人工核对。

### 产出格式：`research-notes.md`

```markdown
# 深度研究笔记

- 写作方向：[一句话]
- deep_research_mode：native / degraded-by-user-request / absent(不应出现在成稿中)
- 深研来源：handoff 文件路径或技能名 + 检索日期
- 门条件（由 rw.py 计算后填写，不靠自评）：G1 [通过/未通过 原因] ｜ G2 [通过/未通过] ｜ G3 [通过/未通过]

## 目标期刊画像
- 期刊名：[已确认/候选待定]
- 收录范围关键词：
- 格式要求：页数/字数限制、引用体系（各带来源链接与检索日期）
- 审稿关注维度：
- 近期同类文章标题：[列表，标注是否已核实真实发表]
- 未检索到的字段：[列出，请作者核实]

## 选题边界
- In scope:
- Out of scope:
- 交叉领域：

## 已确认的研究空白（G1）
1. [gap 描述] — Source: [标题, 出处], [URL 或 DOI] — accessed [YYYY-MM-DD] — 为什么现在还成立：

## 竞争格局
| 方法/系统 | 核心思路 | 优势 | 局限 | 评测口径 | 来源 |
|---|---|---|---|---|---|

## 与现有研究方向对比（G3）
| 维度 | 现有研究方向 | 本稿拟定位 | 关系 |
|------|------------|-----------|------|
| 问题 | | | 重叠 / 继承 / 偏离 / 冲突 |
| 方法 | | | |
| 数据与评测口径 | | | |
| 目标读者/社区 | | | |

- Decision: continuation（延续） / pivot（转向）  ← 只保留一个
- Pivot cost:（仅转向时填写：需重做的实验、需补的相关工作、与既有投稿的自我重复/查重风险）

## 创新点候选
1. [描述] — 支撑证据编号 — 需要什么强度的实验才能说服审稿人：

## 确切的下一步（G2）
- Action: [一条具体可执行动作]
- Resources: [所需数据/算力/人]
- Time estimate: [例如 2 days / 3 天]

## 风险评估
- 竞争力评估（相对目标期刊近期同类文章）：
- 可能的"不够新"风险点：
- 需要什么样的实验强度：
```

---

## Stage 3: 搭建骨架

### 前置条件

`research-notes.md` 的 G1/G2/G3 全部通过，且 `experiment-plan.md` 已存在。

### 执行步骤

1. **选择结构模板** — 按**目标期刊**的惯例与**领域档案**（从期刊画像与进度文件读取，不预设某个期刊为标准）：
   `clinical-prespecified` 按适用指南（STARD 2015 / TRIPOD+AI / CONSORT / CLAIM 等）的结构，
   `systematic-review` 按 PRISMA 2020，`observational` 按 STROBE，并在 outline.md 中写明所用指南名称。

2. **确定主线句**（一句话）：
   - `cs-engineering`：**"本文赢在哪场比赛"**（Where this paper wins）— 由「反防御写作」第三节规则给出；这句话决定
     主线章节、主指标与图表分配。若这句话依赖不占优的指标 → 退回「实验设计」重选口径。
   - `clinical-prespecified`：**"Primary endpoint (protocol, verbatim): …"** + 主要结果（含置信区间）；
     不重选主结果，事后分析标注 exploratory。`rw.py` 检查 outline.md 逐字包含该终点。
   - `systematic-review`：review question（如 PICO）+ 证据确定性；`observational`：exposure → outcome + 混杂控制。

3. **填充各节规划要点** — 每节使用三行式（强制格式，来自「反防御写作」）：

   ```
   [主张] 本节要让读者接受的判断（一句话，措辞强度 ≤ 本节证据）
   [证据] 需要的证据类型：实验表/消融/推导/对比口径说明
   [适用条件] 结论覆盖什么（正向表述），不罗列"没做什么"
   ```

   另附：衔接问题（本节回答上一节留下的什么问题 — 「科研写作」旧→新原则）、
   引用锚点（从 Stage 2 池中取编号，一律 `[需用户核验]`）、预期篇幅占比。

4. **论证链检查**（「科研写作」编辑漏斗的"文档结构"层）：
   - 引言提出的问题 → 方法是否都有回应？
   - 方法声称的优势 → 实验是否有对应验证？
   - 实验结论 → 是否限定在数据支撑范围内？
   - 有无跳步？有无段落属于"工作汇报"式的过程叙述？

5. **标记风险点**（章节标题写作「双向风险标记 / Two-way risk flags」）— 双向标记，两者都要查：
   - `[⚠️过度声称]`：措辞超出可获取的证据、遗漏基线、混淆概念
   - `[⚠️过度防御]`：以免责声明开头的节、hedge 堆叠、把局限写进方法/摘要、
     替审稿人攻击自己、把不占优指标设为叙事中心

6. **局限集中** — 局限清单放在 Discussion/Limitations 节的要点里，每条含
   "是什么 + 为什么是局限 + 影响哪条结论"。其他节不承担局限说明——**除非**领域档案、报告指南或期刊要求
   （例如 PRISMA 2020 for Abstracts 要求摘要写证据局限；部分期刊要求 "strengths and limitations" 框）。

### 产出格式：`outline.md`

```markdown
# 论文骨架：[暂定标题]

## 基本信息
- 目标期刊：[已确认期刊名 或 候选待定]
- 引用格式：[按期刊画像]
- 目标页数/字数：[带来源，未检索到则留空待核实]

## 本文赢在哪场比赛（cs-engineering）/ Primary endpoint (protocol, verbatim)（clinical-prespecified）
[cs-engineering：一句话——在[口径/约束]下，本文的[独特能力]带来[可验证收益]]
[clinical-prespecified：逐字引用方案中的主要终点；主要分析人群与统计方法同方案；偏离方案处列出并说明原因]
[systematic-review：review question + 证据确定性；observational：exposure → outcome + 混杂控制]
- 报告指南：[无 / STARD 2015 / TRIPOD+AI / CONSORT / CLAIM / PRISMA 2020 / STROBE / …]

## 论证主线
[问题] → [方法策略] → [验证指标] → [限定结论]

## 章节规划

### 摘要
- [主张]/[证据]/[适用条件] 三行式
- 结构任务：背景→问题→方法→最强结果→意义（前五句必须出现问题与贡献）
- 关键词建议：[5-7 个]
- ⛔ （cs-engineering）本节不写局限、不写未做事项；其他档案按指南/期刊要求（如 PRISMA 摘要须写证据局限）

### 1. Introduction
- [主张] 该问题值得研究且现有方案不够
- 需要展示：问题动机 + 现有方案缺口 + 编号贡献
- 引用锚点：[编号]（全部 [需用户核验]）
- ⚠️ 贡献声明应是方法论贡献，不是"实现了某系统"
- 预期占比：10-12%

### 2. Related Work
- 分组策略：按方法/问题维度分 2-4 个子方向，每组收束于共同不足 → 本文如何补
- ⚠️ 描述竞品公平：描述机制差异，不做贬低式总结

### 3. Method / System Design
- 核心设计决策清单：每个决策含"为什么选 X 不选 Y"
- 形式化定义需求：需要定义的符号、公式、假设声明位置
- ⛔ 方法节不插入局限说明与"可能不够"的 hedge

### 4. Experimental Setup
- 参见 `experiment-plan.md`
- 需报告维度：数据集/基线/指标/参数/硬件/评测口径
- 口径声明必须在任何结果数字之前

### 5. Results & Analysis
- 主实验 + 消融 + 显著性检验；每个实验标注它承担的论证职责
  （clinical-prespecified：先报告方案预设的主要终点与全部预设结局，含阴性结果；事后分析单列并标 exploratory）
- 需要回答的审稿人预判问题：[列表]
- 分析要素：趋势 → 机制归因 → 对比基线 → 不完美处 → 指向消融

### 6. Discussion & Limitations
- 适用边界声明清单（正向表述为主）
- 局限：编号列出，每条含"影响哪条结论 + 需要什么验证"
- 后续方向：具体可做，禁止"未来将进一步研究"

### 7. Conclusion
- 强化记忆点：解决了什么、提出了什么、证明了什么、为什么重要
- ⛔ 段末不得新增自我否定或扩大局限性

## 各节字数分配表
| 章节 | 占比 | 预估字数 |
|------|------|---------|

## 图表规划
- 图1：[内容 + 承担的论证职责] → 放 §X.Y
- 表1：[内容 + 口径] → 放 §X.Y

## 双向风险标记
| 位置 | 类型 | 说明 |
|------|------|------|
| §X | ⚠️过度声称 / ⚠️过度防御 | |
```

## 禁止事项

- ❌ 不输出任何"段落级"可粘贴进论文的文本（骨架阶段在 advisor 与 sentence-edits 两种模式下都只给结构）
- ❌ 不替用户决定"本节应该这样论证"的完整文字表述
- ❌ 无深研能力时不假装做过 Stage 1；门条件未过不进 Stage 2/3
- ❌ 不把"防御性表述"当作默认安全选项（每节以免责开头是本技能要标记的缺陷）
- ❌ 不在 `clinical-prespecified` 中替换、降级或重新包装方案预设的主要终点
- ✅ 只输出结构、要点、检查清单、对比表与逻辑关系
