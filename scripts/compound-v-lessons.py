#!/usr/bin/env python3
"""
Compound V — lesson DRAFTS from run results (the mechanical half of `/v:lessons`).

`docs/superpowers/memory/routing-lessons.md` is the human-curated, routing-authoritative
lesson file, and its loop — collector -> records -> *a human spots a pattern* -> a lesson —
stalled at the middle step: the repository accrued ~100 run directories while the file
kept only its seed example. This script makes the SPOTTING mechanical. The WRITING stays
human: `/v:lessons` presents each draft, and only an explicit yes puts a bullet in the file.

Subcommands
-----------
``draft [--repo R] [--since YYYY-MM-DD] [--min-count 2] [--json]``   READ-ONLY.
    Mines ``docs/superpowers/execution/*/results/*.json`` joined with each run's
    ``manifest.yaml`` (job ``type`` / ``backend`` / ``model`` or ``tier`` / ``isolation``)
    and ``state.json``. Failures are NOT re-derived here: V-memory's ``scan_failures``
    (scripts/compound-v-memory.py) decides which records are the job's own failure —
    ``scope_violation`` or a failed test floor — and honours ``recall_exclude: true``;
    harness faults, test-supervisor timeouts and pipeline bookkeeping never count.

    Signals and their grouping keys (``fingerprint`` = sha256 of the key, 16 hex chars;
    the key carries no dates, counts or run ids, so it is stable as evidence accrues):

      type_model   (reason, job type, backend, model-or-tier) over attributed failures
      lane_area    (reason, common path prefix of the violated / failing files, 2 levels)
      shared_file  (file) — one violated file written out of lane by different jobs
      escalation   (job type, backend, model-or-tier) — ``escalated_from`` on a result or
                   a state job, or ``retry_exhausted`` on a state job. A retry that later
                   SUCCEEDED is transient and recovered: counted in ``scanned``, never a signal.

    A group becomes a CANDIDATE only when (1) it spans >= ``--min-count`` DISTINCT run ids
    and (2) the fixed menu below has an action for it. A group that clears the count but
    has no menu action is reported as ``unactionable`` (a lesson without "prefer ..." is
    not a lesson). A ``lane_area`` group whose evidence is a subset of another candidate's
    is reported as ``suppressed`` (it would draft the same lesson twice).

    THE PREFER-ACTION MENU (fixed; nothing else is ever proposed):

      shared_file  -> task0_shared_file: "move `<file>` into the serial Task 0
                      `shared_foundation` job"
      type_model / test_failure on a light / standard tier or a Sonnet model
                   -> tier_up: "route `<type>` one tier up (`<cur>` -> `<next>`)"
                      (deep / opus / frontier / fable: no rung the menu may lift to ->
                      unactionable)
      escalation on a review job
                   -> review_start_rung: "start `<type>` reviews at `<rung>`" (the rung
                      the run asked for, else the next rung of the ladder)
                      (escalation on a non-review job -> unactionable: a transient backend
                      outage is not a routing lesson the menu can express)
      type_model / scope_violation, lane_area / scope_violation
                   -> force_worktree when any evidence job ran `isolation: direct`,
                      else narrow_lane: "narrow the `<type>` lane — say in the task body
                      that `<area>` is out of lane"
      lane_area / test_failure -> unactionable (see the type_model group instead)

    ``possibly_covered`` is a HEURISTIC: true when an existing bullet under ``## Lessons``
    in routing-lessons.md names one of the candidate's job types AND its backend as plain
    text. It can be wrong both ways; the human decides.

    Counts come only from records: every number in the output is a count of files read.

``record --fingerprint F --decision accepted|rejected [--note TEXT]``
    Appends ONE JSON line to ``docs/superpowers/memory/lesson-reviews.jsonl`` (created if
    absent): {ts, fingerprint, decision, note, candidate}. ``draft`` skips every fingerprint
    whose latest decision is ``rejected`` (do not propose again) or ``accepted`` (already a
    lesson), listing them under ``skipped_reviewed``.

THIS SCRIPT NEVER WRITES routing-lessons.md. It reads it for ``possibly_covered`` and
nothing else; the single write path in this file is ``_append_review``, which refuses any
basename other than ``lesson-reviews.jsonl``. The selftest asserts both statically (source
scan) and dynamically (a guarded ``open``). The bullet itself is written by the agent
running `/v:lessons`, after a human said yes.

Python 3.9 compatible, stdlib only (PyYAML is used when importable; otherwise the manifest
validator's embedded subset parser, and a manifest neither can read is counted, not fatal).
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EXEC_REL = os.path.join("docs", "superpowers", "execution")
LESSONS_REL = os.path.join("docs", "superpowers", "memory", "routing-lessons.md")  # READ ONLY
REVIEWS_BASENAME = "lesson-reviews.jsonl"
REVIEWS_REL = os.path.join("docs", "superpowers", "memory", REVIEWS_BASENAME)
DATE_PLACEHOLDER = "YYYY-MM-DD"
TIER_LADDER = ("light", "standard", "deep", "frontier")
MODEL_LADDER = ("sonnet", "opus", "fable")   # = CLAUDE_ESCALATION in compound-v-emit-workflow.py
TIER_UP_ELIGIBLE = ("light", "standard", "sonnet")
AREA_DEPTH = 2
EVIDENCE_FILES_MAX = 5
SUMMARY_MAX = 120
_FP_RE = re.compile(r"^[0-9a-f]{8,64}$")
_RUN_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")

_FORCE_MINI_YAML = False   # selftest switch: exercise the no-PyYAML path


# --------------------------------------------------------------------------- #
# sibling loading (the codebase's importlib pattern — see compound-v-onboard.py)
# --------------------------------------------------------------------------- #
_SIBLINGS = {}


def _sibling(filename, modname):
    if modname in _SIBLINGS:
        return _SIBLINGS[modname]
    path = os.path.join(HERE, filename)
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SIBLINGS[modname] = mod
    return mod


def memory():
    """V-memory's engine — owner of the failure-attribution rule (scan_failures)."""
    return _sibling("compound-v-memory.py", "cv_memory_for_lessons")


