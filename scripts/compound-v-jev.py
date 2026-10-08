#!/usr/bin/env python3
"""compound-v-jev: key-free Jev request/response layer for Compound V.

Builds System One requests, parses the vault's responses, writes metadata-only
telemetry and shadow pairs to a per-user data dir, and runs the T3 eval. It never
does network I/O and never sees the API key: the compound-v-vault plugin is the
only HTTP client. Python 3.9-safe, stdlib only.

CLI (one JSON object on stdout; exit 0 unless a usage error, which exits 2):
  build --point {t3,detect_ui,onboard_layer} --state-file F --repo R [--context hook|offline]
  t3-request --repo R --request-env NAME --prompt-file P --context hook|offline
  parse --response-file F --repo R --mode M [--hook-budget-left-ms N] [--request-file F]
  pair --request-file F --claude-category C --backend B --t3-reason R --repo R [--claude-measure-json J]
  eval --t3 --freeze --corpus F [--protocol P] --repo R
  eval --t3 --label-claude --corpus F [--protocol P] --repo R      (live headless Claude calls)
  eval --t3 --merge-human [SHEET] --corpus F --repo R
  eval --t3 --prepare [--corpus F] [--pairs] [--protocol P] --repo R
  eval --t3 --report OUT [--protocol P] --repo R
  data-dir --repo R
  --selftest

Data dir: ~/.claude/compound-v-jev/<repo-digest>/ (0700; files 0600), where <repo-digest> is
the first 16 hex of sha256 of the repo's absolute real path. It holds req/, resp/,
calls.jsonl, shadow-pairs.jsonl, eval/ (the eval manifest and the Claude label runs) and the T3
hook's pending-*.json descriptors. Every write prunes entries older than 30 days, descriptors
included, except eval/ and the eval's own `eval-*` request and response files. Request text only
ever arrives in a file or an environment variable, never in argv, and is never written to a pair
or results line.

`t3-request` is the one T3 request builder: the prompt hook (`--context hook`) and `/v:triage`
Phase T (`--context offline`) both call it. It reads the request from the environment variable
NAME and the engine's own `t3_prompt` from P, extracts the bounded state the hook's jq used to
build, and then does what `build --point t3` does. Unless the committed config resolves
`jev.enabled` true and `jev.t3.mode` to `shadow`, it prints {"status": "off", "reason": ...}
and writes nothing. A response body that is not a success body is never read,
so nothing from an OpenRouter error body is copied anywhere: only the status class is recorded.
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
TS_FMT = "%Y-%m-%dT%H:%M:%SZ"

# The T3 eval (2026-10-08 "T3 measurement and eval" spec). Its manifest and results live in the
# data dir's `eval/` subdirectory, which the 30-day prune never enters. Its request and response
# files cannot: the vault serves only `<data dir>/req/<name>.req.json` and writes the sibling
# `resp/`, so they stay there under an `eval-` name, and the prune skips that prefix.
EVAL_DIR = "eval"
EVAL_MANIFEST = os.path.join(EVAL_DIR, "eval-t3.json")
EVAL_PREFIX = "eval-"
CLAUDE_LABELS_FILE = os.path.join(EVAL_DIR, "claude-labels.jsonl")
DEFAULT_PROTOCOL = os.path.join("docs", "superpowers", "research", "2026-10-08-jev-t3-eval-protocol.json")
DEFAULT_SHEET = os.path.join("docs", "superpowers", "research", "2026-10-08-jev-t3-labelling-sheet.md")
PROTOCOL_VERSION = 1
DIGEST_FIELDS = ("id", "request", "paths", "hints")
BASE_REPEATS = 3                 # the original wording, asked three times
CLAUDE_LABEL_RUNS = 3            # headless Claude runs per corpus row for `claude_label`
SPLIT_SEED = 20261008
MIN_HUMAN_LABELS = 80
RISK_GRID = (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99, 1.0)
SKIPPABLE_SHARE_MIN = 0.25
HUMAN_CODES = {"p": "plumbing", "m": "user-facing-minor", "M": "user-facing-major", "u": "unknown"}

# The Claude-side measure `compound-v-classify-request.py --classify-headless` prints and `pair
# --claude-measure-json` stores: a closed key set of non-negative integers or null, plus the
# resolved model id. No money field, ever.
MEASURE_KEYS = ("wall_ms", "duration_ms", "duration_api_ms", "tokens", "model")
MEASURE_INT_KEYS = ("wall_ms", "duration_ms", "duration_api_ms")
MEASURE_TOKEN_FIELDS = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
MEASURE_MAX_CHARS = 1024
CLAUDE_MODEL_RE = re.compile(r"^[A-Za-z0-9._/:\[\]~-]{1,80}$")

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
    "detect_ui": {
        "true": "At least one file renders markup or a user interface that an end user sees.",
        "false": ("No file renders anything an end user sees: build scripts, documentation tooling, "
                  "tests and data files do not count."),
    },
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
    older than the cutoff. It never follows or removes a symlink among them. It never touches the
    `eval/` subdirectory, nor a req/resp file named `eval-*`: an eval may run longer than the
    retention window, and it needs every one of its own inputs.
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
    candidates = []
    for sub in ("req", "resp"):
        sd = os.path.join(dd, sub)
        if os.path.isdir(sd):
            candidates.extend(os.path.join(sd, n) for n in os.listdir(sd) if not n.startswith(EVAL_PREFIX))
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


def build_request(point, state, repo, variant=0, reverse=False, context=None, do_prune=True, name_prefix=""):
    """Redact, budget and write one request file. Returns the CLI result object.

    `name_prefix` is `EVAL_PREFIX` for the eval's own requests, which the prune then skips."""
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
        path = os.path.join(dd, "req", name_prefix + uuid.uuid4().hex + ".req.json")
        _write_new_private(path, text)
        return {"status": "ok", "request_file": path}
    except _Refused as exc:
        return {"status": "error", "reason": exc.reason}
    except Exception:  # noqa: BLE001 - a broken input or environment is bad_input, never a crash
        return {"status": "error", "reason": "bad_input"}


# --------------------------------------------------------------------------- #
# t3-request: the T3 state read back out of the engine's own prompt
# --------------------------------------------------------------------------- #
# The two block headers `build_prompt` (compound-v-classify-request.py) writes. That module
# keeps them as literals inside `build_prompt`, so the selftest builds its fixtures with
# `build_prompt` and fails if either header stops appearing there.
T3_PATHS_HEADER = "RESOLVED FILE PATHS (may be empty or approximate):"
T3_HINTS_HEADER = "PROJECT IMPACT-TAXONOMY CATEGORIES (context only):"
T3_NO_PATHS = "(none resolved)"


def _t3_caps():
    """(request chars, paths, hints): the classify prompt's own bounds, one source of truth."""
    mod = _load("cv_classify_request", "compound-v-classify-request.py")
    return mod.MAX_REQUEST_CHARS, mod.MAX_PATHS, mod.MAX_TAXONOMY_CATEGORIES


def _t3_items(text, header):
    """The `- ` lines of the block under the LAST `header`, up to the first blank line."""
    parts = text.split("\n" + header + "\n")
    if len(parts) < 2:
        return []
    block = parts[-1].split("\n\n")[0]
    return [line[2:] for line in block.split("\n") if line.startswith("- ")]


def t3_state(request, prompt):
    """{"request", "paths", "hints"}: the bounded T3 state, as the hook's jq extracted it.

    Codepoint slices, like jq's. Paths and hints are read from the text after the LAST paths
    header (the request comes before it and is user input); `(none resolved)` is dropped from
    the paths only. A hints header that precedes the paths header yields no hints.
    """
    max_req, max_paths, max_hints = _t3_caps()
    parts = prompt.split("\n" + T3_PATHS_HEADER + "\n")
    tail = "" if len(parts) < 2 else "\n" + T3_PATHS_HEADER + "\n" + parts[-1]
    paths = [p for p in _t3_items(tail, T3_PATHS_HEADER) if p != T3_NO_PATHS][:max_paths]
    hints = _t3_items(tail, T3_HINTS_HEADER)[:max_hints]
    return {"request": request[:max_req], "paths": paths, "hints": hints}


def _utf8_text(raw):
    """Bytes as text; an invalid sequence becomes U+FFFD instead of failing the call."""
    return raw.decode("utf-8", "replace")


def _env_text(name):
    """The value of environment variable `name` as text, "" when unset."""
    value = os.environ.get(name)
    if value is None:
        return ""
    return _utf8_text(os.fsencode(value))


def t3_off_reason(repo):
    """None when the committed config asks for the T3 shadow, else the reason it is off.

    Read with the project's own resolver, so an absent config means the defaults (on, shadow)
    and `t3.mode: active` is already coerced to `shadow`. A config the loader rejects is off,
    as it is for the hook module. Warnings go to stderr, never stdout.
    """
    try:
        pc = _load("cv_project_config", "compound-v-project-config.py")
        cfg = pc.load_project_config(repo)
    except Exception as exc:  # noqa: BLE001 - a malformed config is off, never a traceback
        sys.stderr.write("compound-v-jev: config not readable, T3 shadow off: %s\n" % exc)
        return "config"
    values, warnings = pc.resolve_jev(cfg)
    for w in warnings:
        sys.stderr.write("compound-v-jev: %s\n" % w)
    if values.get("enabled") is not True:
        return "disabled"
    t3 = values.get("t3")
    if not isinstance(t3, dict) or t3.get("mode") != "shadow":
        return "t3_mode_off"
    return None


