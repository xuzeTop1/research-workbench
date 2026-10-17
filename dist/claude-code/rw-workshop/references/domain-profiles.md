# Domain profiles — which writing rules apply to which kind of study

Stage 0 records `domain_profile` in `.writing-progress.json`. The profile decides which of the
workbench's default writing rules apply. **When a profile and a default rule conflict, the profile
wins.** If it is unclear which profile fits, ask the user — never pick one silently.

| Profile | Use for | Reporting guideline(s) — check the EQUATOR Network for the current version |
|---|---|---|
| `cs-engineering` | CS / engineering method and system papers (conferences, CS journals) | none mandatory; use the venue's own checklist (e.g. a reproducibility checklist) if it has one |
| `clinical-prespecified` | Studies run under a protocol and/or statistical analysis plan (SAP), often registered: diagnostic accuracy, prediction models, trials, prespecified reader studies | whichever apply: STARD 2015 (diagnostic accuracy), TRIPOD+AI (prediction models, including machine learning), CONSORT (randomised trials), SPIRIT (trial protocols), CLAIM (AI in medical imaging) |
| `systematic-review` | Systematic reviews and meta-analyses | PRISMA 2020, including PRISMA 2020 for Abstracts |
| `observational` | Cohort, case-control and cross-sectional studies without a binding prespecified analysis | STROBE |
| `custom` | Anything else (qualitative, mixed methods, humanities, …) | what the user names in `domain_profile_notes` |

Intake fields per profile (Stage 0):

- every profile: `domain_profile`;
- `clinical-prespecified`: `protocol.primary_endpoint` copied **verbatim** from the protocol/SAP, plus
  `protocol.registered` / `protocol.registry_id`, `protocol.protocol_file`, `protocol.sap_file` when they exist;
- `systematic-review`: `protocol.registry_id` (e.g. a PROSPERO ID) when the protocol is registered;
- `custom`: `domain_profile_notes` (which guideline applies, which default rules to relax).

`python3 scripts/rw.py check` enforces the profile-specific items marked **[checked]** below.

---

## cs-engineering (default for CS venues)

All default rules apply, including the claim-forward rules of 「rw-claim-forward」 with their evidence ceiling:

- decide at **design time** which comparison the paper competes on ("where this paper wins") — never
  delete reported numbers afterwards;
- limitations collected in Discussion/Limitations; no apologetic openers; one qualifier per claim;
- the outline states where the paper wins **[checked: "Where this paper wins" / "本文赢在哪场比赛" in outline.md]**.

## clinical-prespecified

The protocol and SAP are the contract. The workbench treats them as fixed inputs, not as narrative choices.

1. **Endpoint and analysis are fixed by the protocol.** The experiment plan and the outline quote the
   prespecified primary endpoint verbatim **[checked in experiment-plan.md and outline.md]**.
2. **No post-hoc re-framing of results.** These claim-forward rules do **not** apply to prespecified
   outcomes: "re-select the main result", "redefine the problem / rewrite the story when results do not
   support it", "switch to an evaluation dimension where the paper wins", and steps 2–6 of the default
   decision order in 「rw-claim-forward」. Further analyses are allowed only when labelled *post hoc / exploratory*.
3. **Report every prespecified outcome**, including null or unfavourable ones, where the protocol and the
   guideline expect them.
4. **Disclose protocol deviations** with the reason (changed reference standard, population, threshold, …);
   never absorb them silently.
5. **Limitations**: a limitations section in the Discussion is required. Put limitations in the abstract or a
   "strengths and limitations" box whenever the journal or guideline asks for it — the default
   "no limitations in the abstract" rule does not apply.
6. **Uncertainty instead of hedge words**: effect sizes with confidence intervals; "significant" only for the
   prespecified test at the prespecified threshold; no causal verbs for non-randomised comparisons.
   "One qualifier per claim" still applies to filler ("may possibly", "to some extent"), not to statistical
   uncertainty, which is always reported.
7. **Claim-forward still applies to tone** — no apologetic openers, no attacking your own work for the
   reviewer, limitations not scattered through Methods/Results — but content is never moved out of sight.
8. **Stage 2 becomes an analysis-plan check**: alignment with the protocol/SAP, sample-size justification,
   reference standard and blinding of readers/assessors, handling of indeterminate and missing results,
   prespecified subgroup and sensitivity analyses, multiplicity.
9. **Mock review**: R2 uses the applicable reporting guideline as its checklist. Extra P0 triggers:
   switched or unreported primary outcome, undisclosed protocol deviation, missing ethics approval or
   required registration.
10. If `protocol.registered` is true, `protocol.registry_id` must be filled **[checked]**.

## systematic-review

1. Record the registered protocol (e.g. PROSPERO) in `protocol.registry_id` when there is one.
2. "Where this paper wins" is replaced by the review question (e.g. PICO) and the certainty of the evidence.
3. Claim strength is capped by the certainty of evidence (e.g. GRADE), not by the preferred story.
4. Keep the limitations of the evidence in the abstract (PRISMA 2020 for Abstracts asks for them).
5. The outline is mapped to PRISMA 2020 **[checked: "PRISMA" in outline.md]**.
6. Mock review R2: reproducible search (sources, dates, full strategy), selection with flow diagram, risk of
   bias, synthesis methods, certainty, limitations of the evidence.

## observational

1. The outline is mapped to STROBE **[checked: "STROBE" in outline.md]**.
2. Causal language only as far as the design supports; confounding and bias handling are part of the main
   argument, not an afterthought.
3. If an analysis plan was written before the analysis, treat its outcomes like `clinical-prespecified`
   (record `protocol.primary_endpoint`, no post-hoc re-framing).
4. A limitations section in the Discussion is required.

## custom

Describe in `domain_profile_notes` which guideline applies and which default rules to relax
**[checked: notes not empty]**. When a default rule conflicts with the named guideline, follow the guideline.
When in doubt, apply the stricter of the two rules.

---

## Template conflicts resolved by profile

- 「rw-skeleton」 `references/paper-structure-templates.md`: the Chinese system-paper template places
  "6.6 已知局限" in the experiments chapter and a "不足声明" in the conclusion. Under `cs-engineering`, keep
  them only when the target journal's own template asks for that layout; otherwise move them to a
  Discussion/Limitations section. All other profiles follow their guideline's structure.
- 「rw-skeleton」 Stage 3 outline: "⛔ 本节不写局限" for the abstract applies to `cs-engineering` only.
- 「rw-experiment-design」: "decide which metric is the main battlefield" applies to `cs-engineering`; under
  `clinical-prespecified` the main outcome is the protocol's.
