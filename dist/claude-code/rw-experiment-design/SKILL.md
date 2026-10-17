---
name: "rw-experiment-design"
description: "Gated experiment design — requires the tool-checked Stage 1 gates (confirmed gap + concrete next step + direction comparison). Literature recommendation, dataset/metric/baseline selection; for prespecified clinical studies an analysis-plan check against the protocol/SAP instead of choosing a \"winning\" metric. Never produces paper text."
argument-hint: "基于 research-notes.md 设计实验方案和推荐文献"
user-invocable: false
allowed-tools: "Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py *)"
license: "MIT"
metadata:
  version: "2.2.0"
  source-skill: "实验设计"
  description-zh: "带入口门禁的实验设计：需 rw.py 校验的 Stage 1 门条件（已确认 gap + 确切下一步 + 现有方向对比）。文献推荐（需核验）+ 数据集/指标/基线选择；预注册临床研究改为对照方案/SAP 的分析计划核对。绝不产出论文正文。"
---

# 实验设计与写作规划

## 零、入口门禁（不满足则不设计实验）

开工前检查 `research-notes.md`。有 shell 时运行 `python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py check --stage design`，
原样转述结果——它按「rw-skeleton」的模板格式计算 G1/G2/G3，不接受自评"通过"：

| 检查项 | 要求 | 不满足时的动作 |
|--------|------|--------------|
| Stage 1 门条件 G1/G2/G3 | 全部"通过"（rw.py 计算） | 拒绝设计，输出缺哪一条，退回 Stage 1 补检索/补对比/定下一步 |
| `deep_research_mode` | `native`、`external-handoff`（且 handoff 文件存在）或 `degraded-by-user-request`（且笔记顶部有降级声明） | 若为 `absent`/`unprobed`/缺失 → 停止，交由「rw-skeleton」输出硬中断块 |
| 领域档案 | `domain_profile` 已选；`clinical-prespecified` 已记录 `protocol.primary_endpoint`（逐字取自方案/SAP） | 退回 Stage 0 问询 |
| 已确认的研究空白 | 至少 1 条带来源的 gap | 输出"要证明这条 gap 需要哪些检索"，等用户 |
| 与现有研究方向对比 | 已填，延续/转向已判定 | 向用户提一个问询：现有方向是什么，然后再设计 |
| 下一步可执行 | 已写成一条具体动作 | 给 2-3 个候选动作让用户选，不自行挑一个 |

**理由**：在还没确认"问题真实存在且没人解决"之前排出实验矩阵，产出的是一份看起来很完整
但方向错误的方案。宁可停在 Stage 1，也不要编一个方案。

## 零之一、领域档案适配 / Profile adaptations

Full rules: `${CLAUDE_SKILL_DIR}/../rw-workshop/references/domain-profiles.md`.

- `cs-engineering`: this skill as written.
- `clinical-prespecified`: Stage 2 is an **analysis-plan check**, not a free design. `experiment-plan.md` must
  quote the protocol's primary endpoint verbatim (`rw.py` checks it) and cover: alignment of every planned
  analysis with the protocol/SAP; sample-size justification; reference standard and blinding of
  readers/assessors; handling of indeterminate and missing results; prespecified subgroup and sensitivity
  analyses; multiplicity; which analyses are post hoc (labelled exploratory). "Choose the main battlefield"
  does not apply — the main outcome is the protocol's.
- `systematic-review`: protocol/registration, search sources and dates, full search strategy, selection,
  risk-of-bias tool, synthesis and certainty-of-evidence approach (PRISMA 2020).
- `observational`: exposure/outcome definitions, confounder selection (e.g. a causal diagram), missing data,
  bias analysis (STROBE).

## 绝对禁止

- ❌ 不写论文段落、句子、措辞
- ❌ 不编造 DOI、页码、发表信息
- ❌ 不虚构实验数据或结果
- ✅ 所有输出为"方案"、"清单"、"指引"，由用户决定和执行

---

## 一、文献推荐

### 执行流程

1. 基于 `research-notes.md` 的选题边界和创新点，确定检索关键词矩阵（中英各 3-5 组）
2. **取文献来源的优先顺序**：
   - 优先使用深研产物（`deep-research-handoff.md` 或 Stage 1 来源清单）中已带出处的文献
   - 其次才是本技能自行发起的网页检索（arXiv / Semantic Scholar / DBLP / CNKI 等）
   - 两者都没有 → 不做文献推荐，退回 Stage 1 的硬中断流程
3. 按类别整理推荐
4. 自主检索到的每条文献附检索日期与来源链接；不可达时写"无法在线验证"，不写"不存在"

### 强制输出规则

**在文献清单顶部必须输出以下警告块**：

```
⚠️ 学术诚信警告

以下文献列表由 AI 根据训练知识和联网检索生成。AI 存在以下已知风险：
1. 可能虚构不存在的论文（标题、作者、DOI 完全编造）
2. 可能混淆相似论文的卷号/页码/年份
3. 可能将 preprint 误标为正式发表
4. 联网搜索有覆盖盲区，不代表"搜索到的就是全部"

你必须：
- 逐条在 Google Scholar / DBLP / CNKI / IEEE Xplore 核实
- 确认作者、标题、年份、出处、DOI 完全一致后方可引用
- 未核实的文献绝对不可写入论文参考文献列表
```

### 分类输出格式

