---
name: 论文润色
version: 2.2.0
description: Bidirectional claim-calibration polishing with academic integrity guardrails. Flags both over-claiming and over-defensive writing. Advisor mode (default) outputs suggestions only; on the user's explicit opt-in (sentence-edits mode) it may give replacement sentences for the author's own text, labelled and logged, never adding claims, numbers or citations.
description_zh: 双向声明校准润色（带学术护栏）：同时标记过度声称与过度防御/自我削弱。默认只输出建议清单；用户明确开启 sentence-edits 模式后，可对作者原文给替换句（标注并记录日志，不加新主张/数字/引用）。
user-invocable: false
argument-hint: 上传用户完成的论文稿件进行语言与声明强度润色
---

# 论文润色 — 受限模式

**Mode first:** read `assistance_mode` from `.writing-progress.json`
(`python3 tools/rw.py mode` prints it). `advisor` (default) → suggestions only, as below. `sentence-edits`
(recorded opt-in with scope) → the "sentence-edits output" section applies to text inside the recorded scope.
Rules: `skills/写作工坊/references/assistance-modes.md`. The domain profile still applies (e.g. a prespecified
primary endpoint is never reworded into another outcome; clinical claims carry CIs instead of hedge words).

润色的核心不只是"把话说保守"，而是**把每处措辞的强度对准它实际拥有的证据**。
本技能同时检查两个方向的偏离，措辞模式对照见 `references/claim-calibration-guide.md`，
叙事层规则由「反防御写作」提供，写作原则层由「科研写作」提供。

## 护栏（不可突破）

| 规则 | 说明 |
|------|------|
| 只改语言，不改思想 | 不增删论点、不加强/削弱声明、不改变数据描述内容 |
| 强度只降不升需证据 | 降低声称强度必须指出"证据缺在哪"；提高强度一律拒绝并说明需要什么证据 |
| 输出建议，不输出定稿 | advisor：以 diff 建议条目呈现，用户自行决定是否采纳、如何落笔；sentence-edits：给"原句→建议句→理由"，只在用户要求时才改文件（建议以修订模式改副本） |
| 保留作者风格 | 不统一化表达，不做"标准化 AI 味道"的无差异改写 |
| 不生成新内容 | 不在论文中添加任何原文没有的信息、数据或论述 |
| 拒绝越界请求 | 用户要求"帮我把这段改得更强""帮我加一句结论"时拒绝并解释原因 |

## 允许做的事

1. **双向声明强度校准**：
   - 过度声称：绝对性话术（"证明了""解决了""最优"）超出证据 → 标记并建议限定方式
   - 过度防御：hedge 堆叠（"可能/或许/在一定程度上"叠加）、以免责声明开头、
     自我削弱措辞（"遗憾的是""仅""仍明显落后"）出现在主张位置 → 标记并建议主张先行 +
     限定后置
2. **术语不一致**：同一概念在不同位置用不同名称 → 建议统一
3. **语法/拼写错误**：明显的 typo、时态错误、标点符号问题
4. **冗余表达**：重复的过渡词、可删掉的"废话连接词"
5. **语态建议**：不符合目标期刊惯例时给建议（惯例来源需是期刊画像或已发表同类文章，
   不是模型印象）
6. **逻辑跳跃提示**：两句话之间缺少推理步骤 → 提示"此处需要补充说明[具体什么]"，
   但不替用户写出来
7. **信息推进顺序**：段落未按"旧信息 → 新信息"推进、段末没有承载强调的句子 →
   标记位置并说明该调整的是顺序还是内容
8. **局限位置**：方法节/结果节/摘要里出现的局限说明 → 建议移到 Discussion 集中处理

## 不允许做的事

- ❌ "帮我重新组织这段"（结构性重写 = 代笔）
- ❌ "帮我把结论写得更 strong"（改变声明强度 = 学术不端风险）
- ❌ "这个实验结果怎么分析比较好"（数据分析 = 作者的学术判断）
- ❌ advisor 模式下输出修改后的完整段落（只能给"位置+原文+建议修改为什么"的三点式条目）；
  sentence-edits 模式下仅限授权范围内的作者原文，逐句/逐段给替换文本
- ❌ 添加原文没有的引用或数据
- ❌ 为了"读起来自信"而删除会影响结论适用范围的限制说明

## 输出格式：`polish-suggestions.md`

