"""Gate enforcement: init/check/advance/migrate/mode/hook-guard."""
import json
import os
import unittest

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # allow `python3 -m unittest tests/<file>`
from helpers import GOOD_G1, GOOD_G2, GOOD_G3, ProjectCase, notes


class InitAndSchema(ProjectCase):
    def test_init_writes_schema_valid_progress(self):
        self.rw("init", check=0)
        out = self.rw("check", check=0).stdout
        self.assertIn("schema OK", out)
        self.assertEqual(self.state()["assistance_mode"], "advisor")

    def test_init_refuses_to_overwrite(self):
        self.rw("init", check=0)
        self.assertEqual(self.rw("init").returncode, 2)

    def test_invalid_enum_fails_schema(self):
        self.rw("init", check=0)
        s = self.state()
        s["target_journal_status"] = "maybe"
        self.save_state(s)
        out = self.rw("check", check=1).stdout
        self.assertIn("target_journal_status", out)

    def test_migrate_upgrades_a_v21_template_file(self):
        v21 = {
            "topic": "t", "writing_direction_confirmed": True, "existing_direction": "e",
            "manuscript_file": "", "target_journal": "",
            "target_journal_status": "unknown | candidate | confirmed", "journal_profile": {},
            "current_stage": "intake",
            "stages": {"intake": {"status": ""},
                       "research": {"status": "", "output_file": "research-notes.md",
                                    "deep_research_mode": "unprobed | native | degraded-by-user-request | absent",
                                    "handoff_file": "deep-research-handoff.md",
                                    "gate": {"G1_confirmed_gap": "", "G2_concrete_next_step": "",
                                             "G3_direction_compared": ""}},
                       "review-loop": {"status": "", "round": 0, "max_rounds": 5,
                                       "isolation": "worktree | snapshot | none",
                                       "blockers": {"P0": 0, "P1": 0, "P2": 0, "P3": 0}}}}
        self.save_state(v21)
        self.rw("check", check=1)
        self.rw("migrate", check=0)
        s = self.state()
        self.assertEqual(s["target_journal_status"], "unknown")
        self.assertEqual(s["stages"]["research"]["deep_research_mode"], "unprobed")
        self.assertEqual(s["assistance_mode"], "advisor")
        self.assertEqual(s["topic"], "t")  # real values survive
        self.rw("check", check=0)


