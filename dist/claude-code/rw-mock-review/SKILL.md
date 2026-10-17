---
name: "rw-mock-review"
description: "Blinded multi-reviewer simulation. Each reviewer gets a snapshot sandbox outside the project (built by rw.py review-packet), calibrated via web search against similar published papers in the target venue; rw.py aggregate counts P0-P3 deterministically and flags leakage or forbidden verdicts. Never predicts acceptance odds or decision tiers, never rewrites."
argument-hint: "上传稿件进行审稿，或说\"再审一轮\""
user-invocable: false
allowed-tools: "Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py *)"
license: "MIT"
metadata:
  version: "2.2.0"
  source-skill: "模拟审稿"
  description-zh: "脱盲模拟审稿：rw.py review-packet 为每位审稿人在项目外建快照沙箱（无 .git/进度文件/前轮意见），用 web search 校准目标期刊同类文章与评审关注点；rw.py aggregate 确定性计数 P0-P3 并标出越界与违规表述。不给录用概率/档位判定，不代写。"
---

# 模拟审稿 — 脱盲子代理评审

## 一、两条硬禁令（最高优先级）

| 禁令 | 说明 |
|------|------|
| 🚫 不给概率 | 禁止任何百分比、"X 成把握"、"大概率 minor"、"录用可能性较高"之类的表述。模拟审稿不预测编辑决定，真实结果取决于审稿人构成、随机性与编辑偏好 |
| 🚫 不给档位判定 | 不输出 ACCEPT / MINOR REVISE / MAJOR REVISE / REJECT 判定。改为输出**可核查的阻塞点清单**（P0-P3 分级 + 条目计数） |

允许输出的强度信息只有两种：分级（P0-P3，定义见第五节）与条目计数（"本轮 P0 3 条、P1 5 条"）。
用户问"这版能中吗"→ 回答阻塞点清单 + "无法预测录用结果"，并指出哪些 P0/P1 仍在。

每次输出顶部固定附声明块：

```
⚠️ 本文件是模拟评审，不是录用结果预测。
意见由独立的脱盲评审代理给出，可能包含事实错误、遗漏与不成立的判断。
真实编辑决定不可预测；未被检索到的期刊要求请作者自行核实。
```

## 二、执行形态：必须由独立子代理执行

主对话不是合格审稿人：它已经看过作者意图、修改历史和前轮意见，无法真正脱盲。

### 派发规程（snapshot-first）

1. **Build the sandboxes with the tool** (shell available):

   ```
   python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py review-packet --journal-profile review-calibration.md [--material fig1.png ...]
   ```

   For each reviewer it creates a fresh directory **outside the project** (system temp by default, neutral
   name `rw-sbx-…`) containing only: the manuscript snapshot under a neutral name (`input/manuscript.<ext>`, so
   file names like `paper_v3_after_R2.docx` do not leak history), explicitly listed materials (renamed
   `material-N`), the journal-profile excerpt, `REVIEWER_BRIEF.md` (role, rules, P0–P3 definitions, the
   domain-profile checklist) and an empty `output/`. No `.git`, no `.writing-progress.json`, no earlier reviews,
   no polish suggestions. It records SHA-256 of every input in `reviews/round-N/packet.json`.
   `.docx` manuscripts with tracked changes or comments are refused (they show the revision history) unless
   `--allow-docx-revisions` is passed; author metadata is refused unless `--strip-docx-metadata` (blanks it in
   the snapshot) or `--allow-docx-metadata`.
2. **Dispatch** three independent subagents in parallel. Each gets exactly one instruction:
   "Read `<sandbox>/REVIEWER_BRIEF.md` and follow it exactly. Work only inside `<sandbox>`." — nothing about the
   author, the revision history, earlier rounds or the other reviewers.
3. **Aggregate** with `python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py aggregate`: it archives each review to `reviews/round-N/reviewer-K.md`,
   writes `reviews/round-N.md`, counts P0–P3 from the reviewers' tables, and raises integrity flags for:
   acceptance probabilities or decision tiers, paths outside the reviewer's sandbox, mentions of
   workflow-internal files, an edited manuscript snapshot, files written outside `output/`, a missing review.
   Then it deletes the sandboxes so next-round reviewers cannot find this round's reviews.
