# Research Workbench

> **EN**: An AI research advisor toolkit — from topic intake to peer review. Framework-agnostic prompts for any LLM agent, plus an optional standard-library checker that enforces the gates. Advisor by default; sentence-level edits only when you explicitly ask. Never predicts acceptance odds.
> **中**: AI 学术研究导师工具包——从写作方向确认到模拟审稿。框架无关的 Prompt 集合，外加可选的门禁检查脚本（仅标准库）。默认只做导师；你明确要求时才逐句修改。绝不预测录用概率。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is this?

A collection of **structured AI prompts** (skills) that turn any LLM into an academic research advisor:
direction intake → deep research (with a capability probe) → gated experiment design → claim-forward outline
→ citation audit → bidirectional claim calibration → blinded multi-reviewer simulation.

一组**结构化 AI 提示词**，把任何 LLM 变成学术导师：
启动问询 → 深度研究（先探能力）→ 门禁后实验设计 → 主张先行骨架 → 引用审查 → 双向声明校准 → 脱盲多视角审稿。

### Core philosophy

**Research advisor, not ghostwriter — by default.** In the default *advisor* mode it never produces paragraphs you can paste into a paper: every output is a plan, a diagnostic or a revision point. If you explicitly ask for sentence-level edits of **your own** text, it switches to a recorded, scoped *sentence-edits* mode (original → suggested → reason; no new claims, numbers or citations; every batch logged for AI-use disclosure). Drafting new sections from scratch is not provided in either mode.

**It stops instead of faking.** No deep-research tool → it halts and hands you a copy-paste research prompt, rather than passing model memory off as a literature survey.

**The study type decides the rules.** A prespecified clinical study keeps its protocol's primary endpoint; a systematic review follows PRISMA 2020; a CS method paper may pick the comparison where it wins (at design time, never by deleting numbers).

---

## What's new in v2.2.0

| Change | Why |
|--------|-----|
| **Domain profiles** chosen at intake: `cs-engineering`, `clinical-prespecified`, `systematic-review`, `observational`, `custom` (`skills/写作工坊/references/domain-profiles.md`) | The claim-forward rules ("re-select the main result", "no limitations in the abstract") are wrong for protocol-driven studies and some reporting guidelines |
| **Gates checked by a tool**: `tools/rw.py check / advance` computes G1–G3 and every stage prerequisite from the files themselves; `advance` refuses and records a gate log with SHA-256 of what passed | v2.1 gates were self-assessed by the model |
| **Reviewer sandboxes outside the project** (`rw.py review-packet`): manuscript snapshot under a neutral name, no `.git`, no progress file, no earlier reviews; `.docx` revisions/comments/author metadata refused or stripped; `rw.py aggregate` counts P0–P3 and flags leakage, verdicts and snapshot edits, then deletes the sandboxes | A git worktree (the v2.1 first choice) contains every tracked file and the full history |
| **Opt-in sentence-edits mode** with scope, the user's own request and an `ai-assistance-log.md` | Lets authors ask for replacement sentences without dropping the safeguards |
| **`external-handoff` research mode** | v2.1 had no valid state for "deep research was done elsewhere and handed back" |
| **Packaging**: `tools/build.py` generates the bundle and two exports — `dist/claude-code/rw-*` (ASCII names, Claude Code fields) and `dist/agent-skills/rw-*` (Agent Skills spec-only frontmatter, uploadable) | Chinese skill names work in Claude Code but fail the Agent Skills spec used by claude.ai uploads and the Skills API |
| **Test suite** (`tests/`, stdlib `unittest`) | Gates, isolation, aggregation, exports and an end-to-end clinical walkthrough are regression-tested |
| Citation formats now include Vancouver/NLM, AMA, ACM and APA; template contradictions about where limitations go are resolved per profile | |

<details><summary>What was new in v2.1.0</summary>

| Change | Why |
|--------|-----|
| Stage 0 mandatory intake (writing direction + existing research line + materials + target journal) | Without the direction confirmed, every downstream stage guesses |
| Deep-research capability probe with **hard stop** | 选题判断需要多轮检索+交叉验证；单次或多轮普通网页搜索都不够，假装做过更糟 |
| Stage 1→2 gate `G1/G2/G3` (confirmed gap · concrete next step · direction compared) | Experiment plans built on an unconfirmed gap look complete but are misdirected |
| New skill `反防御写作` (claim-forward) applied to outline + polish | Over-defensive writing turns papers into self-audit reports; claim strength is still capped by evidence |
| Manuscript intake asks for target journal first; if none, web-search a shortlist of verifiable fields | Reviewer calibration and format checks are meaningless without a venue |
| Reviewers run as isolated subagents (v2.2: snapshot sandboxes instead of git worktrees) | The main chat has already seen author intent and revision history — it cannot be truly blind |
| Review output = `P0-P3` blockers + counts | Actionable triage instead of vibes |
| **No acceptance probabilities, no decision tiers** | A simulation cannot predict an editorial decision |