def t3_request(repo, request, prompt_file, context):
    """The `t3-request` result: off (nothing written), an error, or `build --point t3`'s result."""
    if not request.strip():
        sys.stderr.write("compound-v-jev: REFUSED: t3-request needs a non-empty request\n")
        return {"status": "error", "reason": "bad_input"}
    reason = t3_off_reason(repo)
    if reason is not None:
        return {"status": "off", "reason": reason}
    try:
        with open(prompt_file, "rb") as fh:
            raw = fh.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError("prompt too large")
        state = t3_state(request, _utf8_text(raw))
    except Exception:  # noqa: BLE001 - an unreadable prompt is bad_input, never a crash
        return {"status": "error", "reason": "bad_input"}
    return build_request("t3", state, repo, context=context)


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
# Per row: the original wording BASE_REPEATS times, each other variant once (6 calls, amendment 5).
VARIANT_REPEATS = {"original": BASE_REPEATS, "reversed": 1, "wording1": 1, "wording2": 1}
DECISION_RULE = (
    "Spec 1.5 is worth building only if (a) Jev shows zero strictness inversions against the human label, "
    "(b) Jev's agreement with the human label is not worse than Claude's (the 95% Wilson intervals overlap, "
    "or Jev's rate is higher), and (c) the share of calls Jev would decide on its own under the spec 1.5 "
    "candidate policy is at least the pinned minimum. Otherwise spec 1.5 is not built and the next step is "
    "spec 2. With fewer than the pinned number of human labels the rule is not decidable.")


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


def _majority(labels):
    """The most frequent label; a tie goes to the stricter one (`unknown` is the strictest)."""
    counts = {}
    for lab in labels:
        if lab in STRICTNESS:
            counts[lab] = counts.get(lab, 0) + 1
    if not counts:
        return None
    return max(counts, key=lambda lab: (counts[lab], STRICTNESS[lab]))


# ----- the measure (pair --claude-measure-json) ----------------------------------------------- #
def _measure_value(v):
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        raise ValueError("measure value")
    return v


def validate_measure(text):
    """The Claude-side measure as a normalised dict (every key present), or ValueError.

    A closed key set: `wall_ms`, `duration_ms`, `duration_api_ms` and the four `tokens` fields are
    non-negative integers or null; `model` is a model id or null. Absent keys are null. Anything
    else - an unknown key, a float, a string number, a nested surprise - is refused whole."""
    if not isinstance(text, str) or len(text) > MEASURE_MAX_CHARS:
        raise ValueError("measure size")
    obj = json.loads(text)
    if not isinstance(obj, dict) or not set(obj) <= set(MEASURE_KEYS):
        raise ValueError("measure keys")
    out = {k: _measure_value(obj.get(k)) for k in MEASURE_INT_KEYS}
    tokens = obj.get("tokens")
    if tokens is None:
        tokens = {}
    if not isinstance(tokens, dict) or not set(tokens) <= set(MEASURE_TOKEN_FIELDS):
        raise ValueError("measure tokens")
    out["tokens"] = {k: _measure_value(tokens.get(k)) for k in MEASURE_TOKEN_FIELDS}
    model = obj.get("model")
    if model is not None and not (isinstance(model, str) and CLAUDE_MODEL_RE.match(model)):
        raise ValueError("measure model")
    out["model"] = model
    return out


