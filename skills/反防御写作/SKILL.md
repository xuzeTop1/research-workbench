---
name: 反防御写作
version: 2.2.0
description: Claim-forward narrative rules that reject over-defensive writing, self-weakening phrasing, and hedging stacks. Claim strength is capped by evidence strength, and the study's domain profile (e.g. a prespecified clinical protocol) overrides the narrative rules wherever they conflict.
description_zh: 主张先行的写作叙事规则：拒绝过度防御性写作、自我削弱措辞、免责声明堆叠。措辞强度以证据强度为上限；领域档案（如预注册临床方案）与叙事规则冲突时以档案为准。
user-invocable: false
argument-hint: 搭建骨架、润色或修订后复检时调用，检查防御性写作倾向
---

# 反防御写作 — 主张先行，但不越证据

把论文当作一场**学术发布会**，不是项目总结、实验日志或自我审查报告。任务不是平均呈现
工作的所有侧面，而是识别其中最值得发表的价值，围绕它建立最有利、最完整、最有说服力的
叙事——同时不替审稿人攻击自己。

> 叙事原则改编自 MIT 许可的社区技能 `Adkid-Zephyr/anti-defensive-writing-Skill`，
> 并按本仓库学术护栏加了证据上限（见下节）。

## 零、领域档案优先 / Domain profile precedence

Read `domain_profile` from `.writing-progress.json` first (definitions:
`skills/写作工坊/references/domain-profiles.md`).

- `cs-engineering`: everything below applies as written.
- `clinical-prespecified` (and `observational` with a prespecified analysis plan): the protocol/SAP fixes the
  primary endpoint, analysis population and main analysis. **Not applicable to prespecified outcomes:**
  §三 "打不过的维度不设为比赛项目" and "允许重构故事", and steps 2–6 of §六. Report every prespecified outcome
  (including null results), disclose deviations, label post hoc analyses as exploratory, and place limitations
  where the guideline or journal requires (the abstract included, if required). What still applies: tone
  (no apologetic openers, no self-attack, one filler qualifier per claim) and the evidence ceiling.
- `systematic-review`: claim strength is capped by the certainty of evidence; the abstract keeps the
  limitations of the evidence (PRISMA 2020 for Abstracts).
- `custom`: follow the guideline named in `domain_profile_notes`; when unsure, apply the stricter rule.

## 一、硬边界（优先级高于本文件其他规则；仅次于第零节的领域档案）

| 边界 | 说明 |
|------|------|
| 措辞强度 ≤ 证据强度 | 反防御不是过度声称。"证明""保证""最优"只有当数据/推导能逐条支撑时才允许 |
| 不隐瞒影响结论成立性的局限 | 可以调整局限的**位置与承担的角色**，不可删除会让读者误判结论适用范围的信息 |
| 不删结果、不改口径 | 不占优的指标可以不作为主战场，但其原始数字必须仍在实验表中；禁止"不说输"式的数据隐去 |
| 不编造优势 | 不得虚构对比、虚构 baseline 弱点、虚构统计量来制造叙事 |
| 不承担没人问的责任 | 不主动扩大攻击面，不提出本来无人要求回答的自我质疑 |

**与"防御性语态"的关系**：本技能不取消范围限定，而是要求限定用**正向、集中、可核查**的
方式表达——说清"在什么条件下成立"，而不是在每句话前面垫一句"可能未必"。

## 二、四条支柱

1. **主张先行（claim-forward）**：每节、每段先立主张，再给证据，最后才是限定。
   顺序为 `[主张] → [支撑证据] → [适用条件]`，不允许以免责声明开头。
2. **正向界定范围（positive scope delimitation）**：
   - 过度防御："遗憾的是本文未考虑 Y 场景，结论在 Y 上可能不成立"
   - 校准后："本文结论面向 X 条件（数据规模 N、离线评测口径）；Y 场景属于本文范围之外"
   - 模式：声明覆盖什么，而非罗列没覆盖什么。
3. **不确定性校准（calibrated uncertainty）**：一个主张最多一处限定；禁止
   "可能/或许/在一定程度上/似乎"堆叠；禁止用"我们部分地表明"这类缩水动词替代
   数据本身已经支持的表述。
4. **结构分离（separation of concerns）**：局限与未来工作集中在 Discussion 末节，
   不散布进方法节、结果节和摘要。摘要与引言在贡献建立前不讨论不足。

## 三、叙事规则

- **只围绕优势组织主线**：新能力、新问题、新机制、新视角、更强适用性、更低成本、
  更高效率、更有意义的权衡。未形成优势的内容不进入主线（但仍保留在实验材料中）。
- **不写成工作汇报**：不按"先做了什么、后来尝试了什么、哪些失败了"展开。只保留最终
  成立的逻辑：问题为何重要 → 现有方法为何不够 → 本文提供什么新解法 → 证据如何支持。