</details>

---

## Quick start

```bash
git clone https://github.com/xuzeTop1/research-workbench.git
cd research-workbench
```

### Claude Code (recommended: the generated export)

```bash
for d in "$PWD"/dist/claude-code/rw-*; do ln -s "$d" ~/.claude/skills/; done
```

Invoke with **`/rw-workshop`** (only the orchestrator appears in the `/` menu; Claude loads the other seven
`rw-*` skills itself). The skills call the bundled checker as `${CLAUDE_SKILL_DIR}/scripts/rw.py`, pre-approved
for the invoking turn through `allowed-tools`. Needs `python3` (3.9+) for the checker; the prompts work without it.

| Export name | Source skill | Stage |
|---|---|---|
| `rw-workshop` | 写作工坊 | orchestrator, intake, gates, modes |
| `rw-skeleton` | 论文骨架 | Stage 1 research + Stage 3 outline |
| `rw-writing-principles` | 科研写作 | writing doctrine, journal shortlist |
| `rw-claim-forward` | 反防御写作 | claim-forward rules, profile precedence |
| `rw-experiment-design` | 实验设计 | Stage 2 |
| `rw-citation-audit` | 引用审查 | Stage 4 |
| `rw-polish` | 论文润色 | Stage 5 |
| `rw-mock-review` | 模拟审稿 | Stage 6 |

### claude.ai uploads, the Skills API, other Agent Skills hosts

Use `dist/agent-skills/rw-*`: spec-only frontmatter (`name`, `description`, `license`, `compatibility`,
`metadata`), ASCII names that match their directories, and `scripts/rw.py` inside each skill.

### Qoder (plugin)

The plugin manifest `.qoder-plugin/plugin.json` points at the original source folders under `skills/`
(Chinese names, unchanged). Invoke via `/写作工坊`.

### Cursor / Windsurf / Cline / Aider / any agent with a rules file

```bash
cp BOOTSTRAP.md .cursorrules        # or .windsurfrules, Cline custom instructions, Aider system prompt
```

Open the repository as the workspace so the agent can read `skills/*/SKILL.md` and run `python3 tools/rw.py`.

### ChatGPT / any chat LLM without files or a shell

Paste `dist/research-workbench-full-bundle.md` (BOOTSTRAP + all skills + references), or paste `BOOTSTRAP.md`
first and the relevant `SKILL.md` per stage. The gates are then checked by hand with the checklist in BOOTSTRAP.

---

## The checker: `tools/rw.py`

Python 3.9+, standard library only. Exit codes: `0` ok · `1` check failed / refused · `2` usage or I/O error.

```bash
python3 tools/rw.py init --topic "…" --confirm-direction --existing-direction "…" --materials "…" \
    --domain-profile clinical-prespecified --primary-endpoint "<verbatim from the protocol>" --registry-id NCT…
python3 tools/rw.py check                    # schema + current stage consistent? + what blocks the next stage
python3 tools/rw.py check --stage design     # G1/G2/G3 + everything Stage 2 needs
python3 tools/rw.py advance --to design      # the only way to move current_stage; refuses on failure
python3 tools/rw.py status
python3 tools/rw.py mode sentence-edits --scope "paper.docx §3" --request "<the user's words>"
python3 tools/rw.py mode advisor
python3 tools/rw.py log --stage polish --summary "12 sentence edits in §3–§4"
python3 tools/rw.py review-packet --journal-profile review-calibration.md [--material fig1.png]
python3 tools/rw.py aggregate                # → reviews/round-N.md, P0–P3 counts, integrity flags; deletes sandboxes
python3 tools/rw.py migrate                  # upgrade a v2.1 .writing-progress.json in place
python3 tools/rw.py schema                   # print the progress-file schema
```

What the gates require (format used by the `research-notes.md` template in 「论文骨架」):

