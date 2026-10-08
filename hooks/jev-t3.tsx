import type { EngineInterface, Register } from 'claude-code'

import type { JevT3ClaudeMeasure, JevT3Descriptor, JevT3Noun, JevT3Response } from '../types'
import { register as registerRunBand } from './run-band'

// Compound V T3 shadow (spec 1): after the triage hook has decided, ask Jev the same T3 question
// and store the pair. Nothing here changes a decision: the classic UserPromptSubmit result is
// returned exactly as the hooks beneath produced it, whatever Jev answers or fails to answer.
//
// - classic.UserPromptSubmit, before the hooks beneath run: CV_JEV_T3=1 (a non-secret capability
//   flag the triage hook reads) only when the compound-v-vault noun is present, says Jev is on for
//   this repository, and the committed config resolves `jev.t3.mode` to `shadow`; otherwise the
//   flag is unset. (Not in session.start: this plugin's one module also carries the run band,
//   which owns that hook, and the engine takes one unmatched session.start per load.)
// - classic.UserPromptSubmit, after: once the hooks beneath have answered, pick up the descriptor
//   the triage hook left for this (project, session), send its request file through `$.jev`, write
//   the response file, run `compound-v-jev.py parse` then `pair`, and delete the descriptor.
//
// The key never reaches this module: the vault is the only HTTP client. Every process is a fixed
// argv of file paths and short tokens (never request text), capped at 30 s. The one exception to
// "short tokens" is `pair --claude-measure-json`: compact JSON this module rebuilds itself from
// validated integers, null and a model id, so it carries no text it did not construct.

const PROCESS_TIMEOUT_MS = 30_000
// The UserPromptSubmit registration's `timeout: 25` in hooks.json: what is left of it when Jev has
// answered is recorded as measured, so a later spec can see whether a decision would have fitted.
const HOOK_BUDGET_MS = 25_000
const MAX_PENDING = 50
const MAX_WALK_UP = 40
const SAFE_NAME = /^[A-Za-z0-9._-]+$/

// Per load, by project real path: the data directory compound-v-jev.py resolved, and whether the
// committed config asks for T3 shadow. register() starts both over.
const mem: { dataDirs: Record<string, string>; shadow: Record<string, boolean> } = { dataDirs: {}, shadow: {} }

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

// `$` as this module reaches it. The `jev` noun belongs to the separate compound-v-vault plugin and
// is often absent, so it is typed here, not declared on EngineInterface, and every use is a guarded
// call: the engine's static check takes `$` only as `$.noun.event(...)`, which rules out an
// `'jev' in $` test, and without the vault the call throws.
type JevT3Engine = EngineInterface & { jev: JevT3Noun }

/** Whether Jev is on for this project: true or false as the vault says, null when there is no vault. */
async function jevStatus($: JevT3Engine, proj: string): Promise<boolean | null> {
  let answer: unknown
  try {
    answer = await $.jev.status(proj)
  } catch {
    return null
  }

  return isRecord(answer) && answer.on === true
}

async function isHeadless($: EngineInterface): Promise<boolean> {
  const v = await $.env.get('CV_HEADLESS_CLASSIFY')

  return v !== undefined && v !== '' && v !== '0'
}

/** As the triage hook does: the real path of `cwd`, then up to the nearest ancestor holding `.git`. */
async function projectRoot($: EngineInterface, cwd: string): Promise<string | null> {
  let real: string | undefined
  try {
    real = (await $.fs.stat(cwd, { resolve: true })).realPath
  } catch {
    return null
  }
  if (!real || !real.startsWith('/')) {
    return null
  }
  let d = real
  for (let i = 0; i < MAX_WALK_UP; i += 1) {
    if (await $.fs.exists(`${d}/.git`)) {
      return d
    }
    if (d === '/') {
      break
    }
    const up = d.slice(0, d.lastIndexOf('/')) || '/'
    if (up === d) {
      break
    }
    d = up
  }

  return real
}

async function python($: EngineInterface, script: string, args: string[]): Promise<unknown> {
  const argv = ['python3', '-B', `${$.plugin.root}/scripts/${script}`, ...args]
  const { exitCode, stdout } = await $.process.run(argv, { timeoutMs: PROCESS_TIMEOUT_MS })
  if (exitCode !== 0) {
    return null
  }
  try {
    return JSON.parse(stdout)
  } catch {
    return null
  }
}

async function isShadowConfigured($: EngineInterface, proj: string): Promise<boolean> {
  const doc = await python($, 'compound-v-project-config.py', [proj])
  const jev = isRecord(doc) && isRecord(doc.jev) ? doc.jev : null
  const t3 = jev && isRecord(jev.t3) ? jev.t3 : null

  return jev !== null && jev.enabled === true && t3 !== null && t3.mode === 'shadow'
}