# ----- the corpus ------------------------------------------------------------------------------ #
def _corpus_rows(path):
    """The raw corpus rows, in file order, key order kept."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict) or not isinstance(row.get("id"), str) or not isinstance(row.get("request"), str):
                raise ValueError("corpus row")
            rows.append(row)
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("corpus ids")
    return rows


def _corpus_items(path):
    items = []
    for row in _corpus_rows(path):
        state = {"request": row["request"], "paths": row.get("paths") or [], "hints": row.get("hints") or []}
        items.append({"id": row["id"], "source": "corpus", "state": state,
                      "t3_reason": row.get("t3_reason") if isinstance(row.get("t3_reason"), str) else None,
                      "labels": {"human": _label_or_none(row.get("human_label")),
                                 "claude": _label_or_none(row.get("claude_label")),
                                 "draft": _label_or_none(row.get("label_draft"))}})
    return items


def _write_corpus(path, rows):
    """Rewrite the corpus atomically, one row per line, every row's key order unchanged."""
    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".tmp-corpus-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def corpus_digest(path):
    """sha256 over `id`, `request`, `paths` and `hints` of every row, in file order.

    Labels are left out on purpose: `--label-claude` and `--merge-human` rewrite them after the
    freeze, and must not invalidate it (amendment 4)."""
    h = hashlib.sha256()
    for row in _corpus_rows(path):
        sub = {k: row.get(k) for k in DIGEST_FIELDS}
        h.update(json.dumps(sub, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        h.update(b"\n")
    return "sha256:" + h.hexdigest()


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


# ----- the frozen protocol ------------------------------------------------------------------------ #
def _eval_dir(dd):
    d = os.path.join(dd, EVAL_DIR)
    os.makedirs(d, mode=0o700, exist_ok=True)
    os.chmod(d, 0o700)
    return d


def _repo_rel(repo, path):
    real_repo = os.path.realpath(os.path.abspath(repo))
    real = os.path.realpath(os.path.abspath(path))
    return os.path.relpath(real, real_repo) if _inside(real, real_repo) else real


def _protocol_frozen_part(corpus):
    """Everything the freeze pins and a later run must still match. Never the models block."""
    return {
        "protocol_version": PROTOCOL_VERSION,
        "corpus_digest": corpus_digest(corpus),
        "digest_fields": list(DIGEST_FIELDS),
        "rows": len(_corpus_rows(corpus)),
        "catalogue_hashes": {name: catalogue_hash("t3", variant, reverse) for name, variant, reverse in VARIANTS},
        "variants": [{"name": name, "repeats": VARIANT_REPEATS[name]} for name, _v, _r in VARIANTS],
        "label_claude_runs": CLAUDE_LABEL_RUNS,
        "split_seed": SPLIT_SEED,
        "thresholds": {"risk_coverage_grid": list(RISK_GRID),
                       "fit_rule": "the lowest grid threshold with zero disagreements on the fit half",
                       "skippable_share_min": SKIPPABLE_SHARE_MIN,
                       "min_human_labels": MIN_HUMAN_LABELS,
                       "hook_budget_ms": TIMEOUT_MS["hook"],
                       "offline_cap_ms": TIMEOUT_MS["offline"]},
        "decision_rule": DECISION_RULE,
    }


def _frozen_digest(frozen):
    canon = json.dumps(frozen, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _claude_requested_model():
    try:
        return _load("cv_classify_request", "compound-v-classify-request.py").resolve_claude_light_model()
    except Exception:  # noqa: BLE001
        return None


def _protocol_path(repo, protocol):
    return protocol if protocol else os.path.join(repo, DEFAULT_PROTOCOL)


def eval_freeze(repo, corpus, protocol=None):
    """Write the protocol before any call. Refuses to overwrite one that exists."""
    path = _protocol_path(repo, protocol)
    if os.path.exists(path):
        return {"status": "error", "reason": "already_frozen", "protocol": path}
    frozen = _protocol_frozen_part(corpus)
    doc = {"frozen_at": _ts(), "corpus_path": _repo_rel(repo, corpus)}
    doc.update(frozen)
    doc["frozen_digest"] = _frozen_digest(frozen)
    # The resolved ids are unknown before the first call: `--label-claude` fills Claude's, the
    # report fills Jev's. Neither is part of the frozen digest.
    doc["models"] = {"jev": {"requested": MODEL_DEFAULT, "resolved": None},
                     "claude": {"requested": _claude_requested_model(), "resolved": None}}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    return {"status": "ok", "protocol": path, "frozen_digest": doc["frozen_digest"]}


def _check_protocol(repo, protocol, corpus, required=False):
    """(protocol doc or None, None) when usable; (None, reason) when it refuses.

    An explicit `--protocol` must exist. The default path is enforced when it exists."""
    path = _protocol_path(repo, protocol)
    if not os.path.isfile(path):
        return (None, "no_protocol") if (protocol or required) else (None, None)
    try:
        doc = _read_json_file(path)
        frozen = {k: doc[k] for k in _protocol_frozen_part(corpus)}
    except Exception:  # noqa: BLE001
        return None, "protocol_unreadable"
    if doc.get("frozen_digest") != _frozen_digest(frozen):
        return None, "protocol_edited"
    now = _protocol_frozen_part(corpus)
    if now["corpus_digest"] != frozen["corpus_digest"] or now["rows"] != frozen["rows"]:
        return None, "corpus_changed"
    if now["catalogue_hashes"] != frozen["catalogue_hashes"]:
        return None, "catalogue_changed"
    if now != frozen:
        return None, "protocol_mismatch"
    doc["_path"] = path
    return doc, None


def _protocol_set_resolved(doc, side, model_id):
    """Fill `models.<side>.resolved` once. A different id later is reported, never overwritten."""
    if not doc or not model_id:
        return
    models = doc.get("models") if isinstance(doc.get("models"), dict) else {}
    entry = models.get(side) if isinstance(models.get(side), dict) else {}
    if entry.get("resolved") is not None:
        return
    entry["resolved"] = model_id
    models[side] = entry
    doc["models"] = models
    path = doc.pop("_path")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    doc["_path"] = path


# ----- labels ------------------------------------------------------------------------------------- #
def _append_eval_line(dd, name, obj):
    _eval_dir(dd)
    path = os.path.join(dd, name)
    line = json.dumps(obj, ensure_ascii=False) + "\n"
    if KEY_SHAPED_RE.search(line):
        raise ValueError("key-shaped value refused")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(line)
    os.chmod(path, 0o600)


def eval_label_claude(repo, corpus, protocol=None, runs=CLAUDE_LABEL_RUNS, timeout_s=None):
    """Run the headless Claude classifier CLAUDE_LABEL_RUNS times per row and write `claude_label`.

    The prompt is `build_prompt` over the row's own request, paths and hints: the one the hook
    classifies. Each run's outcome and measure go to `eval/claude-labels.jsonl` (no request text);
    the majority (ties to the stricter label) goes into the corpus."""
    doc, why = _check_protocol(repo, protocol, corpus)
    if why:
        return {"status": "error", "reason": why}
    cr = _load("cv_classify_request", "compound-v-classify-request.py")
    dd = data_dir(repo)
    rows = _corpus_rows(corpus)
    started = _ts()
    models = set()
    labelled = 0
    for row in rows:
        paths, hints = row.get("paths") or [], row.get("hints") or []
        prompt = cr.build_prompt(row["request"], paths, hints)
        decided = []
        for run in range(runs):
            kw = {"cwd": repo, "taxonomy_categories": hints, "prompt": prompt}
            if timeout_s is not None:
                kw["timeout_s"] = timeout_s
            res = cr.classify_headless(row["request"], paths, **kw)
            ran = res.get("backend") in ("claude", "codex") and not res.get("timed_out")
            measure = res.get("measure") if isinstance(res.get("measure"), dict) else None
            try:
                measure = validate_measure(json.dumps(measure)) if measure is not None else None
            except ValueError:
                measure = None
            if ran:
                decided.append(res.get("category"))
            if measure and measure.get("model"):
                models.add(measure["model"])
            _append_eval_line(dd, CLAUDE_LABELS_FILE, {
                "ts": _ts(), "batch": started, "id": row["id"], "run": run + 1,
                "backend": res.get("backend") if isinstance(res.get("backend"), str) else None,
                "timed_out": bool(res.get("timed_out")),
                "category": _label_or_none(res.get("category")) if ran else None,
                "measure": measure})
        row["claude_label"] = _majority(decided)
        labelled += 1 if row["claude_label"] is not None else 0
    _write_corpus(corpus, rows)
    if len(models) == 1:
        _protocol_set_resolved(doc, "claude", next(iter(models)))
    return {"status": "ok", "rows": len(rows), "labelled": labelled,
            "results": os.path.join(dd, CLAUDE_LABELS_FILE),
            "claude_models": sorted(models)}


_SHEET_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")


def eval_merge_human(repo, corpus, sheet):
    """Read the maintainer's blind sheet into `human_label`. All or nothing.

    Refused (nothing written): a label row without exactly four cells, an id twice or not in the
    corpus, a code outside `p m M u` (case-sensitive), or a corpus row missing from the sheet. An
    empty label cell leaves that row's `human_label` null."""
    rows = _corpus_rows(corpus)
    by_id = {r["id"]: r for r in rows}
    seen = {}
    with open(sheet, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s[1:-1].split("|")] if s.endswith("|") else None
        first = cells[0] if cells else s[1:].split("|")[0].strip()
        if not _SHEET_ID_RE.match(first):
            continue  # a header, a separator or the legend
        if cells is None or len(cells) != 4:
            return {"status": "error", "reason": "sheet_row", "id": first}
        if first not in by_id:
            return {"status": "error", "reason": "sheet_unknown_id", "id": first}
        if first in seen:
            return {"status": "error", "reason": "sheet_duplicate_id", "id": first}
        code = cells[3].strip("`").strip()
        if code and code not in HUMAN_CODES:
            return {"status": "error", "reason": "sheet_unknown_code", "id": first}
        seen[first] = HUMAN_CODES[code] if code else None
    missing = [r["id"] for r in rows if r["id"] not in seen]
    if missing:
        return {"status": "error", "reason": "sheet_missing_rows", "missing": len(missing), "first_missing": missing[0]}
    for r in rows:
        r["human_label"] = seen[r["id"]]
    _write_corpus(corpus, rows)
    labelled = sum(1 for r in rows if r["human_label"] is not None)
    return {"status": "ok", "rows": len(rows), "labelled": labelled}


# ----- prepare ------------------------------------------------------------------------------------ #
def _manifest_path(dd):
    _eval_dir(dd)
    return os.path.join(dd, EVAL_MANIFEST)


def eval_prepare(repo, corpus=None, pairs=False, protocol=None):
    """Write every eval request: per row the original wording BASE_REPEATS times and each other
    variant once. The order is by pass (pass 1: every row's original and variants; passes 2..n:
    the original again), and `position` (1-based) is the place in that order: position 1 is the
    batch's cold call, every later one warm, by position and not by any observed cache state."""
    doc = None
    if corpus:
        doc, why = _check_protocol(repo, protocol, corpus)
        if why:
            return {"status": "error", "reason": why}
    dd = data_dir(repo)
    prune(dd)
    items = _corpus_items(corpus) if corpus else []
    if pairs:
        items.extend(_pair_items(dd))
    plan = []
    for repeat in range(BASE_REPEATS):
        for item in items:
            for vname, variant, reverse in VARIANTS:
                if repeat < VARIANT_REPEATS[vname]:
                    plan.append((item, vname, variant, reverse, repeat + 1))
    entries, skipped, files = [], [], []
    for item, vname, variant, reverse, repeat in plan:
        res = build_request("t3", item["state"], repo, variant, reverse, context="offline", do_prune=False,
                            name_prefix=EVAL_PREFIX)
        if res["status"] != "ok":
            skipped.append({"id": item["id"], "variant": vname, "repeat": repeat, "reason": res["reason"]})
            continue
        files.append(res["request_file"])
        entries.append({"id": item["id"], "source": item["source"], "variant": vname, "repeat": repeat,
                        "position": len(entries) + 1,
                        "request_id": "%s:%s:%d" % (item["id"], vname, repeat),
                        "request_file": res["request_file"], "t3_reason": item["t3_reason"],
                        "labels": item["labels"]})
    manifest = {"created": _ts(), "point": "t3", "model": MODEL_DEFAULT,
                "corpus": os.path.realpath(corpus) if corpus else None,
                "protocol_digest": doc.get("frozen_digest") if doc else None,
                "entries": entries, "skipped": skipped}
    _replace_private(_manifest_path(dd), json.dumps(manifest, ensure_ascii=False) + "\n")
    return {"request_files": files, "skipped": len(skipped), "protocol": "checked" if doc else "none"}


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


def _lat_line(name, vals, budget=None):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return "- %s: no measured sample." % name
    line = "- %s: p50 %d ms, p95 %d ms (n = %d)" % (name, _percentile(v, 0.5), _percentile(v, 0.95), len(v))
    if budget is not None:
        k = sum(1 for x in v if x <= budget)
        line += "; %d/%d (%.3f) at or under %d ms" % (k, len(v), k / len(v), budget)
    return line + "."


def _inversions_text(k, n, who):
    if n == 0:
        return "%s: no row has both an answer and a human label." % who
    if k == 0:
        return "%s: 0/%d observed; 95%% upper bound by the rule of three: 3/%d = %.3f." % (who, n, n, 3.0 / n)
    lo, hi = wilson(k, n)
    return "%s: %d/%d observed (Wilson 95%% interval %.3f - %.3f)." % (who, k, n, lo, hi)


def _would_decide(answer, t3_reason):
    """Whether Jev's answer needs no Claude confirmation under the spec 1.5 candidate policy.

    `unknown` falls back to Claude; a demoting answer (`plumbing` or `user-facing-minor` on a
    `demotion` or `sensitive` consultation) is at best provisional and still costs the Claude call
    at bind. Anything else Jev decides on its own."""
    if answer is None or answer == "unknown":
        return False
    if (t3_reason or "unbanded") in ("demotion", "sensitive") and answer in ("plumbing", "user-facing-minor"):
        return False
    return True


def _split(ids, seed):
    order = sorted(ids, key=lambda i: hashlib.sha256(("%d:%s" % (seed, i)).encode("utf-8")).hexdigest())
    half = len(order) // 2
    return set(order[:half]), set(order[half:])


def _read_jsonl(path):
    out = []
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    return out


# ----- report ------------------------------------------------------------------------------------- #
def eval_report(repo, out_path, protocol=None):
    dd = data_dir(repo)
    prune(dd)
    mpath = os.path.join(dd, EVAL_MANIFEST)
    if not os.path.isfile(mpath):
        return {"status": "error", "reason": "no_eval"}
    manifest = _read_json_file(mpath)
    corpus = manifest.get("corpus")
    doc = None
    if corpus and os.path.isfile(corpus):
        doc, why = _check_protocol(repo, protocol, corpus)
        if why:
            return {"status": "error", "reason": why}
        if doc and manifest.get("protocol_digest") not in (None, doc.get("frozen_digest")):
            return {"status": "error", "reason": "protocol_mismatch"}
    elif protocol:
        return {"status": "error", "reason": "no_corpus"}
    # Labels are read fresh from the corpus: `--merge-human` may have run after `--prepare`.
    fresh = {}
    if corpus and os.path.isfile(corpus):
        fresh = {it["id"]: it for it in _corpus_items(corpus)}

    answers = {}       # (id, variant, repeat) -> parsed answer
    meta = {}
    outcomes = {}
    ok_answers = []
    models = set()
    hashes = set()
    cold, warm = [], []
    for e in manifest.get("entries", []):
        res = parse_response(_response_for_request(e["request_file"]), e["request_file"])
        key = res["status"] if res["status"] == "ok" else "%s/%s" % (res["status"], res.get("reason"))
        outcomes[key] = outcomes.get(key, 0) + 1
        if e["id"] not in meta:
            m = dict(e)
            if e["id"] in fresh:
                m["labels"] = fresh[e["id"]]["labels"]
                m["t3_reason"] = fresh[e["id"]]["t3_reason"]
            meta[e["id"]] = m
        if e["variant"] == "original" and res.get("catalogue_hash"):
            hashes.add(res["catalogue_hash"])
        if res["status"] != "ok":
            continue
        ans = res["answers"].get("category")
        if ans is None:
            continue
        answers[(e["id"], e["variant"], e.get("repeat", 1))] = ans
        ok_answers.append(ans)
        if res.get("model"):
            models.add(res["model"])
        if res.get("latency_ms") is not None:
            (cold if e.get("position") == 1 else warm).append(res["latency_ms"])

    ids = list(meta)
    base, base_top, consistent = {}, {}, [0, 0]
    for i in ids:
        reps = [answers[(i, "original", r)] for r in range(1, BASE_REPEATS + 1) if (i, "original", r) in answers]
        if not reps:
            continue
        base[i] = _majority([a["answer"] for a in reps])
        tops = [max(a["probs"].values()) for a in reps if a["probs"]]
        base_top[i] = min(tops) if tops else None
        if len(reps) == BASE_REPEATS:
            consistent[1] += 1
            consistent[0] += 1 if len({a["answer"] for a in reps}) == 1 else 0
    n = len(base)

    human = {i: meta[i]["labels"].get("human") for i in ids}
    claude = {i: meta[i]["labels"].get("claude") for i in ids}
    n_human = sum(1 for i in ids if human[i] is not None)
    no_human = len(ids) - n_human

    def agree(pred, ref):
        k = m = 0
        for i in ids:
            if pred.get(i) is None or ref.get(i) is None:
                continue
            m += 1
            k += 1 if pred[i] == ref[i] else 0
        return k, m

    def inversions(pred):
        k = m = 0
        for i in ids:
            if pred.get(i) is None or human[i] is None:
                continue
            m += 1
            k += 1 if STRICTNESS[pred[i]] < STRICTNESS[human[i]] else 0
        return k, m

    jev_h, cl_h, jev_cl = agree(base, human), agree(claude, human), agree(base, claude)
    inv_j, inv_c = inversions(base), inversions(claude)

    def flips(variant):
        k = m = 0
        for i in ids:
            a = answers.get((i, variant, 1))
            if a is None or base.get(i) is None:
                continue
            m += 1
            k += 1 if a["answer"] != base[i] else 0
        return k, m

    any_k = any_m = 0
    for i in ids:
        w1, w2 = answers.get((i, "wording1", 1)), answers.get((i, "wording2", 1))
        if base.get(i) is None or w1 is None or w2 is None:
            continue
        any_m += 1
        any_k += 1 if (w1["answer"] != base[i] or w2["answer"] != base[i]) else 0

    maxp = [max(a["probs"].values()) for a in ok_answers if a["probs"]]
    bins = [0] * 10
    for p in maxp:
        bins[min(9, int(p * 10))] += 1
    hard = sum(1 for p in maxp if p in (0.0, 1.0))
    usable = len(models) == 1 and n > 0
    if not models:
        gate_line = "Not usable for gating: no successful response carried a model id."
    elif len(models) > 1:
        gate_line = "Not usable for gating: the responses name more than one resolved model id."
    elif n == 0:
        gate_line = "Not usable for gating: no original request has an answer."
    else:
        gate_line = "One resolved model id across all responses; usable for gating on that id only."
    if doc and len(models) == 1:
        _protocol_set_resolved(doc, "jev", next(iter(models)))

    th = (doc or {}).get("thresholds") or {}
    seed = (doc or {}).get("split_seed", SPLIT_SEED)
    grid = th.get("risk_coverage_grid") or list(RISK_GRID)
    share_min = th.get("skippable_share_min", SKIPPABLE_SHARE_MIN)
    min_labels = th.get("min_human_labels", MIN_HUMAN_LABELS)
    hook_budget = th.get("hook_budget_ms", TIMEOUT_MS["hook"])

    labelled = [i for i in ids if base.get(i) is not None and human[i] is not None and base_top.get(i) is not None]
    fit, rep = _split(labelled, seed)

    def curve(rows, t):
        cov = [i for i in rows if base_top[i] >= t]
        err = sum(1 for i in cov if base[i] != human[i])
        return len(cov), err

    theta = None
    for t in sorted(grid):
        c, err = curve(fit, t)
        if c > 0 and err == 0:
            theta = t
            break

    sk_k = sum(1 for i in base if _would_decide(base[i], meta[i].get("t3_reason")))

    shadow_calls = [c for c in _read_jsonl(os.path.join(dd, CALLS_FILE))
                    if c.get("mode") == "shadow" and c.get("point") == "t3"]
    shadow_ok = [c.get("latency_ms") for c in shadow_calls if c.get("status") == "ok"]
    pairs_measures = []
    for p in _read_jsonl(os.path.join(dd, PAIRS_FILE)):
        try:
            pairs_measures.append(validate_measure(json.dumps(p.get("claude_measure"))))
        except (ValueError, TypeError):
            continue
    label_runs = []
    for r in _read_jsonl(os.path.join(dd, CLAUDE_LABELS_FILE)):
        try:
            label_runs.append(validate_measure(json.dumps(r.get("measure"))))
        except (ValueError, TypeError):
            continue
    trusted_runs = [m for m in label_runs if m["wall_ms"] is not None]

    pm = (doc or {}).get("models") or {}
    lines = [
        "# Jev T3 eval",
        "",
        "- Generated: %s by `scripts/compound-v-jev.py eval --t3 --report`." % _ts(),
        "- Frozen protocol: %s." % ("`%s` (%s)" % (_repo_rel(repo, doc["_path"]), doc.get("frozen_digest"))
                                   if doc else "none; the decision rule below is not applied"),
        "- Requests prepared: %s. Requested model: `%s`." % (manifest.get("created"), manifest.get("model")),
        "- Resolved Jev model id(s) in the responses: %s." % (", ".join("`%s`" % m for m in sorted(models)) or "none"),
        "- Models pinned by the protocol: Jev %s, Claude %s." % (
            json.dumps((pm.get("jev") or {}).get("resolved")), json.dumps((pm.get("claude") or {}).get("resolved"))),
        "- Catalogue hash (original wording): %s." % (", ".join("`%s`" % h for h in sorted(hashes)) or "none"),
        "- Items with an answer to the original wording (n): %d. Items prepared: %d." % (n, len(ids)),
        "- Rows with a human label: %d; rows without one, excluded from agreement and inversions: %d." % (n_human, no_human),
        "- Response outcomes: %s." % (", ".join("%s %d" % (k, outcomes[k]) for k in sorted(outcomes)) or "none"),
        "- Requests skipped at prepare: %d." % len(manifest.get("skipped", [])),
        "",
        "## Agreement with the human label (Wilson 95% interval)",
        "",
        "Jev's answer is the majority of its %d answers to the original wording (a tie goes to the stricter "
        "label). Claude's is `claude_label`, the majority of %d headless runs." % (BASE_REPEATS, CLAUDE_LABEL_RUNS),
        "",
        "| Pair | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("Jev vs human", *jev_h),
        _rate_row("Claude vs human", *cl_h),
        _rate_row("Jev vs Claude", *jev_cl),
        "",
        "## Strictness inversions",
        "",
        "An answer less strict than the human label. Rows without a human label are not counted.",
        "",
        "- " + _inversions_text(inv_j[0], inv_j[1], "Jev"),
        "- " + _inversions_text(inv_c[0], inv_c[1], "Claude"),
        "",
        "## Self-consistency over %d repeats" % BASE_REPEATS,
        "",
        "| Rows | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("all %d answers give the same label" % BASE_REPEATS, *consistent),
        "",
        "## Order and wording stability (Wilson 95% interval)",
        "",
        "Each variant's label against the majority label of the original wording, compared by label.",
        "",
        "| Flip | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("options reversed", *flips("reversed")),
        _rate_row("alternate wording 1", *flips("wording1")),
        _rate_row("alternate wording 2", *flips("wording2")),
        _rate_row("either alternate wording", any_k, any_m),
        "",
        "## Probability histogram",
        "",
        "Maximum probability per answer, all variants and repeats, 10 bins.",
        "",
        "| Bin | Answers |",
        "|---|---|",
    ]
    for b in range(10):
        hi_edge = "1.0]" if b == 9 else "%.1f)" % ((b + 1) / 10.0)
        lines.append("| [%.1f, %s | %d |" % (b / 10.0, hi_edge, bins[b]))
    lines += ["", "## Hard answers", ""]
    if maxp:
        lines.append("%d/%d answers (%.3f) have a maximum probability of exactly 0 or 1." % (hard, len(maxp), hard / len(maxp)))
    else:
        lines.append("No answers.")
    lines += [
        "",
        "## Risk and coverage",
        "",
        "A row is covered at threshold t when the lowest of its original-wording top probabilities is at least t. "
        "Rows with a human label are split in two halves by a fixed seed (%d): the threshold is fitted on the "
        "first (the lowest grid value with zero disagreements) and reported on the second." % seed,
        "",
        "| t | fit half: covered | fit half: disagreements | report half: covered | report half: disagreements |",
        "|---|---|---|---|---|",
    ]
    for t in grid:
        fc, fe = curve(fit, t)
        rc, re_ = curve(rep, t)
        lines.append("| %.2f | %d/%d | %d/%d | %d/%d | %d/%d |" % (t, fc, len(fit), fe, fc, rc, len(rep), re_, rc))
    lines.append("")
    if theta is None:
        lines.append("No grid threshold has zero disagreements on the fit half (n = %d)." % len(fit))
    else:
        rc, re_ = curve(rep, theta)
        lines += ["Fitted threshold %.2f, on the report half:" % theta, "",
                  "| Report half | k/n | rate | 95% Wilson interval |", "|---|---|---|---|",
                  _rate_row("covered", rc, len(rep)), _rate_row("disagreements among covered", re_, rc)]
    lines += [
        "",
        "## Calls Jev would decide",
        "",
        "Under the spec 1.5 candidate policy Jev decides on its own unless it answers `unknown` or demotes "
        "(`plumbing` or `user-facing-minor` on a `demotion` or `sensitive` consultation, which stays provisional "
        "until Claude confirms it). This share is of the Claude classify calls spec 1.5 could actually skip.",
        "",
        "| Share | k/n | rate | 95% Wilson interval |",
        "|---|---|---|---|",
        _rate_row("Jev decides alone", sk_k, len(base)),
        "",
        "## Latency",
        "",
        "Jev, from the vault's own `latency_ms`; only `ok` responses are samples. The eval's requests run in "
        "the offline context (cap %d ms); a hook call has %d ms. A 429 retry inside the vault is part of the "
        "latency it reports. Cold and warm are by position in the batch, not by an observed cache state."
        % (TIMEOUT_MS["offline"], hook_budget),
        "",
        _lat_line("Jev, eval batch, first call (cold)", cold, hook_budget),
        _lat_line("Jev, eval batch, later calls (warm)", warm, hook_budget),
        "- Jev, eval batch, non-ok responses: %d." % sum(v for k, v in outcomes.items() if k != "ok"),
        _lat_line("Jev, live shadow calls (the hook path, cold)", shadow_ok, hook_budget),
        "- Jev, live shadow calls, non-ok: %d." % sum(1 for c in shadow_calls if c.get("status") != "ok"),
        "",
        "Claude, the headless classify: `wall_ms` is the whole process (what the hook waits for), "
        "`duration_api_ms` the API time. Token counts are `usage`, the main loop only. A run whose result "
        "was not trusted is not a sample.",
        "",
        _lat_line("Claude wall_ms, label runs", [m["wall_ms"] for m in trusted_runs]),
        _lat_line("Claude duration_api_ms, label runs", [m["duration_api_ms"] for m in trusted_runs]),
        _lat_line("Claude wall_ms, live shadow pairs", [m["wall_ms"] for m in pairs_measures]),
        "- Claude label runs not measured (untrusted, failed or timed out): %d." % (len(label_runs) - len(trusted_runs)),
    ]
    for f in MEASURE_TOKEN_FIELDS:
        v = sorted(m["tokens"][f] for m in trusted_runs if m["tokens"][f] is not None)
        lines.append("- Claude %s per call: %s." % (
            f, "p50 %d, p95 %d (n = %d)" % (_percentile(v, 0.5), _percentile(v, 0.95), len(v)) if v else "no sample"))

    lines += ["", "## Decision", "", DECISION_RULE, ""]
    decidable = False
    if doc is None:
        lines.append("Not decidable: no frozen protocol.")
    elif n_human < min_labels:
        lines.append("Not decidable: %d human labels; the rule needs %d." % (n_human, min_labels))
    else:
        decidable = True
        a = inv_j[1] > 0 and inv_j[0] == 0
        jl, jh = wilson(*jev_h) if jev_h[1] else (0.0, 0.0)
        cl, ch = wilson(*cl_h) if cl_h[1] else (0.0, 0.0)
        b = jev_h[1] > 0 and cl_h[1] > 0 and (jl <= ch and cl <= jh or jev_h[0] / jev_h[1] > cl_h[0] / cl_h[1])
        share = sk_k / len(base) if base else 0.0
        c = share >= share_min
        lines += [
            "- (a) zero strictness inversions for Jev: %s." % ("met" if a else "not met"),
            "- (b) Jev's agreement not worse than Claude's: %s." % ("met" if b else "not met"),
            "- (c) share Jev decides alone %.3f against the pinned minimum %.2f: %s." % (
                share, share_min, "material" if c else "not material"),
            "",
            "Verdict: %s" % ("build spec 1.5." if (a and b and c) else "do not build spec 1.5; the next step is spec 2."),
        ]
    lines += ["", "## Gating", "", gate_line, ""]
    text = "\n".join(lines)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return {"status": "ok", "report": out_path, "n": n, "usable_for_gating": usable, "decidable": decidable,
            "human_labels": n_human}


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
    # The request text has no argv form: only the NAME of the variable that holds it. The
    # context is required, so no caller inherits the hook's 1,500 ms cap by omission. No
    # abbreviations: `--request` must never be read as `--request-env`.
    tr = sub.add_parser("t3-request", allow_abbrev=False)
    tr.add_argument("--repo", required=True)
    tr.add_argument("--request-env", required=True, metavar="NAME")
    tr.add_argument("--prompt-file", required=True)
    tr.add_argument("--context", required=True, choices=tuple(TIMEOUT_MS))
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
    # Optional: the headless Claude classify's measure as compact JSON (numbers, null and a model id;
    # never request text). The Task route has none and omits it.
    pa.add_argument("--claude-measure-json", metavar="JSON")
    ev = sub.add_parser("eval", allow_abbrev=False)
    ev.add_argument("--t3", action="store_true", required=True)
    g = ev.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true", help="write the frozen protocol before any call")
    g.add_argument("--label-claude", action="store_true", help="headless Claude labels (live calls)")
    g.add_argument("--merge-human", nargs="?", const=DEFAULT_SHEET, metavar="SHEET",
                   help="read the blind labelling sheet into human_label")
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--report", metavar="OUT")
    ev.add_argument("--corpus")
    ev.add_argument("--pairs", action="store_true")
    ev.add_argument("--protocol", help="frozen protocol path (default: %s under --repo)" % DEFAULT_PROTOCOL)
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
    if args.cmd == "t3-request":
        _emit(t3_request(args.repo, _env_text(args.request_env), args.prompt_file, args.context))
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
            line = {"ts": _ts(), "request_file": rf, "claude_category": args.claude_category,
                    "backend": args.backend, "t3_reason": args.t3_reason}
            if args.claude_measure_json is not None:
                # Validated whole; a malformed measure refuses the line rather than storing junk.
                line["claude_measure"] = validate_measure(args.claude_measure_json)
            _append_jsonl(dd, PAIRS_FILE, line)
            _emit({"status": "ok"})
        except Exception:  # noqa: BLE001
            _emit({"status": "error", "reason": "bad_input"})
        return 0
    if args.cmd == "eval":
        needs_corpus = args.freeze or args.label_claude or args.merge_human is not None
        if needs_corpus and not args.corpus:
            parser.error("this eval mode needs --corpus")
        try:
            if args.freeze:
                _emit(eval_freeze(args.repo, args.corpus, args.protocol))
            elif args.label_claude:
                _emit(eval_label_claude(args.repo, args.corpus, args.protocol))
            elif args.merge_human is not None:
                sheet = args.merge_human
                if not os.path.isabs(sheet) and not os.path.isfile(sheet):
                    sheet = os.path.join(args.repo, sheet)
                _emit(eval_merge_human(args.repo, args.corpus, sheet))
            elif args.prepare:
                if not args.corpus and not args.pairs:
                    parser.error("eval --prepare needs --corpus, --pairs or both")
                _emit(eval_prepare(args.repo, args.corpus, args.pairs, args.protocol))
            else:
                _emit(eval_report(args.repo, args.report, args.protocol))
        except SystemExit:
            raise
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

        def noul_criteria_shape_ok(q):
            """A Noul `criteria` is absent or an object keyed by a subset of true/false with text values."""
            if q.get("type") != "noul" or "criteria" not in q:
                return True
            crit = q["criteria"]
            return (isinstance(crit, dict) and set(crit) <= {"true", "false"}
                    and all(isinstance(v, str) and v.strip() for v in crit.values()))

        wire = [qq for p in POINTS for v in (0, 1, 2) for qq in questions_for(catalogue_entry(p, v)).values()]
        check("catalogue Noul criteria are a true/false object on the wire",
              any(qq["type"] == "noul" for qq in wire) and all(noul_criteria_shape_ok(qq) for qq in wire))
        check("Noul criteria shape check rejects the string form",
              not noul_criteria_shape_ok({"type": "noul", "criteria": "Yes when ...; no for ..."}))

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

        # -- pair with the Claude-side measure (optional, validated, never request text).
        measure = {"wall_ms": 9900, "duration_ms": 6168, "duration_api_ms": 2360,
                   "tokens": {"input_tokens": 2, "output_tokens": 6, "cache_read_input_tokens": 0,
                              "cache_creation_input_tokens": 53136},
                   "model": "claude-sonnet-4-5-20250929"}
        rc, out, raw = _run_cli(["pair", "--request-file", rf, "--claude-category", "plumbing", "--backend", "claude",
                                 "--t3-reason", "demotion", "--repo", repo,
                                 "--claude-measure-json", json.dumps(measure, separators=(",", ":"))])
        with open(os.path.join(dd, PAIRS_FILE)) as fh:
            plines = [json.loads(x) for x in fh.read().splitlines()]
        check("pair with a measure ok", out == {"status": "ok"})
        check("pair with a measure: six keys, the measure stored beside the Claude category",
              list(plines[-1]) == ["ts", "request_file", "claude_category", "backend", "t3_reason", "claude_measure"]
              and plines[-1]["claude_measure"] == measure)
        rc, out, raw = _run_cli(["pair", "--request-file", rf, "--claude-category", "plumbing", "--backend", "codex",
                                 "--t3-reason", "demotion", "--repo", repo,
                                 "--claude-measure-json", json.dumps({"wall_ms": 4100})])
        with open(os.path.join(dd, PAIRS_FILE)) as fh:
            last = json.loads(fh.read().splitlines()[-1])
        check("pair: a partial measure (codex: wall_ms only) is stored with every other field null",
              last["claude_measure"]["wall_ms"] == 4100 and last["claude_measure"]["model"] is None
              and all(v is None for v in last["claude_measure"]["tokens"].values()))
        n_before = len(plines) + 1
        bad_measures = [
            "not json", json.dumps([1]), json.dumps({"wall_ms": -1}), json.dumps({"wall_ms": 1.5}),
            json.dumps({"wall_ms": "12"}), json.dumps({"wall_ms": True}), json.dumps({"cost": 1}),
            json.dumps({"total_cost_usd": 0.1}), json.dumps({"tokens": {"input_tokens": 1, "x": 2}}),
            json.dumps({"model": "has space"}), json.dumps({"model": "x" * 2000}),
            json.dumps({"tokens": "lots"})]
        refused = []
        for bm in bad_measures:
            rc, out, raw = _run_cli(["pair", "--request-file", rf, "--claude-category", "plumbing", "--backend",
                                     "claude", "--t3-reason", "demotion", "--repo", repo, "--claude-measure-json", bm])
            refused.append(out == {"status": "error", "reason": "bad_input"})
        with open(os.path.join(dd, PAIRS_FILE)) as fh:
            n_after = len(fh.read().splitlines())
        check("pair refuses every malformed measure as bad_input", all(refused))
        check("...and a refused measure writes no pair line", n_after == n_before)
        with open(os.path.join(dd, PAIRS_FILE)) as fh:
            ptext = fh.read()
        check("no request text in any pair line", "lint config" not in ptext and "hunter2" not in ptext)

        # -- the prune leaves the eval's own files alone.
        ev_req = os.path.join(dd, "req", EVAL_PREFIX + "old.req.json")
        ev_resp = os.path.join(dd, "resp", EVAL_PREFIX + "old.resp.json")
        plain_req = os.path.join(dd, "req", "plainold.req.json")
        os.makedirs(os.path.join(dd, EVAL_DIR), exist_ok=True)
        ev_man = os.path.join(dd, EVAL_MANIFEST)
        for p in (ev_req, ev_resp, plain_req, ev_man):
            with open(p, "w") as fh:
                fh.write("{}")
            os.utime(p, (old, old))
        prune(dd)
        check("prune keeps a 31-day-old eval-* request and response file",
              os.path.exists(ev_req) and os.path.exists(ev_resp))
        check("prune keeps a 31-day-old file under eval/", os.path.exists(ev_man))
        check("prune still removes a 31-day-old ordinary request file", not os.path.exists(plain_req))
        for p in (ev_req, ev_resp, ev_man):
            os.unlink(p)

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

        # -- t3-request: the hook's jq extraction, ported; the config gate; request only in env.
        st_rows = _t3_request_rows(tmp, repo, printed)
        for name, cond in st_rows:
            check(name, cond)

        # -- eval: Wilson, rule of three, mixed models, histogram, hard share.
        lo, hi = wilson(5, 10)
        check("wilson 5/10", (round(lo, 4), round(hi, 4)) == (0.2366, 0.7634))
        lo, hi = wilson(0, 10)
        check("wilson 0/10", (round(lo, 4), round(hi, 4)) == (0.0, 0.2775))
        lo, hi = wilson(10, 10)
        check("wilson 10/10", (round(lo, 4), round(hi, 4)) == (0.7225, 1.0))
        for name, cond in _eval_rows(tmp, repo, printed):
            check(name, cond)

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


def _t3_request_rows(tmp, repo, printed):
    """Selftest rows for `t3_state` and the `t3-request` subcommand, as (name, passed) pairs."""
    import subprocess
    rows = []
    cr = _load("cv_classify_request", "compound-v-classify-request.py")
    max_req, max_paths, max_hints = _t3_caps()
    rows.append(("t3-request caps come from compound-v-classify-request.py",
                 (max_req, max_paths, max_hints) == (cr.MAX_REQUEST_CHARS, cr.MAX_PATHS,
                                                     cr.MAX_TAXONOMY_CATEGORIES)))
    plain = cr.build_prompt("x", ["a.py"], ["legal_copy"])
    rows.append(("build_prompt still writes both headers t3_state reads",
                 ("\n%s\n" % T3_PATHS_HEADER) in plain and ("\n%s\n" % T3_HINTS_HEADER) in plain))

    # A request that carries both headers itself (user input), and straddles the 2,000 cap
    # with a two-byte character: the LAST paths header wins and the slice is by codepoint.
    inject = ("Add a retry.\n%s\n- fake/inject.py\n\n%s\n- fake_hint\n\n" % (T3_PATHS_HEADER, T3_HINTS_HEADER))
    req_a = inject + "word " * ((max_req - len(inject) - 10) // 5)
    req_a = req_a + "é" * (max_req + 40 - len(req_a))
    st = t3_state(req_a, cr.build_prompt(req_a, ["src/a.py", "src/b.py"], ["legal_copy", "pii"]))
    rows.append(("t3_state keys in the hook's order", list(st) == ["request", "paths", "hints"]))
    rows.append(("t3_state caps the request by codepoint",
                 st["request"] == req_a[:max_req] and len(st["request"]) == max_req
                 and st["request"].endswith("é")))
    rows.append(("t3_state reads the LAST paths header, not one inside the request",
                 st["paths"] == ["src/a.py", "src/b.py"] and st["hints"] == ["legal_copy", "pii"]))
    st = t3_state("r", cr.build_prompt("r", [], None))
    rows.append(("t3_state drops (none resolved) and has no hints without a taxonomy",
                 st == {"request": "r", "paths": [], "hints": []}))
    many = ("REQUEST:\nr\n\n%s\n- %s\n%s\n\n%s\n- %s\n%s\n\nReply." % (
        T3_PATHS_HEADER, T3_NO_PATHS, "\n".join("- p%d" % i for i in range(max_paths + 5)),
        T3_HINTS_HEADER, T3_NO_PATHS, "\n".join("- h%d" % i for i in range(max_hints + 5))))
    st = t3_state("r", many)
    rows.append(("t3_state caps paths after dropping (none resolved)",
                 st["paths"] == ["p%d" % i for i in range(max_paths)]))
    rows.append(("t3_state keeps (none resolved) in hints and caps them",
                 len(st["hints"]) == max_hints and st["hints"][0] == T3_NO_PATHS))
    swapped = "REQUEST:\nr\n\n%s\n- h1\n\n%s\n- p1\n\nReply." % (T3_HINTS_HEADER, T3_PATHS_HEADER)
    rows.append(("t3_state: a hints block before the paths header yields no hints",
                 t3_state("r", swapped) == {"request": "r", "paths": ["p1"], "hints": []}))
    long_paths = ["src/dir%02d/%s.py" % (i, "segment-" * 16) for i in range(max_paths)]
    long_hints = ["hint%02d %s" % (i, "kind " * 13) for i in range(max_hints)]
    cut = cr.build_prompt("word " * 400, long_paths, long_hints)
    st = t3_state("r", cut)
    rows.append(("t3_state tolerates a prompt cut by the 8,000-char ceiling",
                 len(cut) <= cr.MAX_PROMPT_CHARS and st["paths"] == long_paths
                 and 0 < len(st["hints"]) < max_hints
                 and st["hints"][:-1] == long_hints[:len(st["hints"]) - 1]))

    # The subcommand. HOME is the selftest sandbox; the request travels only in the env.
    env_name = "CV_JEV_SELFTEST_REQ"
    pf = os.path.join(tmp, "t3-prompt.txt")
    request = "Add a retry loop to the uploader in src/a.py MARKER-T3REQ"
    prompt = cr.build_prompt(request, ["src/a.py"], ["legal_copy"])
    with open(pf, "w", encoding="utf-8") as fh:
        fh.write(prompt)
    old_env = os.environ.get(env_name)
    os.environ[env_name] = request
    try:
        def run(argv, target=repo):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                rc, out, raw = _run_cli(["t3-request", "--repo", target, "--request-env", env_name,
                                         "--prompt-file", pf] + argv)
            printed.append(raw)
            return rc, out, raw, err.getvalue()

        def req_of(out):
            with open(out["request_file"], encoding="utf-8") as fh:
                return json.load(fh)

        rc, out, raw, _err = run(["--context", "offline"])
        ok = rc == 0 and isinstance(out, dict) and out.get("status") == "ok"
        rows.append(("t3-request prints what build --point t3 prints", ok and sorted(out) == ["request_file", "status"]))
        req = req_of(out) if ok else {}
        rows.append(("t3-request offline context is 5,000 ms",
                     req.get("context") == "offline" and req.get("timeout_ms") == TIMEOUT_MS["offline"]))
        rows.append(("t3-request state equals t3_state of the env request and the prompt file",
                     ok and req["body"]["state"] == json.dumps(t3_state(request, prompt), ensure_ascii=False)))
        rc, out, raw, _err = run(["--context", "hook"])
        req = req_of(out) if rc == 0 and out.get("status") == "ok" else {}
        rows.append(("t3-request hook context is 1,500 ms",
                     req.get("context") == "hook" and req.get("timeout_ms") == TIMEOUT_MS["hook"]))
        usage = None
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                main(["t3-request", "--repo", repo, "--request-env", env_name, "--prompt-file", pf])
            except SystemExit as exc:
                usage = exc.code
        rows.append(("t3-request without --context is a usage error", usage == 2))
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                usage = None
                main(["t3-request", "--repo", repo, "--request", request, "--prompt-file", pf,
                      "--context", "hook"])
            except SystemExit as exc:
                usage = exc.code
        rows.append(("t3-request has no argv form for the request text", usage == 2))
        os.environ[env_name] = "  \n "
        rc, out, raw, err = run(["--context", "hook"])
        rows.append(("t3-request refuses an empty request",
                     rc == 0 and out == {"status": "error", "reason": "bad_input"} and "REFUSED" in err))
        del os.environ[env_name]
        rc, out, raw, err = run(["--context", "hook"])
        rows.append(("t3-request refuses an unset request variable",
                     out == {"status": "error", "reason": "bad_input"}))
        os.environ[env_name] = request
        rc, out, raw, err = run(["--context", "hook", "--prompt-file", os.path.join(tmp, "absent.txt")])
        rows.append(("t3-request with an unreadable prompt is bad_input",
                     out == {"status": "error", "reason": "bad_input"}))

        # The config gate, in a repo of its own (the main repo must stay empty).
        crepo = os.path.join(tmp, "crepo")
        os.makedirs(os.path.join(crepo, ".claude"))
        home = os.path.realpath(os.path.expanduser("~"))
        cdd = os.path.join(home, ".claude", "compound-v-jev",
                           hashlib.sha256(os.path.realpath(crepo).encode("utf-8")).hexdigest()[:16])

        def gate(cfg_text):
            with open(os.path.join(crepo, ".claude", "compound-v.json"), "w") as fh:
                fh.write(cfg_text)
            return run(["--context", "offline"], crepo)

        rc, out, raw, err = gate(json.dumps({"jev": {"enabled": False}}))
        rows.append(("t3-request is off when jev.enabled is false",
                     rc == 0 and out == {"status": "off", "reason": "disabled"}))
        rc, out, raw, err = gate(json.dumps({"jev": {"t3": {"mode": "off"}}}))
        rows.append(("t3-request is off when jev.t3.mode is off",
                     rc == 0 and out == {"status": "off", "reason": "t3_mode_off"}))
        rc, out, raw, err = gate("{not json")
        rows.append(("t3-request is off on a malformed config, with no traceback",
                     rc == 0 and out == {"status": "off", "reason": "config"} and "Traceback" not in err))
        rows.append(("t3-request off writes nothing: no data dir for that repo", not os.path.exists(cdd)))
        rc, out, raw, err = gate(json.dumps({"jev": {"t3": {"mode": "active"}}}))
        rows.append(("t3-request coerces t3.mode active to shadow, warning on stderr only",
                     rc == 0 and out.get("status") == "ok" and "1.5" in err and "1.5" not in raw
                     and len(raw.strip().splitlines()) == 1))

        # A real process: its argv never holds the request, and the request still arrives.
        argv = [sys.executable, "-B", os.path.abspath(__file__), "t3-request", "--repo", repo,
                "--request-env", env_name, "--prompt-file", pf, "--context", "hook"]
        env = dict(os.environ)
        env[env_name] = request
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=60)
        try:
            pout = json.loads(proc.stdout)
            pstate = json.loads(req_of(pout)["body"]["state"])
        except Exception:  # noqa: BLE001
            pout, pstate = {}, {}
        rows.append(("t3-request process: the request is in no argv element",
                     not any("MARKER-T3REQ" in a for a in argv)))
        rows.append(("t3-request process: the request arrives through the environment",
                     proc.returncode == 0 and pout.get("status") == "ok"
                     and "MARKER-T3REQ" in pstate.get("request", "")))
    finally:
        if old_env is None:
            os.environ.pop(env_name, None)
        else:
            os.environ[env_name] = old_env
    return rows


def _eval_rows(tmp, repo, printed):
    """Selftest rows for the T3 eval: freeze, label-claude, merge-human, prepare, report."""
    global MIN_HUMAN_LABELS
    rows = []
    ok = rows.append
    dd = data_dir(repo)
    corpus = os.path.join(tmp, "corpus.jsonl")
    proto = os.path.join(tmp, "protocol.json")
    reqs = {"c0": "Bump the lint rule config REQTEXT0", "c1": "Change the checkout payment flow REQTEXT1",
            "c2": "Change how the modal closes REQTEXT2", "c3": "Reword the empty state REQTEXT3"}
    # c3 has no human label, and its draft label is stricter than Jev's answer: under the old
    # `human or claude or draft` fallback that row was an inversion; against the human label only
    # it is excluded and counted.
    spec = (("c0", "demotion", "plumbing", "plumbing", "plumbing"),
            ("c1", "sensitive", "user-facing-major", "user-facing-major", "user-facing-major"),
            ("c2", "unbanded", "unknown", "unknown", "user-facing-major"),
            ("c3", "unbanded", "user-facing-major", None, None))

    def write_corpus():
        with open(corpus, "w") as fh:
            for cid, reason, draft, human, claude in spec:
                fh.write(json.dumps({"id": cid, "request": reqs[cid], "paths": ["src/%s.py" % cid],
                                     "hints": ["legal_copy"], "t3_reason": reason, "label_draft": draft,
                                     "label_source": "implementer-draft", "human_label": human,
                                     "claude_label": claude}) + "\n")

    write_corpus()

    def cli(argv):
        with contextlib.redirect_stderr(io.StringIO()):
            rc, out, raw = _run_cli(argv)
        printed.append(raw)
        return rc, out

    # -- freeze: before any call, refuses to overwrite, digest over the four immutable fields.
    rc, out = cli(["eval", "--t3", "--freeze", "--corpus", corpus, "--protocol", proto, "--repo", repo])
    pdoc = json.load(open(proto)) if os.path.isfile(proto) else {}
    ok(("eval --freeze writes the protocol", rc == 0 and out.get("status") == "ok" and bool(pdoc)))
    ok(("protocol pins corpus digest, catalogue hashes, variants, repeats, seed and thresholds",
        pdoc.get("corpus_digest") == corpus_digest(corpus)
        and sorted(pdoc.get("catalogue_hashes", {})) == sorted(v[0] for v in VARIANTS)
        and pdoc.get("variants", [{}])[0] == {"name": "original", "repeats": 3}
        and pdoc.get("split_seed") == SPLIT_SEED
        and pdoc.get("thresholds", {}).get("min_human_labels") == MIN_HUMAN_LABELS
        and pdoc.get("digest_fields") == ["id", "request", "paths", "hints"]))
    ok(("protocol records both models, resolved ids unknown before any call",
        pdoc.get("models", {}).get("jev") == {"requested": MODEL_DEFAULT, "resolved": None}
        and set(pdoc.get("models", {}).get("claude", {})) == {"requested", "resolved"}))
    rc, out = cli(["eval", "--t3", "--freeze", "--corpus", corpus, "--protocol", proto, "--repo", repo])
    ok(("eval --freeze refuses to overwrite a frozen protocol", out.get("reason") == "already_frozen"))
    base_digest = corpus_digest(corpus)
    rows_now = _corpus_rows(corpus)
    rows_now[0]["human_label"], rows_now[0]["claude_label"] = "unknown", "unknown"
    _write_corpus(corpus, rows_now)
    ok(("corpus digest ignores the label fields", corpus_digest(corpus) == base_digest))
    write_corpus()
    changed = _corpus_rows(corpus)
    changed[1]["request"] = changed[1]["request"] + " and the refund flow"
    _write_corpus(corpus, changed)
    rc, out = cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--protocol", proto, "--repo", repo])
    ok(("eval --prepare refuses a corpus that no longer matches the protocol", out.get("reason") == "corpus_changed"))
    write_corpus()
    edited = dict(pdoc)
    edited["split_seed"] = 1
    with open(proto, "w") as fh:
        json.dump(edited, fh)
    rc, out = cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--protocol", proto, "--repo", repo])
    ok(("eval --prepare refuses a protocol edited after the freeze", out.get("reason") == "protocol_edited"))
    with open(proto, "w") as fh:
        json.dump(pdoc, fh)
    rc, out = cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--protocol", os.path.join(tmp, "absent.json"),
                   "--repo", repo])
    ok(("an explicit --protocol that does not exist is refused", out.get("reason") == "no_protocol"))

    # -- label-claude, through a fake `claude` that prints the JSON result object.
    fake = os.path.join(tmp, "fake-claude.py")
    with open(fake, "w") as fh:
        fh.write("#!%s\n" % sys.executable + r'''import json, os, sys
c = os.environ["FAKE_LC_COUNTER"]
n = int(open(c).read()) if os.path.exists(c) else 0
open(c, "w").write(str(n + 1))
seq = os.environ["FAKE_LC_SEQ"].split(",")
ans = seq[n % len(seq)]
if ans == "TEXT":
    sys.stdout.write("plumbing\n")
    sys.exit(0)
sys.stdout.write(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": ans,
    "duration_ms": 5000 + n, "duration_api_ms": 2000 + n, "total_cost_usd": 0.5,
    "usage": {"input_tokens": 2, "output_tokens": 6, "cache_read_input_tokens": 0,
              "cache_creation_input_tokens": 53136},
    "modelUsage": {"claude-sonnet-4-5-20250929": {"costUSD": 0.5}}}) + "\n")
''')
    os.chmod(fake, 0o755)
    saved_env = {k: os.environ.get(k) for k in ("CV_CLASSIFY_CLAUDE_BIN", "CV_CLASSIFY_CODEX_BIN",
                                                "FAKE_LC_COUNTER", "FAKE_LC_SEQ")}
    os.environ.update({"CV_CLASSIFY_CLAUDE_BIN": fake, "CV_CLASSIFY_CODEX_BIN": "",
                       "FAKE_LC_COUNTER": os.path.join(tmp, "lc-counter"),
                       # c0: plumbing x2 + minor; c1: major, minor, plain text (untrusted -> plumbing);
                       # c2: a three-way tie -> the stricter (unknown); c3: minor x3.
                       "FAKE_LC_SEQ": ",".join(["plumbing", "user-facing-minor", "plumbing",
                                                "user-facing-major", "user-facing-minor", "TEXT",
                                                "plumbing", "unknown", "user-facing-minor",
                                                "user-facing-minor", "user-facing-minor", "user-facing-minor"])})
    try:
        before = [list(r) for r in _corpus_rows(corpus)]
        res = eval_label_claude(repo, corpus, proto, timeout_s=10)
    finally:
        for k, v in saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    after = _corpus_rows(corpus)
    ok(("eval --label-claude runs %d headless classifies per row" % CLAUDE_LABEL_RUNS,
        res.get("status") == "ok" and open(os.path.join(tmp, "lc-counter")).read() == "12"))
    # c1's plain-text run is untrusted for the measure but still an answer (today's parse), so
    # c1 is a three-way tie like c2, and both go to the stricter label.
    ok(("claude_label is the majority, a tie going to the stricter label",
        [r["claude_label"] for r in after] == ["plumbing", "user-facing-major", "unknown", "user-facing-minor"]))
    ok(("label-claude keeps every row's key order", [list(r) for r in after] == before))
    results = _read_jsonl(os.path.join(dd, CLAUDE_LABELS_FILE))
    rtext = open(os.path.join(dd, CLAUDE_LABELS_FILE)).read()
    ok(("label-claude writes one results line per run under eval/, with its measure",
        len(results) == 12 and results[0]["measure"]["duration_api_ms"] == 2000
        and results[0]["measure"]["model"] == "claude-sonnet-4-5-20250929"))
    ok(("an untrusted run is recorded with a null measure", results[5]["measure"]["wall_ms"] is None))
    ok(("no request text and no money field in any results line",
        "REQTEXT" not in rtext and "cost" not in rtext.lower()))
    ok(("label-claude fills the protocol's resolved Claude id; the freeze still holds",
        json.load(open(proto))["models"]["claude"]["resolved"] == "claude-sonnet-4-5-20250929"
        and _check_protocol(repo, proto, corpus)[1] is None))

    # -- merge-human: codes p m M u, all or nothing.
    sheet = os.path.join(tmp, "sheet.md")

    def write_sheet(rows_):
        with open(sheet, "w") as fh:
            fh.write("# sheet\n\n| Code | Category | Meaning |\n|---|---|---|\n| `p` | plumbing | x |\n\n"
                     "| # | Request | Paths | Label |\n|---|---|---|---|\n")
            for r in rows_:
                fh.write(r + "\n")

    good = ["| c0 | a | `p` | p |", "| c1 | b | `q` | M |", "| c2 | c | `r` | u |", "| c3 | d | `s` |  |"]
    snapshot = open(corpus).read()
    for name, bad, reason in (
            ("an unknown code", good[:3] + ["| c3 | d | `s` | x |"], "sheet_unknown_code"),
            ("an upper-case P (codes are case-sensitive)", ["| c0 | a | `p` | P |"] + good[1:], "sheet_unknown_code"),
            ("a missing row", good[:3], "sheet_missing_rows"),
            ("an id not in the corpus", good + ["| c9 | z | `z` | p |"], "sheet_unknown_id"),
            ("a row without four cells", good[:3] + ["| c3 | d | m |"], "sheet_row"),
            ("a duplicate id", good + ["| c0 | a | `p` | p |"], "sheet_duplicate_id")):
        write_sheet(bad)
        rc, out = cli(["eval", "--t3", "--merge-human", sheet, "--corpus", corpus, "--repo", repo])
        ok(("eval --merge-human refuses %s and writes nothing" % name,
            out.get("reason") == reason and open(corpus).read() == snapshot))
    write_sheet(good)
    rc, out = cli(["eval", "--t3", "--merge-human", sheet, "--corpus", corpus, "--repo", repo])
    merged = {r["id"]: r["human_label"] for r in _corpus_rows(corpus)}
    ok(("eval --merge-human maps p/M/u and leaves an empty cell null",
        out.get("status") == "ok" and out.get("labelled") == 3
        and merged == {"c0": "plumbing", "c1": "user-facing-major", "c2": "unknown", "c3": None}))
    ok(("merge-human keeps every row's key order and the frozen digest",
        [list(r) for r in _corpus_rows(corpus)] == before and corpus_digest(corpus) == base_digest))

    # -- prepare: 6 requests per row (original x3, three variants x1), keyed by repeat, positioned.
    rc, out = cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--protocol", proto, "--repo", repo])
    man = json.load(open(os.path.join(dd, EVAL_MANIFEST)))
    ents = man["entries"]
    ok(("eval --prepare writes 6 requests per row", rc == 0 and len(out.get("request_files", [])) == 24
        and out.get("protocol") == "checked"))
    per = {}
    for e in ents:
        per.setdefault(e["id"], []).append((e["variant"], e["repeat"]))
    ok(("each row: the original wording 3 times, each variant once",
        all(sorted(v) == [("original", 1), ("original", 2), ("original", 3), ("reversed", 1), ("wording1", 1),
                          ("wording2", 1)] for v in per.values())))
    ok(("request ids carry the repeat index and are unique",
        len({e["request_id"] for e in ents}) == 24 and ents[0]["request_id"] == "c0:original:1"))
    ok(("positions run 1..n in send order; position 1 is the batch's cold call",
        [e["position"] for e in ents] == list(range(1, 25))))
    ok(("eval requests are named eval-* (skipped by the prune) and sit in req/ for the vault",
        all(os.path.basename(e["request_file"]).startswith(EVAL_PREFIX)
            and os.path.dirname(e["request_file"]) == os.path.join(dd, "req") for e in ents)))
    rev = [e for e in ents if e["variant"] == "reversed"][0]
    rtext2 = open(rev["request_file"]).read()
    ridx = [rtext2.find('"%s":' % k) for k in reversed(T3_ORDER)]
    ok(("eval reversed variant reverses the options", -1 not in ridx and ridx == sorted(ridx)))

    # Fake answers. c0's third original answer differs: the majority keeps `plumbing`, where the old
    # overwrite-by-variant aggregation kept the LAST answer. c1's wording2 names another model.
    jev = {"c0": "plumbing", "c1": "user-facing-major", "c2": "unknown", "c3": "user-facing-minor"}
    for e in ents:
        ans = jev[e["id"]]
        if e["id"] == "c0" and e["variant"] == "original" and e["repeat"] == 3:
            ans = "user-facing-minor"
        mdl = "typesafe/jev-1.13-20261001" if (e["id"] == "c1" and e["variant"] == "wording2") \
            else "typesafe/jev-1.13-20260917"
        probs = {k: (1.0 if k == ans else 0.0) for k in T3_ORDER}
        if e["id"] == "c2":
            probs = {"unknown": 0.55, "user-facing-major": 0.25, "user-facing-minor": 0.1, "plumbing": 0.1}
        with open(_response_for_request(e["request_file"]), "w") as fh:
            json.dump({"status": "ok", "latency_ms": 900 if e["position"] == 1 else 300,
                       "body": {"model": mdl, "answers": {"category": {"type": "choice", "choice": ans,
                                                                       "probabilities": probs}}}}, fh)
    report = os.path.join(tmp, "out", "report.md")
    rc, out = cli(["eval", "--t3", "--report", report, "--protocol", proto, "--repo", repo])
    rt = open(report).read() if os.path.isfile(report) else ""
    printed.append(rt)
    ok(("eval report ok", out.get("status") == "ok" and out.get("n") == 4))
    ok(("report aggregates by (id, variant, repeat): Jev's majority agrees 3/3 with the human label",
        "| Jev vs human | 3/3 |" in rt))
    ok(("report: Claude vs human and Jev vs Claude rows",
        "| Claude vs human | 3/3 |" in rt and "| Jev vs Claude | 4/4 |" in rt))
    ok(("report: inversions against the human label only, rule of three at zero",
        "Jev: 0/3 observed; 95% upper bound by the rule of three: 3/3 = 1.000." in rt))
    ok(("report: rows without a human label are excluded and counted",
        "rows without one, excluded from agreement and inversions: 1." in rt))
    ok(("report: self-consistency over the 3 repeats", "| all 3 answers give the same label | 3/4 |" in rt))
    ok(("report: flips compared by label against the majority", "| options reversed | 0/4 |" in rt))
    ok(("report: the share of calls Jev would decide (no demotion, not unknown)",
        "| Jev decides alone | 2/4 |" in rt))
    ok(("report: risk-coverage with a fixed-seed split", "## Risk and coverage" in rt and "| 0.50 |" in rt
        and ("Fitted threshold" in rt or "No grid threshold" in rt)))
    ok(("report: cold and warm latency separately, with the hook budget share",
        "first call (cold): p50 900 ms, p95 900 ms (n = 1); 1/1 (1.000) at or under 1500 ms." in rt
        and "later calls (warm): p50 300 ms" in rt))
    ok(("report: Claude wall_ms and duration_api_ms from the label runs, tokens per call",
        "Claude duration_api_ms, label runs: p50" in rt and "Claude cache_creation_input_tokens per call: p50 53136" in rt))
    ok(("report: not decidable below the pinned number of human labels",
        "Not decidable: 3 human labels; the rule needs %d." % MIN_HUMAN_LABELS in rt
        and out.get("decidable") is False))
    ok(("eval hard-answer share", "18/24 answers" in rt))
    ok(("eval histogram has 10 bins", "## Probability histogram" in rt and rt.count("| [0.") == 10
        and "| [0.9, 1.0] |" in rt))
    ok(("eval mixed model ids are not usable for gating",
        "Not usable for gating" in rt and out.get("usable_for_gating") is False))
    anti = re.compile("|".join((
        r"tokens? " + "saved", r"token-cost (saved|savings)", "cost " + "savings:", r"saved [0-9]+ tokens",
        r"baseline ?= ?" + "1000", r"\$[0-9]+\.[0-9]+ " + "saved")), re.I)
    ok(("eval report has no anti-ruflo phrase", not anti.search(rt)))
    ok(("eval report holds no request text and no money field", "REQTEXT" not in rt and "cost_usd" not in rt))
    ok(("eval one model id is usable for gating", eval_report_single_model_check(repo, tmp)))
    ok(("the report fills the protocol's resolved Jev id once one id is seen",
        json.load(open(proto))["models"]["jev"]["resolved"] == "typesafe/jev-1.13-20260917"))

    # -- the decision rule applied, in a repo of its own with the label minimum pinned at 3.
    saved_min = MIN_HUMAN_LABELS
    MIN_HUMAN_LABELS = 3
    try:
        repo2 = os.path.join(tmp, "repo2")
        os.makedirs(repo2)
        proto2 = os.path.join(tmp, "protocol2.json")
        cli(["eval", "--t3", "--freeze", "--corpus", corpus, "--protocol", proto2, "--repo", repo2])
        rc, out = cli(["eval", "--t3", "--prepare", "--corpus", corpus, "--protocol", proto2, "--repo", repo2])
        dd2 = data_dir(repo2)
        for e in json.load(open(os.path.join(dd2, EVAL_MANIFEST)))["entries"]:
            ans = jev[e["id"]]
            with open(_response_for_request(e["request_file"]), "w") as fh:
                json.dump({"status": "ok", "latency_ms": 300, "body": {"model": "typesafe/jev-1.13-20260917",
                           "answers": {"category": {"type": "choice", "choice": ans,
                                                    "probabilities": {ans: 1.0}}}}}, fh)
        report2 = os.path.join(tmp, "out", "report2.md")
        rc, out = cli(["eval", "--t3", "--report", report2, "--protocol", proto2, "--repo", repo2])
        r2 = open(report2).read() if os.path.isfile(report2) else ""
        ok(("with enough human labels the rule is applied: (a), (b), (c) and a verdict",
            out.get("decidable") is True and "- (a) zero strictness inversions for Jev: met." in r2
            and "- (b) Jev's agreement not worse than Claude's: met." in r2
            and "(c) share Jev decides alone 0.500 against the pinned minimum 0.25: material." in r2
            and "Verdict: build spec 1.5." in r2))
    finally:
        MIN_HUMAN_LABELS = saved_min
    return rows


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
    res = eval_report(repo, os.path.join(tmp, "out", "report-one.md"), os.path.join(tmp, "protocol.json"))
    return res.get("usable_for_gating") is True


if __name__ == "__main__":
    sys.exit(main())