- **G1** — every confirmed gap carries a URL or DOI **and** `accessed YYYY-MM-DD`; no template placeholders.
- **G2** — `Action:` (a concrete action, not "continue research"), `Resources:`, `Time estimate:` with a duration.
- **G3** — the 4-row comparison table filled (problem, method, data/evaluation, audience) and exactly one
  `Decision: continuation` or `Decision: pivot` (+ `Pivot cost:` when pivoting).
- **Profiles** — `clinical-prespecified`: primary endpoint recorded at intake and quoted verbatim in
  `experiment-plan.md` and `outline.md`; `systematic-review`: outline mapped to PRISMA; `observational`: STROBE.

### Optional: a Claude Code hook that enforces the gates

`rw.py hook-guard` reads a PreToolUse payload on stdin. For a project that has `.writing-progress.json` it
blocks (exit 2, reason on stderr) writes to `experiment-plan.md` / `outline.md` while their prerequisites fail,
and edits to the manuscript file while the project is in advisor mode; everything else is allowed (exit 0),
including malformed payloads and paths outside workbench projects. Add it to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          { "type": "command", "command": "python3 \"$HOME/.claude/skills/rw-workshop/scripts/rw.py\" hook-guard" }
        ]
      }
    ]
  }
}
```

The guard's decisions are unit-tested with synthetic payloads; the wiring above follows Claude Code's
settings-file hook format but was not exercised end-to-end in a live session — check it against your Claude Code
version's hooks documentation before relying on it. It does not see edits made through shell commands or scripts.

---

## Migrating from v2.1

- Run `python3 tools/rw.py migrate` in each project: it adds the v2.2 fields and replaces v2.1 template
  placeholders such as `"unknown | candidate | confirmed"` with real defaults; real values are kept.
- Answer the new intake question ⑤ (study type) — `rw.py check` reports it until `domain_profile` is set.
- Re-write G1–G3 in `research-notes.md` in the checkable format above if `check --stage design` rejects them.
- Stage 6 no longer uses git worktrees; use `rw.py review-packet`.
- Claude Code users: switch from the Chinese-named source folders to `dist/claude-code/rw-*` and `/rw-workshop`.

---

## Usage example

```
You: /rw-workshop  方向是"面向端侧资源的个性化混合检索"

AI:  [Intake] 先确认五件事：①写作方向 ②你/课题组现有研究方向 ③手头材料 ④目标期刊（没有就说"未定"）
     ⑤研究类型（CS 方法论文 / 预注册临床研究 / 系统综述 / 观察性研究 / 其他）。

You: 现有方向的延续；有 2 个数据集和部分结果；刊未定；CS 方法论文。

AI:  [rw.py advance --to research ✓] [Capability probe] 未检测到深度研究工具（只有单次网页搜索）。
     ⛔ Stage 1 中断。请用下面这段交接 prompt 在带 deep research 的平台跑一次，
     把结果存为 deep-research-handoff.md 后说"继续"。

You: [runs it elsewhere, saves the file] 继续

AI:  [deep_research_mode = external-handoff] [research-notes.md written]
     rw.py check --stage design → G1 PASS (3 sourced gaps) · G2 FAIL — missing 'Time estimate:' · G3 PASS
     → 下一步需要一个耗时估计：在 [数据集B] 上补 [方法Y] 对照大约要多久？

You: 两天。

AI:  [rw.py advance --to design ✓ gate log written] → Stage 2 … → Stage 3 outline.md

You: [writes the paper] 我写完了，帮我查引用，然后直接帮我改摘要里的句子。

AI:  先确认目标期刊…  [citation-report.md]
     你要求逐句修改摘要 → rw.py mode sentence-edits --scope "paper.docx Abstract" --request "直接帮我改摘要里的句子"
     | # | 位置 | 原文 | 建议句 | 理由 | … (no new claims, numbers or citations; logged)

You: 审稿一轮。

AI:  [review-calibration.md from web search] [rw.py review-packet → 3 sandboxes outside the project]
     [3 isolated reviewers, each told only: "Read <sandbox>/REVIEWER_BRIEF.md and follow it"]
     [rw.py aggregate] Round 1: P0 1 · P1 4 · P2 3 · P3 2 · integrity flags 0.
     P0-1 §5.3 表4：正文称跨数据集一致提升，表中数据集C的 NDCG 下降 → 缩小主张或补机制分析。
     （不预测录用结果，不给档位判定。修改后说"再审"。）