class Gates(ProjectCase):
    def ready_for_design(self, text=None, mode="native", profile="cs-engineering", *extra):
        self.init_complete(profile, *extra)
        self.rw("advance", "--to", "research", check=0)
        self.set_research_mode(mode)
        self.write("research-notes.md", text if text is not None else notes())

    def design_failures(self):
        out = self.rw("check", "--stage", "design", "--json").stdout
        report = json.loads(out)
        return {r["check"]: r["detail"] for r in report["results"] if not r["ok"]}

    def test_intake_must_be_complete_before_research(self):
        self.rw("init", "--topic", "x", check=0)
        before = self.read_bytes(".writing-progress.json")
        out = self.rw("advance", "--to", "research", check=1).stdout
        self.assertIn("refused", out)
        self.assertIn("domain profile chosen", out)
        after = self.read_bytes(".writing-progress.json")
        self.assertEqual(before, after, "a refused advance must not touch the progress file")

    def test_all_gates_pass_and_advance_records_hashes(self):
        self.ready_for_design()
        self.assertEqual(self.design_failures(), {})
        self.rw("advance", "--to", "design", check=0)
        s = self.state()
        self.assertEqual(s["current_stage"], "design")
        self.assertEqual(s["stages"]["research"]["status"], "done")
        entry = s["gate_log"][-1]
        self.assertEqual(entry["to"], "design")
        self.assertIn("research-notes.md", entry["files"])
        self.assertEqual(len(entry["files"]["research-notes.md"]), 64)
        self.assertTrue(s["stages"]["research"]["gate"]["G1_confirmed_gap"].startswith("pass"))

    def test_g1_fails_alone_without_source(self):
        bad = GOOD_G1.replace("https://doi.org/10.1145/1234567", "Smith 2025")
        self.ready_for_design(notes(g1=bad))
        fails = self.design_failures()
        self.assertEqual(list(fails), ["G1 confirmed gap"])
        self.assertIn("gap 1 lacks a source URL or DOI", fails["G1 confirmed gap"])

    def test_g1_fails_without_access_date(self):
        bad = GOOD_G1.replace("— accessed 2026-10-15", "")
        self.ready_for_design(notes(g1=bad))
        self.assertIn("gap 2 lacks an access date", self.design_failures()["G1 confirmed gap"])

    def test_g1_fails_on_template_placeholder(self):
        g1 = "## 已确认的研究空白（G1）\n1. [gap 描述] — 证据来源：[标题/出处/日期] — https://x.org — accessed 2026-01-01\n"
        self.ready_for_design(notes(g1=g1))
        self.assertIn("placeholder", self.design_failures()["G1 confirmed gap"])

    def test_g2_fails_alone_without_time_estimate(self):
        self.ready_for_design(notes(g2=GOOD_G2.replace("- Time estimate: 2 days\n", "")))
        fails = self.design_failures()
        self.assertEqual(list(fails), ["G2 concrete next step"])
        self.assertIn("Time estimate", fails["G2 concrete next step"])

    def test_g2_rejects_vague_action(self):
        g2 = GOOD_G2.replace("run the BM25+dense baseline on dataset B under the 4 GB device profile", "继续调研")
        self.ready_for_design(notes(g2=g2))
        self.assertIn("not concrete", self.design_failures()["G2 concrete next step"])

    def test_g2_accepts_bold_and_chinese_labels(self):
        g2 = "## 确切的下一步（G2）\n- **动作：** 在数据集 B 上补方法 Y 对照\n- **所需资源**：GPU 一张\n- 预计耗时：3 天\n"
        self.ready_for_design(notes(g2=g2))
        self.assertEqual(self.design_failures(), {})

    def test_g3_fails_alone_with_short_table(self):
        g3 = "\n".join(l for l in GOOD_G3.split("\n") if "目标读者" not in l)
        self.ready_for_design(notes(g3=g3))
        fails = self.design_failures()
        self.assertEqual(list(fails), ["G3 direction compared"])
        self.assertIn("3 row(s)", fails["G3 direction compared"])

    def test_g3_requires_decision(self):
        self.ready_for_design(notes(g3=GOOD_G3.replace("- Decision: continuation (延续)\n", "")))
        self.assertIn("Decision", self.design_failures()["G3 direction compared"])

    def test_g3_pivot_requires_cost(self):
        g3 = GOOD_G3.replace("continuation (延续)", "pivot (转向)")
        self.ready_for_design(notes(g3=g3))
        self.assertIn("Pivot cost", self.design_failures()["G3 direction compared"])
        self.write("research-notes.md", notes(g3=g3 + "- Pivot cost: redo the latency experiments (2 weeks)\n"))
        self.assertEqual(self.design_failures(), {})

    def test_g3_untouched_template_decision_fails(self):
        g3 = GOOD_G3.replace("- Decision: continuation (延续)\n",
                             "- Decision: continuation（延续） / pivot（转向）  ← 只保留一个\n"
                             "- Pivot cost:（仅转向时填写：需重做的实验）\n")
        self.ready_for_design(notes(g3=g3))
        self.assertIn("keep exactly one", self.design_failures()["G3 direction compared"])
        g3 = GOOD_G3.replace("- Decision: continuation (延续)\n",
                             "- Decision: pivot（转向）\n- Pivot cost:（仅转向时填写：需重做的实验）\n")
        self.write("research-notes.md", notes(g3=g3))
        self.assertIn("Pivot cost", self.design_failures()["G3 direction compared"])

    def test_skill_template_research_notes_fail_until_filled(self):
        import re
        with open(os.path.join(os.path.dirname(__file__), "..", "skills", "论文骨架", "SKILL.md"), encoding="utf-8") as f:
            skill = f.read()
        template = re.search(r"```markdown\n(# 深度研究笔记.*?)```", skill, re.S).group(1)
        self.ready_for_design(template)
        fails = self.design_failures()
        for gate in ("G1 confirmed gap", "G2 concrete next step", "G3 direction compared"):
            self.assertIn(gate, fails, "an unfilled template must not pass %s" % gate)

    def test_absent_deep_research_is_a_hard_stop(self):
        self.ready_for_design(mode="absent")
        fails = self.design_failures()
        self.assertIn("deep research available", fails)
        self.assertIn("hard stop", fails["deep research available"])
        self.assertEqual(self.rw("advance", "--to", "design").returncode, 1)

    def test_degraded_mode_needs_banner(self):
        self.ready_for_design(mode="degraded-by-user-request")
        self.assertIn("degraded-mode banner at top of notes", self.design_failures())
        self.write("research-notes.md", notes(banner="> ⚠️ 降级模式：普通网页搜索，非 deep research，风险由作者承担\n\n"))
        self.assertEqual(self.design_failures(), {})

    def test_external_handoff_needs_the_file(self):
        self.ready_for_design(mode="external-handoff")
        self.assertIn("hand-off file present", self.design_failures())
        self.write("deep-research-handoff.md", "# hand-off\n")
        self.assertEqual(self.design_failures(), {})

    def test_skeleton_needs_plan_with_integrity_warning_and_duties(self):
        self.ready_for_design()
        self.rw("advance", "--to", "design", check=0)
        self.write("experiment-plan.md", "# 实验设计方案\n## 主实验\n")
        out = self.rw("advance", "--to", "skeleton", check=1).stdout
        self.assertIn("literature integrity warning present", out)
        self.assertIn("argument duty", out)
        self.write("experiment-plan.md", "⚠️ 学术诚信警告\n\n# 实验设计方案\n- 论证职责：证明方法有效\n")
        self.rw("advance", "--to", "skeleton", check=0)


