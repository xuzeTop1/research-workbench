#!/usr/bin/env python3
"""rw.py — Research Workbench checker and helper (Python 3.9+, standard library only).

Turns the workbench's written rules into checks a tool can run:

  init           create a valid .writing-progress.json
  migrate        add fields introduced in v2.2 to an older progress file
  check          validate the progress file, stage prerequisites and gates G1–G3
  advance        move to a stage only if its prerequisites pass (records a gate log)
  status         one-screen summary
  mode           switch assistance mode (advisor | sentence-edits), logged
  log            append an entry to the AI-assistance log
  review-packet  build blinded reviewer sandboxes OUTSIDE the project
  aggregate      merge reviewer outputs, count P0–P3, flag integrity problems
  hook-guard     Claude Code PreToolUse hook: block writes the workflow forbids
  schema         print the progress-file schema (JSON)

Exit codes: 0 = ok, 1 = check failed / refused, 2 = usage or I/O error.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile

VERSION = "2.2.0"
CHECKER = "rw.py " + VERSION
PROGRESS_FILE = ".writing-progress.json"

STAGES = ["intake", "research", "design", "skeleton", "user-draft",
          "citation-check", "polish", "review-loop"]
STATUS_VALUES = ["", "pending", "in-progress", "done", "blocked", "skipped"]
PROFILES = ["cs-engineering", "clinical-prespecified", "systematic-review",
            "observational", "custom"]
RESEARCH_MODES = ["unprobed", "native", "external-handoff",
                  "degraded-by-user-request", "absent"]
PROCEED_MODES = ("native", "external-handoff", "degraded-by-user-request")
ASSISTANCE_MODES = ["advisor", "sentence-edits"]
ISOLATION_VALUES = ["", "snapshot", "subagent-prompt-only", "fresh-sessions", "worktree", "none"]
CALIBRATION_VALUES = ["", "searched", "degraded-no-search", "degraded-paywall"]

DEFAULT_OUTPUTS = {
    "research": "research-notes.md",
    "design": "experiment-plan.md",
    "skeleton": "outline.md",
    "citation-check": "citation-report.md",
    "polish": "polish-suggestions.md",
}


def _status():
    return {"type": "string", "enum": STATUS_VALUES}


SCHEMA = {
    "type": "object",
    "required": ["topic", "writing_direction_confirmed", "existing_direction",
                 "target_journal_status", "current_stage", "stages"],
    "properties": {
        "schema_version": {"type": "string"},
        "topic": {"type": "string"},
        "writing_direction_confirmed": {"type": "boolean"},
        "existing_direction": {"type": "string"},
        "materials": {"type": "string"},
        "manuscript_file": {"type": "string"},
        "target_journal": {"type": "string"},
        "target_journal_status": {"type": "string", "enum": ["unknown", "candidate", "confirmed"]},
        "journal_profile": {"type": "object"},
        "domain_profile": {"type": "string", "enum": [""] + PROFILES},
        "domain_profile_notes": {"type": "string"},
        "protocol": {
            "type": "object",
            "properties": {
                "registered": {"type": "boolean"},
                "registry_id": {"type": "string"},
                "protocol_file": {"type": "string"},
                "sap_file": {"type": "string"},
                "primary_endpoint": {"type": "string"},
            },
        },
        "assistance_mode": {"type": "string", "enum": ASSISTANCE_MODES},
        "assistance_log": {"type": "string"},
        "mode_history": {"type": "array", "items": {
            "type": "object", "required": ["mode", "at"],
            "properties": {"mode": {"type": "string", "enum": ASSISTANCE_MODES},
                           "at": {"type": "string"}, "scope": {"type": "string"},
                           "user_request": {"type": "string"}}}},
        "current_stage": {"type": "string", "enum": STAGES},
        "stages": {
            "type": "object",
            "properties": {
                "intake": {"type": "object", "properties": {"status": _status()}},
                "research": {"type": "object", "properties": {
                    "status": _status(), "output_file": {"type": "string"},
                    "deep_research_mode": {"type": "string", "enum": RESEARCH_MODES},
                    "handoff_file": {"type": "string"}, "source": {"type": "string"},
                    "gate": {"type": "object"}}},
                "design": {"type": "object", "properties": {
                    "status": _status(), "output_file": {"type": "string"},
                    "blocked_by_gate": {"type": "boolean"}}},
                "skeleton": {"type": "object", "properties": {
                    "status": _status(), "output_file": {"type": "string"},
                    "anti_defensive_checked": {"type": "boolean"}}},
                "user-draft": {"type": "object", "properties": {"status": _status()}},
                "citation-check": {"type": "object", "properties": {
                    "status": _status(), "output_file": {"type": "string"}}},
                "polish": {"type": "object", "properties": {
                    "status": _status(), "output_file": {"type": "string"},
                    "bidirectional_scan": {"type": "boolean"}}},
                "review-loop": {"type": "object", "properties": {
                    "status": _status(),
                    "round": {"type": "integer", "minimum": 0},
                    "max_rounds": {"type": "integer", "minimum": 1},
                    "calibration_file": {"type": "string"},
                    "calibration_status": {"type": "string", "enum": CALIBRATION_VALUES},
                    "isolation": {"type": "string", "enum": ISOLATION_VALUES},
                    "blockers": {"type": "object", "properties": {
                        level: {"type": "integer", "minimum": 0}
                        for level in ("P0", "P1", "P2", "P3")}},
                    "reviews": {"type": "array"},
                    "packets": {"type": "array"}}},
            },
        },
        "gate_log": {"type": "array", "items": {"type": "object"}},
    },
}


# ---------------------------------------------------------------- basics

class UsageError(Exception):
    pass


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_json_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def progress_path(project):
    return os.path.join(project, PROGRESS_FILE)


def load_progress(project):
    path = progress_path(project)
    if not os.path.exists(path):
        raise UsageError("no %s in %s — run `rw.py init` first" % (PROGRESS_FILE, project))
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except ValueError as e:
        raise UsageError("%s is not valid JSON: %s" % (path, e))
    if not isinstance(data, dict):
        raise UsageError("%s must contain a JSON object" % path)
    return data


def new_progress():
    return {
        "schema_version": "2.2",
        "topic": "",
        "writing_direction_confirmed": False,
        "existing_direction": "",
        "materials": "",
        "manuscript_file": "",
        "target_journal": "",
        "target_journal_status": "unknown",
        "journal_profile": {},
        "domain_profile": "",
        "domain_profile_notes": "",
        "protocol": {"registered": False, "registry_id": "", "protocol_file": "",
                     "sap_file": "", "primary_endpoint": ""},
        "assistance_mode": "advisor",
        "assistance_log": "ai-assistance-log.md",
        "mode_history": [],
        "current_stage": "intake",
        "stages": {
            "intake": {"status": "in-progress"},
            "research": {"status": "", "output_file": "research-notes.md",
                         "deep_research_mode": "unprobed",
                         "handoff_file": "deep-research-handoff.md", "source": "",
                         "gate": {"G1_confirmed_gap": "", "G2_concrete_next_step": "",
                                  "G3_direction_compared": ""}},
            "design": {"status": "", "output_file": "experiment-plan.md", "blocked_by_gate": False},
            "skeleton": {"status": "", "output_file": "outline.md", "anti_defensive_checked": False},
            "user-draft": {"status": "pending"},
            "citation-check": {"status": "", "output_file": "citation-report.md"},
            "polish": {"status": "", "output_file": "polish-suggestions.md",
                       "bidirectional_scan": True},
            "review-loop": {"status": "", "round": 0, "max_rounds": 5,
                            "calibration_file": "review-calibration.md",
                            "calibration_status": "", "isolation": "",
                            "blockers": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
                            "reviews": [], "packets": []},
        },
        "gate_log": [],
    }


# ---------------------------------------------------------------- schema

def _type_ok(value, expected):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate(value, schema, path="$"):
    """Validate the subset of JSON Schema used by SCHEMA. Returns a list of error strings."""
    errors = []
    expected = schema.get("type")
    if expected and not _type_ok(value, expected):
        return ["%s: expected %s, got %s" % (path, expected, type(value).__name__)]
    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(v) for v in schema["enum"])
        errors.append("%s: %r is not one of %s" % (path, value, allowed))
    if "minimum" in schema and isinstance(value, int) and value < schema["minimum"]:
        errors.append("%s: must be >= %s" % (path, schema["minimum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append("%s: missing required field %r" % (path, key))
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors.extend(validate(value[key], sub, "%s.%s" % (path, key)))
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors.extend(validate(item, schema["items"], "%s[%d]" % (path, i)))
    return errors


# ---------------------------------------------------------------- markdown parsing

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
TOP_ITEM_RE = re.compile(r"^ ?(?:\d+[.)]|[-*+])\s+(.*)$")
URL_RE = re.compile(r"https?://[^\s<>\]\)\"']+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s<>\]\)\"',;]+")
DATE = r"(?:19|20)\d{2}(?:-\d{1,2}-\d{1,2}|/\d{1,2}/\d{1,2}|\.\d{1,2}\.\d{1,2}|年\d{1,2}月\d{1,2}日)"
ACCESS_RE = re.compile(
    r"(?:accessed|access date|retrieved|retrieval date|检索日期|访问日期|检索于|访问于|获取日期|查阅日期)"
    r"[\s:：,，(（]*(?:on\s+)?" + DATE, re.I)
PLACEHOLDER_RE = re.compile(
    r"\[[^\]\n]{0,40}(?:描述|标题|出处|日期|动作|资源|耗时|填写|待填|placeholder|"
    r"description|title|source|date|action|resource|time estimate|TBD)[^\]\n]{0,40}\](?!\()",
    re.I)
VAGUE_ACTIONS = ("继续调研", "进一步调研", "继续研究", "进一步研究", "继续检索", "再看看",
                 "continue research", "more research", "further research", "keep researching",
                 "tbd", "to be decided", "待定")
DURATION_RE = re.compile(r"\d|半|一|两|三|几|day|week|hour|month|天|周|小时|月|日", re.I)


def md_sections(text):
    lines = text.split("\n")
    heads = []
    in_code = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if not in_code:
            m = HEADING_RE.match(line)
            if m:
                heads.append((i, len(m.group(1)), m.group(2)))
    result = []
    for k, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lv, _t in heads[k + 1:]:
            if lv <= level:
                end = j
                break
        result.append((title, "\n".join(lines[i + 1:end])))
    return result


def find_section(text, token):
    for title, body in md_sections(text):
        if token in title:
            return body
    return None


def list_items(body):
    items, cur = [], None
    for line in body.split("\n"):
        m = TOP_ITEM_RE.match(line)
        if m:
            if cur is not None:
                items.append(cur)
            cur = m.group(1).strip()
        elif cur is not None and (not line.strip() or line[:1] in (" ", "\t")):
            if line.strip():
                cur += " " + line.strip()
        elif cur is not None:
            items.append(cur)
            cur = None
    if cur is not None:
        items.append(cur)
    return items


def _split_row(row):
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", s)]


def md_tables(body):
    blocks, cur = [], []
    for line in body.split("\n"):
        if line.strip().startswith("|"):
            cur.append(line)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    tables = []
    for block in blocks:
        rows = [_split_row(r) for r in block]
        if len(rows) >= 2 and rows[1] and all(re.match(r"^:?-{2,}:?$", c) for c in rows[1] if c):
            tables.append((rows[0], rows[2:]))
    return tables


def labelled_value(body, labels):
    """Value of a `Label: value` line; tolerates bullets, **bold** and a parenthetical gloss."""
    pattern = re.compile(
        r"(?:^|\n)\s*(?:[-*+]\s*)?(?:\*\*)?(?:%s)(?:\s*[(（][^)）\n]{0,24}[)）])?"
        r"(?:\s*[:：]\s*\*\*|\s*\*\*\s*[:：]|\s*[:：])\s*(.*)" % "|".join(labels), re.I)
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def is_placeholder(text):
    stripped = (text or "").strip()
    return (not stripped or bool(PLACEHOLDER_RE.search(stripped)) or stripped in ("-", "…", "...")
            or bool(re.fullmatch(r"[（(][^)）]*[)）]", stripped)))  # a template hint in parentheses


# ---------------------------------------------------------------- gates

class Result(object):
    def __init__(self, label, ok, detail="", files=None):
        self.label = label
        self.ok = ok
        self.detail = detail
        self.files = files or []

    def as_dict(self):
        return {"check": self.label, "ok": self.ok, "detail": self.detail}


def gate_g1(notes):
    body = find_section(notes, "G1")
    if body is None:
        return Result("G1 confirmed gap", False, "no section heading containing 'G1' in research notes")
    items = list_items(body)
    if not items:
        items = [" | ".join(r) for _h, rows in md_tables(body) for r in rows]
    if not items:
        return Result("G1 confirmed gap", False, "the G1 section lists no gaps")
    problems = []
    for n, item in enumerate(items, 1):
        missing = []
        if not (URL_RE.search(item) or DOI_RE.search(item)):
            missing.append("a source URL or DOI")
        if not ACCESS_RE.search(item):
            missing.append("an access date (e.g. 'accessed 2026-10-16')")
        if is_placeholder(URL_RE.sub("", item)):
            missing.append("real content (template placeholder left in)")
        if missing:
            problems.append("gap %d lacks %s" % (n, " and ".join(missing)))
    if problems:
        return Result("G1 confirmed gap", False, "; ".join(problems))
    return Result("G1 confirmed gap", True, "%d sourced gap(s)" % len(items))


def gate_g2(notes):
    body = find_section(notes, "G2")
    if body is None:
        return Result("G2 concrete next step", False, "no section heading containing 'G2'")
    action = labelled_value(body, ["Action", "Next action", "动作", "行动", "下一步动作"])
    resources = labelled_value(body, ["Resources?", "Resources needed", "所需资源", "资源"])
    time_est = labelled_value(body, ["Time estimate", "Estimated time", "Time", "预计耗时", "耗时", "时间"])
    problems = []
    if is_placeholder(action):
        problems.append("missing 'Action:'")
    elif any(action.lower().strip(" .。").startswith(v) and len(action) < 24 for v in VAGUE_ACTIONS):
        problems.append("action is not concrete (%r) — name the baseline/dataset/paper/claim it acts on" % action)
    if is_placeholder(resources):
        problems.append("missing 'Resources:'")
    if is_placeholder(time_est):
        problems.append("missing 'Time estimate:'")
    elif not DURATION_RE.search(time_est):
        problems.append("time estimate has no duration (%r)" % time_est)
    if problems:
        return Result("G2 concrete next step", False, "; ".join(problems))
    return Result("G2 concrete next step", True, action[:80])


def gate_g3(notes):
    body = find_section(notes, "G3")
    if body is None:
        return Result("G3 direction compared", False, "no section heading containing 'G3'")
    tables = md_tables(body)
    if not tables:
        return Result("G3 direction compared", False, "no comparison table in the G3 section")
    _header, rows = max(tables, key=lambda t: len(t[1]))
    problems = []
    if len(rows) < 4:
        problems.append("comparison table has %d row(s); need problem, method, data/evaluation, audience" % len(rows))
    for row in rows:
        cells = (row + ["", "", "", ""])[:4]
        if any(is_placeholder(c) for c in cells):
            problems.append("row %r has empty cells" % (cells[0] or "?"))
    decision = labelled_value(body, ["Decision", "判定", "结论", "决定"]) or ""
    keeps = bool(re.search(r"延续|continu", decision, re.I))
    pivots = bool(re.search(r"转向|pivot", decision, re.I))
    if not (keeps or pivots):
        problems.append("missing 'Decision: continuation' or 'Decision: pivot' (延续/转向)")
    elif keeps and pivots:
        problems.append("decision names both continuation and pivot — keep exactly one")
    elif pivots:
        cost = labelled_value(body, ["Pivot cost", "Cost", "转向代价", "代价"])
        if is_placeholder(cost):
            problems.append("pivot chosen but 'Pivot cost:' (转向代价) is missing")
    if problems:
        return Result("G3 direction compared", False, "; ".join(problems))
    return Result("G3 direction compared", True, decision[:60])


def normalized(text):
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def contains_endpoint(text, endpoint):
    return bool(endpoint.strip()) and normalized(endpoint) in normalized(text)


# ---------------------------------------------------------------- prerequisites

def stage_file(state, stage, project):
    name = (state.get("stages", {}).get(stage, {}) or {}).get("output_file") or DEFAULT_OUTPUTS[stage]
    return os.path.join(project, name)


def check_intake(state):
    out = []
    out.append(Result("topic recorded", bool(state.get("topic", "").strip()),
                      "ask ① writing direction"))
    out.append(Result("writing direction confirmed", state.get("writing_direction_confirmed") is True,
                      "set writing_direction_confirmed after the user answers ①"))
    out.append(Result("existing research line recorded", bool(state.get("existing_direction", "").strip()),
                      "ask ② existing research line (continuation or pivot)"))
    out.append(Result("materials recorded", bool(state.get("materials", "").strip()),
                      "ask ③ current materials (draft / results / literature pool)"))
    status = state.get("target_journal_status", "")
    journal_ok = status == "unknown" or (status in ("candidate", "confirmed")
                                         and bool(state.get("target_journal", "").strip()))
    out.append(Result("target journal answered", journal_ok,
                      "ask ④ target journal ('undecided' is a valid answer → status unknown)"))
    profile = state.get("domain_profile", "")
    out.append(Result("domain profile chosen", profile in PROFILES,
                      "ask ⑤ study type → one of: " + ", ".join(PROFILES)))
    protocol = state.get("protocol") or {}
    if profile == "clinical-prespecified":
        out.append(Result("primary endpoint recorded from the protocol",
                          bool(protocol.get("primary_endpoint", "").strip()),
                          "clinical-prespecified needs protocol.primary_endpoint (copied from the protocol/SAP)"))
        if protocol.get("registered"):
            out.append(Result("registry ID recorded", bool(protocol.get("registry_id", "").strip()),
                              "protocol.registered is true but protocol.registry_id is empty"))
    if profile == "custom":
        out.append(Result("custom profile described", bool(state.get("domain_profile_notes", "").strip()),
                          "custom profile needs domain_profile_notes (guidelines and which rules to relax)"))
    return out


def check_research_ready(state, project):
    out = []
    research = state.get("stages", {}).get("research", {}) or {}
    mode = research.get("deep_research_mode", "unprobed")
    if mode in PROCEED_MODES:
        out.append(Result("deep research available", True, mode))
    else:
        out.append(Result("deep research available", False,
                          "deep_research_mode=%s — hard stop: hand off to a deep-research product, "
                          "or proceed only on the user's explicit request (degraded-by-user-request)" % mode))
    notes_path = stage_file(state, "research", project)
    if not os.path.exists(notes_path):
        out.append(Result("research notes exist", False, "%s not found" % os.path.basename(notes_path)))
        return out, None
    notes = read_text(notes_path)
    out.append(Result("research notes exist", True, os.path.basename(notes_path), [notes_path]))
    if mode == "external-handoff":
        handoff = os.path.join(project, research.get("handoff_file") or "deep-research-handoff.md")
        out.append(Result("hand-off file present", os.path.exists(handoff),
                          "%s not found" % os.path.basename(handoff),
                          [handoff] if os.path.exists(handoff) else []))
    if mode == "degraded-by-user-request":
        head = "\n".join(notes.split("\n")[:15])
        out.append(Result("degraded-mode banner at top of notes",
                          bool(re.search(r"降级模式|degraded mode", head, re.I)),
                          "notes must open with the degraded-mode warning"))
    return out, notes


def check_stage(state, stage, project):
    """Prerequisites for being in `stage`. Returns a list of Result."""
    if stage not in STAGES:
        raise UsageError("unknown stage %r (stages: %s)" % (stage, ", ".join(STAGES)))
    if stage == "intake":
        return []
    results = check_intake(state)
    profile = state.get("domain_profile", "")
    endpoint = (state.get("protocol") or {}).get("primary_endpoint", "")
    if stage in ("citation-check", "polish", "review-loop"):
        manuscript = state.get("manuscript_file", "").strip()
        path = os.path.join(project, manuscript) if manuscript else ""
        ok = bool(manuscript) and os.path.isfile(path)
        results.append(Result("manuscript file exists", ok,
                              "set manuscript_file to the current draft" if not manuscript else "%s not found" % manuscript,
                              [path] if ok else []))
        if stage == "review-loop":
            confirmed = (state.get("target_journal_status") == "confirmed"
                         and bool(state.get("target_journal", "").strip()))
            results.append(Result("target journal confirmed", confirmed,
                                  "review calibration needs a confirmed journal"))
        return results
    if stage == "research":
        return results
    ready, notes = check_research_ready(state, project)
    results.extend(ready)
    if notes is not None:
        results.extend([gate_g1(notes), gate_g2(notes), gate_g3(notes)])
    else:
        results.append(Result("G1–G3 gates", False, "research notes missing"))
    if stage == "design":
        return results
    plan_path = stage_file(state, "design", project)
    if not os.path.exists(plan_path):
        results.append(Result("experiment plan exists", False, "%s not found" % os.path.basename(plan_path)))
    else:
        plan = read_text(plan_path)
        results.append(Result("experiment plan exists", True, os.path.basename(plan_path), [plan_path]))
        results.append(Result("literature integrity warning present",
                              bool(re.search(r"学术诚信警告|academic integrity warning", plan, re.I)),
                              "experiment plan must carry the AI-citation warning block"))
        results.append(Result("each experiment states its argument duty",
                              bool(re.search(r"论证职责|argument duty", plan, re.I)),
                              "add an 'argument duty' (论证职责) for every experiment"))
        if profile == "clinical-prespecified":
            results.append(Result("plan names the prespecified primary endpoint", contains_endpoint(plan, endpoint),
                                  "experiment-plan must quote the protocol primary endpoint verbatim: %r" % endpoint))
    if stage == "skeleton":
        return results
    outline_path = stage_file(state, "skeleton", project)
    if not os.path.exists(outline_path):
        results.append(Result("outline exists", False, "%s not found" % os.path.basename(outline_path)))
        return results
    outline = read_text(outline_path)
    results.append(Result("outline exists", True, os.path.basename(outline_path), [outline_path]))
    results.append(Result("two-way risk flags section",
                          bool(re.search(r"双向风险标记|two-way risk flags", outline, re.I)),
                          "outline needs the two-way risk flag table"))
    if profile == "cs-engineering":
        results.append(Result("'where this paper wins' sentence",
                              bool(re.search(r"赢在哪场比赛|where this paper wins", outline, re.I)),
                              "cs-engineering outlines state where the paper wins"))
    elif profile == "clinical-prespecified":
        results.append(Result("outline keeps the prespecified primary endpoint", contains_endpoint(outline, endpoint),
                              "outline must quote the protocol primary endpoint verbatim: %r" % endpoint))
    elif profile == "systematic-review":
        results.append(Result("outline mapped to PRISMA 2020", "PRISMA" in outline,
                              "systematic-review outlines follow PRISMA 2020"))
    elif profile == "observational":
        results.append(Result("outline mapped to STROBE", "STROBE" in outline,
                              "observational outlines follow STROBE"))
    return results


def failed(results):
    return [r for r in results if not r.ok]


# ---------------------------------------------------------------- commands

def cmd_init(args):
    path = progress_path(args.project)
    if os.path.exists(path) and not args.force:
        raise UsageError("%s already exists (use --force to overwrite, or `rw.py migrate`)" % path)
    state = new_progress()
    if args.topic:
        state["topic"] = args.topic
    if args.confirm_direction:
        state["writing_direction_confirmed"] = True
    for key in ("existing_direction", "materials", "manuscript_file", "domain_profile_notes"):
        value = getattr(args, key)
        if value:
            state[key] = value
    if args.domain_profile:
        state["domain_profile"] = args.domain_profile
    if args.journal:
        state["target_journal"] = args.journal
        state["target_journal_status"] = args.journal_status or "candidate"
    elif args.journal_status:
        state["target_journal_status"] = args.journal_status
    if args.primary_endpoint:
        state["protocol"]["primary_endpoint"] = args.primary_endpoint
    if args.registry_id:
        state["protocol"]["registered"] = True
        state["protocol"]["registry_id"] = args.registry_id
    os.makedirs(args.project, exist_ok=True)
    write_json_atomic(path, state)
    missing = failed(check_intake(state))
    print("wrote %s" % path)
    if missing:
        print("intake still open: " + "; ".join(r.label for r in missing))
    return 0


PLACEHOLDER_VALUE_RE = re.compile(r"\s\|\s")
# Only enum-like fields can carry v2.1 template placeholders such as "unknown | candidate | confirmed".
ENUM_KEYS = {"target_journal_status", "deep_research_mode", "isolation", "calibration_status",
             "status", "assistance_mode", "domain_profile"}


def cmd_migrate(args):
    path = progress_path(args.project)
    state = load_progress(args.project)
    template = new_progress()
    changes = []

    def merge(dst, src, prefix):
        for key, value in src.items():
            where = prefix + key
            if key not in dst:
                dst[key] = json.loads(json.dumps(value))
                changes.append("added " + where)
            elif isinstance(value, dict) and isinstance(dst[key], dict) and key not in ("journal_profile", "gate"):
                merge(dst[key], value, where + ".")
            elif (key in ENUM_KEYS and isinstance(dst[key], str)
                  and PLACEHOLDER_VALUE_RE.search(dst[key])):
                # v2.1 templates shipped "a | b | c" placeholders; they are not values.
                dst[key] = value
                changes.append("reset placeholder %s" % where)

    merge(state, template, "")
    state["schema_version"] = "2.2"
    if "intake" in state.get("stages", {}) and state["stages"]["intake"].get("status") == "":
        state["stages"]["intake"]["status"] = "in-progress" if state.get("current_stage") == "intake" else "done"
    write_json_atomic(path, state)
    print("migrated %s (%d change(s))" % (path, len(changes)))
    for c in changes:
        print("  " + c)
    errors = validate(state, SCHEMA)
    for e in errors:
        print("  schema: " + e)
    return 1 if errors else 0


def summarize(results):
    lines = []
    for r in results:
        mark = "PASS" if r.ok else "FAIL"
        detail = (" — " + r.detail) if r.detail and (not r.ok or r.label.startswith("G")) else ""
        lines.append("  [%s] %s%s" % (mark, r.label, detail))
    return lines


def next_stage(stage):
    i = STAGES.index(stage)
    return STAGES[i + 1] if i + 1 < len(STAGES) else None


def cmd_check(args):
    state = load_progress(args.project)
    errors = validate(state, SCHEMA)
    report = {"checker": CHECKER, "project": os.path.abspath(args.project),
              "schema_errors": errors}
    if errors:
        report["ok"] = False
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print("%s — schema: %d error(s) (older v2.1 file? try `rw.py migrate`)" % (CHECKER, len(errors)))
            for e in errors:
                print("  " + e)
        return 1
    current = state["current_stage"]
    target = args.stage or current
    results = check_stage(state, target, args.project)
    report["stage"] = target
    report["results"] = [r.as_dict() for r in results]
    nxt = None if args.stage else next_stage(current)
    if nxt:
        report["next_stage"] = nxt
        report["next_results"] = [r.as_dict() for r in check_stage(state, nxt, args.project)]
    report["ok"] = not failed(results)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1
    print("%s — schema OK — profile: %s — mode: %s" % (
        CHECKER, state.get("domain_profile") or "(not chosen)", state.get("assistance_mode", "advisor")))
    label = "prerequisites for stage '%s'" % target
    if not args.stage:
        label = "current stage '%s' is consistent" % current
    print("%s: %s" % (label, "YES" if report["ok"] else "NO"))
    for line in summarize(results):
        print(line)
    if nxt:
        nr = check_stage(state, nxt, args.project)
        print("next stage '%s': %s" % (nxt, "ready" if not failed(nr) else "blocked"))
        for line in summarize(failed(nr)):
            print(line)
    return 0 if report["ok"] else 1


def cmd_advance(args):
    state = load_progress(args.project)
    errors = validate(state, SCHEMA)
    if errors:
        print("refused: progress file fails the schema (run `rw.py check`)")
        return 1
    target = args.to
    results = check_stage(state, target, args.project)
    bad = failed(results)
    if bad:
        print("refused: cannot enter '%s' — %d prerequisite(s) fail:" % (target, len(bad)))
        for line in summarize(bad):
            print(line)
        return 1
    previous = state["current_stage"]
    files = {}
    for r in results:
        for f in r.files:
            if os.path.isfile(f):
                files[os.path.relpath(f, args.project)] = sha256_file(f)
    stamp = now_iso()
    stages = state.setdefault("stages", {})
    if previous != target and stages.get(previous, {}).get("status") in ("", "in-progress"):
        forward = STAGES.index(target) > STAGES.index(previous)
        stages.setdefault(previous, {})["status"] = "done" if forward else ""
    stages.setdefault(target, {})["status"] = "in-progress"
    if target in ("design", "skeleton", "user-draft"):
        gate = stages.setdefault("research", {}).setdefault("gate", {})
        verdict = "pass (%s, %s)" % (CHECKER, stamp)
        for key in ("G1_confirmed_gap", "G2_concrete_next_step", "G3_direction_compared"):
            gate[key] = verdict
        stages.setdefault("design", {})["blocked_by_gate"] = False
    state["current_stage"] = target
    state.setdefault("gate_log", []).append({
        "from": previous, "to": target, "at": stamp, "checker": CHECKER,
        "checks": [r.label for r in results], "files": files})
    write_json_atomic(progress_path(args.project), state)
    print("advanced %s → %s (%d check(s) passed; gate log entry written)" % (previous, target, len(results)))
    return 0


def cmd_status(args):
    state = load_progress(args.project)
    review = state.get("stages", {}).get("review-loop", {}) or {}
    blockers = review.get("blockers", {}) or {}
    print("topic: %s" % (state.get("topic") or "(not set)"))
    print("stage: %s · profile: %s · mode: %s" % (
        state.get("current_stage"), state.get("domain_profile") or "(not chosen)",
        state.get("assistance_mode", "advisor")))
    print("journal: %s (%s)" % (state.get("target_journal") or "-", state.get("target_journal_status")))
    print("deep research: %s" % (state.get("stages", {}).get("research", {}) or {}).get("deep_research_mode"))
    print("review round %s · P0 %s · P1 %s · P2 %s · P3 %s" % (
        review.get("round", 0), blockers.get("P0", 0), blockers.get("P1", 0),
        blockers.get("P2", 0), blockers.get("P3", 0)))
    for stage in STAGES:
        print("  %-15s %s" % (stage, (state.get("stages", {}).get(stage, {}) or {}).get("status", "")))
    return 0


def append_log(project, state, lines):
    log_path = os.path.join(project, state.get("assistance_log") or "ai-assistance-log.md")
    new = not os.path.exists(log_path)
    with open(log_path, "a", encoding="utf-8", newline="\n") as f:
        if new:
            f.write("# AI assistance log\n\nKeep this file for the journal's AI-use disclosure. "
                    "Entries are appended by the workbench and by the assistant.\n\n")
        f.write("\n".join(lines) + "\n\n")
    return log_path


def cmd_mode(args):
    state = load_progress(args.project)
    if not args.mode:
        print(state.get("assistance_mode", "advisor"))
        return 0
    if args.mode == "sentence-edits":
        if not (args.request or "").strip() or not (args.scope or "").strip():
            raise UsageError("sentence-edits needs --request (the user's own words asking for edits) "
                             "and --scope (which files/sections)")
    entry = {"mode": args.mode, "at": now_iso()}
    if args.scope:
        entry["scope"] = args.scope
    if args.request:
        entry["user_request"] = args.request
    state["assistance_mode"] = args.mode
    state.setdefault("mode_history", []).append(entry)
    write_json_atomic(progress_path(args.project), state)
    log_path = append_log(args.project, state, [
        "## %s — assistance mode → %s" % (entry["at"], args.mode),
        "- scope: %s" % (args.scope or "-"),
        "- user request: %s" % (args.request or "-")])
    print("assistance mode = %s (logged in %s)" % (args.mode, os.path.basename(log_path)))
    return 0


def cmd_log(args):
    state = load_progress(args.project)
    path = append_log(args.project, state, [
        "## %s — %s" % (now_iso(), args.stage),
        "- mode: %s" % state.get("assistance_mode", "advisor"),
        "- %s" % args.summary])
    print("logged to %s" % os.path.basename(path))
    return 0


# ---------------------------------------------------------------- review isolation

REVIEWERS = {
    "R1": ("methods", "novelty, formalisation, design rationale ('why X not Y'), hidden assumptions, "
                      "black-box steps, errors in formulas or algorithms"),
    "R2": ("experiments and evidence", "baseline strength and fairness, dataset representativeness, "
                                       "ablations, statistical power and significance, reproducibility, "
                                       "over-interpretation, numbers in tables vs. claims in the text"),
    "R3": ("writing and contribution", "each stated contribution is supported in the body; over-claiming AND "
                                       "over-defensive wording; missing or unfair related work; honest, "
                                       "located limitations; abstract matches the paper"),
}
PROFILE_CHECKLISTS = {
    "cs-engineering": "",
    "clinical-prespecified": (
        "Prespecified clinical study. Check against the protocol/SAP and the applicable reporting "
        "guideline (e.g. STARD 2015, TRIPOD+AI, CONSORT, CLAIM): primary endpoint and analysis match "
        "the protocol, and any change is disclosed as a deviation with a reason; all prespecified "
        "outcomes are reported, including null results; participant flow and exclusions; reference "
        "standard and blinding of readers/assessors; sample-size justification; handling of missing "
        "or indeterminate results; estimates with confidence intervals; post hoc analyses labelled "
        "exploratory; registration and ethics statements. Extra P0 triggers: switched or unreported "
        "primary outcome, undisclosed protocol deviation, missing ethics approval or required registration."),
    "systematic-review": (
        "Systematic review. Check against PRISMA 2020: registered protocol, reproducible search "
        "(sources, dates, full strategy), selection with flow diagram, risk-of-bias assessment, "
        "synthesis methods, certainty of evidence, limitations of the evidence (PRISMA 2020 for "
        "Abstracts asks for them in the abstract too)."),
    "observational": (
        "Observational study. Check against STROBE: design, setting, eligibility, exposures, outcomes "
        "and confounders defined; confounding and bias handled; missing data; no causal language "
        "beyond what the design supports; limitations discussed."),
    "custom": "Use the reporting guideline(s) named in the brief's profile notes.",
}
TEXT_EXTS = (".md", ".markdown", ".txt", ".tex", ".rst")
DOCX_EXTS = (".docx", ".docm", ".dotx")
FORBIDDEN_IN_SANDBOX = (".git", PROGRESS_FILE, "reviews")
SANDBOX_PREFIX = "rw-sbx-"


def inspect_docx(path):
    """Return a list of issue keys found in a .docx: revisions, comments, author-metadata."""
    issues = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        doc = z.read("word/document.xml").decode("utf-8", "replace") if "word/document.xml" in names else ""
        if re.search(r"<w:(ins|del|moveFrom|moveTo)\b", doc):
            issues.append("revisions")
        comments = z.read("word/comments.xml").decode("utf-8", "replace") if "word/comments.xml" in names else ""
        if re.search(r"<w:comment\b", comments):
            issues.append("comments")
        core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in names else ""
        app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in names else ""
        if (re.search(r"<dc:creator>\s*[^<\s][^<]*</dc:creator>", core)
                or re.search(r"<cp:lastModifiedBy>\s*[^<\s][^<]*</cp:lastModifiedBy>", core)
                or re.search(r"<(Company|Manager)>\s*[^<\s][^<]*</\1>", app)
                or "word/people.xml" in names):
            issues.append("author-metadata")
    return issues


def strip_docx_metadata(src, dst):
    """Copy a .docx, blanking author fields in docProps (all other parts byte-identical)."""
    blank = [
        (re.compile(r"(<dc:creator>)[^<]*(</dc:creator>)"), r"\1\2"),
        (re.compile(r"(<cp:lastModifiedBy>)[^<]*(</cp:lastModifiedBy>)"), r"\1\2"),
        (re.compile(r"(<(Company|Manager)>)[^<]*(</\2>)"), r"\1\3"),
    ]
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w") as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if info.filename in ("docProps/core.xml", "docProps/app.xml"):
                text = data.decode("utf-8")
                for pattern, repl in blank:
                    text = pattern.sub(repl, text)
                data = text.encode("utf-8")
            zout.writestr(info, data)


def is_within(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def reviewer_brief(rid, sandbox, journal, profile, profile_notes, manuscript_name, materials):
    role, focus = REVIEWERS[rid]
    extra = PROFILE_CHECKLISTS.get(profile, "")
    if profile == "custom" and profile_notes:
        extra += " Profile notes: " + profile_notes
    mat = "\n".join("- input/materials/%s" % m for m in materials) or "- (none)"
    return """# Reviewer brief — {rid} ({role})