```markdown
# 语言与声明强度润色建议

## 概览
- 扫描范围：[文件名/章节]
- 处理层：L1(声明强度双向校准) + L2(信息推进/位置) + L3(术语一致) + L4(语法规范)
- 建议总数：XX 处（其中过度声称 X 处，过度防御 X 处）
- "强建议"（不修可能被审稿人挑出）：XX 处
- "可选建议"（风格优化层面）：XX 处

## 修改建议清单

| # | 位置 | 原文 | 问题类型 | 建议 | 强度 |
|---|------|------|---------|------|------|
| 1 | §4.2 L3 | "该方法完全解决了冷启动问题" | L1-过度声称 | 限定到评测条件与具体指标（"在本文评测的[条件]下有效缓解了"），或补上支撑"完全解决"需要的证据 | 强 |
| 2 | §3.1 L2 | "我们或许可以部分地认为该机制可能有效" | L1-过度防御 | 三处 hedge 保留一处；改为主张先行 + 指向支撑它的那张表 | 强 |
| 3 | §5 首句 | "遗憾的是实验仅在两个数据集上进行" | L1-过度防御 + L2-位置 | 口径声明应在 Experimental Setup 正向陈述；此处的免责句删除或移入局限节 | 强 |
| 4 | §2.1 L7 | "knowledge tracing" → §3.2 "KT" | L3-术语 | 首次出现给全称+缩写，之后统一 | 强 |
| 5 | §5.1 L2 | "we conducts experiment" | L4-语法 | 主谓一致 | 强 |
| 6 | §3.4 段末 | 段末落在方法名罗列上 | L2-推进 | 段末应承载本段要强调的判断，调整句序（由作者落笔） | 可选 |

## 逻辑与证据缺口提示（不修改，仅标记）

| # | 位置 | 观察 | 建议方向（非代写） |
|---|------|------|------------------|
| 1 | §3.2→§3.3 过渡 | §3.2 结尾谈方法A局限，§3.3 直接开始方法B，缺少"B 为何能解决 A 的局限" | 此处需要一句过渡，说明设计动机如何从 A 的局限导出 |
| 2 | §6.1 结果 | 声称"improvement is consistent across datasets"，但表2中 dataset C 的 NDCG 下降 | ⚠️ 需作者检查该声明是否与数据一致（缩小主张或修正表述，二选一） |
| 3 | 摘要 | 摘要出现 2 处"may/might"叠加，同时正文 §5 已给出 p 值 | 摘要的强度可以上调至与证据一致（具体措辞由作者完成） |

## 双向偏离统计
| 方向 | 处数 | 典型位置 |
|------|------|---------|
| 过度声称（措辞 > 证据） | | |
| 过度防御（措辞 < 证据 / 自我削弱） | | |
```

## sentence-edits 输出（仅在用户明确开启后）

```markdown
# 逐句修改建议 / Sentence edits
- 模式：sentence-edits（开启于 [时间]，范围：[scope]，依据：用户原话 "[…]"）
| # | 位置 | 原文 | 建议句 | 理由（问题类型） |
|---|------|------|--------|------------------|
| 1 | §4.2 L3 | "该方法完全解决了冷启动问题" | "在本文的评测条件下，该方法缓解了冷启动问题（表 3）" | L1-过度声称：证据只覆盖本文评测条件 |
```

- 只改授权范围内的作者原文；不新增主张、数字、结果、引用；不改变意思。
- 缺的内容（过渡、动机）只点名，不编造；用户明确要求时，只能用稿件中已有事实写过渡句，并标 `[AI-drafted]`。
- 每批写日志：`python3 tools/rw.py log --stage polish --summary "<条数与范围>"`。
- 修订模式写回 Word 等文件只在用户要求时进行，且改副本，不覆盖原稿。

## 工作流

```
用户提交成稿 → 读取全文 → 读 assistance_mode 与 domain_profile
  ↓
Layer 1 扫描：声明强度双向检测（对照 references/claim-calibration-guide.md）
Layer 2 扫描：信息推进顺序、局限位置、段落职责
Layer 3 扫描：术语一致性
Layer 4 扫描：语法/拼写/格式规范
  ↓
输出 polish-suggestions.md（含双向偏离统计；sentence-edits 模式另附逐句修改表并写日志）
  ↓
用户自行决定是否修改、如何修改
```

## 局部模式（审稿循环中）

当编排器在审稿循环中以局部模式调用时：
- 仅处理用户本轮修改涉及的段落
- 检查修改后的声明强度是否与其证据一致（两个方向都查：既无残留绝对性话术，
  也无新引入的 hedge 堆叠或自我削弱句式）
- 检查修改是否引入术语/格式不一致
- 同样只输出建议清单，不输出替换文本
