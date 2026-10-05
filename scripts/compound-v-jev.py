#!/usr/bin/env python3
"""compound-v-jev: key-free Jev request/response layer for Compound V.

Builds System One requests, parses the vault's responses, writes metadata-only
telemetry and shadow pairs to a per-user data dir, and runs the T3 eval. It never
does network I/O and never sees the API key: the compound-v-vault plugin is the
only HTTP client. Python 3.9-safe, stdlib only.

CLI (one JSON object on stdout; exit 0 unless a usage error, which exits 2):
  build --point {t3,detect_ui,onboard_layer} --state-file F --repo R [--context hook|offline]
  parse --response-file F --repo R --mode M [--hook-budget-left-ms N] [--request-file F]
  pair --request-file F --claude-category C --backend B --t3-reason R --repo R
  eval --t3 --prepare [--corpus F] [--pairs] --repo R
  eval --t3 --report OUT --repo R
  data-dir --repo R
  --selftest

Data dir: ~/.claude/compound-v-jev/<repo-digest>/ (0700; files 0600), where <repo-digest> is
the first 16 hex of sha256 of the repo's absolute real path. It holds req/, resp/,
calls.jsonl, shadow-pairs.jsonl, eval-t3.json and the T3 hook's pending-*.json descriptors.
Every write prunes entries older than 30 days, descriptors included. Request text only ever arrives in a file, never in argv. A response body that is not a
success body is never read, so nothing from an OpenRouter error body is copied anywhere: only
the status class is recorded.
"""
import argparse
import calendar
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
import re
import stat
import sys
import tempfile
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DEFAULT = "typesafe/jev-1.13"
TOKEN_BUDGET = 32000
TOKENS_PER_CHAR = 0.25
RETENTION_S = 30 * 86400
T3_ORDER = ("unknown", "user-facing-major", "user-facing-minor", "plumbing")
STRICTNESS = {"unknown": 3, "user-facing-major": 2, "user-facing-minor": 1, "plumbing": 0}
LAYERS = ("unknown", "ui", "api", "domain", "data", "infra", "tooling", "tests", "docs")
POINTS = ("t3", "detect_ui", "onboard_layer")
MODES = ("off", "shadow", "active", "eval")
TIMEOUT_MS = {"hook": 1500, "offline": 5000}
DEFAULT_CONTEXT = {"t3": "hook", "detect_ui": "offline", "onboard_layer": "offline"}
MAX_INPUT_BYTES = 1 << 20

CALLS_FILE = "calls.jsonl"
PAIRS_FILE = "shadow-pairs.jsonl"
EVAL_MANIFEST = "eval-t3.json"
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

UNAVAILABLE_REASONS = ("no_vault", "disabled", "no_key", "egress", "timeout", "rate_limited",
                       "upstream", "credits", "auth")
ERROR_REASONS = ("schema", "bad_input")

# Key-shaped strings that must never be written or printed. Spelled in pieces so that this file
# itself never carries the literals a repository-wide grep looks for.
_KEY_PREFIX = "sk-" + "or-"
_AUTH_WORD = "Bear" + "er"
KEY_SHAPED_RE = re.compile(re.escape(_KEY_PREFIX) + "|" + _AUTH_WORD + r"\s")
MODEL_RE = re.compile(r"^[A-Za-z0-9._/:~-]{1,80}$")
HASH_RE = re.compile(r"^[0-9a-f]{16}$")
LABEL_RE = re.compile(r"^[a-z0-9_-]{1,40}$")
TOKEN_ARG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")

# --------------------------------------------------------------------------- #
# Question catalogue. Choice options are listed safest first and are never sorted.
# --------------------------------------------------------------------------- #
QUESTION_NAMES = {"t3": "category", "detect_ui": "ui", "onboard_layer": "layer"}
QUESTION_TYPES = {"t3": "choice", "detect_ui": "noul", "onboard_layer": "choice"}
INSTRUCTIONS = {
    "t3": "What kind of change does `request` describe, given `paths` and `hints`?",
    "detect_ui": ("Does any file in `files` render user-facing markup or UI "
                  "(HTML, templates, components, views)?"),
    "onboard_layer": "Which architectural layer does the directory in `directory` belong to, judging by its `paths`?",
}
ALT_WORDINGS = {
    "t3": (
        "Classify the code change asked for in `request`. `paths` are files it likely touches and "
        "`hints` are the project's taxonomy categories.",
        "Which category best fits the change that `request` asks for? Use `paths` and `hints` as "
        "supporting context only.",
    ),
    "detect_ui": (
        "Is at least one file in `files` code that produces something an end user sees, such as "
        "pages, templates, components or views?",
        "Judging by each entry's `path` and `head`, does this sample of `files` contain user interface code?",
    ),
    "onboard_layer": (
        "Given the directory name in `directory` and the files listed in `paths`, which layer of the "
        "architecture does this directory implement?",
        "Assign the directory `directory` to one architectural layer, based on the files in `paths`.",
    ),
}
NOUL_CRITERIA = {
    "detect_ui": ("Yes when at least one file renders markup or a user interface that an end user sees; "
                  "no for build scripts, documentation tooling, tests or data files."),
}
LAYER_DEFS = (
    ("unknown", "The paths do not let you place the directory in exactly one of the layers below."),
    ("ui", "The directory renders what an end user sees: pages, views, components, templates or styles."),
    ("api", "The directory is the boundary other programs call: HTTP routes, controllers, RPC handlers, "
            "command-line entry points or a public SDK surface."),
    ("domain", "The directory holds business rules and core logic that do not depend on how data is "
               "stored or shown."),
    ("data", "The directory handles storage and persistence: models, schemas, migrations, repositories "
             "or queries."),
    ("infra", "The directory describes where and how the software runs: containers, CI/CD, cloud or "
              "server configuration."),
    ("tooling", "The directory holds developer tooling: build scripts, linters, code generators or local "
                "helper scripts."),
    ("tests", "The directory holds automated tests, test fixtures or test helpers."),
    ("docs", "The directory holds documentation written for people: guides, references, examples or "
             "changelogs."),
)

_MODULES = {}


def _load(name, filename):
    """Import a sibling script by path (one source of truth), writing no bytecode."""
    if name in _MODULES:
        return _MODULES[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, filename))
    mod = importlib.util.module_from_spec(spec)
    prev = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = prev
    _MODULES[name] = mod
    return mod


def _t3_defs():
    """T3 option descriptions from compound-v-classify-request.py `_CATEGORY_DEFS`."""
    mod = _load("cv_classify_request", "compound-v-classify-request.py")
    return dict(mod._CATEGORY_DEFS)


def _redactor():
    """`redact_uncapped` from compound-v-epic-arbiter.py, or None when it cannot be loaded."""
    try:
        mod = _load("cv_epic_arbiter", "compound-v-epic-arbiter.py")
        fn = getattr(mod, "redact_uncapped", None)
        return fn if callable(fn) else None
    except Exception:  # noqa: BLE001 - a missing redactor fails closed at the caller
        return None


