#!/usr/bin/env python3
"""Build the distributable forms of Research Workbench from the sources.

Outputs (all deterministic, no timestamps):
  dist/research-workbench-full-bundle.md   single file for paste-only chat LLMs
  dist/claude-code/rw-*/                   Claude Code skills (ASCII names, Claude Code fields kept)
  dist/agent-skills/rw-*/                  Agent Skills spec export (spec-only frontmatter)

Usage:
  python3 tools/build.py            # rebuild dist/
  python3 tools/build.py --check    # build into a temp dir and fail if dist/ is stale
  python3 tools/build.py --out DIR  # build somewhere else

Python 3.9+, standard library only.
"""
import argparse
import filecmp
import json
import os
import shutil
import sys
import tempfile

VERSION = "2.2.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (source directory under skills/, exported ASCII name, included in the bundle)
# Order matters: it is the bundle order. The orchestrator SKILL.md is not bundled
# because BOOTSTRAP.md is its paste-friendly equivalent; its references are.
SKILLS = [
    ("写作工坊", "rw-workshop", False),
    ("论文骨架", "rw-skeleton", True),
    ("科研写作", "rw-writing-principles", True),
    ("反防御写作", "rw-claim-forward", True),
    ("实验设计", "rw-experiment-design", True),
    ("引用审查", "rw-citation-audit", True),
    ("论文润色", "rw-polish", True),
    ("模拟审稿", "rw-mock-review", True),
]

# Claude Code fields we keep in the claude-code export (all documented frontmatter fields).
CLAUDE_CODE_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools", "disallowed-tools",
    "model", "effort", "context", "agent", "background", "hooks", "paths", "shell",
    "metadata", "license", "compatibility",
}
# Agent Skills spec: the only fields uploads and the Skills API accept.
SPEC_FIELDS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")