def _load_manifest(path):
    """(doc, error). PyYAML when importable, else the validator's subset parser. Never raises."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return None, "unreadable: %s" % exc
    yaml = None
    if not _FORCE_MINI_YAML:
        try:
            import yaml  # noqa: F811 — optional dependency
        except ImportError:
            yaml = None
    try:
        if yaml is not None:
            doc = yaml.safe_load(text)
        else:
            doc = _sibling("compound-v-validate-manifest.py", "cv_validate_for_lessons")._mini_yaml(text)
    except Exception as exc:  # noqa: BLE001 — a manifest we cannot read is counted, not fatal
        return None, str(exc).splitlines()[0][:160] if str(exc) else type(exc).__name__
    return (doc if isinstance(doc, dict) else None), (None if isinstance(doc, dict) else "not a mapping")


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# run context
# --------------------------------------------------------------------------- #
class Run(object):
    def __init__(self, exec_root, rel_dir):
        self.rel_dir = rel_dir
        self.run_id = os.path.basename(rel_dir)
        self.path = os.path.join(exec_root, rel_dir)
        self._jobs = None
        self._state = None
        self.manifest_error = None

    def jobs(self):
        if self._jobs is None:
            self._jobs = {}
            doc, err = _load_manifest(os.path.join(self.path, "manifest.yaml"))
            if doc is None:
                self.manifest_error = err
            else:
                for j in doc.get("jobs") or []:
                    if isinstance(j, dict) and j.get("id") is not None:
                        self._jobs[str(j.get("id"))] = j
        return self._jobs

    def state(self):
        if self._state is None:
            s = _read_json(os.path.join(self.path, "state.json"))
            self._state = s if isinstance(s, dict) else {}
        return self._state

    def state_job(self, job_id):
        jobs = self.state().get("jobs")
        if isinstance(jobs, dict):
            v = jobs.get(job_id)
            return v if isinstance(v, dict) else {}
        if isinstance(jobs, list):
            for v in jobs:
                if isinstance(v, dict) and str(v.get("id")) == job_id:
                    return v
        return {}

    def date(self):
        m = _RUN_DATE_RE.match(self.run_id)
        return m.group(1) if m else None


def _job_facts(run, job_id):
    j = run.jobs().get(job_id) or {}
    model = j.get("model")
    tier = j.get("tier")
    if model:
        label, source = str(model), "model"
    elif tier:
        label, source = str(tier), "tier"
    else:
        label, source = "?", "unknown"
    return {
        "type": str(j.get("type") or "?"),
        "backend": str(j.get("backend") or "?"),
        "model": label,
        "model_source": source,
        "isolation": str(j.get("isolation") or "?"),
        "known": bool(j),
    }


def _is_review(job_id, facts):
    return facts["type"] == "review" or "review" in job_id


def _area(files):
    parts = []
    for f in files:
        p = str(f).replace("\\", "/").rstrip("/")
        d = p.rsplit("/", 1)[0] if "/" in p else ""
        parts.append([x for x in d.split("/") if x])
    if not parts:
        return None
    common = parts[0]
    for p in parts[1:]:
        n = 0
        while n < len(common) and n < len(p) and common[n] == p[n]:
            n += 1
        common = common[:n]
    if not common:
        # every file at the top level is one area; files in DIFFERENT top-level trees are none
        return "(repo root)" if all(not p for p in parts) else None
    return "/".join(common[:AREA_DEPTH])


def fingerprint(key):
    return hashlib.sha256(json.dumps(list(key), separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# reviews (lesson-reviews.jsonl)
# --------------------------------------------------------------------------- #
def load_reviews(repo):
    """{fingerprint: latest review line}. A malformed line is skipped, never fatal."""
    out = {}
    path = os.path.join(repo, REVIEWS_REL)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and isinstance(rec.get("fingerprint"), str) \
                and rec.get("decision") in ("accepted", "rejected"):
            out[rec["fingerprint"]] = rec
    return out


def _append_review(path, obj):
    """THE ONLY WRITE PATH IN THIS SCRIPT. Appends one JSON line to lesson-reviews.jsonl and
    refuses every other target — routing-lessons.md above all."""
    if os.path.basename(path) != REVIEWS_BASENAME:
        raise ValueError("refusing to write %s: this script only appends to %s" % (path, REVIEWS_BASENAME))
    if os.path.islink(path):
        raise ValueError("refusing to append through a symlink: %s" % path)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# existing lessons (read-only) — possibly_covered heuristic
# --------------------------------------------------------------------------- #
def load_lesson_bullets(repo):
    try:
        with open(os.path.join(repo, LESSONS_REL), "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return []
    bullets, cur, inside = [], None, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.strip().lower() == "## lessons"
            if cur:
                bullets.append(cur)
                cur = None
            continue
        if not inside:
            continue
        if line.startswith("- "):
            if cur:
                bullets.append(cur)
            cur = line[2:].strip()
        elif cur is not None and line.strip():
            cur += " " + line.strip()
        elif cur is not None:
            bullets.append(cur)
            cur = None
    if cur:
        bullets.append(cur)
    return bullets


def _covered_by(bullets, pairs):
    hits = []
    for b in bullets:
        for t, be in pairs:
            if t == "?" or be == "?":
                continue
            if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(t), b) and \
                    re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(be), b, re.I):
                hits.append(b[:100])
                break
    return hits


# --------------------------------------------------------------------------- #
# the menu
# --------------------------------------------------------------------------- #
def _next_rung(label):
    low = label.lower()
    if low in MODEL_LADDER and MODEL_LADDER.index(low) + 1 < len(MODEL_LADDER):
        return MODEL_LADDER[MODEL_LADDER.index(low) + 1]
    if low in TIER_LADDER and TIER_LADDER.index(low) + 1 < len(TIER_LADDER):
        return TIER_LADDER[TIER_LADDER.index(low) + 1]
    return None


def _choose_action(group):
    """(action_id, prefer_text) or (None, why-not). The ONLY source of a 'prefer …'."""
    sig, key, ev = group["signal"], group["key"], group["evidence"]
    types = group["types"]
    tlist = "/".join("`%s`" % t for t in types)
    if sig == "shared_file":
        return "task0_shared_file", "moving `%s` into the serial Task 0 `shared_foundation` job" % key[1]
    if sig == "type_model" and key[1] == "test_failure":
        cur = key[4]
        if cur.lower() in TIER_UP_ELIGIBLE and _next_rung(cur):
            return "tier_up", "routing %s one tier up (`%s` → `%s`)" % (tlist, cur, _next_rung(cur))
        return None, "test-floor failures on `%s`: the menu lifts only light / standard / Sonnet rungs" % cur
    if sig == "escalation":
        if not all(e["is_review"] for e in ev):
            return None, "exhausted retries on a non-review job: a transient backend outage, no menu action"
        asked = sorted({e.get("escalated_to") for e in ev if e.get("escalated_to")})
        rung = asked[-1] if len(asked) == 1 else (None if asked else _next_rung(key[3]))
        if not rung and asked:
            rung = "/".join(asked)
        if not rung:
            return None, "no rung above `%s` on the ladder" % key[3]
        return "review_start_rung", "starting %s reviews at `%s`" % (tlist, rung)
    if sig in ("type_model", "lane_area") and key[1] == "scope_violation":
        if any(e["isolation"] == "direct" for e in ev):
            return "force_worktree", "forcing worktree isolation for %s jobs" % tlist
        area = key[2] if sig == "lane_area" else _area([f for e in ev for f in e["files"]])
        return "narrow_lane", "narrowing the %s lane — say in the task body that `%s` is out of lane" % (tlist, area)
    if sig == "lane_area" and key[1] == "test_failure":
        return None, "test-floor failures grouped by area: act on the type·model group instead"
    return None, "no menu entry for this signal"


def _outcome(group):
    sig, key, n = group["signal"], group["key"], group["run_count"]
    if sig == "shared_file":
        return "wrote the shared file `%s` outside its lane in %d independent runs" % (key[1], n)
    if sig == "escalation":
        return "exhausted its retry budget (reviewer lift requested) in %d independent runs" % n
    if key[1] == "test_failure":
        return "failed its test floor in %d independent runs" % n
    if sig == "lane_area":
        return "charged by the scope gate for paths under `%s` outside its lane in %d independent runs" % (key[2], n)
    return "charged by the scope gate for paths outside its lane in %d independent runs" % n


def _bullet(group, prefer):
    types = "/".join("`%s`" % t for t in group["types"])
    bms = "/".join("**%s**" % b for b in group["backend_models"])
    iso = "/".join(sorted({e["isolation"] for e in group["evidence"]}))
    runs = ", ".join(group["runs"])
    return "- **%s** — %s on %s (%s) → %s; prefer %s. *(Runs: %s.)*" % (
        DATE_PLACEHOLDER, types, bms, iso, _outcome(group), prefer, runs)


# --------------------------------------------------------------------------- #
# draft
# --------------------------------------------------------------------------- #
def build(repo, since=None, min_count=2):
    """Every group, with no reviews applied. Pure read."""
    exec_root = os.path.join(repo, EXEC_REL)
    scanned = {"exec_root": EXEC_REL, "run_dirs": 0, "result_records": 0,
               "runs_before_since": 0, "attributed_failures": 0,
               "excluded_by_scan_failures": {}, "excluded_scope": "all runs (scan_failures does not filter by date)",
               "retried_then_succeeded": 0, "escalation_records": 0,
               "escalation_recall_excluded": 0, "manifest_unreadable": [],
               "jobs_missing_from_manifest": 0}
    runs = {}

    def run_for(rel_dir):
        if rel_dir not in runs:
            runs[rel_dir] = Run(exec_root, rel_dir)
        return runs[rel_dir]

    def in_window(run):
        if not since:
            return True
        d = run.date()
        return bool(d) and d >= since

    groups = {}

    def add(key, signal, ev):
        g = groups.get(key)
        if g is None:
            g = groups[key] = {"signal": signal, "key": key, "evidence": []}
        if not any(x["run"] == ev["run"] and x["job"] == ev["job"] for x in g["evidence"]):
            g["evidence"].append(ev)

    if not os.path.isdir(exec_root):
        scanned["note"] = "no %s directory" % EXEC_REL
        return scanned, []

    # --- the results walk: counts, and signal (b) ---------------------------------
    for dirpath, dirs, files in os.walk(exec_root):
        dirs.sort()
        if os.path.basename(dirpath) != "results":
            continue
        rel_dir = os.path.relpath(os.path.dirname(dirpath), exec_root)
        run = run_for(rel_dir)
        # `.scope-<job>.json` beside the results is the scope gate's scratch, not a job_result
        jsons = sorted(f for f in files if f.endswith(".json") and not f.startswith("."))
        if not jsons:
            continue
        scanned["run_dirs"] += 1
        if not in_window(run):
            scanned["runs_before_since"] += 1
            continue
        for f in jsons:
            rec = _read_json(os.path.join(dirpath, f))
            if not isinstance(rec, dict):
                continue
            scanned["result_records"] += 1
            job_id = f[:-len(".json")]
            sj = run.state_job(job_id)
            retries = rec.get("retries") if isinstance(rec.get("retries"), list) else []
            esc_from = rec.get("escalated_from") or sj.get("escalated_from")
            exhausted = bool(sj.get("retry_exhausted"))
            if not (esc_from or exhausted):
                if retries and rec.get("status") == "success":
                    scanned["retried_then_succeeded"] += 1
                continue
            if memory().run_recall_excluded(run.path):
                scanned["escalation_recall_excluded"] += 1
                continue
            scanned["escalation_records"] += 1
            facts = _job_facts(run, job_id)
            asked = None
            for r in retries + (sj.get("retries") if isinstance(sj.get("retries"), list) else []):
                if isinstance(r, dict) and r.get("escalated_from") and r.get("model"):
                    asked = str(r.get("model"))
            ev = _evidence(run, job_id, rec, facts, "escalation",
                           ["escalated_from=%s" % esc_from] if esc_from else ["retry_exhausted"])
            ev["escalated_to"] = asked
            add(("escalation", facts["type"], facts["backend"], facts["model"]), "escalation", ev)

    # --- signal (a) and (c): V-memory's attributed failures -------------------------
    stats = {}
    for fl in memory().scan_failures(exec_root, stats):
        rel = str(fl["run"]).replace("\\", "/")
        rel_dir = os.path.dirname(os.path.dirname(rel))
        job_id = os.path.basename(rel)[:-len(".json")]
        if job_id.startswith("."):
            continue            # scope-gate scratch (see the walk above), not a job_result
        run = run_for(rel_dir)
        if not in_window(run):
            continue
        scanned["attributed_failures"] += 1
        rec = _read_json(os.path.join(exec_root, rel)) or {}
        facts = _job_facts(run, job_id)
        if not facts["known"]:
            scanned["jobs_missing_from_manifest"] += 1
        reason = fl["reason"]
        ev = _evidence(run, job_id, rec, facts, reason, fl.get("files") or [])
        add(("type_model", reason, facts["type"], facts["backend"], facts["model"]), "type_model", ev)
        area = _area(ev["all_files"])
        if area:
            add(("lane_area", reason, area), "lane_area", ev)
        if reason == "scope_violation":
            for path in sorted(set(ev["all_files"])):
                add(("shared_file", path), "shared_file", ev)
    scanned["excluded_by_scan_failures"] = stats
    scanned["manifest_unreadable"] = sorted(
        "%s: %s" % (r.run_id, r.manifest_error) for r in runs.values() if r.manifest_error)

    out = []
    for key, g in groups.items():
        g["evidence"].sort(key=lambda e: (e["run"], e["job"]))
        g["runs"] = sorted({e["run"] for e in g["evidence"]})
        g["run_count"] = len(g["runs"])
        g["types"] = sorted({e["type"] for e in g["evidence"]})
        g["backend_models"] = sorted({"%s·%s" % (e["backend"], e["model"]) for e in g["evidence"]})
        g["fingerprint"] = fingerprint(key)
        out.append(g)
    out.sort(key=lambda g: (-g["run_count"], g["signal"], g["fingerprint"]))
    return scanned, out


def _evidence(run, job_id, rec, facts, reason, files):
    files = [str(x) for x in files]
    summary = str(rec.get("summary") or "").replace("\n", " ").strip()
    return {
        "run": run.run_id, "job": job_id, "reason": reason,
        "files": files[:EVIDENCE_FILES_MAX], "files_total": len(files), "all_files": files,
        "summary": summary[:SUMMARY_MAX] + ("…" if len(summary) > SUMMARY_MAX else ""),
        "type": facts["type"], "backend": facts["backend"], "model": facts["model"],
        "model_source": facts["model_source"], "isolation": facts["isolation"],
        "is_review": _is_review(job_id, facts),
        "continues": run.state().get("continues") if isinstance(run.state().get("continues"), str) else None,
    }


def _public(g, extra):
    d = {k: g[k] for k in ("fingerprint", "signal", "run_count", "runs", "types", "backend_models")}
    d["key"] = list(g["key"])
    d["evidence"] = [{k: v for k, v in e.items() if k != "all_files"} for e in g["evidence"]]
    d.update(extra)
    return d


def draft(repo, since=None, min_count=2):
    scanned, groups = build(repo, since, min_count)
    reviews = load_reviews(repo)
    bullets = load_lesson_bullets(repo)
    candidates, unactionable, below, suppressed, skipped = [], [], [], [], []
    for g in groups:
        if g["run_count"] < min_count:
            below.append({"fingerprint": g["fingerprint"], "signal": g["signal"], "key": list(g["key"]),
                          "run_count": g["run_count"], "runs": g["runs"]})
            continue
        action, prefer = _choose_action(g)
        if action is None:
            unactionable.append(_public(g, {"why": prefer}))
            continue
        pairs = sorted({(e["type"], e["backend"]) for e in g["evidence"]})
        hits = _covered_by(bullets, pairs)
        g["_cand"] = _public(g, {
            "action": action,
            "prefer": prefer,
            "bullet": _bullet(g, prefer),
            "possibly_covered": bool(hits),
            "covered_by": hits,
        })
        candidates.append(g)
    # a lane_area draft that a stronger candidate already explains is the same lesson twice
    final = []
    for g in candidates:
        mine = {(e["run"], e["job"]) for e in g["evidence"]}
        by = None
        if g["signal"] == "lane_area":
            for o in candidates:
                if o is g or o["signal"] == "lane_area":
                    continue
                if mine <= {(e["run"], e["job"]) for e in o["evidence"]}:
                    by = o["fingerprint"]
                    break
        if by:
            suppressed.append({"fingerprint": g["fingerprint"], "key": list(g["key"]), "subsumed_by": by})
            continue
        rv = reviews.get(g["fingerprint"])
        if rv:
            skipped.append({"fingerprint": g["fingerprint"], "decision": rv.get("decision"),
                            "ts": rv.get("ts"), "note": rv.get("note")})
            continue
        final.append(g["_cand"])
    return {
        "tool": "compound-v-lessons draft",
        "repo": os.path.abspath(repo),
        "since": since,
        "min_count": min_count,
        "scanned": scanned,
        "candidates": final,
        "unactionable": unactionable,
        "suppressed": suppressed,
        "skipped_reviewed": skipped,
        "below_threshold": below,
        "notes": [
            "counts are counts of records read; no number is estimated",
            "possibly_covered is a heuristic: plain-text match of job type AND backend in an existing lesson",
            "bullet carries the literal date placeholder %s — replace it with the real date on accept" % DATE_PLACEHOLDER,
            "this script never writes routing-lessons.md",
        ],
    }


def record(repo, fp, decision, note=None, since=None, min_count=2):
    if not _FP_RE.match(fp or ""):
        raise ValueError("fingerprint must be 8-64 lowercase hex characters")
    if decision not in ("accepted", "rejected"):
        raise ValueError("decision must be accepted or rejected")
    _scanned, groups = build(repo, since, min_count)
    cand = None
    for g in groups:
        if g["fingerprint"] == fp:
            action, prefer = _choose_action(g)
            cand = {"signal": g["signal"], "key": list(g["key"]), "runs": g["runs"],
                    "action": action, "bullet": _bullet(g, prefer) if action else None}
            break
    warning = None
    if cand is None:
        warning = "fingerprint %s is not among the groups drafted from this repo; recorded without a candidate" % fp
    line = {"ts": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
            "fingerprint": fp, "decision": decision,
            "note": (note or "").replace("\n", " ").strip()[:500] or None,
            "candidate": cand}
    _append_review(os.path.join(repo, REVIEWS_REL), line)
    return line, warning


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _human(res):
    s = res["scanned"]
    print("scanned: %d run dir(s), %d result record(s), %d attributed failure(s), %d escalation record(s)"
          % (s["run_dirs"], s["result_records"], s["attributed_failures"], s["escalation_records"]))
    print("excluded (scan_failures): %s" % json.dumps(s["excluded_by_scan_failures"], sort_keys=True))
    if not res["candidates"]:
        print("no lesson candidates at --min-count %d (%d group(s) below it, %d unactionable, %d already reviewed)"
              % (res["min_count"], len(res["below_threshold"]), len(res["unactionable"]),
                 len(res["skipped_reviewed"])))
    for i, c in enumerate(res["candidates"], 1):
        print("\n[%d] %s  %s  (%d runs)%s" % (i, c["fingerprint"], c["signal"], c["run_count"],
                                            "  POSSIBLY COVERED" if c["possibly_covered"] else ""))
        print("    " + c["bullet"])
        for e in c["evidence"]:
            print("    - %s / %s: %s %s" % (e["run"], e["job"], e["reason"], ", ".join(e["files"])))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--selftest":
        return _selftest()
    ap = argparse.ArgumentParser(description="Compound V — lesson drafts from run results (human-confirmed).")
    sub = ap.add_subparsers(dest="cmd")
    d = sub.add_parser("draft", help="read-only: propose lesson candidates")
    d.add_argument("--repo", default=".")
    d.add_argument("--since", default=None)
    d.add_argument("--min-count", type=int, default=2)
    d.add_argument("--json", action="store_true")
    r = sub.add_parser("record", help="append one decision to lesson-reviews.jsonl")
    r.add_argument("--repo", default=".")
    r.add_argument("--fingerprint", required=True)
    r.add_argument("--decision", required=True, choices=("accepted", "rejected"))
    r.add_argument("--note", default=None)
    r.add_argument("--since", default=None)
    r.add_argument("--min-count", type=int, default=2)
    args = ap.parse_args(argv)
    if args.cmd is None:
        ap.print_help()
        return 2
    if args.since and not re.match(r"^\d{4}-\d{2}-\d{2}$", args.since):
        print("error: --since must be YYYY-MM-DD", file=sys.stderr)
        return 2
    if args.min_count < 1:
        print("error: --min-count must be >= 1", file=sys.stderr)
        return 2
    if args.cmd == "draft":
        res = draft(args.repo, args.since, args.min_count)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            _human(res)
        return 0
    try:
        line, warning = record(args.repo, args.fingerprint, args.decision, args.note, args.since, args.min_count)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if warning:
        print("warning: %s" % warning, file=sys.stderr)
    print(json.dumps(line, ensure_ascii=False))
    return 0


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #
def _write(path, text):
    parent = os.path.dirname(path)
    if not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, "w", encoding="utf-8") as fh:  # selftest fixture only — never the repo
        fh.write(text)


FIXTURE_LESSONS = """# Routing lessons (fixture)