def catalogue_entry(point, variant=0, reverse=False, t3_defs=None):
    """One catalogue entry: {"name", "type", "instructions", "options"|"criteria"}."""
    if point not in POINTS:
        raise ValueError("unknown point")
    if variant == 0:
        instructions = INSTRUCTIONS[point]
    elif variant in (1, 2):
        instructions = ALT_WORDINGS[point][variant - 1]
    else:
        raise ValueError("unknown variant")
    entry = {"name": QUESTION_NAMES[point], "type": QUESTION_TYPES[point], "instructions": instructions}
    if point == "t3":
        defs = t3_defs if t3_defs is not None else _t3_defs()
        options = [[label, defs[label]] for label in T3_ORDER]
    elif point == "onboard_layer":
        options = [[label, desc] for label, desc in LAYER_DEFS]
    else:
        options = None
    if options is not None:
        if reverse:
            options = list(reversed(options))
        entry["options"] = options
    else:
        entry["criteria"] = NOUL_CRITERIA[point]
    return entry


def catalogue():
    """Every point's default entry."""
    return {point: catalogue_entry(point) for point in POINTS}


def catalogue_hash(point, variant=0, reverse=False, t3_defs=None):
    """First 16 hex of sha256 over the canonical JSON of one entry (options stay a list)."""
    entry = catalogue_entry(point, variant, reverse, t3_defs)
    canon = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


def questions_for(entry):
    """The wire `questions` object: a named map; Choice `criteria` keeps option order."""
    q = {"type": entry["type"], "instructions": entry["instructions"]}
    if "options" in entry:
        criteria = {}
        for label, desc in entry["options"]:
            criteria[label] = desc
        q["criteria"] = criteria
    else:
        q["criteria"] = entry["criteria"]
    return {entry["name"]: q}


# --------------------------------------------------------------------------- #
# Data dir, private writes, retention.
# --------------------------------------------------------------------------- #
def _inside(path, root):
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def data_dir(repo):
    """Resolve and create ~/.claude/compound-v-jev/<repo-digest>/ (0700) with req/ and resp/."""
    real = os.path.realpath(os.path.abspath(repo))
    digest = hashlib.sha256(real.encode("utf-8")).hexdigest()[:16]
    home = os.path.realpath(os.path.expanduser("~"))
    base = os.path.join(home, ".claude", "compound-v-jev")
    d = os.path.join(base, digest)
    if _inside(d, real):
        raise ValueError("data dir would be inside the repository")
    for p in (base, d, os.path.join(d, "req"), os.path.join(d, "resp")):
        os.makedirs(p, mode=0o700, exist_ok=True)
        os.chmod(p, 0o700)
    return d


def _now():
    return time.time()


def _ts(now=None):
    return time.strftime(TS_FMT, time.gmtime(_now() if now is None else now))


def _parse_ts(value):
    try:
        return calendar.timegm(time.strptime(value, TS_FMT))
    except Exception:  # noqa: BLE001
        return None


def _write_new_private(path, text):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o600)


