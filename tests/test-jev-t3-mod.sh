#!/usr/bin/env bash
# The T3 shadow module (hooks/jev-t3.tsx): the engine's own validator must accept it as this
# plugin's one hooks module, carrying the run band's hooks and its own, and must not load the
# compound-v-vault plugin as part of this plugin; its tests and the band's must pass.
#
# The engine takes ONE hooks module per plugin (a second `modules` entry is refused) and one
# unmatched `session.start` per load, so hooks/jev-t3.tsx is the entry: it registers the run
# band's hooks by import, then its own `classic.UserPromptSubmit`. The validator therefore names
# every hook under `./jev-t3.tsx`.
#
# CLI resolution as tests/test-run-band-mod.sh: a local `claude` >= 2.1.287, else the pinned CLI
# through npx. No CLI and no npx is a FAILURE, not a skip.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

PIN="2.1.289"
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

# --- static: the module list and the module's own promises ---------------------------------
mods="$(python3 -B -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["modules"]))' hooks/hooks.json 2>&1)"
[ "$mods" = '["./jev-t3.tsx"]' ] && ok "hooks.json names one module, ./jev-t3.tsx" || bad "hooks.json modules: $mods"
grep -qE "^import \{ register as registerRunBand \} from './run-band'" hooks/jev-t3.tsx \
  && grep -qE '^  registerRunBand\(on, options\)' hooks/jev-t3.tsx \
  && ok "jev-t3.tsx registers the run band's hooks" || bad "jev-t3.tsx does not register the run band"
# The module never writes another hook's context: the name does not appear outside comments.
if grep -vE '^\s*(//|\*|/\*)' hooks/jev-t3.tsx | grep -q 'additionalContext'; then
  bad "jev-t3.tsx touches additionalContext"
else
  ok "jev-t3.tsx never touches additionalContext"
fi
if grep -nE 'sk-or-|Bearer|openrouter_key|user_id' hooks/jev-t3.tsx; then
  bad "jev-t3.tsx names a key, an auth header or an error-body field"
else
  ok "no key, auth header or error-body field in jev-t3.tsx"
fi
runs="$(grep -c '\$\.process\.run(' hooks/jev-t3.tsx)"
capped="$(grep -cE '\$\.process\.run\(.*timeoutMs: PROCESS_TIMEOUT_MS' hooks/jev-t3.tsx)"
if [ "$runs" -gt 0 ] && [ "$runs" -eq "$capped" ] && grep -qE '^const PROCESS_TIMEOUT_MS = 30_000$' hooks/jev-t3.tsx; then
  ok "every process.run in jev-t3.tsx is capped at 30 s ($runs)"
else
  bad "process.run calls $runs, capped $capped"
fi

# --- the engine's validator -------------------------------------------------------------------
out="$("${CLAUDE[@]}" plugin validate . 2>&1)"; rc=$?
line="$(printf '%s\n' "$out" | grep -E 'jev-t3\.tsx hooks: ' || true)"
if [ "$rc" -eq 0 ] && printf '%s' "$line" | grep -qF 'session.start, ui.render{component=AbovePrompt}, classic.UserPromptSubmit'; then
  ok "plugin validate accepts jev-t3.tsx with the band's hooks and classic.UserPromptSubmit"
else
  bad "plugin validate (rc=$rc)"; printf '%s\n' "$out" | tail -15
fi
calls="$(printf '%s\n' "$out" | grep -E 'jev-t3\.tsx calls: ' || true)"
printf '%s' "$calls" | grep -qF 'readHud' && printf '%s' "$calls" | grep -qF 'readLiveness' \
  && ok "run-band.tsx's readers are part of the module (run-band.tsx loaded through jev-t3.tsx)" \
  || bad "run-band.tsx's readers missing from the calls line"
printf '%s' "$calls" | grep -qF '$.jev.classify' && printf '%s' "$calls" | grep -qF '$.jev.status' \
  && ok "the module reaches the vault only through \$.jev" || bad "\$.jev calls missing"
printf '%s\n' "$out" | grep -qE 'jev-t3\.tsx env writes: CV_JEV_T3$' \
  && ok "the module writes one environment variable, CV_JEV_T3" || bad "env writes line is not exactly CV_JEV_T3"
# run-band.tsx owns both keys (`band`, and `spin` since 3.8.2); jev-t3.tsx adds none of its own.
printf '%s\n' "$out" | grep -qE 'jev-t3\.tsx state writes: superpowers-v\.band, superpowers-v\.spin$' \
  && ok "the module writes only the band's declared state" || bad "state contract line missing"
if printf '%s' "$out" | grep -qiE 'compound-v-vault|vault\.tsx'; then
  echo "BLOCKED plugins/compound-v-vault is loaded as part of this plugin (Task R must move the marketplace root)"
  bad "plugins/compound-v-vault loaded as part of superpowers-v"
else
  ok "plugins/compound-v-vault is not loaded as part of this plugin"
fi

# --- the engine's test runner -----------------------------------------------------------------
out="$("${CLAUDE[@]}" plugin test . 2>&1)"; rc=$?
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -qE '^ *0 fail' && printf '%s' "$out" | grep -qE '^ *[1-9][0-9]* pass'; then
  ok "plugin test: $(printf '%s' "$out" | grep -E '^ *[0-9]+ pass' | tr -s ' ')"
else
  bad "plugin test (rc=$rc)"; printf '%s\n' "$out" | tail -25
fi
printf '%s' "$out" | grep -qF 'hooks/jev-t3.test.tsx:' && ok "plugin test ran hooks/jev-t3.test.tsx" || bad "jev-t3 tests not run"
if printf '%s' "$out" | grep -qF 'vault.test.tsx'; then
  bad "the vault's tests ran as this plugin's"
else
  ok "the vault's tests are not run as this plugin's"
fi

echo "tests/test-jev-t3-mod.sh: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