class ClinicalProfile(ProjectCase):
    ENDPOINT = "sensitivity of PET/CT for lateralising aldosterone-producing adenoma"

    def test_intake_requires_primary_endpoint(self):
        self.init_complete("clinical-prespecified")
        out = self.rw("advance", "--to", "research", check=1).stdout
        self.assertIn("primary endpoint recorded from the protocol", out)

    def test_plan_and_outline_must_keep_the_prespecified_endpoint(self):
        self.init_complete("clinical-prespecified", "--primary-endpoint", self.ENDPOINT, "--registry-id", "NCT00000000")
        self.rw("advance", "--to", "research", check=0)
        self.set_research_mode("native")
        self.write("research-notes.md", notes())
        self.rw("advance", "--to", "design", check=0)
        plan = "⚠️ 学术诚信警告\n- 论证职责：x\n- Primary endpoint: specificity at 12 months\n"
        self.write("experiment-plan.md", plan)
        out = self.rw("advance", "--to", "skeleton", check=1).stdout
        self.assertIn("plan names the prespecified primary endpoint", out)
        self.write("experiment-plan.md", plan + "- Prespecified primary endpoint: Sensitivity of PET/CT for lateralising\n  aldosterone-producing adenoma\n")
        self.rw("advance", "--to", "skeleton", check=0)
        self.write("outline.md", "# outline\n## 双向风险标记\n- Main result: AUC (post hoc)\n")
        out = self.rw("advance", "--to", "user-draft", check=1).stdout
        self.assertIn("outline keeps the prespecified primary endpoint", out)
        self.write("outline.md", "# outline\n- Primary endpoint (protocol): %s\n## 双向风险标记\n" % self.ENDPOINT)
        self.rw("advance", "--to", "user-draft", check=0)