def _replace_private(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def prune(dd, now=None):
    """Drop jsonl lines and req/resp files older than RETENTION_S. Unparseable lines go too.

    Also removes regular pending-*.json descriptors (left by the T3 hook in the data dir root)
    older than the cutoff. It never follows or removes a symlink among them.
    """
    cutoff = (_now() if now is None else now) - RETENTION_S
    for name in (CALLS_FILE, PAIRS_FILE):
        path = os.path.join(dd, name)
        if not os.path.isfile(path) or os.path.islink(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        keep = []
        for line in lines:
            try:
                ts = _parse_ts(json.loads(line).get("ts"))
            except Exception:  # noqa: BLE001
                ts = None
            if ts is not None and ts >= cutoff:
                keep.append(line)
        if len(keep) != len(lines):
            _replace_private(path, "".join(x + "\n" for x in keep))
    candidates = [os.path.join(dd, EVAL_MANIFEST)]
    for sub in ("req", "resp"):
        sd = os.path.join(dd, sub)
        if os.path.isdir(sd):
            candidates.extend(os.path.join(sd, n) for n in os.listdir(sd))
    for path in candidates:
        try:
            st = os.lstat(path)
        except OSError:
            continue
        if st.st_mtime < cutoff and not os.path.isdir(path):
            with contextlib.suppress(OSError):
                os.unlink(path)
    try:
        names = os.listdir(dd)
    except OSError:
        names = []
    for n in names:
        if not (n.startswith("pending-") and n.endswith(".json")):
            continue
        path = os.path.join(dd, n)
        try:
            st = os.lstat(path)
        except OSError:
            continue
        if stat.S_ISREG(st.st_mode) and st.st_mtime < cutoff:
            with contextlib.suppress(OSError):
                os.unlink(path)


def _append_jsonl(dd, name, obj, now=None):
    prune(dd, now)
    path = os.path.join(dd, name)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    if KEY_SHAPED_RE.search(line):
        raise ValueError("key-shaped value refused")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(line)
    os.chmod(path, 0o600)


def _read_json_file(path):
    with open(path, "rb") as fh:
        raw = fh.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input too large")
    return json.loads(raw.decode("utf-8"))


# --------------------------------------------------------------------------- #
# build
# --------------------------------------------------------------------------- #
class _Refused(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def _redact_value(value, redact):
    if isinstance(value, str):
        out = redact(value)
        if out is None or KEY_SHAPED_RE.search(out):
            raise _Refused("redaction")
        return out
    if isinstance(value, dict):
        res = {}
        for k, v in value.items():
            if not isinstance(k, str) or KEY_SHAPED_RE.search(k):
                raise _Refused("redaction")
            res[k] = _redact_value(v, redact)
        return res
    if isinstance(value, list):
        return [_redact_value(v, redact) for v in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise _Refused("bad_input")


def _check_state(point, state):
    if not isinstance(state, dict) or not state:
        raise _Refused("bad_input")
    if point == "t3" and not isinstance(state.get("request"), str):
        raise _Refused("bad_input")
    if point == "detect_ui":
        files = state.get("files")
        if not isinstance(files, list) or not files:
            raise _Refused("bad_input")
        for f in files:
            if not isinstance(f, dict) or not isinstance(f.get("path"), str):
                raise _Refused("bad_input")


def build_request(point, state, repo, variant=0, reverse=False, context=None, do_prune=True):
    """Redact, budget and write one request file. Returns the CLI result object."""
    try:
        _check_state(point, state)
        entry = catalogue_entry(point, variant, reverse)
        chash = catalogue_hash(point, variant, reverse)
        redact = _redactor()
        if redact is None:
            raise _Refused("redaction")
        clean = _redact_value(state, redact)
        state_text = json.dumps(clean, ensure_ascii=False)
        questions = questions_for(entry)
        estimate = (len(state_text) + len(json.dumps(questions, ensure_ascii=False))) * TOKENS_PER_CHAR
        if estimate > TOKEN_BUDGET:
            raise _Refused("bad_input")
        ctx = context or DEFAULT_CONTEXT[point]
        if ctx not in TIMEOUT_MS:
            raise _Refused("bad_input")
        dd = data_dir(repo)
        req = {
            "point": point,
            "catalogue_hash": chash,
            "model": MODEL_DEFAULT,
            "body": {"model": MODEL_DEFAULT, "state": state_text, "questions": questions},
            "timeout_ms": TIMEOUT_MS[ctx],
            "context": ctx,
            "repo": os.path.realpath(os.path.abspath(repo)),
        }
        text = json.dumps(req, ensure_ascii=False) + "\n"
        if KEY_SHAPED_RE.search(text):
            raise _Refused("redaction")
        if do_prune:
            prune(dd)
        path = os.path.join(dd, "req", uuid.uuid4().hex + ".req.json")
        _write_new_private(path, text)
        return {"status": "ok", "request_file": path}
    except _Refused as exc:
        return {"status": "error", "reason": exc.reason}
    except Exception:  # noqa: BLE001 - a broken input or environment is bad_input, never a crash
        return {"status": "error", "reason": "bad_input"}


# --------------------------------------------------------------------------- #
# parse
# --------------------------------------------------------------------------- #
def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not math.isnan(x)


def _classify_http(code):
    """(status, reason) for a non-2xx HTTP status; never looks at the body."""
    if code in (401, 403):
        return "unavailable", "auth"
    if code == 402:
        return "unavailable", "credits"
    if code == 429:
        return "unavailable", "rate_limited"
    if code in (400, 422):
        return "error", "bad_input"
    if code >= 500 or code in (524, 529):
        return "unavailable", "upstream"
    return "error", "bad_input"


def _request_for_response(resp_path):
    """The sibling request file of a vault response: <dd>/resp/<base> -> <dd>/req/<base>.req.json."""
    name = os.path.basename(resp_path)
    for suffix in (".resp.json", ".req.json"):
        if name.endswith(suffix):
            base = name[: -len(suffix)]
            break
    else:
        return None
    cand = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(resp_path))), "req", base + ".req.json")
    return cand if os.path.isfile(cand) else None


def _request_meta(req_path):
    """(point, catalogue_hash, {name: (type, [labels] or None)}) from a request file, or Nones."""
    if not req_path:
        return None, None, None
    try:
        req = _read_json_file(req_path)
    except Exception:  # noqa: BLE001
        return None, None, None
    if not isinstance(req, dict):
        return None, None, None
    point = req.get("point") if req.get("point") in POINTS else None
    chash = req.get("catalogue_hash")
    chash = chash if isinstance(chash, str) and HASH_RE.match(chash) else None
    expected = None
    body = req.get("body")
    if isinstance(body, dict) and isinstance(body.get("questions"), dict):
        expected = {}
        for name, q in body["questions"].items():
            if not isinstance(q, dict) or q.get("type") not in ("choice", "noul"):
                continue
            labels = list(q["criteria"]) if q["type"] == "choice" and isinstance(q.get("criteria"), dict) else None
            expected[name] = (q["type"], labels)
    return point, chash, expected


def _parse_answer(a, qtype, labels):
    """{type, answer, probs} for one answer, or None when its shape is wrong."""
    if not isinstance(a, dict):
        return None
    if a.get("type") is not None and qtype is not None and a.get("type") != qtype:
        return None
    qtype = qtype or a.get("type")
    if qtype == "noul":
        p = a.get("noul")
        if not _is_number(p) or p < 0 or p > 1:
            return None
        p = float(p)
        return {"type": "noul", "answer": "yes" if p >= 0.5 else "no", "probs": {"yes": p}}
    if qtype != "choice":
        return None
    raw = a.get("probabilities")
    raw = raw if isinstance(raw, dict) else {}
    probs = {}
    for label, p in raw.items():
        if not isinstance(label, str) or not _is_number(p) or p < 0 or p > 1:
            return None
        if labels is not None and label not in labels:
            continue
        if labels is None and not LABEL_RE.match(label):
            continue
        probs[label] = float(p)
    order = labels if labels is not None else sorted(probs)
    probs = {label: probs[label] for label in order if label in probs}
    choice = a.get("choice")
    if choice is None and probs:
        choice = max(probs, key=lambda k: probs[k])
    if not isinstance(choice, str):
        return None
    if labels is not None and choice not in labels:
        return None
    if labels is None and not LABEL_RE.match(choice):
        return None
    return {"type": "choice", "answer": choice, "probs": probs}


def parse_response(resp_path, request_path=None):
    """Normalise one vault response file. Error bodies are never read."""
    point, chash, expected = _request_meta(request_path or _request_for_response(resp_path))

    def result(status, reason=None, answers=None, latency=None, model=None):
        out = {"status": status}
        if reason is not None:
            out["reason"] = reason
        out.update({"point": point, "answers": answers or {}, "latency_ms": latency,
                    "model": model, "catalogue_hash": chash})
        return out

    if not os.path.isfile(resp_path):
        return result("unavailable", "no_vault")
    try:
        resp = _read_json_file(resp_path)
    except Exception:  # noqa: BLE001
        return result("error", "schema")
    if not isinstance(resp, dict):
        return result("error", "schema")
    lat = resp.get("latency_ms")
    latency = int(round(lat)) if _is_number(lat) and lat >= 0 else None
    status = resp.get("status")
    http = resp.get("http_status")
    http = http if isinstance(http, int) and not isinstance(http, bool) else None
    if status not in ("ok", "unavailable", "error"):
        return result("error", "schema", latency=latency)
    if http is not None and not 200 <= http < 300:
        s, r = _classify_http(http)
        return result(s, r, latency=latency)
    if status == "unavailable":
        reason = resp.get("reason")
        return result("unavailable", reason if reason in UNAVAILABLE_REASONS else "upstream", latency=latency)
    if status == "error":
        reason = resp.get("reason")
        return result("error", reason if reason in ERROR_REASONS else "schema", latency=latency)
    body = resp.get("body")
    if not isinstance(body, dict) or not isinstance(body.get("answers"), dict) or not body["answers"]:
        return result("error", "schema", latency=latency)
    model = body.get("model")
    model = model if isinstance(model, str) and MODEL_RE.match(model) else None
    answers = {}
    if expected:
        wanted = [(name, t, labels) for name, (t, labels) in expected.items()]
    else:
        wanted = [(name, None, None) for name in body["answers"] if isinstance(name, str) and LABEL_RE.match(name)]
    if not wanted:
        return result("error", "schema", latency=latency, model=model)
    for name, qtype, labels in wanted:
        parsed = _parse_answer(body["answers"].get(name), qtype, labels)
        if parsed is None:
            return result("error", "schema", latency=latency, model=model)
        answers[name] = parsed
    return result("ok", answers=answers, latency=latency, model=model)


def telemetry_line(res, mode, hook_budget_left_ms=None, now=None):
    """Metadata only: never the state, the request text or any header."""
    line = {"ts": _ts(now), "point": res.get("point"), "status": res["status"]}
    if res.get("reason") is not None:
        line["reason"] = res["reason"]
    answers = res.get("answers") or {}
    if answers:
        first = answers[next(iter(answers))]
        line["answer"] = first["answer"]
        line["probs"] = first["probs"]
    line["latency_ms"] = res.get("latency_ms")
    if hook_budget_left_ms is not None:
        line["hook_budget_left_ms"] = hook_budget_left_ms
    line["model"] = res.get("model")
    line["catalogue_hash"] = res.get("catalogue_hash")
    line["mode"] = mode
    return line


# --------------------------------------------------------------------------- #
# eval
# --------------------------------------------------------------------------- #
VARIANTS = (("original", 0, False), ("reversed", 0, True), ("wording1", 1, False), ("wording2", 2, False))


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))