- **打不过的维度不设为比赛项目**（`cs-engineering`）：某指标不占优时，重新选择更能反映本文价值的任务定义、
  评价维度、约束条件或比较口径——但这是**在实验设计阶段**决定的事，不是在结果出来后
  删数据的理由。方案预设的结局不适用此条。
- **优势必须明说**：不期待审稿人自己从表格里发现贡献；主动说明在什么条件下表现最好、
  为什么会出现这种优势、解决了什么实际问题。
- **控制比较范围**：不追求"所有数据集所有指标全面领先"；说服力来自主张与证据高度一致。
- **允许重构故事**（仅 `cs-engineering`，且绝不用于方案预设的主要终点）：现有结果无法支撑原始叙事时，
  重定义问题、重排贡献、重选主结果，而不是围绕原叙事防守。故事服务于最强证据，不忠于最初设想。
  预注册/有方案的研究：主要终点不变，新故事只能作为明确标注的探索性分析出现。

## 四、语言模式对照表

模式示例，供识别与自检使用，**不得直接作为论文正文粘贴**。

| 过度防御写法 | 校准写法 |
|-------------|---------|
| 遗憾的是，我们的方法仅在有限数据集上进行了评估 | 评估覆盖 [N] 个数据集（公开 [X] + 领域内 [Y]），结论限定于该评测口径 |
| 结果表明该方法可能在一定程度上缓解了问题 | 结果支持该机制在[具体指标]上缓解[具体问题] |
| 本文还存在一些不足，未来仍需改进 | 局限：（1）…（2）…（影响哪条结论、需要什么验证） |
| 我们的性能虽略低于 SOTA，但… | 本文优化目标为[约束A]，在同等[约束A]下对比方法为[列表]（数字见 §X 表Y） |
| 由于时间/资源限制，我们未能比较 XX | 未纳入 XX 对比的原因：[可核查的口径差异]；纳入需要[具体条件] |
| 或许可以认为这一现象部分地反映了机制的作用 | §X.Y 的消融将该现象归因于[组件]：移除后[指标]变化[方向] |

**禁用式自我削弱措辞**（在主张位置）："遗憾的是""仅""仍明显落后""效果有限""存在严重不足"
"我们未能""不可避免地存在缺陷"。允许它们在 Discussion 的**事实陈述**中出现，但不允许
充当结论的替代品。

## 五、实验即论证工具

每个实验必须承担一项明确职责：证明核心方法有效 / 证明优势来自关键机制 / 证明方法在目标
场景中有价值 / 排除最可能的替代解释。无法强化主线、容易分散注意力或引出无关争论的实验：
删除、弱化、移入附录或重新设计（在实验设计阶段决定；成稿后不得删除已报告的原始数字）。

## 六、默认决策顺序（遇到不理想材料时；第 2–6 步仅适用于 `cs-engineering` 或非预设结局）

1. 删除与核心主张无关的内容 → 2. 缩小主张避免无意义正面对撞 → 3. 更换更能体现价值的
评价维度 → 4. 将结果解释为目标差异或合理权衡 → 5. 重组实验让优势成为叙事中心 →
6. 重新定义论文故事 → 7. 仅在无法回避且确实影响核心结论时才做必要说明。

## 七、骨架/修订阶段调用规程

被「论文骨架」Stage 3 与「论文润色」调用时逐条执行：

1. 每个章节规划要点按 `主张 → 证据类型 → 适用条件` 三行式书写；缺任一行即标记 `[不完整]`
2. 检查是否有任何节以免责开头；有 → 改写为主张开头 + 限定后置
3. 汇总"本文赢在哪场比赛"一句话；若这句话依赖不占优的指标 → 回到「实验设计」重选口径
4. 局限清单只允许出现在 Discussion/Limitations 节的要点里，条目需含"影响哪条结论"
5. 输出 `[⚠️过度防御]` 与 `[⚠️过度声称]` 两类标记，两者同时检查，不偏向任一侧

## 八、交稿前自查（不给审稿人递刀子）

- 这句话是否无意中扩大了本文需要承担的责任？
- 是否提出了本来没人要求回答的问题？
- 是否把局部现象描述成了普遍缺陷？
- 是否使用了比证据更宽泛的负面判断？
- 有没有按"我们做了什么过程"在展开？
- 有没有把不领先的指标设成主战场？
- 摘要前五句里问题和贡献都出来了吗？
- 结论段有没有突然的自我否定？
- 反向自查：有没有哪条主张的措辞超出了它引用的那张表/那个实验？

## 禁止事项

- ❌ advisor 模式下不产出可粘贴进论文的段落（本节所有示例为模式示例）；用户明确开启 sentence-edits 模式后，
  只可对作者已有文字给替换句，规则见 `skills/写作工坊/references/assistance-modes.md`
- ❌ 不为"更有进攻性"而提高声称强度、隐瞒局限、删改已报告数据
- ❌ 不生成 rebuttal 措辞稿；只给"这条意见的事实缺口是什么、需要补什么证据"
- ✅ 只输出：结构诊断 + 措辞模式标记 + 需要作者自行完成的决策
