#!/usr/bin/env python3
"""
Compound V model discovery — turn a backend's live model catalog into a tier map.

The model broker routes by INTENT (tier ∈ frontier/deep/standard/light), resolving to a concrete
model through a refreshable `models` block in .claude/compound-v.json
(see compound-v-resolve-model.py). This script does the DISCOVERY half deterministically:
it reads a backend's catalog (a plain list of model names, one per line) and PROPOSES a
frontier/deep/standard/light assignment, so /v:models and /v:init can suggest a real, current map
instead of a hand-curated one that rots when the provider ships new models.

I/O is intentionally split: the CALLER fetches the catalog (e.g. `agy models </dev/null`)
and pipes it in; this script only PARSES + RANKS (so it is pure and testable, and never
hangs on a backend call). It never invents names — it only ranks what it was given.

Ranking (antigravity / Gemini-family default):
  - Prefer the configured family (default "Gemini") for error-decorrelation from the
    Claude planner; other families in the catalog (e.g. GPT-OSS, Claude-via-agy) are
    reported under `available` and can be set explicitly, but are not auto-assigned.
  - A model name carries its effort in trailing parens, e.g. "Gemini 3.1 Pro (High)".
  - deep  = strongest series (Pro > Flash; higher version breaks ties) at its TOP effort.
  - frontier = the same as deep -- for backends whose catalog has no separate top rung
    above their strongest everyday model (antigravity/Gemini has no "Ultra" tier here;
    cursor/opencode are opaque strings, not ranked at all). This is NOT universal: codex
    (below) has a genuine top rung (gpt-6-astra above gpt-6-sol) and frontier is picked
    as that distinct model, never mirrored from deep.
  - light = weakest series at its LOWEST effort.
  - standard = the strong series at a LOWER effort if it has one (a capable model, cheaper);
    else the weak series at its top effort; else the median of the catalog.

Ranking (codex, `--backend codex`):
  - Input is the RAW JSON `codex debug models` prints: on codex-cli 0.156.1 (live-checked
    2026-09-24) that is a top-level OBJECT ``{"models": [...]}``, not a bare array --
    `propose_codex` accepts either shape. Each catalog entry is an object per model with
    `slug`, `display_name`, `description`, `visibility` ("list"/"hide"), `priority` (lower
    = shown first / stronger), `upgrade` (null or {model, migration_markdown,
    retirement_at}), `supported_reasoning_levels` ([{effort, description}, ...]),
    `default_reasoning_level`, `context_window`) -- piped in, never fetched by this script.
  - Keep only `visibility == "list"` entries for `available`; a `hide`d entry (e.g. an
    internal reserve/auto-review slug) never appears in `available` or in a proposal.
  - Of those, drop any whose `upgrade` carries a `retirement_at` from the PROPOSAL
    candidate pool (it still appears in `available`, and separately in `retiring`) --
    routing new work onto a model that is already scheduled to retire is a foreseeable
    failure, not a coincidence.
  - ROLES FIRST (3.7.5). OpenAI names a model's role in its slug suffix, the same way
    across two generations: `-astra` frontier, `-sol` workhorse, `-luna` fast/cheap
    (`-terra`, a mid tier, is not auto-assigned: `standard` shares `sol` by the
    maintainer's 3.7.1 decision). For each role suffix keep the NEWEST version -- the
    number between `gpt-` and the suffix, compared numerically (`gpt-6.1-sol` beats
    `gpt-6-sol`), lower `priority` breaking a tie. Then `frontier` = astra (else sol),
    `deep` = `standard` = sol (else astra), `light` = luna (else deep). Tier and effort are
    orthogonal axes (see compound-v-resolve-model.py), so deep/standard legitimately share
    a model and differ only by effort.
    Why not priority: until codex-cli 0.157 `priority` happened to order strength
    (astra 1, sol 2, luna 3). 0.159.1 (live-checked 2026-09-30) lists the new workhorse
    `gpt-6.1-sol` at priority 1 above `gpt-6-astra` at 2 -- priority is the picker's
    display order, not a strength rank -- and the family rule below proposed
    `gpt-6.1-sol` for all four tiers, frontier review included.
  - FALLBACK, when no candidate carries a known role suffix: group by FAMILY (the slug up
    to the last alphabetic `-<suffix>`; `gpt-5.5` is its own family), take the family
    holding the lowest `priority`, order it by priority; `frontier` = 1st, `deep` =
    `standard` = 2nd (or the 1st), `light` = last. The `note` says the fallback ran.
  - `efforts_not_adopted` = every effort name appearing in any visible entry's
    `supported_reasoning_levels` that is outside this project's adopted `low|medium|high|
    xhigh` vocabulary (sorted, deduplicated) -- visible so a new rung (`ultra`, `max`, or
    whatever comes next) is never silently invisible, without being auto-routable.

Usage:
  agy models </dev/null | compound-v-discover-models.py --backend antigravity
  compound-v-discover-models.py --backend antigravity --from-file catalog.txt \
      --write-config .claude/compound-v.json
  codex debug models | compound-v-discover-models.py --backend codex
  compound-v-discover-models.py --backend codex --from-file catalog.json \
      --write-config .claude/compound-v.json
  compound-v-discover-models.py --selftest

Python 3.9-safe, stdlib only.
"""