def _label_or_none(x):
    return x if x in T3_ORDER else None


def _corpus_items(path):
    items = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("request"), str):
                raise ValueError("corpus row")
            state = {"request": row["request"], "paths": row.get("paths") or [], "hints": row.get("hints") or []}
            items.append({"id": row["id"], "source": "corpus", "state": state,
                          "t3_reason": row.get("t3_reason") if isinstance(row.get("t3_reason"), str) else None,
                          "labels": {"human": _label_or_none(row.get("human_label")),
                                     "claude": _label_or_none(row.get("claude_label")),
                                     "draft": _label_or_none(row.get("label_draft"))}})
    return items


def _pair_items(dd):
    items = []
    path = os.path.join(dd, PAIRS_FILE)
    if not os.path.isfile(path):
        return items
    req_dir = os.path.join(dd, "req")
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            try:
                row = json.loads(line)
                rf = os.path.realpath(row["request_file"])
                if not _inside(rf, os.path.realpath(req_dir)):
                    continue
                req = _read_json_file(rf)
                state = json.loads(req["body"]["state"])
            except Exception:  # noqa: BLE001 - a pair whose request is gone is skipped
                continue
            items.append({"id": "pair-%d" % (i + 1), "source": "pair", "state": state,
                          "t3_reason": row.get("t3_reason"),
                          "labels": {"human": None, "claude": _label_or_none(row.get("claude_category")),
                                     "draft": None}})
    return items


def eval_prepare(repo, corpus=None, pairs=False):
    dd = data_dir(repo)
    prune(dd)
    items = _corpus_items(corpus) if corpus else []
    if pairs:
        items.extend(_pair_items(dd))
    entries, skipped, files = [], [], []
    for item in items:
        for vname, variant, reverse in VARIANTS:
            res = build_request("t3", item["state"], repo, variant, reverse, context="offline", do_prune=False)
            if res["status"] != "ok":
                skipped.append({"id": item["id"], "variant": vname, "reason": res["reason"]})
                continue
            files.append(res["request_file"])
            entries.append({"id": item["id"], "source": item["source"], "variant": vname,
                            "request_file": res["request_file"], "t3_reason": item["t3_reason"],
                            "labels": item["labels"]})
    manifest = {"created": _ts(), "point": "t3", "model": MODEL_DEFAULT, "entries": entries, "skipped": skipped}
    _replace_private(os.path.join(dd, EVAL_MANIFEST), json.dumps(manifest, ensure_ascii=False) + "\n")
    return {"request_files": files, "skipped": len(skipped)}


def _response_for_request(req_path):
    base = os.path.basename(req_path)[: -len(".req.json")]
    resp_dir = os.path.join(os.path.dirname(os.path.dirname(req_path)), "resp")
    for name in (base + ".resp.json", base + ".req.json"):
        cand = os.path.join(resp_dir, name)
        if os.path.isfile(cand):
            return cand
    return os.path.join(resp_dir, base + ".resp.json")


def _percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    rank = max(1, int(math.ceil(q * len(sorted_vals))))
    return sorted_vals[rank - 1]


def _rate_row(name, k, n):
    if n == 0:
        return "| %s | 0/0 | n/a | n/a |" % name
    lo, hi = wilson(k, n)
    return "| %s | %d/%d | %.3f | %.3f - %.3f |" % (name, k, n, k / n, lo, hi)