/**
 * CV_JEV_T3=1 when the vault noun is present, Jev is on for this project and the committed config
 * resolves `jev.t3.mode` to `shadow`; unset otherwise. The config verdict is read once per project
 * per load; the vault's answer is asked every time, so `/egress allow` given
 * mid-session counts from the next prompt.
 */
async function refreshFlag($: JevT3Engine, cwd: unknown): Promise<void> {
  let on = false
  if (typeof cwd === 'string' && !(await isHeadless($))) {
    const proj = await projectRoot($, cwd)
    // The vault first: with no vault there is no config process to start.
    if (proj !== null && (await jevStatus($, proj)) === true) {
      let isShadow = mem.shadow[proj]
      if (isShadow === undefined) {
        isShadow = await isShadowConfigured($, proj)
        mem.shadow[proj] = isShadow
      }
      on = isShadow
    }
  }
  const now = await $.env.get('CV_JEV_T3')
  if (on && now !== '1') {
    await $.env.set('CV_JEV_T3', '1')
  } else if (!on && now !== undefined) {
    await $.env.set('CV_JEV_T3', undefined)
  }
}

async function dataDir($: EngineInterface, proj: string): Promise<string | null> {
  const known = mem.dataDirs[proj]
  if (known !== undefined) {
    return known
  }
  const doc = await python($, 'compound-v-jev.py', ['data-dir', '--repo', proj])
  if (!isRecord(doc) || doc.status !== 'ok' || typeof doc.data_dir !== 'string' || !doc.data_dir.startsWith('/')) {
    return null
  }
  mem.dataDirs[proj] = doc.data_dir

  return doc.data_dir
}

function asDescriptor(v: unknown): JevT3Descriptor | null {
  if (!isRecord(v)) {
    return null
  }
  const keys = ['pre_eval_id', 'request_file', 't3_reason', 'claude_category', 'backend', 'proj', 'sid'] as const
  for (const k of keys) {
    if (typeof v[k] !== 'string') {
      return null
    }
  }
  // The eighth key is optional, and a string when present.
  if (v.claude_measure !== undefined && typeof v.claude_measure !== 'string') {
    return null
  }

  return v as unknown as JevT3Descriptor
}

const MEASURE_INTS = ['wall_ms', 'duration_ms', 'duration_api_ms'] as const
const MEASURE_TOKENS = ['input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens'] as const
const MEASURE_MODEL = /^[A-Za-z0-9._/:[\]~-]{1,80}$/
const MEASURE_MAX_CHARS = 1024

function measureInt(v: unknown): number | null | undefined {
  if (v === undefined || v === null) {
    return null
  }

  return typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : undefined
}

/**
 * The descriptor's measure, rebuilt from validated numbers and re-serialised, or null. Only what
 * this returns reaches `pair`'s argv: a closed key set of non-negative integers or null and a model
 * id. A malformed or absent measure never drops the pair; the pair is written without it.
 */
function measureArg(text: string | undefined): string | null {
  if (typeof text !== 'string' || text === '' || text.length > MEASURE_MAX_CHARS) {
    return null
  }
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    return null
  }
  if (!isRecord(raw) || !Object.keys(raw).every(k => ['wall_ms', 'duration_ms', 'duration_api_ms', 'tokens', 'model'].includes(k))) {
    return null
  }
  const tokensRaw = raw.tokens === undefined || raw.tokens === null ? {} : raw.tokens
  if (!isRecord(tokensRaw) || !Object.keys(tokensRaw).every(k => (MEASURE_TOKENS as readonly string[]).includes(k))) {
    return null
  }
  const out: JevT3ClaudeMeasure = {
    wall_ms: null,
    duration_ms: null,
    duration_api_ms: null,
    tokens: { input_tokens: null, output_tokens: null, cache_read_input_tokens: null, cache_creation_input_tokens: null },
    model: null,
  }
  for (const k of MEASURE_INTS) {
    const n = measureInt(raw[k])
    if (n === undefined) {
      return null
    }
    out[k] = n
  }
  for (const k of MEASURE_TOKENS) {
    const n = measureInt(tokensRaw[k])
    if (n === undefined) {
      return null
    }
    out.tokens[k] = n
  }
  if (raw.model !== undefined && raw.model !== null) {
    if (typeof raw.model !== 'string' || !MEASURE_MODEL.test(raw.model)) {
      return null
    }
    out.model = raw.model
  }

  return JSON.stringify(out)
}