You are an independent reviewer for **{journal}**. Perspective: **{role}**.
Review ONLY the manuscript snapshot in this folder. You do not know who the authors are,
that other reviewers exist, or how the manuscript was revised.

## Files you may open — nothing else
- input/{manuscript}
{materials}
- input/journal-profile.md (scope, format rules, recent similar papers; titles unverified)

Do not open, list or search any path outside this folder: `{sandbox}`.
Do not modify anything except `output/review.md`.

## Write output/review.md

1. A blocker table, one row per problem:

| Level | ID | Location | Problem | Missing evidence or explanation | Direction (no rewritten text) | Rerun experiments? | Effort |
|---|---|---|---|---|---|---|---|
| P0 | {rid}-1 | §5.3, Table 4 | ... | ... | ... | yes/no | hours/days |

2. Optional short notes per item.
3. A final section `## Files consulted` listing every file you opened.

## Levels
- P0 blocking: the conclusion does not stand without a fix, or a hard defect gets the paper returned
  (claim contradicts its own table/figure, core claim unsupported, key comparison missing,
  ethics/data-permission statement missing, citations that do not resolve, hard format limits exceeded).
- P1 must fix: reviewers will very likely demand more evidence or argument
  ("significant" without a test, missing ablation, undeclared assumption, missing key competitor, black-box step).
