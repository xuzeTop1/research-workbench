"""Reviewer isolation: review-packet sandboxes, .docx checks, aggregate counting and flags."""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import zipfile

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # allow `python3 -m unittest tests/<file>`
from helpers import ProjectCase

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(path, revisions=False, comments=False, creator="Dr. Example Author"):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
        body = "<w:p><w:r><w:t>Results</w:t></w:r></w:p>"
        if revisions:
            body += '<w:ins w:id="1" w:author="A"><w:r><w:t>added after R2</w:t></w:r></w:ins>'
        z.writestr("word/document.xml", '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>' % (W, body))
        if comments:
            z.writestr("word/comments.xml", '<w:comments xmlns:w="%s"><w:comment w:id="0" w:author="R2"/></w:comments>' % W)
        z.writestr("docProps/core.xml",
                   '<cp:coreProperties xmlns:cp="c" xmlns:dc="http://purl.org/dc/elements/1.1/">'
                   "<dc:creator>%s</dc:creator><cp:lastModifiedBy>%s</cp:lastModifiedBy></cp:coreProperties>"
                   % (creator, creator))


def files_under(root):
    return sorted(os.path.relpath(os.path.join(dp, f), root) for dp, _d, fs in os.walk(root) for f in fs)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class PacketCase(ProjectCase):
    def setUp(self):
        super().setUp()
        self.out = os.path.join(self.tmp, "sandboxes")  # outside the project, inside the test temp dir
        subprocess.run(["git", "init", "-q", self.project], check=True)
        self.init_complete()
        self.write("paper.md", "# A paper\n\nWe show X.\n")
        self.write("fig1_revised_after_R2.png", "PNG")
        self.write("review-calibration.md", "# Journal profile\n- scope: IR\n")
        self.write("reviews/round-1/reviewer-R2.md", "R2-1 P0: table 4 contradicts claim\n")
        self.write("polish-suggestions.md", "| 1 | §3 | ... |\n")
        s = self.state()
        s.update(manuscript_file="paper.md", target_journal="J. Example", target_journal_status="confirmed")
        self.save_state(s)

    def packet(self, *extra, round_no="2", check=0):
        self.rw("review-packet", "--round", round_no, "--out-root", self.out, *extra, check=check)
        path = os.path.join(self.project, "reviews", "round-%s" % round_no, "packet.json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return None


class ReviewPacket(PacketCase):
    def test_sandboxes_hold_only_whitelisted_inputs(self):
        p = self.packet("--material", "fig1_revised_after_R2.png")
        self.assertEqual([r["id"] for r in p["reviewers"]], ["R1", "R2", "R3"])
        sandboxes = [r["sandbox"] for r in p["reviewers"]]
        self.assertEqual(len(set(sandboxes)), 3)
        for r in p["reviewers"]:
            sb = r["sandbox"]
            self.assertFalse(os.path.realpath(sb).startswith(os.path.realpath(self.project)))
            self.assertTrue(os.path.basename(sb).startswith("rw-sbx-"), "name must not reveal role/round")
            self.assertEqual(files_under(sb), sorted([
                "PASTE_PROMPT.md", "REVIEWER_BRIEF.md", "input/journal-profile.md",
                "input/manuscript.md", "input/materials/material-1.png"]))
            self.assertEqual(sha(os.path.join(sb, "input", "manuscript.md")), p["inputs"]["manuscript"]["sha256"])
            with open(os.path.join(sb, "REVIEWER_BRIEF.md"), encoding="utf-8") as f:
                brief = f.read()
            self.assertIn(sb, brief)
            self.assertIn("Do not open, list or search any path outside this folder", brief)
            with open(os.path.join(sb, "PASTE_PROMPT.md"), encoding="utf-8") as f:
                self.assertIn("We show X.", f.read())
        loop = self.state()["stages"]["review-loop"]
        self.assertEqual(loop["isolation"], "snapshot")
        self.assertEqual(loop["packets"][-1]["round"], 2)

    def test_r2_brief_carries_profile_checklist(self):
        s = self.state()
        s["domain_profile"] = "clinical-prespecified"
        s["protocol"]["primary_endpoint"] = "sensitivity"
        self.save_state(s)
        p = self.packet()
        r2 = [r for r in p["reviewers"] if r["id"] == "R2"][0]
        with open(os.path.join(r2["sandbox"], "REVIEWER_BRIEF.md"), encoding="utf-8") as f:
            self.assertIn("switched or unreported primary outcome", f.read())

    def test_out_root_inside_project_is_refused(self):
        out = self.rw("review-packet", "--round", "2", "--out-root", os.path.join(self.project, "rev")).stdout
        self.assertIn("inside the project", out)
        self.assertFalse(os.path.exists(os.path.join(self.project, "reviews", "round-2", "packet.json")))

    def test_missing_calibration_needs_explicit_flag(self):
        os.remove(os.path.join(self.project, "review-calibration.md"))
        self.assertEqual(self.rw("review-packet", "--round", "2", "--out-root", self.out).returncode, 2)
        p = self.packet("--no-calibration")
        with open(os.path.join(p["reviewers"][0]["sandbox"], "input", "journal-profile.md"), encoding="utf-8") as f:
            self.assertIn("No calibration", f.read())
        self.assertEqual(self.state()["stages"]["review-loop"]["calibration_status"], "degraded-no-search")

    def test_existing_round_is_not_silently_overwritten(self):
        first = self.packet()
        out = self.rw("review-packet", "--round", "2", "--out-root", self.out, check=1).stdout
        self.assertIn("already has a packet", out)
        second = self.packet("--force")
        self.assertNotEqual(first["reviewers"][0]["sandbox"], second["reviewers"][0]["sandbox"])

    def test_corrupt_docx_is_a_clear_error(self):
        self.write("paper.docx", "not a zip")
        s = self.state()
        s["manuscript_file"] = "paper.docx"
        self.save_state(s)
        res = self.rw("review-packet", "--round", "2", "--out-root", self.out)
        self.assertEqual(res.returncode, 2)
        self.assertIn("not a valid .docx", res.stderr)
        self.assertNotIn("Traceback", res.stderr)

    def test_default_sandboxes_live_in_system_temp(self):
        self.rw("review-packet", "--round", "3", check=0)
        with open(os.path.join(self.project, "reviews", "round-3", "packet.json"), encoding="utf-8") as f:
            p = json.load(f)
        try:
            for r in p["reviewers"]:
                self.assertTrue(os.path.realpath(r["sandbox"]).startswith(os.path.realpath(tempfile.gettempdir())))
        finally:
            for r in p["reviewers"]:
                shutil.rmtree(r["sandbox"], ignore_errors=True)


class Docx(PacketCase):
    def use_docx(self, **kw):
        path = os.path.join(self.project, "paper.docx")
        make_docx(path, **kw)
        s = self.state()
        s["manuscript_file"] = "paper.docx"
        self.save_state(s)
        return path

    def test_revisions_and_comments_are_refused_unless_waived(self):
        src = self.use_docx(revisions=True, comments=True)
        out = self.rw("review-packet", "--round", "2", "--out-root", self.out, check=1).stdout
        self.assertIn("revisions and comments", out)
        out = self.rw("review-packet", "--round", "2", "--out-root", self.out, "--allow-docx-revisions", check=1).stdout
        self.assertIn("author metadata", out)
        p = self.packet("--allow-docx-revisions", "--strip-docx-metadata")
        self.assertIn("docx-revisions+comments", p["waivers"])
        snap = os.path.join(p["reviewers"][0]["sandbox"], "input", "manuscript.docx")
        with zipfile.ZipFile(snap) as z, zipfile.ZipFile(src) as orig:
            core = z.read("docProps/core.xml").decode()
            self.assertIn("<dc:creator></dc:creator>", core)
            self.assertNotIn("Dr. Example Author", core)
            self.assertEqual(z.read("word/document.xml"), orig.read("word/document.xml"))
            self.assertEqual(z.testzip(), None)

    def test_clean_docx_passes_without_flags(self):
        self.use_docx(creator="")
        p = self.packet()
        self.assertEqual(p["waivers"], [])


class Aggregate(PacketCase):
    def write_review(self, packet, rid, text):
        r = [x for x in packet["reviewers"] if x["id"] == rid][0]
        with open(r["output"], "w", encoding="utf-8") as f:
            f.write(text.replace("{SANDBOX}", r["sandbox"]))
        return r

    HEADER = ("| Level | ID | Location | Problem | Missing evidence or explanation | Direction (no rewritten text) "
              "| Rerun experiments? | Effort |\n|---|---|---|---|---|---|---|---|\n")

    def make_round(self):
        p = self.packet()
        self.write_review(p, "R1", self.HEADER
                          + "| P0 | R1-1 | ... | ... | ... | ... | ... | ... |\n"
                          + "| P1 | R1-1 | §3.1 | No rationale for X over Y | design rationale | add motivation | no | half a day |\n"
                          + "| **P2** | R1-2 | §2 | terminology drifts | - | unify terms | no | minutes |\n\n"
                          + "We do not give an ACCEPT/REJECT verdict.\n\n## Files consulted\n- {SANDBOX}/input/manuscript.md\n")
        self.write_review(p, "R2", self.HEADER
                          + "| P0 | R2-1 | Table 4 | claim contradicts the table | consistent claim | narrow the claim | maybe | 1 day |\n\n"
                          + "Overall I would put the chance of acceptance at 70%.\nRecommendation: major revision.\n")
        r3 = self.write_review(p, "R3", "- [P3] R3-1 style nit in the abstract\n"
                               "I also checked /Users/someone/project/.writing-progress.json for context.\n")
        with open(os.path.join(r3["sandbox"], "input", "manuscript.md"), "a", encoding="utf-8") as f:
            f.write("edited by reviewer\n")
        with open(os.path.join(r3["sandbox"], "notes.txt"), "w", encoding="utf-8") as f:
            f.write("scratch")
        return p

    def test_counts_flags_archive_and_cleanup(self):
        p = self.make_round()
        res = self.rw("aggregate", "--round", "2", check=0)
        self.assertIn("P0 1 · P1 1 · P2 1 · P3 1", res.stdout)
        report = self.read_bytes(os.path.join("reviews", "round-2.md")).decode("utf-8")
        flags = report.split("## Integrity flags")[1]
        self.assertIn("R2 line", flags)
        self.assertIn("acceptance probability", flags)
        self.assertIn("decision-tier wording", flags)
        self.assertIn("outside its sandbox", flags)
        self.assertIn("workflow-internal file '.writing-progress.json'", flags)
        self.assertIn("R3 modified its manuscript snapshot", flags)
        self.assertIn("R3 wrote outside output/: notes.txt", flags)
        self.assertNotIn("R1 line", flags, "negated verdicts and in-sandbox paths are not flagged")
        for rid in ("R1", "R2", "R3"):
            self.assertTrue(os.path.exists(os.path.join(self.project, "reviews", "round-2", "reviewer-%s.md" % rid)))
        loop = self.state()["stages"]["review-loop"]
        self.assertEqual(loop["blockers"], {"P0": 1, "P1": 1, "P2": 1, "P3": 1})
        self.assertEqual(loop["round"], 2)
        for r in p["reviewers"]:
            self.assertFalse(os.path.exists(r["sandbox"]), "sandboxes are removed after archiving")

    def test_strict_mode_fails_on_flags(self):
        self.make_round()
        self.rw("aggregate", "--round", "2", "--keep-sandboxes", check=0)
        self.assertEqual(self.rw("aggregate", "--round", "2", "--force", "--strict").returncode, 1)

    def test_aggregate_defaults_to_the_latest_packet(self):
        p = self.packet(round_no="3")
        for r in p["reviewers"]:
            self.write_review(p, r["id"], self.HEADER + "| P2 | %s-1 | §1 | x | y | z | no | 1h |\n" % r["id"])
        out = self.rw("aggregate", check=0).stdout
        self.assertIn("reviews/round-3.md", out)
        self.assertEqual(self.state()["stages"]["review-loop"]["round"], 3)

    def test_missing_output_is_flagged(self):
        p = self.packet()
        self.write_review(p, "R2", self.HEADER + "| P1 | R2-1 | §4 | x | y | z | no | 1h |\n")
        out = self.rw("aggregate", "--round", "2", check=0).stdout
        self.assertIn("R1: no output/review.md", out)

    def test_cleanup_never_touches_foreign_directories(self):
        p = self.packet()
        foreign = os.path.join(self.tmp, "important-data")
        os.makedirs(foreign)
        with open(os.path.join(foreign, "REVIEWER_BRIEF.md"), "w") as f:
            f.write("not a sandbox name")
        p["reviewers"][0]["sandbox"] = foreign
        p["reviewers"][1]["sandbox"] = self.project
        path = os.path.join(self.project, "reviews", "round-2", "packet.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(p, f)
        self.rw("aggregate", "--round", "2", check=0)
        self.assertTrue(os.path.isdir(foreign))
        self.assertTrue(os.path.isdir(self.project))


if __name__ == "__main__":
    unittest.main()