/** The descriptor the triage hook left for this (project, session), and its path; matched by content. */
async function findPending(
  $: EngineInterface,
  dd: string,
  proj: string,
  sid: string,
): Promise<{ path: string; desc: JevT3Descriptor | null } | null> {
  const names = (await $.fs.list(dd))
    .filter(f => f.kind === 'file' && !f.isLink && f.name.startsWith('pending-') && f.name.endsWith('.json'))
    .map(f => f.name)
    .sort()
    .slice(0, MAX_PENDING)
  for (const name of names) {
    const path = `${dd}/${name}`
    let doc: unknown
    try {
      doc = JSON.parse(String(await $.fs.read(path)))
    } catch {
      continue
    }
    if (isRecord(doc) && doc.sid === sid && doc.proj === proj) {
      return { path, desc: asDescriptor(doc) }
    }
  }

  return null
}

function asResponse(v: unknown, latency: number): JevT3Response {
  if (isRecord(v) && (v.status === 'ok' || v.status === 'unavailable' || v.status === 'error')) {
    return v as unknown as JevT3Response
  }

  return { status: 'error', reason: 'schema', latency_ms: latency }
}

async function runShadow($: JevT3Engine, dd: string, proj: string, desc: JevT3Descriptor, started: number) {
  const m = /^([^/]+)\.req\.json$/.exec(desc.request_file.startsWith(`${dd}/req/`) ? desc.request_file.slice(dd.length + 5) : '')
  if (m === null || !SAFE_NAME.test(m[1]!) || m[1]!.startsWith('.')) {
    return
  }
  for (const token of [desc.claude_category, desc.backend, desc.t3_reason]) {
    if (!SAFE_NAME.test(token)) {
      return
    }
  }
  const req = JSON.parse(String(await $.fs.read(desc.request_file)))

  const asked = await $.clock.now()
  let res: JevT3Response
  try {
    res = asResponse(await $.jev.classify(req), (await $.clock.now()) - asked)
  } catch {
    res = { status: 'unavailable', reason: 'upstream', latency_ms: (await $.clock.now()) - asked }
  }
  const left = Math.max(0, Math.round(HOOK_BUDGET_MS - ((await $.clock.now()) - started)))

  const respFile = `${dd}/resp/${m[1]}.resp.json`
  await $.fs.write(respFile, JSON.stringify(res))
  await $.process.run(['/bin/chmod', '600', respFile], { timeoutMs: PROCESS_TIMEOUT_MS })

  await python($, 'compound-v-jev.py', [
    'parse',
    '--response-file',
    respFile,
    '--request-file',
    desc.request_file,
    '--repo',
    proj,
    '--mode',
    'shadow',
    '--hook-budget-left-ms',
    String(left),
  ])
  const measure = measureArg(desc.claude_measure)
  await python($, 'compound-v-jev.py', [
    'pair',
    '--request-file',
    desc.request_file,
    '--claude-category',
    desc.claude_category,
    '--backend',
    desc.backend,
    '--t3-reason',
    desc.t3_reason,
    '--repo',
    proj,
    ...(measure === null ? [] : ['--claude-measure-json', measure]),
  ])
}

async function recordShadow($: JevT3Engine, e: { session_id?: unknown; cwd?: unknown }, started: number): Promise<void> {
  if (await isHeadless($)) {
    return
  }
  // Refreshed by this same prompt: '1' only while the vault is present and on, and shadow configured.
  if ((await $.env.get('CV_JEV_T3')) !== '1') {
    return
  }
  if (typeof e.session_id !== 'string' || e.session_id === '' || typeof e.cwd !== 'string') {
    return
  }
  const proj = await projectRoot($, e.cwd)
  if (proj === null) {
    return
  }
  const dd = await dataDir($, proj)
  if (dd === null) {
    return
  }
  const pending = await findPending($, dd, proj, e.session_id)
  if (pending === null) {
    return
  }
  try {
    if (pending.desc !== null) {
      await runShadow($, dd, proj, pending.desc, started)
    }
  } finally {
    await $.process.run(['/bin/rm', '-f', pending.path], { timeoutMs: PROCESS_TIMEOUT_MS })
  }
}

// This plugin's only hooks module (hooks.json takes one per plugin, and a load registers an
// unmatched `session.start` once): it registers the run band's hooks first, unchanged, then its own.
export const register: Register = (on, options) => {
  mem.dataDirs = {}
  mem.shadow = {}
  registerRunBand(on, options)

  on('classic.UserPromptSubmit', async ($, e, next) => {
    let started = 0
    try {
      started = await $.clock.now()
      // Before the hooks beneath run: the triage hook reads the flag from its environment.
      await refreshFlag($ as JevT3Engine, e.cwd)
    } catch {
      try {
        await $.env.set('CV_JEV_T3', undefined)
      } catch {
        // the flag stays as it was; the triage hook's own path is unchanged either way
      }
    }
    const res = await next(e)
    try {
      await recordShadow($ as JevT3Engine, e, started)
    } catch {
      // shadow is best effort: a failure here never reaches the prompt
    }

    return res
  })
}