4. 主 Agent 只承担 AE 聚合角色——合并条目、定级、排优先级，**不改写也不软化**审稿人的原始判断；分歧条目全部保留并标注分歧。
   Treat any integrity flag as "this review may be contaminated": tell the user and rerun that reviewer if needed.

**Honest limits.** Prompt-level isolation cannot stop a subagent that has file tools from opening other paths
if it decides to; the sandbox therefore lives outside the project, contains nothing workflow-related, and the
aggregate step flags what it can detect. It cannot detect a reviewer that silently read something and did not
cite it. The three sandboxes exist at the same time in the temp directory during a round.

### 隔离方式（按可用性依次尝试）

| 优先级 | 方式 | 做法 |
|--------|------|------|
| 1 | **项目外快照沙箱 + 独立子代理**（`isolation: snapshot`） | 上面的 `review-packet` → 子代理 → `aggregate` |
| 2 | **三个互不相关的新会话**（`isolation: fresh-sessions`，无子代理能力的平台） | 仍先跑 `review-packet`；用户把每个沙箱里的 `PASTE_PROMPT.md`（文本稿件已内联，Word/PDF 需附 `input/manuscript.*`）分别粘贴进三个新会话，把回复存为各沙箱的 `output/review.md`，再 `aggregate`。没有 shell 时用下面的单审稿人提示块手工完成 |
| 3 | 都做不到（`isolation: none`） | 必须在输出顶部声明：`⚠️ 本轮未实现评审隔离，脱盲性不完整，以下意见可能被作者上下文污染` |

Why not git worktrees (the v2.1 first choice): a worktree checks out **every** tracked file — including
`.writing-progress.json` and earlier `reviews/` if they were committed — and shares the full history, so
`git log` shows every revision message. A snapshot copy does not.

### 单审稿人提示块（无 shell 时手工使用；有 shell 时 `rw.py review-packet` 生成更完整的 REVIEWER_BRIEF.md）

