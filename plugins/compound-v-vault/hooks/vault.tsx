// compound-v-vault: holds the OpenRouter key for Compound V's Jev classifier and is its only
// HTTP client. The key lives in this plugin's sensitive userConfig (secure storage), reaches this
// module as `options.openrouter_key`, and leaves it only as the Authorization header of
// `$.http.fetch`. It is never written to a file, a tool result, a status line, a toast, an argv or
// the transcript. This module never answers a Bash tool call.
//
// Step 1, API confirmed 2026-10-05 from the plugin-authoring skill's types/claude-code.d.ts and
// reference.md, then checked against the pinned CLI (Claude Code 2.1.289) by `claude plugin
// validate` and by the tests in ../.tests/vault.test.tsx under `claude plugin test`:
// - engine.create: a step runs post-order, `const built = await next(e)`, and returns
//   `{ ...built, jev }` to ADD a noun; it may not replace another step's noun. Its own `$` is empty
//   (NoEngineInterface). A noun's methods are events (`jev.classify`, `jev.status`): this plugin
//   serves `jev.classify` with its own hook, which has a `$` of its own. A hook's input is an
//   object, so `jev.status(repo: string)` is answered by the noun's body from state the hooks
//   keep. Other plugins can hook these events too (README, "Boundary").
// - $.http.fetch(url: string, init?: { method?, headers?: Record<string,string>, body?: string,
//   auth?, socketPath? }) => Promise<{ status: number, ok: boolean, headers: Record<string,string>
//   (lower-cased names), text: string }>. It takes no timeout and no signal.
// - Timeout race: `$.clock.after(ms, fn) => Timer` with `cancel()`, raced against the fetch;
//   `$.clock.now()` for latency; `$.clock.sleep(ms)` for the one offline 429 retry.
// - $.store.get(key) => Promise<unknown>; $.store.set(key, value) => Promise<void> (JSON, kept
//   across sessions, the plugin's own file under the user's config directory).
// - $.tool.register({ name, description, inputSchema }) => Promise<{ tool }>, listed as
//   mcp__<plugin>__<name>, served by a `tool.call` hook returning `{ result }`; rejects before
//   session.start binds the session.
// - $.command.register({ name, description, argumentHint? }) => Promise<{ command }>, served by a
//   `command.run` hook returning `{ text }`.
// - $.ui.status(text | undefined): void; $.ui.toast(text, { timeoutMs? }): void.
// - $.env.get(name: string literal) => Promise<string | undefined>.
// - $.fs.stat(path, { resolve: true }) => { kind, size, mtimeMs, isLink, realPath? };
//   $.fs.read(path) => text; $.fs.write(path, text) => void (no mode argument, so the response
//   file is chmod'ed 0600 through $.process.run(argv) with a fixed argv holding only its path).
// - session.append: `next({ ...e, message: { ...e.message, content } })` rewrites a row's text
//   blocks and tool_result content before it is stored.
// - claude plugin test: a test's `on('http.fetch', ...)` sits beneath the plugin and answers the
//   fetch (`{ value: HttpResponse }`), so http.fetch is stubbed with no network; mock.clock,
//   mock.store and mock.env answer the clock, the store and the environment.
// - claude plugin test <dir> runs every *.test.ts(x) under <dir> and skips dot-folders. The tests
//   therefore live in ../.tests/, so the root plugin's own `claude plugin test .` never runs them
//   against the wrong plugin; tests/test-vault-mod.sh runs them from a staged copy of this folder.

import type { Jev, JevRequest, JevResponse } from '../types'

const DEFAULT_ROUTE = 'https://openrouter.ai/api/v1/systemone'
const HOOK_TIMEOUT_MS = 1_500
const OFFLINE_TIMEOUT_MS = 5_000
const RETRY_AFTER_MAX_MS = 1_000
const TOOL_NAME = 'jev_classify'
const COMMAND_NAME = 'egress'
const DATA_ROOT = '/.claude/compound-v-jev'
const REDACTED = '[redacted]'
// The auth scheme, spelled in two pieces so that no key-shaped literal sits in the tree.
const AUTH_SCHEME = 'Bear' + 'er '
const EGRESS_ASK =
  'Jev is off for this repository until you answer /egress allow (or deny). ' +
  'Allowing sends request text, file paths, taxonomy hints and file heads to OpenRouter and TypeSafe.'
const TOOL_DESCRIPTION =
  'Send one Compound V Jev request file to the System One classifier and write its response. ' +
  'request_file must be a <name>.req.json file under ~/.claude/compound-v-jev/<repo-digest>/req/, as ' +
  'written by scripts/compound-v-jev.py build. Returns the response file path (the sibling resp/ ' +
  'directory, <name>.resp.json), or "refused: <reason>".'