> No script writes this file.

## Lessons

- **2026-06-26** — `large_isolated` on **codex·gpt-5.5** (worktree) blocked twice on
  shared barrel files → prefer moving barrels into Task 0.

## How to add a lesson

1. Mention `docs` and claude here — outside ## Lessons, so it must not count.
"""


def _manifest(run_id, jobs, recall_exclude=None):
    out = ["run_id: %s" % run_id]
    if recall_exclude is not None:
        out.append("recall_exclude: %s" % ("true" if recall_exclude else "false"))
    out.append("jobs:")
    for j in jobs:
        out.append("  - id: %s" % j["id"])
        for k in ("type", "backend", "model", "tier", "isolation"):
            if j.get(k):
                out.append("    %s: %s" % (k, j[k]))
        out.append("    write_allowed: [\"%s\"]" % j.get("lane", "x/**"))
    return "\n".join(out) + "\n"


def _result(status="success", violations=None, tests_exit=0, files_changed=None, summary="s", **extra):
    r = {"status": status, "blocked": status == "blocked", "violations": violations or [],
         "files_changed": files_changed or [], "summary": summary, "exit_code": 0,
         "failure_class": None, "tests": {"exit_code": tests_exit}}
    r.update(extra)
    return r


def build_fixture(root):
    """The selftest / tests/test-lessons.sh fixture. Returns nothing; writes under root."""
    ex = os.path.join(root, EXEC_REL)
    _write(os.path.join(root, LESSONS_REL), FIXTURE_LESSONS)

    def run(run_id, jobs, results, recall_exclude=None, state=None, raw_manifest=None):
        d = os.path.join(ex, run_id)
        _write(os.path.join(d, "manifest.yaml"), raw_manifest or _manifest(run_id, jobs, recall_exclude))
        for jid, rec in results.items():
            _write(os.path.join(d, "results", jid + ".json"), json.dumps(rec))
        _write(os.path.join(d, "state.json"), json.dumps(state or {"run_id": run_id, "jobs": {}}))

    # SF: the same shared file, two different jobs, two runs  -> task0_shared_file
    run("2026-01-01-sf-a", [{"id": "slice-a", "type": "core_slice", "backend": "claude", "tier": "deep",
                             "isolation": "worktree"}],
        {"slice-a": _result("blocked", violations=["src/shared/index.ts"], summary="slice A")})
    run("2026-01-02-sf-b", [{"id": "crud-b", "type": "bounded_crud", "backend": "claude", "tier": "light",
                             "isolation": "worktree"}],
        {"crud-b": _result("blocked", violations=["src/shared/index.ts"], summary="crud B")})
    # TF: docs on light fails its floor twice -> tier_up light -> standard
    for rid in ("2026-01-03-tf-a", "2026-01-04-tf-b"):
        run(rid, [{"id": "doc-job", "type": "docs", "backend": "claude", "tier": "light", "isolation": "worktree"}],
            {"doc-job": _result("blocked", tests_exit=1, files_changed=["guide/a.md"], summary="docs")})
    # LANE: codex large_isolated strays twice inside one lane -> narrow_lane; possibly_covered (seed names it)
    run("2026-01-05-lane-a", [{"id": "iso", "type": "large_isolated", "backend": "codex", "model": "gpt-5.5",
                               "isolation": "worktree"}],
        {"iso": _result("blocked", violations=["lib/util/a.py"])})
    run("2026-01-06-lane-b", [{"id": "iso", "type": "large_isolated", "backend": "codex", "model": "gpt-5.5",
                               "isolation": "worktree"}],
        {"iso": _result("blocked", violations=["lib/util/b.py"])}, state={"run_id": "x", "continues": "2026-01-05-lane-a",
                                                                          "jobs": {}})
    # REV: direct review jobs write outside their lane twice -> force_worktree
    run("2026-01-07-rev-a", [{"id": "spec-review", "type": "review", "backend": "claude", "tier": "deep",
                              "isolation": "direct"}],
        {"spec-review": _result("blocked", violations=["CHANGELOG.md"])})
    run("2026-01-08-rev-b", [{"id": "spec-review", "type": "review", "backend": "claude", "tier": "deep",
                              "isolation": "direct"}],
        {"spec-review": _result("blocked", violations=["README.md"])})
    # ESC: a reviewer lifted opus -> fable twice (once on the result, once only in state.json)
    lift = [{"stage": "implement", "job": "gate-review", "attempt": 4, "wait_ms": 0,
             "escalated_from": "opus", "model": "fable"}]
    run("2026-01-09-esc-a", [{"id": "gate-review", "type": "review", "backend": "claude", "model": "opus",
                              "isolation": "direct"}],
        {"gate-review": _result("error", escalated_from="opus", retries=lift)})
    run("2026-01-10-esc-b", [{"id": "gate-review", "type": "review", "backend": "claude", "model": "opus",
                              "isolation": "direct"}],
        {"gate-review": _result("error")},
        state={"run_id": "esc-b", "jobs": {"gate-review": {"retry_exhausted": True, "escalated_from": "opus",
                                                           "retries": lift}}})
    # BELOW: one real mechanical_refactor floor failure — plus an excluded run and a harness fault
    # on the SAME key; either one counted would lift the group to 2 runs.
    mr = [{"id": "mr", "type": "mechanical_refactor", "backend": "claude", "tier": "light",
           "isolation": "worktree"}]
    run("2026-01-11-below", mr, {"mr": _result("blocked", tests_exit=1, files_changed=["pkg/m.py"])})
    run("2026-01-12-excluded", mr, {"mr": _result("blocked", tests_exit=1, files_changed=["pkg/m.py"])},
        recall_exclude=True)
    run("2026-01-13-harness", mr, {"mr": _result("error", tests_exit=1, files_changed=["pkg/m.py"],
                                                 failure_class="other")})
    _write(os.path.join(ex, "2026-01-11-below", "results", ".scope-mr.json"),
           json.dumps({"verdict": "fail", "violations": ["pkg/m.py"]}))
    # a transient retry that recovered: counted in scanned, never a signal
    run("2026-01-14-retry-ok", [{"id": "impl", "type": "implement", "backend": "claude", "tier": "standard",
                                 "isolation": "worktree"}],
        {"impl": _result("success", retries=[{"stage": "implement", "job": "impl", "attempt": 1, "wait_ms": 2000}])})


def _selftest():
    import builtins

    global _FORCE_MINI_YAML
    failures = []
    count = [0]

    def check(name, cond):
        count[0] += 1
        print(("  ok   - " if cond else "  FAIL - ") + name)
        if not cond:
            failures.append(name)

    def cands(res):
        return {tuple(c["key"]): c for c in res["candidates"]}

    tmp = tempfile.mkdtemp(prefix="cv-lessons-")
    real_open = builtins.open
    lessons_path = os.path.join(tmp, LESSONS_REL)

    def guarded_open(file, mode="r", *a, **k):
        if isinstance(file, (str, bytes, os.PathLike)) and any(c in str(mode) for c in "wax+") \
                and os.path.basename(os.fspath(file)) in ("routing-lessons.md", b"routing-lessons.md"):
            raise AssertionError("attempted write to routing-lessons.md: %r" % (file,))
        return real_open(file, mode, *a, **k)

    try:
        build_fixture(tmp)
        before = real_open(lessons_path, "rb").read()
        builtins.open = guarded_open
        try:
            res = draft(tmp)
        finally:
            builtins.open = real_open
        c = cands(res)
        K_SF = ("shared_file", "src/shared/index.ts")
        K_TF = ("type_model", "test_failure", "docs", "claude", "light")
        K_LANE = ("type_model", "scope_violation", "large_isolated", "codex", "gpt-5.5")
        K_REV = ("type_model", "scope_violation", "review", "claude", "deep")
        K_ESC = ("escalation", "review", "claude", "opus")
        K_MR = ("type_model", "test_failure", "mechanical_refactor", "claude", "light")

        print("-- signals")
        check("shared file across 2 runs -> task0_shared_file",
              K_SF in c and c[K_SF]["action"] == "task0_shared_file"
              and "`src/shared/index.ts`" in c[K_SF]["prefer"]
              and "Task 0 `shared_foundation`" in c[K_SF]["prefer"])
        check("docs on light fails its floor twice -> tier_up light → standard",
              K_TF in c and c[K_TF]["action"] == "tier_up" and "`light` → `standard`" in c[K_TF]["prefer"])
        check("codex worktree lane strays twice -> narrow_lane under lib/util",
              K_LANE in c and c[K_LANE]["action"] == "narrow_lane" and "`lib/util`" in c[K_LANE]["prefer"])
        check("direct review jobs stray twice -> force_worktree",
              K_REV in c and c[K_REV]["action"] == "force_worktree")
        check("reviewer lift opus→fable in 2 runs (result + state.json) -> review_start_rung fable",
              K_ESC in c and c[K_ESC]["action"] == "review_start_rung" and "`fable`" in c[K_ESC]["prefer"]
              and c[K_ESC]["run_count"] == 2)
        check("bullet follows the routing-lessons format with the date placeholder",
              all(re.match(r"^- \*\*YYYY-MM-DD\*\* — .+ on .+ → .+; prefer .+\. \*\(Runs: .+\.\)\*$", x["bullet"])
                  for x in res["candidates"]))
        check("evidence names run, job, reason and a summary line",
              all(e["run"] and e["job"] and e["reason"] and "summary" in e
                  for x in res["candidates"] for e in x["evidence"]))
        check("model_source says `tier` when the manifest pins no model",
              c[K_TF]["evidence"][0]["model_source"] == "tier"
              and c[K_LANE]["evidence"][0]["model_source"] == "model")
        check("evidence surfaces a -rN chain (`continues`)",
              any(e["continues"] == "2026-01-05-lane-a" for e in c[K_LANE]["evidence"]))
        check("lane_area duplicates of stronger candidates are suppressed, not re-proposed",
              not any(k[0] == "lane_area" and k[1] == "scope_violation" for k in c)
              and any(s["key"][:2] == ["lane_area", "scope_violation"] for s in res["suppressed"]))
        check("lane_area test_failure is reported unactionable, never a candidate",
              any(u["key"][:2] == ["lane_area", "test_failure"] for u in res["unactionable"]))
        check("recovered retry is counted, never a signal",
              res["scanned"]["retried_then_succeeded"] == 1
              and not any("implement" in k for k in c))
        check("counts come from records: 14 run dirs, 14 result records",
              res["scanned"]["run_dirs"] == 14 and res["scanned"]["result_records"] == 14)

        check("area: common prefix to 2 levels; top-level files = (repo root); disjoint trees = none",
              _area(["a/b/c/d.py", "a/b/c/e.py"]) == "a/b" and _area(["README.md", "CHANGELOG.md"]) == "(repo root)"
              and _area(["a/x.py", "b/y.py"]) is None and _area(["README.md", "a/x.py"]) is None)

        check("scope-gate scratch (.scope-*.json) is never evidence",
              not any(e["job"].startswith(".") for g in build(tmp)[1] for e in g["evidence"]))

        print("-- threshold / exclusions")
        check("1-run group is below threshold, not a candidate",
              K_MR not in c and any(tuple(b["key"]) == K_MR and b["run_count"] == 1 for b in res["below_threshold"]))
        check("recall_exclude run ignored (scan_failures tally)",
              res["scanned"]["excluded_by_scan_failures"].get("recall_exclude") == 1)
        check("harness fault ignored (scan_failures tally)",
              res["scanned"]["excluded_by_scan_failures"].get("harness_fault", 0) >= 1)

        print("-- possibly_covered")
        check("seed lesson (large_isolated + codex) -> possibly_covered",
              c[K_LANE]["possibly_covered"] is True and c[K_LANE]["covered_by"])
        check("docs/claude mentioned only outside ## Lessons -> not covered",
              c[K_TF]["possibly_covered"] is False)

        print("-- fingerprint")
        check("fingerprint is the hash of the grouping key", c[K_TF]["fingerprint"] == fingerprint(K_TF))

        print("-- planted failures: each guard must SEE the plant, then recover on restore")
        ex = os.path.join(tmp, EXEC_REL)

        def swap(path, old, new):
            t = real_open(path, "r", encoding="utf-8").read()
            assert old in t, (path, old)
            _write(path, t.replace(old, new))

        # (1) threshold: plant a second real run for the below-threshold key
        extra = os.path.join(ex, "2026-01-15-below-2")
        shutil.copytree(os.path.join(ex, "2026-01-11-below"), extra)
        check("plant: a 2nd mechanical_refactor run makes the group a candidate",
              K_MR in cands(draft(tmp)))
        shutil.rmtree(extra)
        check("restore: back below threshold", K_MR not in cands(draft(tmp)))
        # (2) recall_exclude
        mpath = os.path.join(ex, "2026-01-12-excluded", "manifest.yaml")
        swap(mpath, "recall_exclude: true", "recall_exclude: false")
        check("plant: recall_exclude false -> excluded run counts -> candidate", K_MR in cands(draft(tmp)))
        swap(mpath, "recall_exclude: false", "recall_exclude: true")
        check("restore: excluded again", K_MR not in cands(draft(tmp)))
        # (3) harness fault
        rpath = os.path.join(ex, "2026-01-13-harness", "results", "mr.json")
        swap(rpath, '"status": "error"', '"status": "blocked"')
        check("plant: harness fault turned blocked -> counts -> candidate", K_MR in cands(draft(tmp)))
        swap(rpath, '"status": "blocked"', '"status": "error"')
        check("restore: harness fault ignored again", K_MR not in cands(draft(tmp)))
        # (4) remove a signal's second run -> each candidate vanishes
        for key, rid in ((K_SF, "2026-01-02-sf-b"), (K_TF, "2026-01-04-tf-b"),
                         (K_REV, "2026-01-08-rev-b"), (K_ESC, "2026-01-10-esc-b")):
            src = os.path.join(ex, rid)
            hold = os.path.join(tmp, "hold-" + rid)
            shutil.move(src, hold)
            check("plant: drop %s -> %s no longer a candidate" % (rid, key[0]), key not in cands(draft(tmp)))
            shutil.move(hold, src)
            check("restore: %s back" % key[0], key in cands(draft(tmp)))
        # (5) possibly_covered
        swap(lessons_path, "`large_isolated` on **codex", "`other_type` on **codex")
        check("plant: seed lesson renamed -> LANE not covered", cands(draft(tmp))[K_LANE]["possibly_covered"] is False)
        _write(lessons_path, before.decode("utf-8"))
        check("restore: covered again", cands(draft(tmp))[K_LANE]["possibly_covered"] is True)
        # (6) --since drops the older SF run
        check("--since 2026-01-02 drops SF's first run -> below threshold",
              K_SF not in cands(draft(tmp, since="2026-01-02")))
        # (7) the menu refuses a deep-tier test failure
        g = {"signal": "type_model", "key": ("type_model", "test_failure", "implement", "claude", "deep"),
             "evidence": [], "types": ["implement"]}
        check("menu: test failures on deep have no tier_up (unactionable)", _choose_action(g)[0] is None)

        print("-- record / reviews")
        fp_tf = c[K_TF]["fingerprint"]
        builtins.open = guarded_open
        try:
            line, warn = record(tmp, fp_tf, "rejected", "noise: fixture")
            res2 = draft(tmp)
        finally:
            builtins.open = real_open
        rv = os.path.join(tmp, REVIEWS_REL)
        check("record appended one line with the candidate summary",
              len(real_open(rv).read().splitlines()) == 1 and line["candidate"]["signal"] == "type_model"
              and warn is None and line["decision"] == "rejected")
        check("rejected fingerprint is filtered from the next draft",
              K_TF not in cands(res2) and any(s["fingerprint"] == fp_tf for s in res2["skipped_reviewed"]))
        _write(rv, "")
        check("plant: remove the review line -> candidate returns", K_TF in cands(draft(tmp)))
        record(tmp, c[K_SF]["fingerprint"], "accepted", None)
        check("accepted fingerprint is skipped too (already a lesson)",
              K_SF not in cands(draft(tmp)))
        _write(rv, "")
        check("unknown fingerprint is recorded with a warning and no candidate",
              record(tmp, "0123456789abcdef", "rejected", "x")[1] is not None)
        try:
            record(tmp, "NOT-HEX", "rejected")
            ok = False
        except ValueError:
            ok = True
        check("malformed fingerprint refused", ok)

        print("-- never writes routing-lessons.md")
        check("routing-lessons.md byte-identical after draft + record",
              real_open(lessons_path, "rb").read() == before)
        try:
            _append_review(lessons_path, {"x": 1})
            ok = False
        except ValueError:
            ok = True
        check("_append_review refuses routing-lessons.md", ok and real_open(lessons_path, "rb").read() == before)
        src = real_open(os.path.abspath(__file__), "r", encoding="utf-8").read()
        writes = [m.group(0) for m in re.finditer(r"open\([^()]*(?:\([^()]*\))?[^()]*,\s*[\"'][wax+][^\"']*[\"']", src)]
        check("source: exactly two write-mode open() calls (the jsonl append + the selftest fixture writer)",
              len(writes) == 2 and any("\"a\"" in w for w in writes) and any("\"w\"" in w for w in writes))
        check("source: the append is inside _append_review and the \"w\" write only in the fixture writer",
              re.search(r"def _append_review\(.*?with open\(path, \"a\"", src, re.S) is not None
              and re.search(r"def _write\(path, text\):.*?with open\(path, \"w\"", src, re.S) is not None)
        check("source: LESSONS_REL is only ever read",
              all("LESSONS_REL" not in w for w in writes))

        print("-- YAML fallback")
        _FORCE_MINI_YAML = True
        _SIBLINGS.pop("cv_validate_for_lessons", None)
        try:
            res_mini = draft(tmp)
            _write(os.path.join(ex, "2026-01-16-unreadable", "manifest.yaml"), "- not\n- a mapping\n")
            _write(os.path.join(ex, "2026-01-16-unreadable", "results", "j.json"),
                   json.dumps(_result("blocked", violations=["z/q.md"])))
            res_bad = draft(tmp)
        finally:
            _FORCE_MINI_YAML = False
        res_full = draft(tmp)
        check("no-PyYAML path drafts the same candidates",
              sorted(x["fingerprint"] for x in res_mini["candidates"])
              == sorted(x["fingerprint"] for x in res_full["candidates"]))
        check("an unreadable manifest is counted and its job is `?`, never fatal (both parsers)",
              all(any("2026-01-16-unreadable" in m for m in r["scanned"]["manifest_unreadable"])
                  and r["scanned"]["jobs_missing_from_manifest"] == 1 for r in (res_bad, res_full)))
    finally:
        builtins.open = real_open
        _FORCE_MINI_YAML = False
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("\nSELFTEST FAILED: %d of %d case(s)" % (len(failures), count[0]))
        return 1
    print("\nSELFTEST PASSED: %d/%d" % (count[0], count[0]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