```
你是 [目标期刊] 的独立审稿人，视角：[方法/实验/写作与贡献]。
仅评审下面这份稿件当前版本。你不知道作者是谁、不知有其他审稿人、不知它的修改历史。

必读材料：[稿件路径/粘贴内容]、[期刊画像]、[该刊近期同类文章标题清单（未核实）]

要求：
- 只阅读上面给你的材料；不要打开、列出或搜索其他任何路径
- 每条意见给出：位置（节/页/行/表图编号）→ 问题类型 → 缺什么证据或说明 → 修改方向
  （只给方向，不替作者重写任何句子）
- 按 P0/P1/P2/P3 分级（定义附后）
- 禁止：预测录用结果、给出百分比、输出 ACCEPT/MAJOR/REJECT 档位、
  引用其他审稿人或猜测其意见
- 禁止：编造文献、编造该刊规则；查不到就写"需作者核实"
- 输出写入 [路径]，除该文件外不得修改任何文件；最后一节 `## Files consulted` 列出你打开过的每个文件
```

## 三、评审关注点校准（派发前做，需要联网搜索）

三位审稿人的关注点必须来自**该刊实际发表的文章与公开评审标准**，不是模型印象。

1. 用可用的联网搜索工具检索：
   - 目标期刊/会议近 1-2 年同主题文章 3-8 篇（标题、年份、其评测口径与篇幅结构）
   - 该刊公开的 reviewer guidelines / editorial criteria / 审稿问题清单
   - 同主题已发表工作中被指出过的典型缺陷（如后续文章的 comparison/discussion 部分）
2. 结果整理为 `review-calibration.md`：每条附来源链接 + 检索日期 + `[需用户核验]`。
   禁止把未核实的具体数字（审稿周期、拒稿率、IF）写进校准文件。
3. **不可达时显式降级**：无搜索工具、paywall、403 等情况下，不假装做过校准，
   在 `review-round-N.md` 顶部写
   `⚠️ 关注点校准缺失：以下视角权重来自模型先验，未经该刊实际文章验证`。
   403/付费墙 ≠ 文章不存在，标记"无法在线验证"。
4. 检索到的同类文章标题只能用于确定"该刊接受什么样的结构与证据强度"，
   不得作为审稿意见中的事实论据（"某刊某文说你的方法不行"这种编造禁止）。

## 四、审稿人配置

视角权重由期刊画像决定，不预设某个期刊为标准。默认三视角：

| 视角 | 关注 | 典型检查 |
|------|------|---------|
| R1 方法 | 形式化与设计依据 | 问题定义是否有歧义；为何选 X 不选 Y；黑箱步骤；隐含假设是否声明且成立；公式/算法错误 |
| R2 实验 | 证据是否支撑主张 | 基线强弱与公平性；数据集代表性与公开 benchmark；指标是否覆盖主张；统计效力（样本量/显著性/多次运行）；消融能否证明组件必要；可复现描述；结果是否被过度解读；表内数字与正文叙述是否一致 |
| R3 写作与贡献 | 声明与证据对齐 | 贡献列表与正文是否逐条对应；过度声称**与**过度防御两个方向；相关工作是否遗漏关键竞品、描述是否公平；局限是否诚实且集中；结构与逻辑是否通顺；摘要是否准确反映内容；讨论是否回避关键弱点 |

R3 同时按「rw-claim-forward」的双向标准检查：既不放过超出证据的措辞，也把
"以免责开头 / hedge 堆叠 / 替审稿人攻击自己"列为需要修复的问题（P2 起）。

**Domain profile checklists** (built into each `REVIEWER_BRIEF.md` by `rw.py`; definitions in
`${CLAUDE_SKILL_DIR}/../rw-workshop/references/domain-profiles.md`): `clinical-prespecified` → R2 checks the protocol/SAP and the
applicable reporting guideline (e.g. STARD 2015, TRIPOD+AI, CONSORT, CLAIM): primary endpoint and analysis as
prespecified, all prespecified outcomes reported, deviations disclosed, participant flow, reference standard
and blinding, sample size, missing/indeterminate results, CIs, post hoc analyses labelled, registration and
ethics. `systematic-review` → PRISMA 2020. `observational` → STROBE. Under these profiles R3 does **not** ask
for limitations to be removed from places the guideline or journal requires.

## 五、阻塞点分级（替代档位判定）

| 级别 | 定义 | 判据示例 |
|------|------|---------|
| **P0 阻塞** | 不修则该结论不成立、或存在会让稿件被直接退回的硬缺陷 | 正文声明与其引用的表/图数字矛盾；核心主张没有任何实验或推导支撑；缺少该主张直接对照的基线；伦理批准/数据许可声明缺失；引用无法对应参考文献；格式或字数超出目标期刊硬性限制 |
| **P1 必修** | 审稿人大概率据此要求补证据或补论证 | 缺消融以证明关键组件必要；无显著性检验而正文使用了"显著"；隐含假设未声明；相关工作遗漏公认关键竞品；方法节存在无法复现的黑箱步骤 |
| **P2 应修** | 影响说服力与可读性，不动结论 | 术语不一致；图表脱离正文不可读；贡献表述与正文支撑错位；过度防御/自我削弱措辞出现在主张位置 |
| **P3 可选** | 风格与锦上添花 | 语态偏好、句式节奏、可选的补充实验 |

分级只看**问题与证据的关系**，不看提意见的审稿人是谁；同一问题被两位审稿人提出不自动升级。
`clinical-prespecified` 额外 P0：主要终点被替换或未报告、未披露的方案偏离、缺伦理批准或要求的注册号。

## 六、输出格式：`reviews/round-N.md`

`python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py aggregate` writes this file (merged blocker table, verbatim reviewer reports, integrity
flags, revision checklist). Without a shell, produce the same structure by hand:

```markdown
# 模拟评审意见 Round [N]

[顶部声明块]
- 目标期刊：[已确认期刊名]（校准来源见 review-calibration.md / 或校准缺失声明）
- 执行方式：项目外快照沙箱（snapshot）/ 三个新会话（fresh-sessions）/ 未隔离（none）
- 条目计数：P0 [X] ｜ P1 [Y] ｜ P2 [Z] ｜ P3 [W]