TOOL_SOURCE_TOKEN = "tools/rw.py"
CC_TOOL_PATH = "${CLAUDE_SKILL_DIR}/scripts/rw.py"
SPEC_TOOL_PATH = "scripts/rw.py"
CC_ALLOWED_TOOLS = "Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/rw.py *)"
COMPATIBILITY = (
    "Plain-Markdown instructions usable by any agent. The optional checker scripts/rw.py "
    "needs Python 3.9+ (standard library only) and a shell."
)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def split_frontmatter(text):
    """Return (fields, body). Source frontmatter is flat `key: value` lines."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.index("\n---\n", 4)
    fields = {}
    for line in text[4:end].split("\n"):
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, text[end + len("\n---\n"):]


def yaml_str(value):
    # JSON string syntax is valid YAML double-quoted scalar syntax.
    return json.dumps(value, ensure_ascii=False)


def render_frontmatter(pairs):
    out = ["---"]
    for key, value in pairs:
        if isinstance(value, bool):
            out.append("%s: %s" % (key, "true" if value else "false"))
        elif isinstance(value, dict):
            out.append("%s:" % key)
            for k, v in value.items():
                out.append("  %s: %s" % (k, yaml_str(v)))
        else:
            out.append("%s: %s" % (key, yaml_str(value)))
    out.append("---")
    return "\n".join(out) + "\n"


def parse_bool(value):
    return str(value).strip().lower() in ("true", "yes", "on", "1")


def reference_files(source_dir):
    ref_dir = os.path.join(ROOT, "skills", source_dir, "references")
    if not os.path.isdir(ref_dir):
        return []
    return sorted(f for f in os.listdir(ref_dir) if f.endswith(".md"))


def build_bundle():
    parts = [read(os.path.join(ROOT, "BOOTSTRAP.md"))]
    for source, _export, bundled in SKILLS:
        if bundled:
            parts.append(("[REFERENCE] %s" % source,
                          read(os.path.join(ROOT, "skills", source, "SKILL.md"))))
        for ref in reference_files(source):
            parts.append(("[REF] %s/%s" % (source, ref),
                          read(os.path.join(ROOT, "skills", source, "references", ref))))
    text = parts[0]
    for marker, content in parts[1:]:
        text += "\n\n---\n\n# %s\n\n%s" % (marker, content)
    return text


def rewrite_references(text, flavor, in_skill_md):
    """Point cross-skill references at exported names and the bundled checker.

    Claude Code substitutes ${CLAUDE_SKILL_DIR} only in SKILL.md bodies, so reference
    files get plain sibling-relative names instead.
    """
    if in_skill_md and flavor == "claude-code":
        tool_path, sibling = CC_TOOL_PATH, "${CLAUDE_SKILL_DIR}/../%s/"
    elif in_skill_md:
        tool_path, sibling = SPEC_TOOL_PATH, "../%s/"
    else:
        tool_path, sibling = SPEC_TOOL_PATH, "%s/"
    for source, export, _ in SKILLS:
        text = text.replace("skills/%s/" % source, sibling % export)
        text = text.replace("`skills/%s`" % source, "`%s`" % export)
        text = text.replace("「%s」" % source, "「%s」" % export)
    return text.replace(TOOL_SOURCE_TOKEN, tool_path)


def export_skill(out_root, flavor, source, export):
    fields, body = split_frontmatter(read(os.path.join(ROOT, "skills", source, "SKILL.md")))
    description = fields.get("description", "")
    description_zh = fields.get("description_zh", "")
    metadata = {"version": fields.get("version", VERSION), "source-skill": source}
    if description_zh:
        metadata["description-zh"] = description_zh

    if flavor == "claude-code":
        pairs = [("name", export), ("description", description)]
        if "argument-hint" in fields:
            pairs.append(("argument-hint", fields["argument-hint"]))
        if "user-invocable" in fields:
            pairs.append(("user-invocable", parse_bool(fields["user-invocable"])))
        pairs.append(("allowed-tools", CC_ALLOWED_TOOLS))
        pairs.append(("license", "MIT"))
        pairs.append(("metadata", metadata))
        assert all(k in CLAUDE_CODE_FIELDS for k, _ in pairs)
    else:
        if "user-invocable" in fields:
            metadata["user-invocable"] = str(parse_bool(fields["user-invocable"])).lower()
        if "argument-hint" in fields:
            metadata["argument-hint"] = fields["argument-hint"]
        pairs = [("name", export), ("description", description), ("license", "MIT"),
                 ("compatibility", COMPATIBILITY), ("metadata", metadata)]
        assert all(k in SPEC_FIELDS for k, _ in pairs)

    skill_dir = os.path.join(out_root, flavor, export)
    write(os.path.join(skill_dir, "SKILL.md"),
          render_frontmatter(pairs) + rewrite_references(body, flavor, True))
    for ref in reference_files(source):
        content = read(os.path.join(ROOT, "skills", source, "references", ref))
        write(os.path.join(skill_dir, "references", ref), rewrite_references(content, flavor, False))
    tool_src = os.path.join(ROOT, "tools", "rw.py")
    if os.path.exists(tool_src):
        os.makedirs(os.path.join(skill_dir, "scripts"), exist_ok=True)
        shutil.copyfile(tool_src, os.path.join(skill_dir, "scripts", "rw.py"))
    write(os.path.join(skill_dir, "LICENSE"), read(os.path.join(ROOT, "LICENSE")))


def build(out_root):
    write(os.path.join(out_root, "research-workbench-full-bundle.md"), build_bundle())
    for flavor in ("claude-code", "agent-skills"):
        flavor_dir = os.path.join(out_root, flavor)
        if os.path.isdir(flavor_dir):
            shutil.rmtree(flavor_dir)
        for source, export, _ in SKILLS:
            export_skill(out_root, flavor, source, export)


def tree_diff(a, b):
    """Return relative paths that differ between two directory trees."""
    diffs = []
    cmp = filecmp.dircmp(a, b)
    stack = [("", cmp)]
    while stack:
        prefix, c = stack.pop()
        for name in c.left_only + c.right_only:
            diffs.append(os.path.join(prefix, name))
        _match, mismatch, errors = filecmp.cmpfiles(
            os.path.join(a, prefix), os.path.join(b, prefix), c.common_files, shallow=False)
        diffs.extend(os.path.join(prefix, n) for n in mismatch + errors)
        for name, sub in sorted(c.subdirs.items()):
            stack.append((os.path.join(prefix, name), sub))
    return sorted(diffs)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out", default=os.path.join(ROOT, "dist"))
    parser.add_argument("--check", action="store_true",
                        help="build into a temp dir and report whether --out is up to date")
    args = parser.parse_args(argv)
    if not args.check:
        build(args.out)
        print("built %s" % os.path.relpath(args.out, ROOT))
        return 0
    tmp = tempfile.mkdtemp(prefix="rw-build-")
    try:
        build(tmp)
        stale = tree_diff(tmp, args.out) if os.path.isdir(args.out) else ["<missing dist>"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if stale:
        print("dist is stale; run `python3 tools/build.py`. Differences:")
        for path in stale:
            print("  " + path)
        return 1
    print("dist is up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