import argparse
import json
import os
import re
import sys

_EFFORT_RANK = {"high": 3, "thinking": 3, "max": 4, "medium": 2, "standard": 2, "low": 1}


# Stance names, mirrored from compound-v-resolve-model.py VALID_STANCES (the selftest
# asserts parity so the two cannot drift apart silently).
_STANCES = ("balanced", "conservative", "cost-aware", "claude-only")


def _parse_line(line):
    """'Gemini 3.1 Pro (High)' -> dict(full, series, version, strength, effort_rank).

    agy >= 1.1 prints two columns, ``id<TAB>Display Name`` (verified 1.1.22:
    ``gemini-3.1-pro-low\tGemini 3.1 Pro (Low)``); older builds printed the display
    name alone. Rank on the display column and keep it as the value written — agy
    1.1.22 accepts both forms for ``--model`` (probed live 2026-09-03), and every
    adapter doc, fixture and built-in default already uses the display name.
    """
    full = line.strip()
    if "\t" in full:
        full = full.split("\t")[-1].strip()
    if not full:
        return None
    m = re.search(r"\(([^)]+)\)\s*$", full)
    effort = m.group(1).strip().lower() if m else ""
    series = re.sub(r"\s*\([^)]*\)\s*$", "", full).strip()  # name without the effort paren
    ver_m = re.search(r"(\d+(?:\.\d+)?)", series)
    # A tuple of ints, never a float: float("3.10") == 3.1 < 3.8 would rank a newer
    # generation below an older one (pr-review 2026-09-04 on the 3.4.14 ranker).
    version = tuple(int(x) for x in ver_m.group(1).split(".")) if ver_m else (0,)
    low = series.lower()
    if "ultra" in low:
        strength = 3
    elif "pro" in low:
        strength = 2
    elif "flash" in low or "spark" in low or "mini" in low:
        strength = 1
    else:
        strength = 2  # unknown tier — treat as mid/strong, not throwaway
    # effort_rank: default 2 (medium) when the catalog omits an effort suffix
    eff = 2
    for key, rank in _EFFORT_RANK.items():
        if key in effort:
            eff = rank
            break
    return {"full": full, "series": series, "version": version,
            "strength": strength, "effort_rank": eff}


def _family_of(series):
    """First token is the family label, e.g. 'Gemini', 'Claude', 'GPT-OSS'."""
    return series.split()[0] if series.split() else series


