"""Shared fixtures for the Research Workbench test suite (stdlib only)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RW = os.path.join(ROOT, "tools", "rw.py")

GOOD_G1 = """## 已确认的研究空白（G1）
1. No evaluation of personalised hybrid retrieval under a 4 GB memory budget
   — Source: Smith et al. 2025, https://doi.org/10.1145/1234567 — accessed 2026-10-16
2. Benchmarks ignore on-device latency — Source: arXiv 10.48550/arXiv.2501.00001 — accessed 2026-10-15
"""
GOOD_G2 = """## 确切的下一步（G2）
- Action: run the BM25+dense baseline on dataset B under the 4 GB device profile
- Resources: dataset B, one RTX 4090 for embeddings, a test phone
- Time estimate: 2 days
"""
GOOD_G3 = """## 与现有研究方向对比（G3）

| 维度 | 现有研究方向 | 本稿拟定位 | 关系 |
|------|------------|-----------|------|
| 问题 | server-side retrieval | on-device retrieval | 继承 |
| 方法 | BM25 + dense | hybrid + personalisation | 继承 |
| 数据与评测口径 | MS MARCO | MS MARCO + on-device latency | 偏离 |
| 目标读者/社区 | IR | IR + mobile systems | 重叠 |

- Decision: continuation (延续)
"""


def notes(g1=GOOD_G1, g2=GOOD_G2, g3=GOOD_G3, banner=""):
    return "%s# 深度研究笔记\n\n- 写作方向：hybrid retrieval\n- deep_research_mode：native\n\n%s\n## 竞争格局\n- x\n\n%s\n%s" % (
        banner, g1, g3, g2)


class ProjectCase(unittest.TestCase):
    """Each test gets a fresh project directory in the system temp dir."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rw-test-")
        self.project = os.path.join(self.tmp, "project")
        os.makedirs(self.project)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def rw(self, *args, stdin=None, check=None):
        proc = subprocess.run([sys.executable, RW] + list(args), cwd=self.project,
                              input=stdin, capture_output=True, text=True)
        if check is not None:
            self.assertEqual(proc.returncode, check, proc.stdout + proc.stderr)
        return proc

    def write(self, name, text):
        path = os.path.join(self.project, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def read_bytes(self, name):
        with open(os.path.join(self.project, name), "rb") as f:
            return f.read()

    def state(self):
        with open(os.path.join(self.project, ".writing-progress.json"), encoding="utf-8") as f:
            return json.load(f)

    def save_state(self, state):
        with open(os.path.join(self.project, ".writing-progress.json"), "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def init_complete(self, profile="cs-engineering", *extra):
        self.rw("init", "--topic", "hybrid retrieval on edge devices", "--confirm-direction",
                "--existing-direction", "lab works on server-side IR (continuation)",
                "--materials", "two datasets, partial results", "--journal-status", "unknown",
                "--domain-profile", profile, *extra, check=0)

    def set_research_mode(self, mode):
        s = self.state()
        s["stages"]["research"]["deep_research_mode"] = mode
        self.save_state(s)