def eval_report(repo, out_path):
    dd = data_dir(repo)
    prune(dd)
    mpath = os.path.join(dd, EVAL_MANIFEST)
    if not os.path.isfile(mpath):
        return {"status": "error", "reason": "no_eval"}
    manifest = _read_json_file(mpath)
    by_id = {}
    meta = {}
    outcomes = {}
    ok_answers = []
    models = set()
    latencies = []
    hashes = set()
    for e in manifest.get("entries", []):
        res = parse_response(_response_for_request(e["request_file"]), e["request_file"])
        key = res["status"] if res["status"] == "ok" else "%s/%s" % (res["status"], res.get("reason"))
        outcomes[key] = outcomes.get(key, 0) + 1
        meta.setdefault(e["id"], e)
        if e["variant"] == "original" and res.get("catalogue_hash"):
            hashes.add(res["catalogue_hash"])
        if res["status"] != "ok":
            continue
        ans = res["answers"].get("category")
        if ans is None:
            continue
        by_id.setdefault(e["id"], {})[e["variant"]] = ans["answer"]
        ok_answers.append(ans)
        if res.get("model"):
            models.add(res["model"])
        if res.get("latency_ms") is not None:
            latencies.append(res["latency_ms"])

    originals = {i: v["original"] for i, v in by_id.items() if "original" in v}
    n = len(originals)
    agree = {}
    for ref in ("human", "claude", "draft"):
        k = m = 0
        for i, a in originals.items():
            lab = meta[i]["labels"].get(ref)
            if lab is None:
                continue
            m += 1
            k += 1 if a == lab else 0
        agree[ref] = (k, m)
    inv_k = inv_n = 0
    for i, a in originals.items():
        labels = meta[i]["labels"]
        ref = labels.get("human") or labels.get("claude") or labels.get("draft")
        if ref is None:
            continue
        inv_n += 1
        inv_k += 1 if STRICTNESS[a] < STRICTNESS[ref] else 0

    def flips(variant):
        k = m = 0
        for v in by_id.values():
            if "original" in v and variant in v:
                m += 1
                k += 1 if v["original"] != v[variant] else 0
        return k, m

    any_k = any_m = 0
    for v in by_id.values():
        if "original" in v and "wording1" in v and "wording2" in v:
            any_m += 1
            any_k += 1 if (v["wording1"] != v["original"] or v["wording2"] != v["original"]) else 0

    maxp = [max(a["probs"].values()) if a["probs"] else None for a in ok_answers]
    maxp = [p for p in maxp if p is not None]
    bins = [0] * 10
    for p in maxp:
        bins[min(9, int(p * 10))] += 1
    hard = sum(1 for p in maxp if p in (0.0, 1.0))
    lat = sorted(latencies)
    usable = len(models) == 1 and n > 0
    if not models:
        gate_line = "Not usable for gating: no successful response carried a model id."
    elif len(models) > 1:
        gate_line = "Not usable for gating: the responses name more than one resolved model id."
    elif n == 0:
        gate_line = "Not usable for gating: no original request has an answer."
    else:
        gate_line = "One resolved model id across all responses; usable for gating on that id only."

    lines = [
        "# Jev T3 eval",
        "",
        "- Generated: %s by `scripts/compound-v-jev.py eval --t3 --report`." % _ts(),
        "- Requests prepared: %s. Requested model: `%s`." % (manifest.get("created"), manifest.get("model")),
        "- Resolved model id(s): %s." % (", ".join("`%s`" % m for m in sorted(models)) or "none"),
        "- Catalogue hash (original wording): %s." % (", ".join("`%s`" % h for h in sorted(hashes)) or "none"),
        "- Items with an answer to the original request (n): %d. Items prepared: %d." % (n, len(meta)),
        "- Response outcomes: %s." % (", ".join("%s %d" % (k, outcomes[k]) for k in sorted(outcomes)) or "none"),
        "- Requests skipped at prepare: %d." % len(manifest.get("skipped", [])),
        "",
        "## Agreement (Wilson 95% interval)",
        "",
        "| Reference | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("human label", *agree["human"]),
        _rate_row("Claude classifier label", *agree["claude"]),
        _rate_row("implementer draft label", *agree["draft"]),
        "",
        "## Strictness inversions",
        "",
        "Jev's answer is less strict than the reference label (human, else Claude, else draft).",
        "",
    ]
    if inv_n == 0:
        lines.append("No item has a reference label.")
    elif inv_k == 0:
        lines.append("0/%d observed; 95%% upper bound by the rule of three: 3/%d = %.3f." % (inv_n, inv_n, 3.0 / inv_n))
    else:
        lo, hi = wilson(inv_k, inv_n)
        lines.append("%d/%d observed (Wilson 95%% interval %.3f - %.3f)." % (inv_k, inv_n, lo, hi))
    lines += [
        "",
        "## Order and wording stability (Wilson 95% interval)",
        "",
        "| Flip | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("options reversed", *flips("reversed")),
        _rate_row("alternate wording 1", *flips("wording1")),
        _rate_row("alternate wording 2", *flips("wording2")),
        _rate_row("either alternate wording", any_k, any_m),
        "",
        "## Latency (measured by the vault)",
        "",
    ]
    if lat:
        lines.append("p50 %d ms, p95 %d ms over %d responses." % (_percentile(lat, 0.5), _percentile(lat, 0.95), len(lat)))
    else:
        lines.append("No measured latency.")
    lines += [
        "",
        "## Probability histogram",
        "",
        "Maximum probability per answer, all variants, 10 bins.",
        "",
        "| Bin | Answers |",
        "|---|---|",
    ]
    for b in range(10):
        hi_edge = "1.0]" if b == 9 else "%.1f)" % ((b + 1) / 10.0)
        lines.append("| [%.1f, %s | %d |" % (b / 10.0, hi_edge, bins[b]))
    lines += [
        "",
        "## Hard answers",
        "",
    ]
    if maxp:
        lines.append("%d/%d answers (%.3f) have a maximum probability of exactly 0 or 1." % (hard, len(maxp), hard / len(maxp)))
    else:
        lines.append("No answers.")
    lines += ["", "## Gating", "", gate_line, ""]
    text = "\n".join(lines)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return {"status": "ok", "report": out_path, "n": n, "usable_for_gating": usable}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _emit(obj):
    text = json.dumps(obj, ensure_ascii=False)
    if KEY_SHAPED_RE.search(text):
        text = json.dumps({"status": "error", "reason": "redaction"})
    sys.stdout.write(text + "\n")


def _token_arg(value):
    if not TOKEN_ARG_RE.match(value):
        raise argparse.ArgumentTypeError("expected a short lowercase token")
    return value


