"""Packaging: bundle and exports are reproducible, in sync and spec-compliant."""
import filecmp
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))  # allow `python3 -m unittest tests/<file>`
from helpers import ROOT

BUILD = os.path.join(ROOT, "tools", "build.py")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SPEC_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
CC_FIELDS = {"name", "description", "when_to_use", "argument-hint", "arguments", "disable-model-invocation",
             "user-invocable", "allowed-tools", "disallowed-tools", "model", "effort", "context", "agent",
             "background", "hooks", "paths", "shell", "metadata", "license", "compatibility"}
SOURCE_NAMES = ["写作工坊", "论文骨架", "科研写作", "反防御写作", "实验设计", "论文润色", "引用审查", "模拟审稿"]


def build_into(out):
    subprocess.run([sys.executable, BUILD, "--out", out], check=True, capture_output=True)


def parse_frontmatter(path):
    """Parse the frontmatter build.py emits: `key: <json scalar>` and one-level `key:` maps."""
    import json
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert text.startswith("---\n"), path
    block = text[4:text.index("\n---\n", 4)]
    fields, current = {}, None
    for line in block.split("\n"):
        if line.startswith("  "):
            key, _, value = line.strip().partition(": ")
            fields[current][key] = json.loads(value)
        elif line.endswith(":"):
            current = line[:-1]
            fields[current] = {}
        else:
            key, _, value = line.partition(": ")
            fields[key] = json.loads(value)
    return fields, text[text.index("\n---\n", 4) + 5:]


class Build(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="rw-build-test-")
        cls.a = os.path.join(cls.tmp, "a")
        cls.b = os.path.join(cls.tmp, "b")
        build_into(cls.a)
        build_into(cls.b)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def assertSameTree(self, x, y):
        cmp = filecmp.dircmp(x, y)
        stack = [cmp]
        while stack:
            c = stack.pop()
            self.assertEqual(c.left_only + c.right_only, [], "files differ in %s" % c.left)
            _m, mismatch, errors = filecmp.cmpfiles(c.left, c.right, c.common_files, shallow=False)
            self.assertEqual(mismatch + errors, [], "content differs in %s" % c.left)
            stack.extend(c.subdirs.values())

    def test_build_is_deterministic(self):
        self.assertSameTree(self.a, self.b)

    def test_committed_dist_matches_sources(self):
        res = subprocess.run([sys.executable, BUILD, "--check"], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stdout)

    def test_bundle_contains_every_source_file(self):
        with open(os.path.join(self.a, "research-workbench-full-bundle.md"), encoding="utf-8") as f:
            bundle = f.read()
        with open(os.path.join(ROOT, "BOOTSTRAP.md"), encoding="utf-8") as f:
            self.assertTrue(bundle.startswith(f.read()))
        for d in SOURCE_NAMES:
            if d != "写作工坊":
                with open(os.path.join(ROOT, "skills", d, "SKILL.md"), encoding="utf-8") as f:
                    self.assertIn(f.read(), bundle, d)
            ref_dir = os.path.join(ROOT, "skills", d, "references")
            for ref in (os.listdir(ref_dir) if os.path.isdir(ref_dir) else []):
                with open(os.path.join(ref_dir, ref), encoding="utf-8") as f:
                    self.assertIn(f.read(), bundle, ref)

    def check_export(self, flavor, allowed):
        root = os.path.join(self.a, flavor)
        names = sorted(os.listdir(root))
        self.assertEqual(len(names), 8)
        with open(os.path.join(ROOT, "tools", "rw.py"), "rb") as f:
            tool = f.read()
        for name in names:
            self.assertRegex(name, NAME_RE)
            self.assertLessEqual(len(name), 64)
            self.assertNotIn("--", name)
            fields, body = parse_frontmatter(os.path.join(root, name, "SKILL.md"))
            self.assertEqual(fields["name"], name, "name must equal the directory name")
            self.assertTrue(set(fields) <= allowed, set(fields) - allowed)
            self.assertTrue(0 < len(fields["description"]) <= 1024)
            for key, value in fields.get("metadata", {}).items():
                self.assertIsInstance(value, str, "metadata values must be strings (%s)" % key)
            with open(os.path.join(root, name, "scripts", "rw.py"), "rb") as f:
                self.assertEqual(f.read(), tool, "every export ships the current checker")
            texts = [body]
            ref_dir = os.path.join(root, name, "references")
            for ref in (os.listdir(ref_dir) if os.path.isdir(ref_dir) else []):
                with open(os.path.join(ref_dir, ref), encoding="utf-8") as f:
                    texts.append(f.read())
            for text in texts:
                self.assertNotIn("tools/rw.py", text, "%s: repo-relative tool path left in export" % name)
                for src in SOURCE_NAMES:
                    self.assertNotIn("「%s」" % src, text, "%s: unmapped cross-reference to %s" % (name, src))
                    self.assertNotIn("skills/%s/" % src, text, "%s: repo path to %s" % (name, src))
        return root

    def test_agent_skills_export_is_spec_compliant(self):
        root = self.check_export("agent-skills", SPEC_FIELDS)
        for name in os.listdir(root):
            fields, _ = parse_frontmatter(os.path.join(root, name, "SKILL.md"))
            self.assertLessEqual(len(fields.get("compatibility", "")), 500)
            self.assertNotIn("allowed-tools", fields)

    def test_claude_code_export_uses_documented_fields_only(self):
        root = self.check_export("claude-code", CC_FIELDS)
        workshop, body = parse_frontmatter(os.path.join(root, "rw-workshop", "SKILL.md"))
        self.assertTrue(workshop["user-invocable"])
        self.assertIn("${CLAUDE_SKILL_DIR}/scripts/rw.py", body)
        self.assertEqual(workshop["allowed-tools"], "Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py *)")
        others = [n for n in os.listdir(root) if n != "rw-workshop"]
        for name in others:
            fields, _ = parse_frontmatter(os.path.join(root, name, "SKILL.md"))
            self.assertFalse(fields["user-invocable"], "%s should be invoked by Claude, not from the menu" % name)

    @unittest.skipUnless(__import__("importlib").util.find_spec("yaml"), "PyYAML not installed (optional check)")
    def test_frontmatter_parses_with_a_real_yaml_parser(self):
        import yaml
        for flavor in ("claude-code", "agent-skills"):
            root = os.path.join(self.a, flavor)
            for name in os.listdir(root):
                with open(os.path.join(root, name, "SKILL.md"), encoding="utf-8") as f:
                    text = f.read()
                data = yaml.safe_load(text[4:text.index("\n---\n", 4)])
                mine, _ = parse_frontmatter(os.path.join(root, name, "SKILL.md"))
                self.assertEqual(data, mine, "%s/%s: YAML parser disagrees with the emitter" % (flavor, name))
                if flavor == "claude-code":
                    self.assertIsInstance(data["user-invocable"], bool)

    def test_exported_cross_references_resolve(self):
        root = os.path.join(self.a, "claude-code")
        for name in os.listdir(root):
            with open(os.path.join(root, name, "SKILL.md"), encoding="utf-8") as f:
                body = f.read()
            for target in re.findall(r"\$\{CLAUDE_SKILL_DIR\}/\.\./([a-z0-9-]+/[\w./-]+\.md)", body):
                self.assertTrue(os.path.isfile(os.path.join(root, target)), "%s → %s" % (name, target))


if __name__ == "__main__":
    unittest.main()
