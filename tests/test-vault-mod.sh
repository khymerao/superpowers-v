#!/usr/bin/env bash
# The compound-v-vault plugin (plugins/compound-v-vault): the engine's own validator must accept the
# manifest, the `jev` noun contract and the hooks module, the module must hook engine.create,
# session.start and session.append, the plugin must carry no settings (command) hooks, and its tests
# must pass. Those tests stub the network and check that the key appears only in the fetch
# Authorization header.
#
# `claude plugin validate` and `claude plugin test` need no login. A local `claude` is used when it
# is new enough (function hooks: Claude Code >= 2.1.287); otherwise a pinned CLI is fetched with npx,
# which is what CI does. No CLI and no npx is a FAILURE, not a skip: a guard that silently checks
# nothing is the v2.14.1 false-green.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
REPO_ROOT="$PWD"

PIN="2.1.289"
PLUGIN="plugins/compound-v-vault"
ge() { [ "$(printf '%s\n%s\n' "$1" "$2" | sort -t. -k1,1n -k2,2n -k3,3n | head -1)" = "$2" ]; }

CLAUDE=()
if command -v claude >/dev/null 2>&1; then
  v="$(claude --version 2>/dev/null | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+' || true)"
  if [ -n "$v" ] && ge "$v" "2.1.287"; then CLAUDE=(claude); fi
fi
if [ "${#CLAUDE[@]}" -eq 0 ]; then
  command -v npx >/dev/null 2>&1 || { echo "FAIL no claude >= 2.1.287 and no npx to fetch one"; exit 1; }
  CLAUDE=(npx -y "@anthropic-ai/claude-code@$PIN")
fi

pass=0; fail=0
ok()  { echo "PASS $1"; pass=$((pass + 1)); }
bad() { echo "FAIL $1"; fail=$((fail + 1)); }

out="$("${CLAUDE[@]}" plugin validate "$PLUGIN" 2>&1)"; rc=$?
hooks_line="$(printf '%s\n' "$out" | grep -E 'vault\.tsx hooks: ' || true)"
if [ "$rc" -eq 0 ] && [ -n "$hooks_line" ]; then
  ok "plugin validate accepts the manifest and the module"
else
  bad "plugin validate (rc=$rc)"; printf '%s\n' "$out" | tail -15
fi
for h in engine.create session.start session.append jev.classify 'tool.call{tool=mcp__compound-v-vault__jev_classify}' 'command.run{command=egress}'; do
  if printf '%s' "$hooks_line" | grep -qF "$h"; then ok "the module hooks $h"; else bad "the module does not hook $h"; fi
done
if printf '%s' "$out" | grep -qF 'declares on $: $.jev'; then
  ok "the types contract declares the jev noun"
else
  bad "the jev noun contract line is missing"
fi

# hooks.json names one module and nothing else: no settings hook, so no CLAUDE_PLUGIN_OPTION_* export
# of the sensitive key reaches any hook process.
keys="$(python3 -B -c 'import json, sys; print(",".join(sorted(json.load(open(sys.argv[1])))))' "$PLUGIN/hooks/hooks.json" 2>&1)"
if [ "$keys" = "modules" ]; then ok "hooks.json holds only modules"; else bad "hooks.json keys: $keys"; fi

# The vault's tests live in $PLUGIN/.tests/, not beside the module. `claude plugin test <dir>` runs every
# *.test.ts(x) under <dir> and skips dot-folders, so a test file anywhere else in this folder would also be
# discovered by the root plugin's own `claude plugin test .` (tests/test-run-band-mod.sh) and run there
# against the wrong plugin. Here the plugin is copied to a temporary folder with its tests placed in hooks/.
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
cp -R "$PLUGIN" "$stage/compound-v-vault"
n_tests=0
for t in "$stage/compound-v-vault/.tests/"*.test.ts "$stage/compound-v-vault/.tests/"*.test.tsx; do
  [ -f "$t" ] || continue
  mv "$t" "$stage/compound-v-vault/hooks/"; n_tests=$((n_tests + 1))
done
if [ "$n_tests" -gt 0 ]; then ok "found $n_tests test file(s) in $PLUGIN/.tests"; else bad "no test files in $PLUGIN/.tests"; fi
out="$("${CLAUDE[@]}" plugin test "$stage/compound-v-vault" 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qE '^ *0 fail' && printf '%s' "$out" | grep -qE '^ *[1-9][0-9]* pass'; then
  ok "plugin test: $(printf '%s' "$out" | grep -E '^ *[0-9]+ pass' | tr -s ' ')"
