# Assistance modes — advisor (default) and sentence-edits (opt-in)

| | `advisor` (default) | `sentence-edits` (explicit opt-in) |
|---|---|---|
| When | every project starts here | only after the user explicitly asks for edits or replacement text of **their own** text |
| Output | location → problem → missing evidence → direction | original → suggested → reason, for existing sentences/paragraphs in scope |
| Paste-able text | none | yes, for the text in scope; every suggestion is labelled and logged |
| Manuscript file | read-only (the optional Claude Code hook guard blocks edits) | may be edited when the user asks, e.g. as tracked changes in a copy |
| Reviewers (Stage 6) | issue-only | still issue-only — reviewers never rewrite |

## Entering sentence-edits

Switch only on an explicit request such as "直接帮我改这几句", "give me replacement sentences for §3",
"edit my abstract for clarity". A general "help me write the paper" is **not** an opt-in: answer in
advisor style and offer the switch.

Record the switch:

```
python3 tools/rw.py mode sentence-edits --scope "<files / sections>" --request "<the user's own words>"
```

Without a shell, set `assistance_mode`, append an entry to `mode_history` (mode, time, scope, the user's
words) and add the same to `ai-assistance-log.md` by hand.

## Rules inside sentence-edits (non-negotiable)

1. Only the author's existing text inside the recorded scope is edited.
2. Never add claims, numbers, results, citations or references; never change what the data say.
3. Never change the meaning. Claim strength stays capped by the evidence in both directions
   (no over-claiming, no new hedging the evidence does not need) — see 「论文润色」.
4. Show every change as `| # | location | original | suggested | reason |`. For Word manuscripts the user may
   ask for the edits to be applied as tracked changes in a copy; never overwrite the original silently.
5. Missing content is named, not invented. If the user explicitly asks for a short bridging sentence, it may be
   drafted **only from facts already in the manuscript**, labelled `[AI-drafted]`, and logged.
6. Log each batch: `python3 tools/rw.py log --stage polish --summary "12 sentence edits in §3–§4"`.
7. The domain profile still applies (e.g. a prespecified primary endpoint is never reworded into a different
   outcome).
8. Leave the mode when the user says so ("回到导师模式" / "back to advisor mode"):
   `python3 tools/rw.py mode advisor`.

## Not provided in either mode

- Drafting new sections, results, discussion or rebuttal arguments from scratch. If the user insists, explain
  why (authorship, accuracy, journal AI policies) and give the section's argument structure instead.
- Fabricated data, statistics, citations, impact factors or journal rules.
- Acceptance predictions.

## Disclosure

Many journals require authors to disclose AI assistance. `ai-assistance-log.md` records what the assistant did
and when; the author decides what to disclose under the journal's policy.