- P2 should fix: persuasiveness and readability (terminology, self-explanatory figures, contribution/support mismatch,
  self-weakening wording where a claim belongs).
- P3 optional: style and nice-to-haves.

## Focus
{focus}
{extra}

## Forbidden
- Predicting the editorial decision; any probability or percentage about acceptance;
  ACCEPT / MINOR / MAJOR / REJECT style verdicts.
- Rewriting the author's sentences — give the direction only.
- Inventing literature, data or journal rules — write "needs author verification" instead.
- Mentioning or guessing other reviewers' opinions.
""".format(rid=rid, role=role, journal=journal or "the target journal", manuscript=manuscript_name,
           materials=mat, sandbox=sandbox, focus=focus, extra=extra)


def cmd_review_packet(args):
    project = os.path.abspath(args.project)
    state = load_progress(project)
    manuscript = args.manuscript or state.get("manuscript_file", "")
    if not manuscript:
        raise UsageError("no manuscript: pass --manuscript or set manuscript_file")
    manuscript_path = manuscript if os.path.isabs(manuscript) else os.path.join(project, manuscript)
    if not os.path.isfile(manuscript_path):
        raise UsageError("manuscript not found: %s" % manuscript_path)
    profile_path = args.journal_profile
    if not profile_path:
        default = os.path.join(project, (state.get("stages", {}).get("review-loop", {}) or {}).get(
            "calibration_file") or "review-calibration.md")
        profile_path = default if os.path.exists(default) else None
    if not profile_path and not args.no_calibration:
        raise UsageError("no journal profile / calibration file: pass --journal-profile, or "
                         "--no-calibration to record that reviewer focus comes from model priors")
    warnings, waivers = [], []
    ext = os.path.splitext(manuscript_path)[1].lower()
    strip = False
    if ext in DOCX_EXTS:
        if not zipfile.is_zipfile(manuscript_path):
            raise UsageError("%s is not a valid .docx (not a zip archive)" % manuscript_path)
        issues = inspect_docx(manuscript_path)
        blocking = [i for i in issues if i in ("revisions", "comments")]
        if blocking and not args.allow_docx_revisions:
            print("refused: the .docx contains %s — reviewers would see the revision history. "
                  "Accept all changes and delete comments in a copy, or pass --allow-docx-revisions."
                  % " and ".join(blocking))
            return 1
        if blocking:
            waivers.append("docx-" + "+".join(blocking))
        if "author-metadata" in issues:
            if args.strip_docx_metadata:
                strip = True
            elif not args.allow_docx_metadata:
                print("refused: the .docx carries author metadata (creator / last modified by / company / people). "
                      "Pass --strip-docx-metadata to blank it in the snapshot, or --allow-docx-metadata.")
                return 1
            else:
                waivers.append("docx-author-metadata")
    elif ext == ".pdf":
        warnings.append("PDF snapshot is copied as-is: its metadata and annotations are not inspected")
    round_no = args.round or ((state.get("stages", {}).get("review-loop", {}) or {}).get("round", 0) + 1)
    existing_packet = os.path.join(project, "reviews", "round-%d" % round_no, "packet.json")
    if os.path.exists(existing_packet) and not args.force:
        print("refused: round %d already has a packet (%s). Aggregate it, pick another --round, "
              "or pass --force to rebuild (the old sandboxes are not reused)."
              % (round_no, os.path.relpath(existing_packet, project)))
        return 1
    reviewers = [r.strip().upper() for r in args.reviewers.split(",") if r.strip()]
    for rid in reviewers:
        if rid not in REVIEWERS:
            raise UsageError("unknown reviewer %r (use R1,R2,R3)" % rid)
    if args.out_root and is_within(args.out_root, project):
        print("refused: --out-root %s is inside the project; sandboxes must live outside it" % args.out_root)
        return 1
    materials = []
    for i, m in enumerate(args.material or [], 1):
        mpath = m if os.path.isabs(m) else os.path.join(project, m)
        if not os.path.isfile(mpath):
            raise UsageError("material is not a file: %s (directories are not copied)" % m)
        if os.path.basename(mpath) in FORBIDDEN_IN_SANDBOX or ".git" + os.sep in mpath:
            raise UsageError("refusing to copy workflow state into a sandbox: %s" % m)
        materials.append((mpath, "material-%d%s" % (i, os.path.splitext(mpath)[1].lower())))
    if args.out_root:
        os.makedirs(args.out_root, exist_ok=True)
    manuscript_name = "manuscript" + ext
    packet = {"round": round_no, "created_at": now_iso(), "checker": CHECKER, "isolation": "snapshot",
              "journal": state.get("target_journal", ""), "domain_profile": state.get("domain_profile", ""),
              "inputs": {"manuscript": {"source": os.path.relpath(manuscript_path, project),
                                        "sha256": sha256_file(manuscript_path)},
                         "materials": [{"source": os.path.relpath(p, project), "as": n, "sha256": sha256_file(p)}
                                       for p, n in materials],
                         "journal_profile": ({"source": os.path.relpath(profile_path, project) if is_within(profile_path, project) else profile_path,
                                              "sha256": sha256_file(profile_path)} if profile_path else None)},
              "waivers": waivers, "warnings": warnings, "reviewers": []}
    for rid in reviewers:
        # Neutral prefix: the directory name must not reveal the role, round or project.
        sandbox = tempfile.mkdtemp(prefix=SANDBOX_PREFIX, dir=args.out_root)
        if is_within(sandbox, project):
            shutil.rmtree(sandbox, ignore_errors=True)
            print("refused: temp dir %s resolved inside the project; pass --out-root" % sandbox)
            return 1
        os.makedirs(os.path.join(sandbox, "input", "materials"))
        os.makedirs(os.path.join(sandbox, "output"))
        snap = os.path.join(sandbox, "input", manuscript_name)
        if strip:
            strip_docx_metadata(manuscript_path, snap)
        else:
            shutil.copyfile(manuscript_path, snap)
        for mpath, name in materials:
            shutil.copyfile(mpath, os.path.join(sandbox, "input", "materials", name))
        jp = os.path.join(sandbox, "input", "journal-profile.md")
        if profile_path:
            shutil.copyfile(profile_path, jp)
        else:
            with open(jp, "w", encoding="utf-8") as f:
                f.write("# Journal profile\n\nNo calibration available: reviewer focus comes from model priors, "
                        "not from the journal's published papers.\n")
        brief = reviewer_brief(rid, sandbox, state.get("target_journal", ""), state.get("domain_profile", ""),
                               state.get("domain_profile_notes", ""), manuscript_name, [n for _p, n in materials])
        with open(os.path.join(sandbox, "REVIEWER_BRIEF.md"), "w", encoding="utf-8") as f:
            f.write(brief)
        paste = brief + "\n---\n\n"
        if ext in TEXT_EXTS:
            paste += "## Manuscript (snapshot)\n\n" + read_text(snap)
        else:
            paste += "## Manuscript\n\nAttach `input/%s` from the sandbox to this chat.\n" % manuscript_name
        with open(os.path.join(sandbox, "PASTE_PROMPT.md"), "w", encoding="utf-8") as f:
            f.write(paste)
        packet["reviewers"].append({
            "id": rid, "role": REVIEWERS[rid][0], "sandbox": sandbox,
            "snapshot_sha256": sha256_file(snap),
            "inputs": sorted(os.path.relpath(os.path.join(dp, fn), sandbox)
                             for dp, _dn, fns in os.walk(sandbox) for fn in fns),
            "output": os.path.join(sandbox, "output", "review.md")})
    review_dir = os.path.join(project, "reviews", "round-%d" % round_no)
    os.makedirs(review_dir, exist_ok=True)
    packet_path = os.path.join(review_dir, "packet.json")
    write_json_atomic(packet_path, packet)
    loop = state.setdefault("stages", {}).setdefault("review-loop", {})
    loop.setdefault("packets", []).append({"round": round_no, "packet": os.path.relpath(packet_path, project),
                                           "created_at": packet["created_at"]})
    loop["isolation"] = "snapshot"
    loop["calibration_status"] = loop.get("calibration_status") or ("searched" if profile_path else "degraded-no-search")
    write_json_atomic(progress_path(project), state)
    print("round %d packet: %s" % (round_no, os.path.relpath(packet_path, project)))
    for w in warnings + ["waiver: " + w for w in waivers]:
        print("  note: " + w)
    for r in packet["reviewers"]:
        print("%s (%s) → give the reviewer only this instruction:" % (r["id"], r["role"]))
        print('  "Read %s/REVIEWER_BRIEF.md and follow it exactly. Work only inside %s."' % (r["sandbox"], r["sandbox"]))
    print("no subagents? paste each sandbox's PASTE_PROMPT.md into a separate fresh chat.")
    return 0


DECISION_RE = re.compile(r"\b(ACCEPT(ED)?|REJECT(ED)?)\b|\b(minor|major)\s+revisions?\b|"
                         r"recommend(ation)?\W+(to\s+)?(accept|reject)|小修|大修|拒稿|建议录用|建议接收|直接录用", re.I)
PROB_CONTEXT_RE = re.compile(r"accept|acceptance|chance|likelihood|probability|odds|录用|接收|中稿|把握|概率", re.I)
PERCENT_RE = re.compile(r"\d{1,3}(?:\.\d+)?\s?%|\d\s?成把握|[一二三四五六七八九]成把握")
ABS_PATH_RE = re.compile(r"(?:^|(?<=[\s`'\"(]))((?:/Users|/home|/private|/var|/tmp|/Volumes|~)/[^\s`'\")\]]+|[A-Za-z]:\\[^\s`'\")\]]+)")
NEGATION_RE = re.compile(r"\b(not|no|never|without|nor)\b|不|禁止|无|勿", re.I)
LEAK_NAMES = (PROGRESS_FILE, "research-notes.md", "experiment-plan.md", "outline.md",
              "polish-suggestions.md", "citation-report.md", "reviews/round-", "packet.json")
ROW_LEVEL_RE = re.compile(r"^\**\s*(P[0-3])\s*\**$")
BULLET_LEVEL_RE = re.compile(r"^\s*[-*+]\s*\[(P[0-3])\]")


def scan_review(text, sandbox):
    flags = []
    for n, line in enumerate(text.split("\n"), 1):
        for m in DECISION_RE.finditer(line):
            if not NEGATION_RE.search(line[max(0, m.start() - 40):m.start()]):
                flags.append("line %d: decision-tier wording: %s" % (n, line.strip()[:120]))
                break
        if PERCENT_RE.search(line) and PROB_CONTEXT_RE.search(line):
            flags.append("line %d: acceptance probability/percentage: %s" % (n, line.strip()[:120]))
        for m in ABS_PATH_RE.finditer(line):
            path = os.path.expanduser(m.group(1).rstrip(".,;:"))
            if not is_within(path, sandbox):
                flags.append("line %d: references a path outside its sandbox: %s" % (n, m.group(1)))
        for name in LEAK_NAMES:
            if name in line:
                flags.append("line %d: mentions workflow-internal file %r (possible leakage)" % (n, name))
    return flags


def count_levels(text):
    counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    rows = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("|"):
            cells = _split_row(s)
            m = ROW_LEVEL_RE.match(cells[0]) if cells else None
            if m and all(c in ("", "...", "…") for c in cells[2:]):
                continue  # untouched template example row
            if m:
                counts[m.group(1)] += 1
                rows.append(cells)
            continue
        m = BULLET_LEVEL_RE.match(line)
        if m:
            counts[m.group(1)] += 1
            rows.append([m.group(1), "", "", s])
    return counts, rows


def remove_sandbox(sandbox, project):
    """Delete a reviewer sandbox, but only one that rw.py itself created (packet.json is editable)."""
    real = os.path.realpath(sandbox)
    if (not os.path.isdir(real) or not os.path.basename(real).startswith(SANDBOX_PREFIX)
            or not os.path.isfile(os.path.join(real, "REVIEWER_BRIEF.md"))
            or is_within(real, project) or is_within(project, real)):
        return False
    shutil.rmtree(real)
    return True


def cmd_aggregate(args):
    project = os.path.abspath(args.project)
    state = load_progress(project)
    loop_state = state.get("stages", {}).get("review-loop", {}) or {}
    packet_rounds = [p.get("round", 0) for p in loop_state.get("packets", []) if isinstance(p, dict)]
    round_no = args.round or (max(packet_rounds) if packet_rounds else loop_state.get("round", 0) + 1)
    review_dir = os.path.join(project, "reviews", "round-%d" % round_no)
    packet_path = os.path.join(review_dir, "packet.json")
    if not os.path.exists(packet_path):
        raise UsageError("no packet for round %d (%s) — run `rw.py review-packet` first" % (round_no, packet_path))
    with open(packet_path, encoding="utf-8") as f:
        packet = json.load(f)
    out_path = os.path.join(project, "reviews", "round-%d.md" % round_no)
    if os.path.exists(out_path) and not args.force:
        raise UsageError("%s exists (use --force to rebuild)" % out_path)
    totals = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    merged, sections, flags = [], [], []
    for r in packet["reviewers"]:
        rid, sandbox = r["id"], r["sandbox"]
        if not os.path.exists(r["output"]):
            flags.append("%s: no output/review.md — reviewer did not finish" % rid)
            continue
        text = read_text(r["output"])
        with open(os.path.join(review_dir, "reviewer-%s.md" % rid), "w", encoding="utf-8") as f:
            f.write(text)
        counts, rows = count_levels(text)
        for level in totals:
            totals[level] += counts[level]
        merged.extend((row[0].strip("* "), (row[1] or rid) if len(row) > 1 else rid, row) for row in rows)
        flags.extend("%s %s" % (rid, f) for f in scan_review(text, sandbox))
        snap = os.path.join(sandbox, "input", "manuscript" + os.path.splitext(packet["inputs"]["manuscript"]["source"])[1].lower())
        if os.path.exists(snap) and sha256_file(snap) != r["snapshot_sha256"]:
            flags.append("%s modified its manuscript snapshot (read-only rule broken)" % rid)
        now_files = sorted(os.path.relpath(os.path.join(dp, fn), sandbox)
                           for dp, _dn, fns in os.walk(sandbox) for fn in fns)
        extra = [p for p in now_files if p not in r["inputs"] and not p.startswith("output" + os.sep)]
        if extra:
            flags.append("%s wrote outside output/: %s" % (rid, ", ".join(extra)))
        sections.append("### %s — %s\n\n%s" % (rid, r["role"], text.strip()))
    merged.sort(key=lambda t: (t[0], t[1]))
    lines = ["# Simulated review — round %d" % round_no, "",
             "> ⚠️ Simulated review, not a prediction of the editorial decision. Independent, blinded reviewer "
             "agents can still be wrong or miss things. 本文件是模拟评审，不是录用结果预测。", "",
             "- Target journal: %s" % (packet.get("journal") or "-"),
             "- Isolation: snapshot sandboxes outside the project (%s); waivers: %s" % (
                 packet.get("checker"), ", ".join(packet.get("waivers") or []) or "none"),
             "- Counts: P0 %(P0)d · P1 %(P1)d · P2 %(P2)d · P3 %(P3)d" % totals,
             "- Integrity flags: %d%s" % (len(flags), " (see below — check before trusting this round)" if flags else ""),
             "", "## Blocker table (merged)", "",
             "| Level | Reviewer | Location | Problem | Missing evidence | Direction | Rerun? | Effort |",
             "|---|---|---|---|---|---|---|---|"]
    for level, rid, row in merged:
        cells = (row[2:] if len(row) > 2 else row[1:]) + [""] * 6
        lines.append("| %s | %s | %s |" % (level, rid, " | ".join(c.replace("\n", " ") for c in cells[:6])))
    lines += ["", "## Reviewer reports (verbatim)", ""] + sections
    lines += ["", "## Integrity flags", ""] + (["- " + f for f in flags] or ["- none"])
    lines += ["", "## Revision checklist (for the author; never shown to next-round reviewers)", "",
              "- Fix or answer every P0 and P1; record refusals with reasons here.", ""]
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    loop = state.setdefault("stages", {}).setdefault("review-loop", {})
    loop["round"] = max(loop.get("round", 0), round_no)
    loop["blockers"] = totals
    loop["status"] = "in-progress"
    loop.setdefault("reviews", []).append({"round": round_no, "file": os.path.relpath(out_path, project),
                                           "counts": totals, "flags": len(flags)})
    write_json_atomic(progress_path(project), state)
    if not args.keep_sandboxes:
        # Outputs are archived under reviews/round-N/; deleting the sandboxes stops next-round
        # reviewers from finding this round's reviews by listing the temp directory.
        removed = [r["sandbox"] for r in packet["reviewers"] if remove_sandbox(r["sandbox"], project)]
        packet["sandboxes_removed_at"] = now_iso() if removed else None
        write_json_atomic(packet_path, packet)
    print("wrote %s — P0 %d · P1 %d · P2 %d · P3 %d · flags %d" % (
        os.path.relpath(out_path, project), totals["P0"], totals["P1"], totals["P2"], totals["P3"], len(flags)))
    for f in flags:
        print("  flag: " + f)
    return 1 if (flags and args.strict) else 0


# ---------------------------------------------------------------- Claude Code hook

def find_project_for(path, max_up=6):
    d = os.path.dirname(os.path.abspath(path))
    for _ in range(max_up):
        if os.path.exists(os.path.join(d, PROGRESS_FILE)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def cmd_hook_guard(_args):
    """PreToolUse hook: exit 2 (block, reason on stderr) or 0 (allow)."""
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or tool_input.get("path")
    if payload.get("tool_name") not in ("Write", "Edit", "MultiEdit", "NotebookEdit") or not target:
        return 0
    if not os.path.isabs(target):
        target = os.path.join(payload.get("cwd") or os.getcwd(), target)
    project = find_project_for(target)
    if project is None:
        return 0
    try:
        state = load_progress(project)
    except UsageError as e:
        sys.stderr.write("research-workbench: %s — fix it with `rw.py check` before writing here\n" % e)
        return 2
    rel = os.path.relpath(os.path.realpath(target), os.path.realpath(project))
    guarded = {}
    for stage in ("design", "skeleton"):
        name = (state.get("stages", {}).get(stage, {}) or {}).get("output_file") or DEFAULT_OUTPUTS[stage]
        guarded[os.path.normpath(name)] = stage
    if os.path.normpath(rel) in guarded:
        stage = guarded[os.path.normpath(rel)]
        bad = failed(check_stage(state, stage, project))
        if bad:
            sys.stderr.write("research-workbench: writing %s requires the '%s' prerequisites; failing: %s. "
                             "Run `rw.py check --stage %s`.\n" % (rel, stage, "; ".join(
                                 "%s (%s)" % (r.label, r.detail) for r in bad), stage))
            return 2
    manuscript = state.get("manuscript_file", "")
    if manuscript and os.path.normpath(rel) == os.path.normpath(manuscript) \
            and state.get("assistance_mode", "advisor") != "sentence-edits":
        sys.stderr.write("research-workbench: advisor mode does not edit the manuscript. Give location → problem → "
                         "direction instead, or ask the user whether to switch: "
                         "`rw.py mode sentence-edits --scope ... --request ...`.\n")
        return 2
    return 0


def cmd_schema(_args):
    print(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
    return 0


# ---------------------------------------------------------------- CLI

def build_parser():
    p = argparse.ArgumentParser(prog="rw.py", description="Research Workbench checker (%s)" % VERSION)
    p.add_argument("--version", action="version", version=CHECKER)
    sub = p.add_subparsers(dest="cmd")

    def add(name, fn, help_text):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("--project", default=".", help="workbench project directory (default: .)")
        sp.set_defaults(fn=fn)
        return sp

    sp = add("init", cmd_init, "create .writing-progress.json")
    sp.add_argument("--topic")
    sp.add_argument("--confirm-direction", action="store_true")
    sp.add_argument("--existing-direction", dest="existing_direction")
    sp.add_argument("--materials")
    sp.add_argument("--manuscript", dest="manuscript_file")
    sp.add_argument("--journal")
    sp.add_argument("--journal-status", choices=["unknown", "candidate", "confirmed"])
    sp.add_argument("--domain-profile", choices=PROFILES)
    sp.add_argument("--profile-notes", dest="domain_profile_notes")
    sp.add_argument("--primary-endpoint")
    sp.add_argument("--registry-id")
    sp.add_argument("--force", action="store_true")
    add("migrate", cmd_migrate, "upgrade an older progress file in place")
    sp = add("check", cmd_check, "validate progress, prerequisites and gates")
    sp.add_argument("--stage", choices=STAGES, help="check the prerequisites of this stage instead")
    sp.add_argument("--json", action="store_true")
    sp = add("advance", cmd_advance, "enter a stage if its prerequisites pass")
    sp.add_argument("--to", required=True, choices=STAGES)
    add("status", cmd_status, "summary")
    sp = add("mode", cmd_mode, "show or switch assistance mode")
    sp.add_argument("mode", nargs="?", choices=ASSISTANCE_MODES)
    sp.add_argument("--scope", help="which files/sections the mode covers")
    sp.add_argument("--request", help="the user's own words asking for this mode")
    sp = add("log", cmd_log, "append to the AI-assistance log")
    sp.add_argument("--stage", required=True)
    sp.add_argument("--summary", required=True)
    sp = add("review-packet", cmd_review_packet, "build blinded reviewer sandboxes")
    sp.add_argument("--round", type=int)
    sp.add_argument("--manuscript")
    sp.add_argument("--material", action="append", help="extra file for reviewers (repeatable)")
    sp.add_argument("--journal-profile", help="journal profile / calibration excerpt to give reviewers")
    sp.add_argument("--no-calibration", action="store_true")
    sp.add_argument("--reviewers", default="R1,R2,R3")
    sp.add_argument("--out-root", help="parent dir for sandboxes (must be outside the project)")
    sp.add_argument("--allow-docx-revisions", action="store_true")
    sp.add_argument("--allow-docx-metadata", action="store_true")
    sp.add_argument("--strip-docx-metadata", action="store_true")
    sp.add_argument("--force", action="store_true", help="rebuild a round that already has a packet")
    sp = add("aggregate", cmd_aggregate, "merge reviewer outputs into reviews/round-N.md")
    sp.add_argument("--round", type=int)
    sp.add_argument("--force", action="store_true")
    sp.add_argument("--strict", action="store_true", help="exit 1 when integrity flags are raised")
    sp.add_argument("--keep-sandboxes", action="store_true",
                    help="keep reviewer sandboxes (default: delete them after archiving the outputs)")
    sp = sub.add_parser("hook-guard", help="Claude Code PreToolUse hook (reads hook JSON on stdin)")
    sp.set_defaults(fn=cmd_hook_guard)
    sp = sub.add_parser("schema", help="print the progress schema")
    sp.set_defaults(fn=cmd_schema)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "fn", None):
        parser.print_help()
        return 2
    try:
        return args.fn(args)
    except UsageError as e:
        sys.stderr.write("rw.py: %s\n" % e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
