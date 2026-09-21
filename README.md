# Research Workbench

> **EN**: An AI research advisor toolkit — from topic selection to peer review. Framework-agnostic prompts for any LLM agent. Never ghostwrites.
> **中**: AI 学术研究导师工具包——从选题到审稿。框架无关的 Prompt 集合，适用于任何 LLM Agent。绝不代写。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is this?

A collection of **structured AI prompts** (skills) that turn any LLM into an academic research advisor. Covers: topic research → experiment design → paper outline → citation audit → language polish → iterative peer review.

一组**结构化 AI 提示词**，把任何 LLM 变成学术导师。覆盖：选题 → 实验设计 → 骨架 → 引用审查 → 润色 → 审稿循环。

### Core Philosophy

**Research advisor, not ghostwriter.** It will never produce paragraphs you can paste into a paper. Every output is a plan, a diagnostic, a revision point. You remain the author.

**研究导师，不是代笔人。** 永远不产出可以粘贴进论文的段落。所有输出是规划、诊断、修改点。你始终是作者。

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/xuzeTop1/research-workbench.git
cd research-workbench
```

### 2. Use with your AI agent

Pick your platform below. All methods use the same prompt files.

---

## Platform Guide

### Cursor / Windsurf / any IDE with rules file

```bash
# Symlink or copy BOOTSTRAP.md as your project rules
cp BOOTSTRAP.md .cursorrules
# or
cp BOOTSTRAP.md .windsurfrules
```

Then open the `research-workbench/` folder as your workspace. The AI reads `skills/*/SKILL.md` on demand when you invoke stages.

### Cline (VS Code extension)

Paste `BOOTSTRAP.md` content into Cline's **Custom Instructions** (Settings → Prompts → Custom Context). Add the `skills/` folder to your project context.

### Claude (Web / Desktop / API)

- **Claude Projects**: Upload `BOOTSTRAP.md` as project knowledge + attach relevant `SKILL.md` files per conversation.
- **API**: Use `BOOTSTRAP.md` as system prompt, load skill files into `user` messages as needed.

```python
# Example: Claude API
system = open("BOOTSTRAP.md").read()
user_turn_1 = open("skills/论文骨架/SKILL.md").read()
# → Start Stage 1
```

### ChatGPT / any chat LLM

1. Paste `BOOTSTRAP.md` as your **first message** (or into Custom Instructions)
2. When entering a new stage, paste the corresponding `SKILL.md` file content
3. Tell the AI your topic and target journal

### QoderWork

Copy the entire folder to `~/.qoderworkcn/plugins-custom/` (or `%USERPROFILE%\.qoderworkcn\plugins-custom\` on Windows). Auto-detected on next launch. Invoke via `/写作工坊`.

### Aider / Open Interpreter / Custom agent frameworks

Load `BOOTSTRAP.md` as system instructions. Configure file read access to the `skills/` directory so the agent can progressively load stage-specific rules.

---

## Usage Example

```
You: [paste BOOTSTRAP.md content as first message]

AI:  [Reads bootstrap, adopts Research Advisor role]

You: 我想投 TOIS，选题方向是"面向端侧资源的个性化混合检索"，帮我从 Stage 1 开始。

AI:  [Searches web for TOIS scope, identifies gaps, outputs research-notes.md]
     → Stage 1 完成。推进到 Stage 2？

You: 继续

AI:  [Recommends literature with ⚠️ verification warnings,
      designs experiment plan: datasets, baselines, metrics, ablations]
     → Stage 2 完成。

You: [writes the paper offline for 2 weeks]

You: 我写完了，帮我查引用。

AI:  [Reads your paper, runs 6-dimension citation audit,
      outputs problem list with [需用户决策] tags]
     → 引用审查报告已输出。3 条严重问题需你处理。

You: 改好了，审稿一轮。

AI:  [Three independent reviewers + AE verdict,
      outputs revision points table (位置|问题|方向|严重度)]
     → Round 1: MAJOR REVISE (2 Major, 5 Minor)。修改后说"再审"。

You: [revises independently]

You: 再审。

AI:  [Fresh reviewer perspective, independent of Round 1's specific wording]
     → Round 2: MINOR REVISE。无 Major，3 条 Minor。
```

---

## Architecture

```
BOOTSTRAP.md          ← Single entry: role definition + rules + workflow
skills/
├── 写作工坊/          ← Orchestrator (detailed stage coordination logic)
├── 论文骨架/          ← Stage 1 + 3: research & outline
├── 实验设计/          ← Stage 2: literature + experiment plan
├── 论文润色/          ← Stage 5: language suggestions (diff format)
├── 引用审查/          ← Stage 4: citation audit (6 dimensions)
└── 模拟审稿/          ← Stage 6: multi-persona review (double-blind)
```

Each `SKILL.md` is a self-contained prompt — readable by any LLM, no tool dependencies. The system works purely through conversation + file read/write.

---

## Guardrails

| Rule | Enforcement |
|------|------------|
| No ghostwriting | Refuses "write this paragraph for me" requests |
| Citations need verification | Every literature recommendation tagged `[needs user verification]` |
| No fabricated data | Never outputs numbers that weren't from user's actual experiments |
| Review = points only | Outputs location + problem + direction, never replacement text |
| Polish = language only | Never adds/removes claims, arguments, or data descriptions |
| Double-blind reviews | Reviewers don't see each other; rounds don't leak prior wording |

---

## References (Built-in)

- `skills/论文润色/references/defensive-style-guide.md` — Academic hedging patterns (10+ absolute-claim → defensive-alternative pairs)
- `skills/引用审查/references/citation-formats.md` — GB/T 7714 / IEEE / ACM / APA quick reference
- `skills/论文骨架/references/paper-structure-templates.md` — Chinese journal & English conference structure templates

---

## License

MIT — free for academic and personal use. Attribution appreciated.