```markdown
## A 类：直接竞品（必须对比的方法）
| # | 推测标题 | 作者 | 年份 | 来源 | 核心贡献 | 与本文关系 | 核验状态 |
|---|---------|------|------|------|---------|-----------|---------|
| 1 | [标题] | [作者] | [年] | [Venue] | [一句话] | [为什么必须对比] | [需用户核验] |

## B 类：方法基础（本文使用的技术来源）
| ... |

## C 类：领域背景（引言和相关工作的支撑）
| ... |

## D 类：数据集/工具/Benchmark
| ... |

## 研究空白总结
[2-3 句话指出 gap，供用户在论文引言中使用自己的表述]
```

---

## 二、实验设计方案

### 输入

`research-notes.md` 中的创新点 + 目标期刊审稿标准。

### 输出格式：`experiment-plan.md`

```markdown
# 实验设计方案

## 实验总体目标
本文需要实验回答的核心问题（对应审稿人最可能质疑的点）：
1. [核心方法是否有效？] → 主实验
2. [每个组件是否必要？] → 消融实验
3. [与现有方法相比是否有竞争力？] → 对比实验
4. [在什么条件下会失效？] → 鲁棒性/边界实验
5. [计算开销是否可接受？] → 效率分析

## 每个实验的论证职责（先定职责，再排实验）

实验不是结果仓库，是论证工具。「rw-claim-forward」第五节要求每个实验必须承担下列职责之一：

- 证明核心方法有效 / 证明优势来自关键机制 / 证明方法在目标场景中有价值 /
  排除最可能的替代解释。

承担不了任何一条的实验：在设计阶段就删除、合并或重新设计，不要留到成稿后再删
（成稿后不得删除已报告的原始数字）。

**比较口径在本阶段确定**（`cs-engineering`）：如果某指标上本文不占优，就在本阶段决定不把它设为主战场，
并说明本文赢的是哪场比赛。这是叙事选择，不是结果出来之后的删数据理由。
`clinical-prespecified`：口径与主要终点由方案决定，本节只核对、不选择。

## 数据集选择
| 数据集 | 领域 | 规模 | 获取方式 | 选择理由 | 审稿人可能的质疑 |
|--------|------|------|---------|---------|----------------|
| [名称] | | | [URL] | [为什么用这个] | [如"只用了私有数据不够"] |

建议配置：
- 公开 benchmark 至少 [X] 个（让结果可复现、可比较）
- 私有/领域数据 [Y] 个（展示方法在实际场景的价值）
- 数据规模需说明"为什么这个量级有统计效力"

## 基线方法
| 基线 | 类型 | 年份 | 为什么选它 | 实现来源 |
|------|------|------|-----------|---------|
| [名称] | [经典/强基线/SOTA] | | | [代码仓库URL或"需自行实现"] |

选择策略：
- 包含经典方法（不只看最新，证明理解领域演进）
- 包含至少 1-2 个**近 1-2 年**的方法（证明跟上前沿；具体年份按检索日期确定，不写死）
- 如果有"显而易见的强基线"缺失，会被审稿人标为高优先级问题 → 列出避免遗漏

## 评测指标
| 指标 | 度量什么 | 为什么选 | 报告格式建议 |
|------|---------|---------|-------------|
| [如 NDCG@10] | [排序质量] | [IR领域标准] | [均值±标准差，5次运行] |

指标组合原则：
- 主指标 1-2 个（与核心贡献直接挂钩）
- 辅助指标 2-3 个（从不同角度验证）
- 效率指标（时间/空间开销，如果论文有效率声明则必须包含）
- 统计检验方法：[配对t-test / Wilcoxon / Bootstrap / ...]

## 实验参数设置
- 硬件环境：[CPU/GPU型号、内存、OS]
- 超参数搜索范围：[哪些参数、搜索方式]
- 随机种子数：[建议 ≥ 3 次独立运行]
- 训练/验证/测试划分策略

## 消融实验设计
要验证的组件：
1. [组件A] → 移除/替换后观察哪个指标变化
2. [组件B] → ...
3. [策略选择X vs Y] → ...

## 预期审稿人挑战
依据 `research-notes.md` 的目标期刊画像（近期同类文章 + 公开审稿关注维度）预判；
无期刊画像时标注"未做期刊画像，以下挑战来自模型先验，可靠性较低"：
| 可能的质疑 | 依据来源 | 建议应对 |
|-----------|---------|---------|
| "数据集规模/多样性不够" | [期刊同类文章/需核实] | 增加 [XX] 数据集的交叉验证 |
| "没有和 [YY] 方法比较" | | 将 [YY] 加入基线 |
| "缺乏统计显著性检验" | | 配对检验 + 效应量 |
| "为什么不用 [ZZ] 指标" | | 在 limitation 中说明 |

## 写作指引（非代笔）

各实验节的呈现建议：
- 主实验表格格式建议：[列头设计、最佳值加粗、平均值+标准差]
- 图类型选择：[折线/柱状/雷达/热力图 + 适用场景]
- 分析文字应包含的要素清单：
  1. 描述趋势（"从表X可以看到..."）
  2. 解释原因（"这可能是因为..."）
  3. 对比基线（"相较于[方法A]，本文方法在[B]上..."）
  4. 承认不完美（"但在[C]指标上提升不显著..."）
  5. 指向消融验证（"这一效应在 §X.Y 的消融中进一步确认"）

⚠️ 以上是呈现结构建议，具体文字表述由作者自行完成。
```

---

## 三、禁止事项

1. **绝不输出任何可直接粘贴进论文的句子**（如"实验结果表明本文方法在XX上取得了YY%的提升"——这种句式不能出现）
2. **绝不假设实验结果**：可以建议"预期应该能看到X效应"，但不能写具体数字
3. **绝不虚构数据集名称、规模或获取方式**
4. **文献推荐不声称已验证**：一律标记 [需用户核验]