## 阻塞点总表（作者据此排期）

| 级别 | 编号 | 来源视角 | 位置 | 一句话问题 | 缺什么证据/说明 | 修改方向（不代写） | 是否需重跑实验 | 预估修改量 |
|------|------|---------|------|-----------|----------------|-------------------|--------------|-----------|
| P0 | R2-1 | R2 | §5.3 表4 | 正文称"跨数据集一致提升"，表4 中数据集C的 NDCG 下降 | 与数据一致的表述，或支撑"一致"的额外证据 | 二选一：缩小主张 / 补该数据集上的机制分析 | 视选择而定 | 半天 |
| P1 | R1-2 | R1 | §3.1 | 选 X 不选 Y 无任何理由 | 设计决策 rationale 或理论对比 | 补一段动机说明（由作者落笔） | 否 | 半页 |
| P2 | R3-3 | R3 | Abstract | 三处 hedge 叠加，弱化已证结论 | 无 | 一处限定，指向 §5 对应表 | 否 | 分钟级 |

## 逐条意见（保留原始表述）

### Reviewer 1 — 方法
[原文要点 + 分级编号列表；分歧条目保留]

### Reviewer 2 — 实验
[...]

### Reviewer 3 — 写作与贡献
[...]

## 审稿人之间的分歧
| 问题 | R? 立场 | R? 立场 | 需作者自行裁决的点 |
|------|--------|--------|------------------|

## 修订核对表（下一轮用，本轮不外传给下轮审稿人）
- P0 清单：[编号 → 处理状态 → 作者如何回应]
- 已确认修复：[编号 + 确认方式（在稿件哪一处看到的）]
- 仍未修复：[编号 + 判断依据]
- 用户明确拒绝的意见：[编号 + 用户理由]（记录，不影响下轮审稿视角）
```

## 七、循环与终止

```
用户提交稿件 → 校准检索（可失败，失败即声明）→ 3 个隔离子代理并行评审
    ↓
聚合为 round-N.md（P0-P3 阻塞点 + 计数）
    ↓
用户自行修改 → 说"再审"
    ↓
Round N+1：新的 review-packet 沙箱 + 新子代理，只给当前稿件快照 + 视角说明（不给前轮意见原文；前轮沙箱已删除）
    ↓
按修订核对表检查 P0/P1 是否真的修好（在稿件哪一处看到的）
```

- **可投状态判据**：P0 = 0，且每条 P1 都有已落实的修改或作者书面说明。
  （这只是阻塞点清点，**不是**"可以录用"的判断。）
- 仍有 P0 → 继续下一轮。
- 达到 `max_rounds`(5) 仍有 P0/P1 未清 → 暂停，输出"未清除条目 + 每条需要什么才能清除"，
  由用户决策：继续迭代 / 接受当前状态投稿 / 调整论文范围或目标期刊。

## 八、防止评审失准

- 不要求"补尽所有相关工作"，只标确实影响核心论证的缺失
- 不因"场景不够多"列为 P0/P1——合理的范围限定是正常学术实践（与「rw-claim-forward」一致）
- 每条意见必须可核查：位置精确到节/表/图，"建议加强实验"不算有效意见，
  "应在[数据集]上对比[方法]以支撑§3.1 的主张"才算
- 不要求经验系统给出理论完备性（有对应实验证据即可）
- 不臆测期刊规则：未检索到的规则一律写"需作者核实"
- 不评价作者身份、机构、前作；不关心"这段是新写的还是原来就有的"，只看当前版本

## 九、禁止事项

- ❌ 不输出修改后的文本（"建议你把这段改为…"句式禁止）
- ❌ 不替作者决定"这条不修了"
- ❌ 不引用其他审稿人的具体措辞（脱盲独立）
- ❌ 不编造引用、数据、期刊规则作为意见依据
- ❌ 不给录用概率、档位判定、"照这样改就能中"的承诺
- ✅ 只给：哪里 → 什么问题类型 → 缺什么证据 → 往哪个方向改 → P 级