class LateStages(ProjectCase):
    def test_review_needs_manuscript_and_confirmed_journal(self):
        self.init_complete()
        out = self.rw("check", "--stage", "review-loop", check=1).stdout
        self.assertIn("manuscript file exists", out)
        self.assertIn("target journal confirmed", out)
        self.write("paper.md", "# Paper\n")
        s = self.state()
        s["manuscript_file"] = "paper.md"
        s["target_journal"] = "J. Example"
        s["target_journal_status"] = "confirmed"
        self.save_state(s)
        self.rw("advance", "--to", "review-loop", check=0)

    def test_moving_back_reopens_instead_of_marking_done(self):
        self.init_complete()
        self.rw("advance", "--to", "research", check=0)
        self.rw("advance", "--to", "intake", check=0)
        s = self.state()
        self.assertEqual(s["stages"]["research"]["status"], "")
        self.assertEqual(s["stages"]["intake"]["status"], "in-progress")

    def test_existing_manuscript_can_jump_to_citation_check(self):
        self.init_complete()
        self.write("paper.md", "# Paper\n")
        s = self.state()
        s["manuscript_file"] = "paper.md"
        self.save_state(s)
        self.rw("advance", "--to", "citation-check", check=0)


class Modes(ProjectCase):
    def test_sentence_edits_requires_explicit_request_and_scope(self):
        self.rw("init", check=0)
        self.assertEqual(self.rw("mode", "sentence-edits").returncode, 2)
        self.rw("mode", "sentence-edits", "--scope", "paper.md §3", "--request",
                "请直接帮我改第三节的句子", check=0)
        s = self.state()
        self.assertEqual(s["assistance_mode"], "sentence-edits")
        self.assertEqual(s["mode_history"][-1]["user_request"], "请直接帮我改第三节的句子")
        log = self.read_bytes("ai-assistance-log.md").decode("utf-8")
        self.assertIn("assistance mode → sentence-edits", log)
        self.rw("mode", "advisor", check=0)
        self.assertEqual(self.state()["assistance_mode"], "advisor")


class HookGuard(ProjectCase):
    def hook(self, tool, path):
        payload = {"tool_name": tool, "tool_input": {"file_path": path}, "cwd": self.project,
                   "hook_event_name": "PreToolUse"}
        return self.rw("hook-guard", stdin=json.dumps(payload))

    def test_blocks_experiment_plan_until_gates_pass(self):
        self.init_complete()
        self.rw("advance", "--to", "research", check=0)
        target = os.path.join(self.project, "experiment-plan.md")
        res = self.hook("Write", target)
        self.assertEqual(res.returncode, 2)
        self.assertIn("design", res.stderr)
        self.set_research_mode("native")
        self.write("research-notes.md", notes())
        self.assertEqual(self.hook("Write", target).returncode, 0)

    def test_manuscript_is_read_only_in_advisor_mode(self):
        self.init_complete()
        path = self.write("paper.md", "# Paper\n")
        s = self.state()
        s["manuscript_file"] = "paper.md"
        self.save_state(s)
        self.assertEqual(self.hook("Edit", path).returncode, 2)
        self.rw("mode", "sentence-edits", "--scope", "paper.md", "--request", "please edit my sentences", check=0)
        self.assertEqual(self.hook("Edit", path).returncode, 0)

    def test_ignores_other_tools_and_non_workbench_paths(self):
        self.init_complete()
        self.assertEqual(self.hook("Read", os.path.join(self.project, "experiment-plan.md")).returncode, 0)
        self.assertEqual(self.hook("Write", os.path.join(self.tmp, "elsewhere", "outline.md")).returncode, 0)
        self.assertEqual(self.rw("hook-guard", stdin="not json").returncode, 0)


if __name__ == "__main__":
    unittest.main()