else
  bad "plugin test (rc=$rc)"; printf '%s\n' "$out" | tail -25
fi

# No test file outside .tests/: the root plugin's test run would discover it.
stray="$(find "$PLUGIN" -path "$PLUGIN/.tests" -prune -o \( -name '*.test.ts' -o -name '*.test.tsx' \) -print)"
if [ -z "$stray" ]; then ok "no test file outside $PLUGIN/.tests"; else bad "test files the root run would discover: $stray"; fi

# No key-shaped literal anywhere in the plugin folder (the tests spell their fake key in pieces).
prefix="sk-""or-"
if grep -rn -- "$prefix" "$PLUGIN" >/dev/null 2>&1; then
  bad "a key-shaped literal is in $PLUGIN"; grep -rn -- "$prefix" "$PLUGIN" | head -5
else
  ok "no key-shaped literal in $PLUGIN"
fi

# Optional vault: the marketplace lists it, in lockstep with its own manifest; superpowers-v does not depend on it.
mk_check="$(python3 -B - "$REPO_ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
mk = json.load(open(os.path.join(root, ".claude-plugin", "marketplace.json")))
entry = next((p for p in mk.get("plugins", []) if p.get("name") == "compound-v-vault"), None)
if entry is None:
    print("no marketplace entry"); raise SystemExit
src = os.path.normpath(os.path.join(root, entry.get("source", "")))
mf = os.path.join(src, ".claude-plugin", "plugin.json")
if not os.path.isfile(mf):
    print("source has no plugin.json"); raise SystemExit
pj = json.load(open(mf))
if pj.get("name") != entry.get("name") or pj.get("version") != entry.get("version"):
    print("name/version mismatch"); raise SystemExit
sv = json.load(open(os.path.join(root, ".claude-plugin", "plugin.json")))
deps = json.dumps(sv.get("dependencies", []))
print("ok" if "compound-v-vault" not in deps else "superpowers-v depends on the vault")
PY
)"
if [ "$mk_check" = ok ]; then ok "marketplace lists the vault in lockstep; superpowers-v does not depend on it"; else bad "vault marketplace entry: $mk_check"; fi
if [ ! -f "$PLUGIN/README.md" ]; then
  bad "vault README missing"
elif grep -nE '/config' "$PLUGIN/README.md" | grep -qiE 'fill in|set the key|find \*\*compound-v-vault|enter the key'; then
  bad "vault README still sends the key to /config"
else
  ok "vault README does not send the key to /config"
fi

# /v:init step 1g: the probes never expose the key, and the step covers egress, the 2.1.287 floor, a disabled vault and
# the installed id. Checked on the step's own text, so a revert of any of these trips a row.
init_check="$(python3 - "$REPO_ROOT/commands/v-init.md" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"^### 1g\..*?(?=^## |^### 1h|\Z)", t, re.S | re.M)
if not m:
    print("no step 1g"); raise SystemExit
sec = m.group(0)
code = "\n".join(re.findall(r"```bash\n(.*?)```", sec, re.S))
problems = []
for line in code.splitlines():
    if "plugin configure" in line and "2>/dev/null | python3" not in line:
        problems.append("configure probe not filtered")
if "inputs" in code:
    problems.append("probe code reads inputs")
if "disabled:" not in code:
    problems.append("probe does not tell disabled from absent")
for word, why in (("/egress allow", "no egress note"), ("2.1.287", "no 2.1.287 floor"), ("/plugin enable", "no enable hint")):
    if word not in sec:
        problems.append(why)
step2 = t[t.find("## Step 2"):]
item = step2[step2.find("Jev vault"):step2.find("Jev vault") + 1200]
if "/plugin configure <id>" not in item:
    problems.append("Step 2 does not configure the probed id")
print("ok" if not problems else "; ".join(problems))
PY
)"
if [ "$init_check" = ok ]; then ok "v-init 1g: filtered probes, egress, 2.1.287, disabled and probed id covered"; else bad "v-init 1g: $init_check"; fi

echo "tests/test-vault-mod.sh: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
