"""End-to-end: the documented command sequence for a prespecified clinical study."""
import json
import os
import unittest

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # allow `python3 -m unittest tests/<file>`
from helpers import ProjectCase, notes

ENDPOINT = "per-patient sensitivity for lateralising primary aldosteronism"


class ClinicalWalkthrough(ProjectCase):
    def test_full_workflow(self):
        out = os.path.join(self.tmp, "sandboxes")
        self.rw("init", "--topic", "PET/CT lateralisation in primary aldosteronism", "--confirm-direction",
                "--existing-direction", "department adrenal PET programme (continuation)",
                "--materials", "locked dataset, SAP v1.2, draft methods",
                "--domain-profile", "clinical-prespecified", "--primary-endpoint", ENDPOINT,
                "--registry-id", "NCT00000000", check=0)
        self.rw("advance", "--to", "research", check=0)

        # hard stop until deep research exists, then the user brings a hand-off file
        self.write("research-notes.md", notes())
        self.assertEqual(self.rw("advance", "--to", "design").returncode, 1)
        s = self.state()
        s["stages"]["research"]["deep_research_mode"] = "external-handoff"
        self.save_state(s)
        self.write("deep-research-handoff.md", "# hand-off from an external deep-research run\n")
        self.rw("advance", "--to", "design", check=0)

        self.write("experiment-plan.md", "⚠️ 学术诚信警告\n\n# Analysis-plan check\n"
                   "- Prespecified primary endpoint: %s\n- 论证职责：primary analysis per SAP\n" % ENDPOINT)
        self.rw("advance", "--to", "skeleton", check=0)
        self.write("outline.md", "# Outline (STARD 2015)\n- Primary endpoint (protocol, verbatim): %s\n"
                   "## 双向风险标记\n| § | type | note |\n" % ENDPOINT)
        self.rw("advance", "--to", "user-draft", check=0)

        self.write("manuscript.md", "# Manuscript\n\nSensitivity was 0.91 (95% CI 0.84–0.95).\n")
        s = self.state()
        s.update(manuscript_file="manuscript.md", target_journal="EJNMMI Research", target_journal_status="confirmed")
        self.save_state(s)
        self.rw("advance", "--to", "citation-check", check=0)
        self.rw("advance", "--to", "polish", check=0)
        self.rw("mode", "sentence-edits", "--scope", "manuscript.md Abstract", "--request",
                "please give me replacement sentences for the abstract", check=0)
        self.rw("log", "--stage", "polish", "--summary", "4 sentence edits in the abstract", check=0)
        self.rw("mode", "advisor", check=0)
        self.rw("advance", "--to", "review-loop", check=0)

        self.rw("review-packet", "--out-root", out, "--no-calibration", check=0)
        with open(os.path.join(self.project, "reviews", "round-1", "packet.json"), encoding="utf-8") as f:
            packet = json.load(f)
        for r in packet["reviewers"]:
            with open(r["output"], "w", encoding="utf-8") as f:
                f.write("| Level | ID | Location | Problem | Missing | Direction | Rerun? | Effort |\n"
                        "|---|---|---|---|---|---|---|---|\n"
                        "| P1 | %s-1 | Results | CI method not stated | method | state the CI method | no | 1h |\n" % r["id"])
        res = self.rw("aggregate", check=0)
        self.assertIn("P0 0 · P1 3 · P2 0 · P3 0 · flags 0", res.stdout)

        status = self.rw("status", check=0).stdout
        self.assertIn("profile: clinical-prespecified", status)
        self.assertIn("review round 1 · P0 0 · P1 3", status)
        self.rw("check", check=0)
        s = self.state()
        self.assertEqual([e["to"] for e in s["gate_log"]],
                         ["research", "design", "skeleton", "user-draft", "citation-check", "polish", "review-loop"])
        self.assertEqual([m["mode"] for m in s["mode_history"]], ["sentence-edits", "advisor"])
        with open(os.path.join(self.project, "ai-assistance-log.md"), encoding="utf-8") as f:
            log = f.read()
        self.assertIn("4 sentence edits in the abstract", log)


if __name__ == "__main__":
    unittest.main()