def propose(catalog_lines, family="Gemini"):
    """Return {'available': [...], 'proposed': {deep,standard,light}|None, 'note': str}."""
    parsed = [p for p in (_parse_line(l) for l in catalog_lines) if p]
    available = [p["full"] for p in parsed]
    if not parsed:
        return {"available": [], "proposed": None, "note": "empty catalog"}

    fam_lower = family.lower()
    fam = [p for p in parsed if _family_of(p["series"]).lower() == fam_lower]
    note = ""
    if not fam:
        fam = parsed
        note = "no '%s' models in catalog; ranked across all families" % family

    # Group by series label; rank series by (strength, version).
    series_groups = {}
    for p in fam:
        series_groups.setdefault(p["series"], []).append(p)

    def series_key(label):
        g = series_groups[label]
        return (g[0]["strength"], g[0]["version"])

    labels = sorted(series_groups, key=series_key)  # weakest .. strongest
    strongest = labels[-1]
    # `light` is the NEWEST series of the weakest strength class at its lowest effort —
    # the Flash line ships a new version every few weeks, and the newest one is the
    # cheap, fast, current model (3.4.14: the catalog carried 3.6/3.7/3.8 Flash and the
    # oldest was being proposed). The oldest series is never the answer for a moving line.
    weakest_strength = series_groups[labels[0]][0]["strength"]
    weakest = max((l for l in labels if series_groups[l][0]["strength"] == weakest_strength),
                  key=lambda l: series_groups[l][0]["version"])

    deep = max(series_groups[strongest], key=lambda p: p["effort_rank"])["full"]
    light = min(series_groups[weakest], key=lambda p: p["effort_rank"])["full"]

    strong_efforts = sorted(series_groups[strongest], key=lambda p: p["effort_rank"])
    weak_efforts = sorted(series_groups[weakest], key=lambda p: p["effort_rank"])
    if len(strong_efforts) > 1:
        standard = strong_efforts[0]["full"]          # strong series, cheaper effort
    elif len(weak_efforts) > 1:
        standard = weak_efforts[-1]["full"]           # weak series, top effort
    else:
        ordered = sorted(fam, key=lambda p: (p["strength"], p["version"], p["effort_rank"]))
        standard = ordered[len(ordered) // 2]["full"]

    # `frontier` is the extreme seat (v3.0.5). For THIS ranker (antigravity/Gemini-style
    # single-vendor catalogs with no rung above the strongest everyday model) it is the
    # SAME model as `deep`: proposing a distinct one would be a fabricated route. This is
    # a property of this ranker's catalogs, not a universal rule -- `propose_codex` below
    # covers a backend whose catalog DOES carry a genuine top rung, and there `frontier`
    # is picked as that distinct model. Only `claude` otherwise separates them, via
    # native aliases, not a discovered catalog.
    return {"available": available,
            "proposed": {"frontier": deep, "deep": deep,
                         "standard": standard, "light": light},
            "note": note}


# Effort vocabulary this project actually routes on (compound-v-resolve-model.py:EFFORTS
# plus xhigh, which is codex-only there). Anything else a catalog lists (e.g. codex's
# `max`/`ultra`) is surfaced via `efforts_not_adopted`, never silently dropped.
_ADOPTED_EFFORTS = frozenset(("low", "medium", "high", "xhigh"))


def _codex_family_of(slug):
    """'gpt-6-astra' -> 'gpt-6'; 'gpt-5.5' -> 'gpt-5.5' (no alphabetic suffix to strip)."""
    if "-" in slug:
        prefix, suffix = slug.rsplit("-", 1)
        if suffix.isalpha():
            return prefix
    return slug


_CODEX_ROLE_SUFFIXES = ("astra", "sol", "luna")


def _codex_version(family):
    """'gpt-6.1' -> (6, 1); 'gpt-6' -> (6,); a family with no parseable number -> ()."""
    m = re.search(r"(\d+(?:\.\d+)*)$", family or "")
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def _codex_by_role(candidates):
    """{suffix: entry} -- the newest listed, non-retiring model of each role suffix."""
    best = {}
    for e in candidates:
        slug = e.get("slug") or ""
        fam = _codex_family_of(slug)
        if fam == slug:
            continue
        suffix = slug[len(fam) + 1:]
        if suffix not in _CODEX_ROLE_SUFFIXES:
            continue
        prio = e.get("priority") if isinstance(e.get("priority"), (int, float)) else float("inf")
        key = (_codex_version(fam), -prio)
        if suffix not in best or key > best[suffix][0]:
            best[suffix] = (key, e)
    return {k: v[1] for k, v in best.items()}


def propose_codex(catalog):
    """Propose a frontier/deep/standard/light map from `codex debug models`' raw JSON.

    `catalog` is the parsed JSON: on codex-cli 0.156.1 (live-checked 2026-09-24 for this
    change) `codex debug models` actually prints a top-level OBJECT, ``{"models": [...]}``
    -- not a bare array as an earlier description of this command claimed. Both shapes
    are accepted here (a bare list, or a dict with a "models" list) so a future/older
    codex-cli that does emit a bare array still works. See the module docstring's
    "Ranking (codex, ...)" section for the full rule. Returns the same shape as
    `propose()` (`available`, `proposed`, `note`) plus two codex-specific keys,
    `retiring` and `efforts_not_adopted`.
    """
    if isinstance(catalog, dict):
        catalog = catalog.get("models") or []
    if not isinstance(catalog, list):
        catalog = []
    visible = [e for e in catalog if isinstance(e, dict) and e.get("visibility") == "list"]

    def _efforts(entry):
        return [lvl.get("effort") for lvl in (entry.get("supported_reasoning_levels") or [])
                if isinstance(lvl, dict) and lvl.get("effort")]

    available = [
        {
            "slug": e.get("slug"),
            "description": e.get("description"),
            "priority": e.get("priority"),
            "default_reasoning_level": e.get("default_reasoning_level"),
            "efforts": _efforts(e),
        }
        for e in visible
    ]

    def _retirement_at(e):
        up = e.get("upgrade")
        return up.get("retirement_at") if isinstance(up, dict) else None

    retiring = [
        {"slug": e.get("slug"), "retirement_at": _retirement_at(e),
         "upgrade_model": (e.get("upgrade") or {}).get("model")}
        for e in visible if _retirement_at(e)
    ]

    not_adopted = set()
    for e in visible:
        for eff in _efforts(e):
            if eff not in _ADOPTED_EFFORTS:
                not_adopted.add(eff)
    efforts_not_adopted = sorted(not_adopted)

    candidates = [e for e in visible if not _retirement_at(e)]
    if not candidates:
        return {"available": available, "proposed": None,
                "note": "no non-retiring listed codex models in catalog",
                "retiring": retiring, "efforts_not_adopted": efforts_not_adopted}

    roles = _codex_by_role(candidates)
    if roles:
        sol = roles.get("sol") or roles.get("astra") or roles.get("luna")
        astra = roles.get("astra") or sol
        deep = sol["slug"]
        return {
            "available": available,
            "proposed": {"frontier": astra["slug"], "deep": deep, "standard": deep,
                         "light": (roles.get("luna") or sol)["slug"]},
            "note": "",
            "retiring": retiring,
            "efforts_not_adopted": efforts_not_adopted,
        }

    families = {}
    for e in candidates:
        families.setdefault(_codex_family_of(e.get("slug", "")), []).append(e)

    def _min_priority(members):
        prios = [m.get("priority") for m in members if isinstance(m.get("priority"), (int, float))]
        return min(prios) if prios else float("inf")

    winning_family = min(families, key=lambda fam: _min_priority(families[fam]))
    ordered = sorted(
        families[winning_family],
        key=lambda m: m.get("priority") if isinstance(m.get("priority"), (int, float)) else float("inf"),
    )

    frontier = ordered[0]["slug"]
    deep = ordered[1]["slug"] if len(ordered) >= 2 else ordered[0]["slug"]
    standard = deep
    light = ordered[-1]["slug"]

    return {
        "available": available,
        "proposed": {"frontier": frontier, "deep": deep, "standard": standard, "light": light},
        "note": "no -astra/-sol/-luna role suffix in the catalog; ranked by priority "
                "within the lowest-priority family (fallback rule)",
        "retiring": retiring,
        "efforts_not_adopted": efforts_not_adopted,
    }


def write_config(config_path, backend, tier_map):
    """Merge {backend: tier_map} into the config's `models` block, preserving the rest."""
    data = {}
    if os.path.isfile(config_path):
        with open(config_path, "r") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("config root is not a JSON object: %s" % config_path)
    models = data.get("models")
    if not isinstance(models, dict):
        models = {}
    keys = list(models.keys())
    if keys and all(k in _STANCES for k in keys):
        # Per-stance shape — what /v:init Step 4a writes. The resolver discriminates the
        # two shapes by "EVERY top-level key is a stance name", so a flat `models.<backend>`
        # key dropped beside stance blocks flips the WHOLE map to the legacy branch and
        # silently disables every other backend's override (finding 142). Seed every stance.
        for st in keys:
            if isinstance(models[st], dict):
                models[st][backend] = dict(tier_map)
    else:
        models[backend] = tier_map
    data["models"] = models
    d = os.path.dirname(config_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with open(config_path, "w") as fh:
        fh.write(json.dumps(data, indent=2) + "\n")


def _selftest():
    ok = 0
    fail = 0

    def check(name, cond):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print("  FAIL %s" % name)

    catalog = [
        "Gemini 3.5 Flash (Medium)", "Gemini 3.5 Flash (High)", "Gemini 3.5 Flash (Low)",
        "Gemini 3.1 Pro (Low)", "Gemini 3.1 Pro (High)",
        "Claude Sonnet 4.6 (Thinking)", "Claude Opus 4.6 (Thinking)", "GPT-OSS 120B (Medium)",
    ]
    r = propose(catalog, family="Gemini")
    p = r["proposed"]
    check("deep = Pro High", p["deep"] == "Gemini 3.1 Pro (High)")
    check("standard = Pro Low", p["standard"] == "Gemini 3.1 Pro (Low)")
    check("light = Flash Low", p["light"] == "Gemini 3.5 Flash (Low)")
    check("avoids non-Gemini families", all("Gemini" in v for v in p.values()))
    check("available lists all 8", len(r["available"]) == 8)

    # only one Pro effort -> standard falls to Flash top effort
    cat2 = ["Gemini 3.1 Pro (High)", "Gemini 3.5 Flash (Low)", "Gemini 3.5 Flash (High)"]
    p2 = propose(cat2, family="Gemini")["proposed"]
    check("deep (single-pro)", p2["deep"] == "Gemini 3.1 Pro (High)")
    check("standard falls to Flash High", p2["standard"] == "Gemini 3.5 Flash (High)")
    check("light Flash Low", p2["light"] == "Gemini 3.5 Flash (Low)")

    # no Gemini -> ranks across families with a note
    cat3 = ["GPT-OSS 120B (Medium)", "GPT-OSS 20B (Low)"]
    r3 = propose(cat3, family="Gemini")
    check("no-family note", "no 'Gemini'" in r3["note"])
    check("still proposes something", r3["proposed"] is not None)
    check("proposal carries every tier the resolver knows",
          set(r3["proposed"]) == {"frontier", "deep", "standard", "light"})
    check("frontier mirrors deep for a no-top-rung catalog (this ranker only, not codex)",
          r3["proposed"]["frontier"] == r3["proposed"]["deep"])

    check("empty catalog -> None", propose([], "Gemini")["proposed"] is None)

    # agy >= 1.1 two-column catalog (id<TAB>display): rank on the display column, never
    # write the id or the tab (finding 138 — the whole line used to be parsed as a name,
    # the family check failed, and GPT-OSS 120B won deep/frontier on "version 120").
    cat_tsv = ["gemini-3.8-flash-low\tGemini 3.8 Flash (Low)", "gemini-3.1-pro-high\tGemini 3.1 Pro (High)",
               "gemini-3.1-pro-low\tGemini 3.1 Pro (Low)", "gpt-oss-120b-medium\tGPT-OSS 120B (Medium)"]
    p4 = propose(cat_tsv, family="Gemini")["proposed"]
    check("tsv: deep = Pro High", p4["deep"] == "Gemini 3.1 Pro (High)")
    check("tsv: light = Flash Low", p4["light"] == "Gemini 3.8 Flash (Low)")
    check("tsv: no tab or id in any value", all("\t" not in v and not v.startswith("gemini-") for v in p4.values()))
    check("tsv: avoids non-Gemini families", all("Gemini" in v for v in p4.values()))

    # 3.4.14: three Flash generations in the catalog -> light is the NEWEST Flash at Low,
    # standard stays the Pro line's cheaper effort, deep the Pro line's top effort.
    cat5 = ["Gemini 3.8 Flash (High)", "Gemini 3.8 Flash (Low)", "Gemini 3.7 Flash (Low)",
            "Gemini 3.6 Flash (High)", "Gemini 3.6 Flash (Low)",
            "Gemini 3.1 Pro (High)", "Gemini 3.1 Pro (Low)"]
    p5 = propose(cat5, family="Gemini")["proposed"]
    check("moving Flash line: light = newest Flash (Low)", p5["light"] == "Gemini 3.8 Flash (Low)")
    check("moving Flash line: deep/standard stay on Pro", p5["deep"] == "Gemini 3.1 Pro (High)"
          and p5["standard"] == "Gemini 3.1 Pro (Low)")
    # two-digit minors: 3.10 is newer than 3.8 (a float compare says the opposite)
    cat6 = ["Gemini 3.8 Flash (Low)", "Gemini 3.10 Flash (Low)", "Gemini 3.1 Pro (High)", "Gemini 3.10 Pro (High)"]
    p6 = propose(cat6, family="Gemini")["proposed"]
    check("3.10 > 3.8 for light", p6["light"] == "Gemini 3.10 Flash (Low)")
    check("3.10 > 3.1 for deep", p6["deep"] == "Gemini 3.10 Pro (High)")

    # Per-stance config (/v:init Step 4a shape): the seed lands in EVERY stance block and
    # never as a flat sibling key, and the resolver actually reads it back (finding 142).
    import importlib.util
    rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compound-v-resolve-model.py")
    spec = importlib.util.spec_from_file_location("cv_resolve", rp)
    rmod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rmod)
    check("stance names mirror the resolver", set(_STANCES) == set(rmod.VALID_STANCES))
    import tempfile
    fd, path2 = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        per_stance = {st: {"claude": {"deep": "opus"}, "antigravity": {"deep": "OLD"}} for st in _STANCES}
        with open(path2, "w") as fh:
            json.dump({"stance": "balanced", "models": per_stance}, fh)
        write_config(path2, "antigravity", {"frontier": "P", "deep": "P", "standard": "Q", "light": "R"})
        with open(path2) as fh:
            got2 = json.load(fh)["models"]
        check("per-stance: no flat sibling key", set(got2) == set(_STANCES))
        check("per-stance: every stance seeded", all(got2[st]["antigravity"]["deep"] == "P" for st in _STANCES))
        check("per-stance: other backends untouched", all(got2[st]["claude"] == {"deep": "opus"} for st in _STANCES))
        check("per-stance: resolver reads the seed back",
              rmod._config_cell(got2, "balanced", "antigravity", "deep") == "P"
              and rmod._config_cell(got2, "cost-aware", "claude", "deep") == "opus")
    finally:
        os.unlink(path2)

    # write_config merges, preserving other backends
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        with open(path, "w") as fh:
            json.dump({"models": {"codex": {"deep": "gpt-5.5"}}, "other": 1}, fh)
        write_config(path, "antigravity", {"deep": "X", "standard": "Y", "light": "Z"})
        with open(path) as fh:
            got = json.load(fh)
        check("merge preserves codex", got["models"]["codex"]["deep"] == "gpt-5.5")
        check("merge adds antigravity", got["models"]["antigravity"]["deep"] == "X")
        check("merge preserves other keys", got.get("other") == 1)
    finally:
        os.unlink(path)

    # --- codex: `codex debug models` JSON catalog (trimmed fixture off the 2026-09-24
    # probe on codex-cli 0.156.1 -- see compound-v-resolve-model.py's _CODEX comment for
    # the same facts). Only the fields propose_codex() reads are included.
    def _lvls(*efforts):
        return [{"effort": e, "description": e} for e in efforts]

    codex_catalog = [
        {"slug": "gpt-6-astra", "description": "Frontier intelligence for the most demanding work.",
         "visibility": "list", "priority": 1, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium", "high", "xhigh", "max", "ultra"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-6-sol", "description": "Workhorse model for coding and everyday work.",
         "visibility": "list", "priority": 2, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium", "high", "xhigh", "max", "ultra"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-6-luna", "description": "Fast and affordable model for easier tasks.",
         "visibility": "list", "priority": 3, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium", "high", "xhigh", "max"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-5.6-sol", "description": "Older workhorse model for coding.",
         "visibility": "list", "priority": 4, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium", "high", "xhigh"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-5.6-terra", "description": "Older mid-tier model.",
         "visibility": "list", "priority": 7, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium", "high"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-5.6-luna", "description": "Older fast model.",
         "visibility": "list", "priority": 8, "upgrade": None,
         "supported_reasoning_levels": _lvls("low", "medium"),
         "default_reasoning_level": "low"},
        {"slug": "gpt-5.5", "description": "Retiring model.",
         "visibility": "list", "priority": 12,
         "upgrade": {"model": "gpt-5.6-sol", "migration_markdown": "...",
                     "retirement_at": "2026-10-14"},
         "supported_reasoning_levels": _lvls("low", "medium", "high"),
         "default_reasoning_level": "medium"},
        {"slug": "gpt-reserve", "description": "Internal reserve.",
         "visibility": "hide", "priority": 0, "upgrade": None,
         "supported_reasoning_levels": _lvls("low"), "default_reasoning_level": "low"},
        {"slug": "codex-auto-review", "description": "Internal auto-review.",
         "visibility": "hide", "priority": 0, "upgrade": None,
         "supported_reasoning_levels": _lvls("low"), "default_reasoning_level": "low"},
    ]

    rc = propose_codex(codex_catalog)
    rc_wrapped = propose_codex({"models": codex_catalog})
    check("codex: accepts the real {'models': [...]} wrapper shape",
          rc_wrapped["proposed"] == rc["proposed"])
    check("codex: proposes exactly the maintainer's map",
          rc["proposed"] == {"frontier": "gpt-6-astra", "deep": "gpt-6-sol",
                             "standard": "gpt-6-sol", "light": "gpt-6-luna"})
    check("codex: retiring model excluded from proposal",
          "gpt-5.5" not in rc["proposed"].values())
    check("codex: retiring model reported in retiring",
          any(r["slug"] == "gpt-5.5" and r["retirement_at"] == "2026-10-14"
              and r["upgrade_model"] == "gpt-5.6-sol" for r in rc["retiring"]))
    check("codex: hidden models excluded from available",
          all(a["slug"] not in ("gpt-reserve", "codex-auto-review") for a in rc["available"]))
    check("codex: hidden models excluded from proposal",
          all(v not in ("gpt-reserve", "codex-auto-review") for v in rc["proposed"].values()))
    check("codex: efforts_not_adopted is exactly max/ultra, sorted+deduped",
          rc["efforts_not_adopted"] == ["max", "ultra"])

    # codex-cli 0.159.1 (live 2026-09-30): the new workhorse gpt-6.1-sol is listed at
    # priority 1, ABOVE gpt-6-astra -- priority stopped ranking strength. Roles decide.
    cat_061 = [dict(e) for e in codex_catalog]
    for e in cat_061:
        if e["slug"] == "gpt-6-sol":
            e["priority"] = 3
        elif e["slug"] == "gpt-6-astra":
            e["priority"] = 2
    cat_061.insert(0, {"slug": "gpt-6.1-sol", "description": "Latest workhorse model.",
                       "visibility": "list", "priority": 1, "upgrade": None,
                       "supported_reasoning_levels": _lvls("low", "medium", "high", "xhigh"),
                       "default_reasoning_level": "low"})
    r61 = propose_codex(cat_061)
    check("codex 0.159.1: frontier stays astra though gpt-6.1-sol has priority 1",
          r61["proposed"] == {"frontier": "gpt-6-astra", "deep": "gpt-6.1-sol",
                              "standard": "gpt-6.1-sol", "light": "gpt-6-luna"})
    check("codex: role version compares numerically (gpt-6.10 beats gpt-6.9)",
          _codex_by_role([
              {"slug": "gpt-6.9-sol", "visibility": "list", "priority": 1},
              {"slug": "gpt-6.10-sol", "visibility": "list", "priority": 2},
          ])["sol"]["slug"] == "gpt-6.10-sol")
    check("codex: gpt-5.6-sol never beats gpt-6-sol",
          _codex_by_role([
              {"slug": "gpt-5.6-sol", "visibility": "list", "priority": 1},
              {"slug": "gpt-6-sol", "visibility": "list", "priority": 5},
          ])["sol"]["slug"] == "gpt-6-sol")
    r_no_astra = propose_codex([e for e in cat_061 if not e["slug"].endswith("-astra")])
    check("codex: no astra in the catalog -> frontier falls back to the newest sol",
          r_no_astra["proposed"]["frontier"] == "gpt-6.1-sol")

    # single listed model -> every tier maps to it
    one_model = [
        {"slug": "solo-model", "description": "Only model.", "visibility": "list",
         "priority": 1, "upgrade": None, "supported_reasoning_levels": _lvls("low", "medium"),
         "default_reasoning_level": "medium"},
    ]
    ro = propose_codex(one_model)
    check("codex: single-model catalog maps every tier to it",
          set(ro["proposed"].values()) == {"solo-model"})

    # write_config works for codex too, via the same per-stance-aware logic
    fd, path3 = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path3)  # write_config must work when the config file doesn't exist yet
    try:
        write_config(path3, "codex", rc["proposed"])
        with open(path3) as fh:
            got3 = json.load(fh)
        check("codex: write_config writes the proposed map",
              got3["models"]["codex"] == rc["proposed"])
    finally:
        os.unlink(path3)

    print("SELFTEST: %d ok, %d fail" % (ok, fail))
    return 0 if fail == 0 else 1