```

---

## Architecture

```
BOOTSTRAP.md          ← Single entry for paste-only use: role + rules + gated workflow
skills/               ← Sources (Chinese folder names kept for upstream/Qoder compatibility)
├── 写作工坊/          ← Orchestrator: intake, probe, gates, modes, review loop
│   └── references/   ← domain-profiles.md, assistance-modes.md
├── 论文骨架/          ← Stage 1 + 3: capability probe & hand-off prompt, gates, outline
├── 科研写作/          ← Writing doctrine: editing funnel, given→new, section recipes, venue picking
├── 反防御写作/        ← Claim-forward rules, evidence ceiling, domain-profile precedence
├── 实验设计/          ← Stage 2: entry gate, profile adaptations, per-experiment argument duty
├── 论文润色/          ← Stage 5: bidirectional calibration; sentence-edits output on opt-in
├── 引用审查/          ← Stage 4: citation audit (6 dimensions)
└── 模拟审稿/          ← Stage 6: snapshot sandboxes, calibration, P0-P3 blockers
tools/
├── rw.py             ← checker / mode switch / review packets / aggregation / hook guard
└── build.py          ← generates everything in dist/ (deterministic; --check detects stale output)
tests/                ← stdlib unittest suite
dist/
├── research-workbench-full-bundle.md
├── claude-code/rw-*/ ← Claude Code skills (ASCII names; ship scripts/rw.py)
└── agent-skills/rw-*/← Agent Skills spec export (uploadable)
```

---

## Guardrails

| Rule | Enforcement |
|------|-------------|
| No ghostwriting by default | Advisor mode returns argument structure; the optional hook blocks manuscript edits in advisor mode |
| Sentence edits only on request | `rw.py mode sentence-edits` needs a scope and the user's own words; edits never add claims, numbers or citations; logged |
| Citations need verification | Every recommendation tagged `[needs user verification]` with source + date |
| Venue facts need verification | Impact factor / quartile / limits / turnaround only as retrieved, else "not found — verify yourself" |
| No fabricated data | Never outputs numbers that did not come from your actual experiments |
| Capability honesty | Hard stop when deep research is unavailable; never auto-degrades without your instruction |
| Gates over momentum | `rw.py advance` refuses until G1–G3 and stage prerequisites pass |
| Domain profile first | Prespecified endpoints are never re-selected; limitations follow the reporting guideline |
| Two-way wording calibration | Flags over-claiming **and** over-defensive / self-weakening phrasing |
| Review = blockers only | Location + problem type + missing evidence + direction; never replacement text |
| Review = blinded | Snapshot sandboxes outside the project; leakage, verdicts and snapshot edits flagged by `rw.py aggregate` |
| No outcome prediction | No percentages, no ACCEPT / MINOR / MAJOR / REJECT verdicts |

Known limits: an agent that has file tools can still open paths outside its sandbox if it decides to — the
aggregate step flags what it can detect, not everything; the checker validates structure (sources present,
dates present, fields filled), not whether a cited paper really says what is claimed.

---

## Development

```bash
python3 tools/build.py                       # regenerate dist/ after editing anything under skills/ or tools/
python3 tools/build.py --check               # exit 1 if dist/ is stale
python3 -m unittest discover -s tests -v     # full test suite (Python 3.9+, no network)
```

## Built-in references

- `skills/写作工坊/references/domain-profiles.md` — which rules apply to which study type
- `skills/写作工坊/references/assistance-modes.md` — advisor vs. sentence-edits
- `skills/论文润色/references/claim-calibration-guide.md` — two-way wording calibration table
- `skills/引用审查/references/citation-formats.md` — GB/T 7714 / IEEE / Vancouver (NLM) / AMA / ACM / APA quick reference
- `skills/论文骨架/references/paper-structure-templates.md` — Chinese journal & English conference structure templates
- `dist/research-workbench-full-bundle.md` — single-file bundle for paste-only chat LLMs

## Third-party credits

`skills/科研写作` and `skills/反防御写作` restate principles from two MIT-licensed community skills,
rewritten to fit this repo's no-ghostwriting and evidence-ceiling rules:

- [YuanZHAO321/Scientific-Writing-zh](https://github.com/YuanZHAO321/Scientific-Writing-zh) — scientific writing doctrine
- [Adkid-Zephyr/anti-defensive-writing-Skill](https://github.com/Adkid-Zephyr/anti-defensive-writing-Skill) — anti-defensive writing principles

The upstream "show the rewrite instead of describing it" habit is **not** the default here (see Core
philosophy; it is available only through the explicit sentence-edits opt-in); the "never report a losing result"
reading of anti-defensive writing is excluded — phrasing may be reframed, reported data may not be hidden.

---

## License

MIT — free for academic and personal use. Attribution appreciated.