def _nonneg_int(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("expected an integer")
    if n < 0:
        raise argparse.ArgumentTypeError("expected a non-negative integer")
    return n


def _parser():
    p = argparse.ArgumentParser(prog="compound-v-jev.py", description="Key-free Jev request/response layer.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--point", required=True, choices=POINTS)
    b.add_argument("--state-file", required=True)
    b.add_argument("--repo", required=True)
    b.add_argument("--context", choices=tuple(TIMEOUT_MS))
    pr = sub.add_parser("parse")
    pr.add_argument("--response-file", required=True)
    pr.add_argument("--repo", required=True)
    pr.add_argument("--mode", required=True, choices=MODES)
    pr.add_argument("--hook-budget-left-ms", type=_nonneg_int)
    pr.add_argument("--request-file")
    pa = sub.add_parser("pair")
    pa.add_argument("--request-file", required=True)
    pa.add_argument("--claude-category", required=True, choices=T3_ORDER)
    pa.add_argument("--backend", required=True, type=_token_arg)
    pa.add_argument("--t3-reason", required=True, type=_token_arg)
    pa.add_argument("--repo", required=True)
    ev = sub.add_parser("eval")
    ev.add_argument("--t3", action="store_true", required=True)
    g = ev.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--report", metavar="OUT")
    ev.add_argument("--corpus")
    ev.add_argument("--pairs", action="store_true")
    ev.add_argument("--repo", required=True)
    dd = sub.add_parser("data-dir")
    dd.add_argument("--repo", required=True)
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--selftest"]:
        return _selftest()
    parser = _parser()
    args = parser.parse_args(argv)
    if not os.path.isdir(args.repo):
        _emit({"status": "error", "reason": "bad_input"})
        return 2
    if args.cmd == "data-dir":
        try:
            _emit({"status": "ok", "data_dir": data_dir(args.repo)})
        except Exception:  # noqa: BLE001
            _emit({"status": "error", "reason": "data_dir"})
        return 0
    if args.cmd == "build":
        try:
            state = _read_json_file(args.state_file)
        except Exception:  # noqa: BLE001
            _emit({"status": "error", "reason": "bad_input"})
            return 0
        _emit(build_request(args.point, state, args.repo, context=args.context))
        return 0
    if args.cmd == "parse":
        res = parse_response(args.response_file, args.request_file)
        try:
            _append_jsonl(data_dir(args.repo), CALLS_FILE, telemetry_line(res, args.mode, args.hook_budget_left_ms))
        except Exception:  # noqa: BLE001 - telemetry never fails the caller
            pass
        _emit(res)
        return 0
    if args.cmd == "pair":
        try:
            dd = data_dir(args.repo)
            rf = os.path.realpath(args.request_file)
            if not _inside(rf, os.path.realpath(os.path.join(dd, "req"))):
                _emit({"status": "error", "reason": "bad_input"})
                return 0
            _append_jsonl(dd, PAIRS_FILE, {"ts": _ts(), "request_file": rf, "claude_category": args.claude_category,
                                           "backend": args.backend, "t3_reason": args.t3_reason})
            _emit({"status": "ok"})
        except Exception:  # noqa: BLE001
            _emit({"status": "error", "reason": "bad_input"})
        return 0
    if args.cmd == "eval":
        if args.prepare:
            if not args.corpus and not args.pairs:
                parser.error("eval --prepare needs --corpus, --pairs or both")
            try:
                _emit(eval_prepare(args.repo, args.corpus, args.pairs))
            except Exception:  # noqa: BLE001
                _emit({"status": "error", "reason": "bad_input"})
            return 0
        try:
            _emit(eval_report(args.repo, args.report))
        except Exception:  # noqa: BLE001
            _emit({"status": "error", "reason": "bad_input"})
        return 0
    parser.error("unknown command")
    return 2


# --------------------------------------------------------------------------- #
# selftest (offline; HOME points at a throwaway dir for the whole run)
# --------------------------------------------------------------------------- #
def _run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = main(argv)
    out = buf.getvalue()
    return rc, (json.loads(out) if out.strip() else None), out


def _selftest():
    rows = []
    failures = []

    def check(name, cond):
        rows.append(name)
        if not cond:
            failures.append(name)
            print("FAIL %s" % name)

    tmp = tempfile.mkdtemp(prefix="cv-jev-selftest-")
    old_home = os.environ.get("HOME")
    os.environ["HOME"] = os.path.join(tmp, "home")
    os.makedirs(os.environ["HOME"])
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    printed = []
    try:
        # -- catalogue: safety order, one source for descriptions, stable hash.
        defs = _t3_defs()
        e = catalogue_entry("t3")
        check("catalogue t3 option order", [o[0] for o in e["options"]] == list(T3_ORDER))
        check("catalogue t3 descriptions from _CATEGORY_DEFS", all(o[1] == defs[o[0]] for o in e["options"]))
        check("catalogue hash stable", catalogue_hash("t3") == catalogue_hash("t3"))
        changed = dict(defs)
        changed["plumbing"] = changed["plumbing"] + " (edited)"
        check("catalogue hash moves with a description", catalogue_hash("t3", t3_defs=changed) != catalogue_hash("t3"))
        check("catalogue hash moves with option order", catalogue_hash("t3", reverse=True) != catalogue_hash("t3"))
        check("catalogue hash moves with wording",
              len({catalogue_hash("t3", v) for v in (0, 1, 2)}) == 3)
        check("catalogue layers", [o[0] for o in catalogue_entry("onboard_layer")["options"]] == list(LAYERS))
        check("catalogue detect_ui is one Noul named ui",
              list(questions_for(catalogue_entry("detect_ui"))) == ["ui"]
              and catalogue_entry("detect_ui")["type"] == "noul")
        check("catalogue covers every point", sorted(catalogue()) == sorted(POINTS))

        # -- build: insertion order, modes, redaction, budget.
        sf = os.path.join(tmp, "state.json")
        with open(sf, "w") as fh:
            json.dump({"request": "Tweak the lint config; password=hunter2", "paths": ["a.py"], "hints": []}, fh)
        rc, out, raw = _run_cli(["build", "--point", "t3", "--state-file", sf, "--repo", repo])
        printed.append(raw)
        check("build ok", rc == 0 and out and out.get("status") == "ok")
        rf = out["request_file"]
        with open(rf) as fh:
            text = fh.read()
        idx = [text.find('"%s":' % k) for k in T3_ORDER]
        check("build keeps option insertion order (no sort_keys)", -1 not in idx and idx == sorted(idx))
        dd = data_dir(repo)
        check("build request file 0600", (os.stat(rf).st_mode & 0o777) == 0o600)
        check("build dirs 0700", all((os.stat(p).st_mode & 0o777) == 0o700
                                     for p in (dd, os.path.join(dd, "req"), os.path.join(dd, "resp"))))
        req = json.loads(text)
        check("build request keys", list(req) == ["point", "catalogue_hash", "model", "body", "timeout_ms", "context", "repo"])
        check("build body keys", list(req["body"]) == ["model", "state", "questions"])
        check("build pins the model", req["model"] == MODEL_DEFAULT and req["body"]["model"] == MODEL_DEFAULT)
        check("build redacts state strings", "hunter2" not in text and "[REDACTED]" in text)
        check("build t3 runs in the hook context", req["context"] == "hook" and req["timeout_ms"] == 1500)
        check("build data dir is the repo digest",
              os.path.basename(dd) == hashlib.sha256(os.path.realpath(repo).encode()).hexdigest()[:16])

        def build_state(state, point="t3"):
            return build_request(point, state, repo)

        check("build unclosed private key fails closed",
              build_state({"request": "-----BEGIN PRIVATE KEY-----\nabc"}) == {"status": "error", "reason": "redaction"})
        check("build key-shaped text fails closed",
              build_state({"request": "use " + _AUTH_WORD + " auth"}).get("reason") == "redaction")
        check("build key prefix fails closed",
              build_state({"request": "key " + _KEY_PREFIX + "v1-x"}).get("reason") == "redaction")
        saved = _MODULES.pop("cv_epic_arbiter", None)
        _MODULES["cv_epic_arbiter"] = object()
        check("build without the redactor fails closed", build_state({"request": "x"}).get("reason") == "redaction")
        _MODULES.pop("cv_epic_arbiter")
        if saved is not None:
            _MODULES["cv_epic_arbiter"] = saved
        check("build over the 32k token budget is bad_input",
              build_state({"request": "word " * 26000}).get("reason") == "bad_input")
        check("build under the budget is ok", build_state({"request": "word " * 20000}).get("status") == "ok")
        check("build t3 without request is bad_input", build_state({"paths": []}).get("reason") == "bad_input")
        check("build detect_ui needs files", build_state({"x": 1}, "detect_ui").get("reason") == "bad_input")
        ok_ui = build_state({"files": [{"path": "a.html", "head": "<div>"}]}, "detect_ui")
        check("build detect_ui ok and offline", ok_ui.get("status") == "ok"
              and json.load(open(ok_ui["request_file"]))["context"] == "offline")
        with open(sf, "w") as fh:
            fh.write("not json")
        rc, out, raw = _run_cli(["build", "--point", "t3", "--state-file", sf, "--repo", repo])
        check("build bad JSON is bad_input exit 0", rc == 0 and out == {"status": "error", "reason": "bad_input"})

        # -- parse: Choice by label, Noul, error classes, error body never copied.
        base = os.path.basename(rf)[: -len(".req.json")]
        resp = os.path.join(dd, "resp", base + ".resp.json")
        body = {"id": "gen-1", "provider": "TypeSafe", "model": "typesafe/jev-1.13-20260917",
                "answers": {"category": {"type": "choice", "choice": "plumbing", "confidence": 0.9,
                                         "probabilities": {"plumbing": 0.9, "user-facing-minor": 0.05,
                                                           "unknown": 0.03, "user-facing-major": 0.02}}},
                "usage": {"input_tokens": 10, "output_tokens": 1, "cost": 0.5}}
        with open(resp, "w") as fh:
            json.dump({"status": "ok", "latency_ms": 321.4, "body": body}, fh)
        rc, out, raw = _run_cli(["parse", "--response-file", resp, "--repo", repo, "--mode", "shadow",
                                 "--hook-budget-left-ms", "700"])
        printed.append(raw)
        check("parse ok choice", out["status"] == "ok" and out["answers"]["category"]["answer"] == "plumbing")
        check("parse probs keyed by label in catalogue order",
              list(out["answers"]["category"]["probs"]) == list(T3_ORDER)
              and out["answers"]["category"]["probs"]["plumbing"] == 0.9)
        check("parse output keys", list(out) == ["status", "point", "answers", "latency_ms", "model", "catalogue_hash"])
        check("parse measured latency and resolved model",
              out["latency_ms"] == 321 and out["model"] == "typesafe/jev-1.13-20260917")
        check("parse point and hash from the sibling request",
              out["point"] == "t3" and out["catalogue_hash"] == req["catalogue_hash"])
        check("parse drops usage.cost", "cost" not in raw and "usage" not in raw)
        with open(os.path.join(dd, CALLS_FILE)) as fh:
            tlines = fh.read().splitlines()
        tl = json.loads(tlines[-1])
        check("telemetry keys exact", sorted(tl) == sorted(["ts", "point", "status", "answer", "probs", "latency_ms",
                                                             "hook_budget_left_ms", "model", "catalogue_hash", "mode"]))
        check("telemetry has no state text", "lint config" not in "".join(tlines))
        check("telemetry file 0600", (os.stat(os.path.join(dd, CALLS_FILE)).st_mode & 0o777) == 0o600)

        def parse_obj(obj, request_path=None):
            p = os.path.join(tmp, "r.resp.json")
            with open(p, "w") as fh:
                json.dump(obj, fh)
            return parse_response(p, request_path)

        ui_req = ok_ui["request_file"]
        r = parse_obj({"status": "ok", "latency_ms": 5, "body": {"model": "m", "answers": {"ui": {"type": "noul", "noul": 0.83}}}}, ui_req)
        check("parse noul yes", r["answers"] == {"ui": {"type": "noul", "answer": "yes", "probs": {"yes": 0.83}}})
        r = parse_obj({"status": "ok", "latency_ms": 5, "body": {"answers": {"ui": {"type": "noul", "noul": 0.2}}}}, ui_req)
        check("parse noul no", r["answers"]["ui"]["answer"] == "no" and r["model"] is None)
        table = {401: ("unavailable", "auth"), 403: ("unavailable", "auth"), 402: ("unavailable", "credits"),
                 429: ("unavailable", "rate_limited"), 500: ("unavailable", "upstream"),
                 502: ("unavailable", "upstream"), 503: ("unavailable", "upstream"),
                 524: ("unavailable", "upstream"), 529: ("unavailable", "upstream"),
                 400: ("error", "bad_input"), 422: ("error", "bad_input")}
        uid_key = "user" + "_id"
        for code, want in table.items():
            r = parse_obj({"status": "error", "http_status": code, "latency_ms": 9,
                           "body": {"error": {"message": "LEAKMARKER", "code": code}, uid_key: "LEAKMARKER"}}, rf)
            check("parse http %d -> %s(%s)" % (code, want[0], want[1]), (r["status"], r.get("reason")) == want)
        p = os.path.join(tmp, "e.resp.json")
        with open(p, "w") as fh:
            json.dump({"status": "error", "http_status": 400, "latency_ms": 9,
                       "body": {"error": {"message": "LEAKMARKER"}, uid_key: "user_LEAKMARKER"}}, fh)
        rc, out, raw = _run_cli(["parse", "--response-file", p, "--request-file", rf, "--repo", repo, "--mode", "shadow"])
        printed.append(raw)
        with open(os.path.join(dd, CALLS_FILE)) as fh:
            calls_text = fh.read()
        check("parse never copies an error body", "LEAKMARKER" not in raw and uid_key not in raw
              and "LEAKMARKER" not in calls_text)
        check("parse no answers is error(schema)",
              parse_obj({"status": "ok", "latency_ms": 1, "body": {"model": "m"}}, rf)["reason"] == "schema")
        check("parse unknown choice is error(schema)", parse_obj(
            {"status": "ok", "body": {"answers": {"category": {"type": "choice", "choice": "nope"}}}}, rf)["reason"] == "schema")
        check("parse prob out of range is error(schema)", parse_obj(
            {"status": "ok", "body": {"answers": {"category": {"type": "choice", "choice": "plumbing",
                                                              "probabilities": {"plumbing": 1.5}}}}}, rf)["reason"] == "schema")
        check("parse vault reason kept", parse_obj({"status": "unavailable", "reason": "egress", "latency_ms": 0}, rf)
              ["reason"] == "egress")
        check("parse unknown vault reason is not copied", parse_obj(
            {"status": "unavailable", "reason": "LEAKMARKER", "latency_ms": 0}, rf)["reason"] == "upstream")
        r = parse_obj({"status": "ok", "body": {"answers": {"category": {"type": "choice", "choice": "unknown"}}}}, rf)
        check("parse missing latency stays null", r["status"] == "ok" and r["latency_ms"] is None)
        check("parse missing response is unavailable(no_vault)",
              parse_response(os.path.join(tmp, "absent.resp.json"), rf)["reason"] == "no_vault")

        # -- pair and pruning.
        old = _now() - 31 * 86400
        with open(os.path.join(dd, PAIRS_FILE), "w") as fh:
            fh.write(json.dumps({"ts": _ts(old), "request_file": "x"}) + "\n")
            fh.write(json.dumps({"ts": _ts(_now() - 86400), "request_file": "y"}) + "\n")
        stale = os.path.join(dd, "req", "stale.req.json")
        with open(stale, "w") as fh:
            fh.write("{}")
        os.utime(stale, (old, old))
        rc, out, raw = _run_cli(["pair", "--request-file", rf, "--claude-category", "plumbing", "--backend", "claude",
                                 "--t3-reason", "demotion", "--repo", repo])
        printed.append(raw)
        with open(os.path.join(dd, PAIRS_FILE)) as fh:
            plines = [json.loads(x) for x in fh.read().splitlines()]
        check("pair ok", out == {"status": "ok"})
        check("pruning removes a 31-day-old line and keeps a 1-day-old one",
              [x["request_file"] for x in plines] == ["y", os.path.realpath(rf)])
        check("pair keys exact", list(plines[-1]) == ["ts", "request_file", "claude_category", "backend", "t3_reason"])
        check("pruning removes a 31-day-old request file", not os.path.exists(stale))
        rc, out, raw = _run_cli(["pair", "--request-file", sf, "--claude-category", "plumbing", "--backend", "claude",
                                 "--t3-reason", "demotion", "--repo", repo])
        check("pair refuses a request file outside req/", out == {"status": "error", "reason": "bad_input"})

        # -- pruning stale T3 descriptors (pending-*.json) in the data dir root.
        old_p = os.path.join(dd, "pending-old.json")
        new_p = os.path.join(dd, "pending-new.json")
        fut_p = os.path.join(dd, "pending-future.json")
        for p in (old_p, new_p, fut_p):
            with open(p, "w") as fh:
                fh.write("{}")
        now = _now()
        os.utime(old_p, (now - RETENTION_S - 60, now - RETENTION_S - 60))
        os.utime(fut_p, (now + 3600, now + 3600))
        link_p = os.path.join(dd, "pending-link.json")
        os.symlink(old_p + ".target", link_p)  # dangling on purpose
        os.utime(link_p, (now - RETENTION_S - 60, now - RETENTION_S - 60), follow_symlinks=False)
        dir_p = os.path.join(dd, "pending-dir.json")
        os.mkdir(dir_p)
        os.utime(dir_p, (now - RETENTION_S - 60, now - RETENTION_S - 60))
        prune(dd, now)
        check("prune: a pending-*.json older than 30 days is removed", not os.path.exists(old_p))
        check("prune: a fresh pending-*.json stays", os.path.exists(new_p))
        check("prune: a future-dated pending-*.json stays", os.path.exists(fut_p))
        check("prune: a pending-*.json symlink is never removed", os.path.islink(link_p))
        check("prune: a directory named pending-*.json is never removed", os.path.isdir(dir_p))
        for p in (old_p, new_p, fut_p, link_p):
            with contextlib.suppress(OSError):
                os.unlink(p)
        with contextlib.suppress(OSError):
            os.rmdir(dir_p)

        # -- eval: Wilson, rule of three, mixed models, histogram, hard share.
        lo, hi = wilson(5, 10)
        check("wilson 5/10", (round(lo, 4), round(hi, 4)) == (0.2366, 0.7634))
        lo, hi = wilson(0, 10)
        check("wilson 0/10", (round(lo, 4), round(hi, 4)) == (0.0, 0.2775))
        lo, hi = wilson(10, 10)
        check("wilson 10/10", (round(lo, 4), round(hi, 4)) == (0.7225, 1.0))
        corpus = os.path.join(tmp, "corpus.jsonl")
        with open(corpus, "w") as fh:
            for i, lab in enumerate(("plumbing", "user-facing-major", "unknown")):
                fh.write(json.dumps({"id": "c%d" % i, "request": "request %d" % i, "paths": [], "hints": [],
                                     "t3_reason": "demotion", "label_draft": lab, "label_source": "implementer-draft",
                                     "human_label": None, "claude_label": None}) + "\n")
        rc, out, raw = _run_cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--repo", repo])
        check("eval prepare writes four requests per item", rc == 0 and len(out["request_files"]) == 12)
        manifest = json.load(open(os.path.join(dd, EVAL_MANIFEST)))
        rev = [e for e in manifest["entries"] if e["variant"] == "reversed"][0]
        rtext = open(rev["request_file"]).read()
        ridx = [rtext.find('"%s":' % k) for k in reversed(T3_ORDER)]
        check("eval reversed variant reverses the options", -1 not in ridx and ridx == sorted(ridx))
        labels_of = {"c0": "plumbing", "c1": "user-facing-major", "c2": "unknown"}
        for e in manifest["entries"]:
            ans = labels_of[e["id"]]
            mdl = "typesafe/jev-1.13-20260917"
            if e["id"] == "c1" and e["variant"] == "wording2":
                mdl = "typesafe/jev-1.13-20261001"
            probs = {k: (1.0 if k == ans else 0.0) for k in T3_ORDER}
            if e["id"] == "c2":
                probs = {"unknown": 0.55, "user-facing-major": 0.25, "user-facing-minor": 0.1, "plumbing": 0.1}
            with open(_response_for_request(e["request_file"]), "w") as fh:
                json.dump({"status": "ok", "latency_ms": 300 + len(e["id"]),
                           "body": {"model": mdl, "answers": {"category": {"type": "choice", "choice": ans,
                                                                           "probabilities": probs}}}}, fh)
        report = os.path.join(tmp, "out", "report.md")
        rc, out, raw = _run_cli(["eval", "--t3", "--report", report, "--repo", repo])
        rtext = open(report).read()
        printed.append(raw)
        printed.append(rtext)
        check("eval report ok", out.get("status") == "ok" and out.get("n") == 3)
        check("eval zero inversions reports 3/n", "3/3 = 1.000" in rtext)
        check("eval mixed model ids are not usable for gating",
              "Not usable for gating" in rtext and out.get("usable_for_gating") is False)
        check("eval histogram has 10 bins", "## Probability histogram" in rtext and rtext.count("| [0.") == 10
              and "| [0.9, 1.0] |" in rtext)
        check("eval hard-answer share", "8/12 answers" in rtext)
        check("eval Wilson rows", "Wilson" in rtext and "| implementer draft label | 3/3 |" in rtext)
        # The CI anti-ruflo patterns (validate.yml:194), joined from pieces: that gate greps this
        # file too, and a literal copy of its own patterns would match it.
        anti = re.compile("|".join((
            r"tokens? " + "saved", r"token-cost (saved|savings)", "cost " + "savings:", r"saved [0-9]+ tokens",
            r"baseline ?= ?" + "1000", r"\$[0-9]+\.[0-9]+ " + "saved")), re.I)
        check("eval report has no anti-ruflo phrase", not anti.search(rtext))
        one = eval_report_single_model_check(repo, tmp)
        check("eval one model id is usable for gating", one)

        # -- nothing under the repository; no key-shaped string anywhere.
        check("nothing written under the repository", os.listdir(repo) == [])
        written = []
        for root, _dirs, names in os.walk(os.environ["HOME"]):
            for n in names:
                with open(os.path.join(root, n), encoding="utf-8", errors="replace") as fh:
                    written.append(fh.read())
        check("no key-shaped string in any output or file", not any(KEY_SHAPED_RE.search(x) for x in written + printed))
        with open(os.path.abspath(__file__), encoding="utf-8") as fh:
            src = fh.read()
        net = re.compile(r"^\s*(import|from)\s+(urllib|http|socket|ssl|requests|ftplib|smtplib|asyncio)\b", re.M)
        check("no network import in this file", not net.search(src))
        rc_usage = None
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                main(["build", "--point", "nope", "--state-file", sf, "--repo", repo])
            except SystemExit as exc:
                rc_usage = exc.code
        check("usage error exits 2", rc_usage == 2)
    except Exception as exc:  # noqa: BLE001
        failures.append("selftest crashed: %s: %s" % (type(exc).__name__, exc))
        print("FAIL selftest crashed: %s: %s" % (type(exc).__name__, exc))
    finally:
        if old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = old_home
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    if failures:
        print("selftest: %d of %d rows failed" % (len(failures), len(rows)))
        return 1
    print("selftest: %d rows ok" % len(rows))
    return 0


def eval_report_single_model_check(repo, tmp):
    """Re-point every eval response at one model id and confirm the report says it is usable."""
    dd = data_dir(repo)
    manifest = json.load(open(os.path.join(dd, EVAL_MANIFEST)))
    for e in manifest["entries"]:
        path = _response_for_request(e["request_file"])
        with open(path) as fh:
            obj = json.load(fh)
        obj["body"]["model"] = "typesafe/jev-1.13-20260917"
        with open(path, "w") as fh:
            json.dump(obj, fh)
    res = eval_report(repo, os.path.join(tmp, "out", "report-one.md"))
    return res.get("usable_for_gating") is True


if __name__ == "__main__":
    sys.exit(main())