def main(argv):
    p = argparse.ArgumentParser(description="Compound V model discovery / tier proposal.")
    p.add_argument("--backend", default="antigravity",
                   help="backend label the proposal is for (config key)")
    p.add_argument("--family", default="Gemini",
                   help="preferred model family to auto-assign (default Gemini)")
    p.add_argument("--from-file", help="read the catalog from a file instead of stdin")
    p.add_argument("--write-config", help="merge the proposal into this config JSON's models block")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.backend == "codex":
        # codex's catalog is a JSON array (from `codex debug models`), not a plain
        # line-per-model text catalog -- read it whole and parse as JSON.
        if args.from_file:
            with open(args.from_file, "r", errors="replace") as fh:
                raw = fh.read()
        else:
            raw = sys.stdin.read()
        try:
            catalog = json.loads(raw)
        except ValueError as e:
            print("discover: --backend codex expects the JSON array from "
                  "`codex debug models`: %s" % e, file=sys.stderr)
            return 1
        result = propose_codex(catalog)
    else:
        if args.from_file:
            with open(args.from_file, "r", errors="replace") as fh:
                lines = fh.read().splitlines()
        else:
            lines = sys.stdin.read().splitlines()
        result = propose(lines, family=args.family)
    result["backend"] = args.backend

    if args.write_config:
        if not result["proposed"]:
            print("discover: empty/unusable catalog — nothing written to %s" % args.write_config,
                  file=sys.stderr)
            return 1
        write_config(args.write_config, args.backend, result["proposed"])
        result["written_to"] = args.write_config

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