// What one load of the module holds: the key and route from `options`, whether this session has
// shown the egress toast, and what the hooks last read of the recursion guard and of the egress
// answers (by repository real path), which `jev.status` answers from.
type Vault = { key: string; route: string; asked: boolean; disabled: boolean; consent: Record<string, string> }

type Reply = { status: number; headers: Record<string, string>; text: string } | 'timeout' | 'network'

// `jev.status` is answered by the noun's own body: its input is a string, and the engine hands a
// hook only an object input, so no hook (and no `$`) can serve it. It reads what the hooks keep
// current: the guard and the answers loaded at session.start and refreshed by every classify and
// every egress command. `repo` is the repository's absolute real path.
function statusFrom(vault: Vault, repo: unknown): { on: boolean; reason?: string } {
  if (vault.disabled) return { on: false, reason: 'disabled' }
  if (vault.key === '') return { on: false, reason: 'no_key' }
  if (!vault.route.startsWith('https://')) return { on: false, reason: 'route' }
  if (typeof repo !== 'string' || !repo.startsWith('/')) return { on: false, reason: 'repo' }

  return vault.consent[repo] === 'allow' ? { on: true } : { on: false, reason: 'egress' }
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function unavailable(reason: string, latency_ms = 0, http_status?: number): JevResponse {
  return http_status === undefined
    ? { status: 'unavailable', reason, latency_ms }
    : { status: 'unavailable', reason, http_status, latency_ms }
}

function failed(reason: string, latency_ms = 0, http_status?: number): JevResponse {
  return http_status === undefined
    ? { status: 'error', reason, latency_ms }
    : { status: 'error', reason, http_status, latency_ms }
}

// What a non-2xx status means. The body is never read for these: OpenRouter's error bodies carry
// the account's user_id.
function byStatus(code: number, latency: number): JevResponse {
  if (code === 401 || code === 403) return unavailable('auth', latency, code)
  if (code === 402) return unavailable('credits', latency, code)
  if (code === 429) return unavailable('rate_limited', latency, code)
  if (code >= 500) return unavailable('upstream', latency, code)
  if (code >= 400) return failed('bad_input', latency, code)

  return failed('schema', latency, code)
}

// A 2xx body: a JSON object, or error(schema). usage.cost is dropped, never passed on.
function okBody(text: string, latency: number): JevResponse {
  let body: unknown
  try {
    body = JSON.parse(text)
  } catch {
    return failed('schema', latency)
  }
  if (!isRecord(body)) return failed('schema', latency)
  const usage = body.usage
  if (isRecord(usage) && 'cost' in usage) {
    const kept: Record<string, unknown> = {}
    for (const k of Object.keys(usage)) if (k !== 'cost') kept[k] = usage[k]
    body = { ...body, usage: kept }
  }

  return { status: 'ok', latency_ms: latency, body }
}

// Retry-After in seconds, numeric form only; an absent or HTTP-date header means no retry.
function retryAfterMs(headers: Record<string, string>): number | undefined {
  const raw = headers['retry-after']
  if (raw === undefined || !/^\d+(\.\d+)?$/.test(raw.trim())) return undefined

  return Math.round(Number(raw.trim()) * 1000)
}

function validRequest(req: unknown): req is JevRequest {
  if (!isRecord(req) || !isRecord(req.body)) return false
  if (typeof req.body.model !== 'string' || !isRecord(req.body.questions)) return false
  if (req.context !== 'hook' && req.context !== 'offline') return false

  return typeof req.repo === 'string' && req.repo.startsWith('/')
}

function redactText(text: string, key: string): string {
  return text.split(key).join(REDACTED)
}

function redactBlocks(content: unknown, key: string): unknown {
  if (typeof content === 'string') return redactText(content, key)
  if (!Array.isArray(content)) return content

  return content.map((block: unknown) => {
    if (!isRecord(block)) return block
    if (block.type === 'text' && typeof block.text === 'string') return { ...block, text: redactText(block.text, key) }
    if (block.type === 'tool_result') return { ...block, content: redactBlocks(block.content, key) }

    return block
  })
}

async function isDisabled($: any): Promise<boolean> {
  const v = await $.env.get('CV_HEADLESS_CLASSIFY')

  return v !== undefined && v !== '' && v !== '0'
}

async function realPath($: any, path: string): Promise<string | undefined> {
  try {
    return (await $.fs.stat(path, { resolve: true })).realPath
  } catch {
    return undefined
  }
}

// Why a call for this repository would not be sent now, or undefined when it would.
async function offReason($: any, vault: Vault, repo: string): Promise<string | undefined> {
  if (await isDisabled($)) return 'disabled'
  if (vault.key === '') return 'no_key'
  if (!vault.route.startsWith('https://')) return 'route'
  const repoReal = await realPath($, repo)
  if (repoReal === undefined) return 'repo'

  return (await $.store.get(`egress:${repoReal}`)) === 'allow' ? undefined : 'egress'
}

// One POST, raced against what is left of the deadline.
async function fetchBefore($: any, vault: Vault, body: unknown, deadline: number): Promise<Reply> {
  const remaining = deadline - (await $.clock.now())
  if (remaining <= 0) return 'timeout'
  let timer: { cancel: () => void } | undefined
  const timeout = new Promise<Reply>(resolve => {
    timer = $.clock.after(remaining, () => resolve('timeout'))
  })
  const call: Promise<Reply> = $.http
    .fetch(vault.route, {
      method: 'POST',
      headers: { Authorization: AUTH_SCHEME + vault.key, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    .then((r: any) => ({ status: r.status, headers: r.headers ?? {}, text: r.text ?? '' }))
    .catch(() => 'network' as const)
  try {
    return await Promise.race([call, timeout])
  } finally {
    timer?.cancel()
  }
}

async function send($: any, vault: Vault, req: JevRequest): Promise<JevResponse> {
  const offline = req.context === 'offline'
  const cap = offline ? OFFLINE_TIMEOUT_MS : HOOK_TIMEOUT_MS
  const asked = typeof req.timeout_ms === 'number' && req.timeout_ms > 0 ? req.timeout_ms : cap
  const started = await $.clock.now()
  const deadline = started + Math.min(asked, cap)
  let reply = await fetchBefore($, vault, req.body, deadline)
  if (offline && typeof reply === 'object' && reply.status === 429) {
    const wait = retryAfterMs(reply.headers)
    if (wait !== undefined && wait <= RETRY_AFTER_MAX_MS && (await $.clock.now()) + wait < deadline) {
      await $.clock.sleep(wait)
      reply = await fetchBefore($, vault, req.body, deadline)
    }
  }
  const latency = (await $.clock.now()) - started
  if (reply === 'timeout') return unavailable('timeout', latency)
  if (reply === 'network') return unavailable('upstream', latency)
  if (reply.status >= 200 && reply.status < 300) return okBody(reply.text, latency)

  return byStatus(reply.status, latency)
}

async function classify($: any, vault: Vault, req: unknown): Promise<JevResponse> {
  try {
    if (await isDisabled($)) return unavailable('disabled')
    if (vault.key === '') return unavailable('no_key')
    if (!validRequest(req) || !vault.route.startsWith('https://')) return failed('bad_input')
    const repoReal = await realPath($, req.repo)
    if (repoReal === undefined) return failed('bad_input')
    const consent = await $.store.get(`egress:${repoReal}`)
    if (consent === 'allow' || consent === 'deny') vault.consent[repoReal] = consent
    else delete vault.consent[repoReal]
    if (consent !== 'allow') {
      if (consent !== 'deny' && !vault.asked) {
        vault.asked = true
        $.ui.toast(EGRESS_ASK, { timeoutMs: 15_000 })
      }

      return unavailable('egress')
    }

    return await send($, vault, req)
  } catch {
    return unavailable('upstream')
  }
}

// The repository the session works in: git's top level from the session root, else the root.
async function sessionRepo($: any): Promise<string | undefined> {
  const root: string = await $.session.root()
  try {
    const out = await $.process.run(['git', 'rev-parse', '--show-toplevel'], { cwd: root })
    const top = out.exitCode === 0 ? out.stdout.trim() : ''

    return await realPath($, top !== '' ? top : root)
  } catch {
    return realPath($, root)
  }
}

async function showStatus($: any, vault: Vault): Promise<void> {
  const repo = await sessionRepo($)
  const reason = repo === undefined ? 'repo' : await offReason($, vault, repo)
  $.ui.status(reason === undefined ? 'Jev: on' : `Jev: off (${reason})`)
}

// jev_classify: one request file under ~/.claude/compound-v-jev/<dir>/req/, checked by real path.
async function serveTool($: any, vault: Vault, input: unknown): Promise<string> {
  if (await isDisabled($)) return 'refused: disabled'
  const given = isRecord(input) ? input.request_file : undefined
  if (typeof given !== 'string' || !given.startsWith('/')) return 'refused: request_file must be an absolute path'
  if (given.split('/').some(part => part === '..' || part === '.')) return 'refused: request_file must not contain . or .. segments'
  const home = await $.env.get('HOME')
  if (home === undefined || home === '') return 'refused: HOME is not set'
  const rootReal = await realPath($, `${home}${DATA_ROOT}`)
  if (rootReal === undefined) return 'refused: no Jev data directory'
  let stat: any
  try {
    stat = await $.fs.stat(given, { resolve: true })
  } catch {
    return 'refused: request_file not found'
  }
  if (stat.isLink) return 'refused: request_file is a symbolic link'
  if (stat.kind !== 'file') return 'refused: request_file is not a regular file'
  const real: string | undefined = stat.realPath
  if (real === undefined || !real.startsWith(`${rootReal}/`)) return 'refused: request_file is outside the Jev data directory'
  const m = /^([^/]+)\/req\/([^/]+)\.req\.json$/.exec(real.slice(rootReal.length + 1))
  if (m === null) return 'refused: request_file must be <dir>/req/<name>.req.json'
  let req: unknown
  try {
    req = JSON.parse(await $.fs.read(real))
  } catch {
    return 'refused: request_file is not JSON'
  }
  const res = await classify($, vault, req)
  const respPath = `${rootReal}/${m[1]}/resp/${m[2]}.resp.json`
  await $.fs.write(respPath, JSON.stringify(res))
  try {
    await $.process.run(['/bin/chmod', '600', respPath])
  } catch {
    // The resp/ directory is 0700 already; a failed chmod leaves the file reachable only through it.
  }

  return respPath
}

async function egressCommand($: any, vault: Vault, args: string): Promise<string> {
  const word = args.trim().toLowerCase()
  const repo = await sessionRepo($)
  if (repo === undefined) return 'Jev egress: no repository found for this session.'
  const storeKey = `egress:${repo}`
  if (word === 'allow' || word === 'deny') {
    await $.store.set(storeKey, word)
    vault.consent[repo] = word
    await showStatus($, vault)

    return word === 'allow'
      ? `Jev egress: allow for ${repo}. Jev requests from it go to OpenRouter (TypeSafe System One).`
      : `Jev egress: deny for ${repo}. Nothing from it is sent to Jev.`
  }
  if (word === 'status' || word === '') {
    const v = await $.store.get(storeKey)
    const answer = v === 'allow' || v === 'deny' ? v : 'not answered'

    return `Jev egress for ${repo}: ${answer}.`
  }

  return 'Usage: /egress allow|deny|status'
}

async function startSession($: any, vault: Vault): Promise<void> {
  vault.asked = false
  vault.disabled = await isDisabled($)
  vault.consent = {}
  for (const k of await $.store.keys()) {
    if (!k.startsWith('egress:')) continue
    const v = await $.store.get(k)
    if (v === 'allow' || v === 'deny') vault.consent[k.slice('egress:'.length)] = v
  }
  if (!vault.disabled) {
    await $.tool.register({
      name: TOOL_NAME,
      description: TOOL_DESCRIPTION,
      inputSchema: {
        type: 'object',
        properties: { request_file: { type: 'string', description: 'Absolute path of the request file' } },
        required: ['request_file'],
        additionalProperties: false,
      },
    })
    await $.command.register({
      name: COMMAND_NAME,
      description: 'Allow, deny or show whether Jev requests may leave this machine for this repository',
      argumentHint: 'allow|deny|status',
    })
  }
  await showStatus($, vault)
}

export function register(on: any, options: Record<string, unknown> = {}) {
  const vault: Vault = {
    key: typeof options.openrouter_key === 'string' ? options.openrouter_key.trim() : '',
    route: typeof options.route === 'string' && options.route !== '' ? options.route : DEFAULT_ROUTE,
    asked: false,
    disabled: false,
    consent: {},
  }
  // The noun as engine.create adds it. `classify` is an event this plugin serves with its own
  // `jev.classify` hook (a hook has a `$`); its body here answers only when no hook does.
  const noun: Jev = {
    classify: async () => unavailable('no_vault'),
    status: async (repo: string) => statusFrom(vault, repo),
  }

  on('engine.create', async ($: any, e: any, next: any) => {
    const built = await next(e)

    return { ...built, jev: noun }
  })

  on('jev.classify', async ($: any, e: any) => ({ value: await classify($, vault, e) }))

  on('session.start', async ($: any, e: any, next: any) => {
    const started = await next(e)
    await startSession($, vault)

    return started
  })

  on('tool.call', { tool: 'mcp__compound-v-vault__jev_classify' }, async ($: any, e: any) => ({
    result: await serveTool($, vault, e.input),
  }))

  on('command.run', { command: COMMAND_NAME }, async ($: any, e: any) => ({
    text: await egressCommand($, vault, e.args ?? ''),
  }))

  // Backstop: a row that would store the key stores [redacted] in its place.
  on('session.append', ($: any, e: any, next: any) => {
    if (vault.key.length < 8 || !JSON.stringify(e.message?.content ?? '').includes(vault.key)) return next(e)

    return next({ ...e, message: { ...e.message, content: redactBlocks(e.message.content, vault.key) } })
  })
}
