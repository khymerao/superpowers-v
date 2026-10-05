import { expect, mock, test } from 'claude-code/testing'

// Every test runs against a world mocked noun by noun beneath the plugin. The key is a fake
// with the real prefix, so a leak anywhere is found by a plain substring search.
// Spelled in pieces, so that no key-shaped literal sits in the tree for a grep to trip on.
const KEY = 'sk-' + 'or-v1-vaulttest-0123456789abcdef0123456789abcdef'
const BEARER = 'Bear' + 'er '

// A consumer, as Compound V's own modules are: it reaches the vault only through `$.jev`. A test
// drives it with the probe command, since a test's own `$` carries no plugin noun.
const CONSUMER = {
  name: 'jev-consumer',
  register: (on: any) => {
    on('command.run', { command: 'jev-probe' }, async ($: any, e: any) => {
      const { method, arg } = JSON.parse(e.args)
      const value = method === 'status' ? await $.jev.status(arg) : await $.jev.classify(arg)

      return { text: JSON.stringify(value) }
    })
  },
}
async function jev($: any, method: 'classify' | 'status', arg: unknown): Promise<any> {
  const out = await $.command.run({ command: 'jev-probe', args: JSON.stringify({ method, arg }) })
  const value = JSON.parse(out.text)
  current?.results.push(value)

  return value
}
// Every answer the plugin gives a test (tool results, command text) is recorded for the key check.
async function toolCall($: any, request_file: string): Promise<any> {
  const out = await $.tool.call({ tool: TOOL, input: { request_file } })
  current?.results.push(out)

  return out
}
async function egressCmd($: any, args: string): Promise<string> {
  const out = await $.command.run({ command: 'egress', args })
  current?.results.push(out)

  return out.text
}
const NO_KEY = { plugins: [CONSUMER] }
const WITH_KEY = { plugins: [CONSUMER], options: { openrouter_key: KEY } }
const HOME = '/home/u'
const REPO = '/work/repo'
const ROOT = `${HOME}/.claude/compound-v-jev`
const DD = `${ROOT}/0123456789abcdef`
const REQ_FILE = `${DD}/req/abc.req.json`
const RESP_FILE = `${DD}/resp/abc.resp.json`
const TOOL = 'mcp__compound-v-vault__jev_classify'
const ROUTE = 'https://openrouter.ai/api/v1/systemone'

const BODY = {
  model: 'typesafe/jev-1.13',
  state: { request: 'rename a helper', paths: ['scripts/a.py'], hints: [] },
  questions: { category: { type: 'choice', instructions: 'What kind of change?', criteria: { unknown: 'u', plumbing: 'p' } } },
}
const REQ = {
  point: 't3',
  catalogue_hash: '0123456789abcdef',
  model: 'typesafe/jev-1.13',
  body: BODY,
  timeout_ms: 1500,
  context: 'hook' as const,
  repo: REPO,
}
const OK_BODY = {
  id: 'gen-1',
  provider: 'TypeSafe',
  model: 'typesafe/jev-1.13-20260917',
  answers: { category: { type: 'choice', choice: 'plumbing', probabilities: { plumbing: 1, unknown: 0 }, confidence: 1 } },
  usage: { input_tokens: 120, output_tokens: 3, cost: 0.0001 },
}
const ERROR_TEXT = JSON.stringify({ error: { message: 'Provider returned error', code: 400 }, user_id: 'user_SECRET42' })

type Reply = { status: number; text?: string; headers?: Record<string, string> }
type File = { text?: string; kind?: 'file' | 'dir' | 'other'; isLink?: boolean; realPath?: string }

type WorldOptions = {
  env?: Record<string, string>
  store?: Record<string, unknown>
  replies?: Array<Reply | 'hang'>
  files?: Record<string, File>
}

function world(on: any, opts: WorldOptions = {}) {
  const clock = mock.clock(on, { now: 1_000_000 })
  mock.env(on, { HOME, ...(opts.env ?? {}) })
  const store: Record<string, unknown> = { [`egress:${REPO}`]: 'allow', ...(opts.store ?? {}) }
  if (opts.store !== undefined) {
    for (const k of Object.keys(store)) if (!(k in opts.store)) delete store[k]
  }
  mock.store(on, store)
  const seen = {
    fetches: [] as Array<{ url: string; init: any }>,
    writes: [] as Array<{ path: string; text: string }>,
    toasts: [] as string[],
    statuses: [] as Array<string | undefined>,
    argv: [] as string[][],
    tools: [] as string[],
    commands: [] as string[],
    results: [] as unknown[],
  }
  current = seen
  const files: Record<string, File> = {
    [HOME]: { kind: 'dir' },
    [ROOT]: { kind: 'dir' },
    [REPO]: { kind: 'dir' },
    [`${DD}/resp`]: { kind: 'dir' },
    [REQ_FILE]: { text: JSON.stringify(REQ) },
    ...(opts.files ?? {}),
  }
  const replies = [...(opts.replies ?? [{ status: 200, text: JSON.stringify(OK_BODY) }])]

  on('session.start', () => ({ cwd: REPO }))
  on('session.root', () => ({ value: REPO }))
  on('session.cwd', () => ({ value: REPO }))
  on('tool.register', ($$: any, e: any) => {
    seen.tools.push(e.name)
    return { value: { tool: `mcp__compound-v-vault__${e.name}` } }
  })
  on('command.register', ($$: any, e: any) => {
    seen.commands.push(e.name)
    return { value: { command: e.name } }
  })
  on('ui.toast', ($$: any, e: any) => {
    seen.toasts.push(e.text)
    return { value: undefined }
  })
  on('ui.status', ($$: any, e: any) => {
    seen.statuses.push(e.text)
    return { value: undefined }
  })
  on('fs.stat', ($$: any, e: any) => {
    const f = files[e.path]
    if (f === undefined) throw new Error(`ENOENT: ${e.path}`)
    const real = f.realPath ?? (f.isLink ? undefined : e.path)
    return {
      value: {
        kind: f.kind ?? 'file',
        size: (f.text ?? '').length,
        mtimeMs: 1,
        isLink: f.isLink ?? false,
        ...(e.resolve && real !== undefined ? { realPath: real } : {}),
      },
    }
  })
  on('fs.read', ($$: any, e: any) => {
    const f = files[e.path]
    if (f === undefined || f.text === undefined) throw new Error(`ENOENT: ${e.path}`)
    return { value: f.text }
  })
  on('fs.write', ($$: any, e: any) => {
    seen.writes.push({ path: e.path, text: e.text })
    files[e.path] = { text: e.text }
    return { value: undefined }
  })
  on('process.run', ($$: any, e: any) => {
    seen.argv.push([...e.argv])
    const stdout = e.argv.includes('--show-toplevel') ? `${REPO}\n` : ''
    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('http.fetch', async ($$: any, e: any) => {
    seen.fetches.push({ url: e.url, init: e.init })
    const next = replies.length > 1 ? replies.shift()! : replies[0]!
    if (next === 'hang') {
      await clock.sleep(60_000)
      return { value: { status: 200, ok: true, headers: {}, text: JSON.stringify(OK_BODY) } }
    }
    const status = next.status
    return { value: { status, ok: status >= 200 && status < 300, headers: next.headers ?? {}, text: next.text ?? '' } }
  })
  return { clock, seen, store, files }
}

// The key may appear in exactly one place: the Authorization header of a fetch.
function expectNoKeyOutsideFetchAuth(seen: ReturnType<typeof world>['seen'], extra: unknown[] = []) {
  for (const f of seen.fetches) {
    expect(f.init.headers.Authorization).toBe(BEARER + KEY)
    const { Authorization, ...rest } = f.init.headers
    expect(JSON.stringify({ url: f.url, body: f.init.body, headers: rest }).includes(KEY)).toBe(false)
  }
  const elsewhere = JSON.stringify([seen.writes, seen.toasts, seen.statuses, seen.argv, extra])
  expect(elsewhere.includes(KEY)).toBe(false)
  expect(elsewhere.includes(BEARER)).toBe(false)
}

// The world of the test that runs now; `vtest` checks it once the test body has finished, so
// every test, not only the ones that ask, proves the key never left the Authorization header.
let current: ReturnType<typeof world>['seen'] | undefined
function vtest(name: string, opts: object, body: ($: any, on: any) => Promise<void>) {
  test(name, opts, async ($: any, on: any) => {
    current = undefined
    await body($, on)
    if (current !== undefined) expectNoKeyOutsideFetchAuth(current, current.results)
  })
}

async function start($: any) {
  await $.session.start({ cwd: REPO, surface: 'terminal', isInteractive: true })
}

vtest('one POST with the bearer header and the request body; ok carries latency and the body without usage.cost', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on)
  await start($)
  const res = await jev($, 'classify', REQ)
  expect(seen.fetches).toHaveLength(1)
  const f = seen.fetches[0]!
  expect(f.url).toBe(ROUTE)
  expect(f.init.method).toBe('POST')
  expect(f.init.headers['Content-Type']).toBe('application/json')
  expect(JSON.parse(f.init.body)).toEqual(BODY)
  expect(res.status).toBe('ok')
  expect(typeof res.latency_ms).toBe('number')
  expect(res.body.model).toBe('typesafe/jev-1.13-20260917')
  expect(res.body.usage).toEqual({ input_tokens: 120, output_tokens: 3 })
  expect(JSON.stringify(res).includes('cost')).toBe(false)
  expect(seen.tools).toEqual(['jev_classify'])
  expect(seen.commands).toEqual(['egress'])
  expect(seen.statuses.at(-1)).toBe('Jev: on')
  expectNoKeyOutsideFetchAuth(seen, [res])
})

vtest('no key: unavailable(no_key) and no fetch', NO_KEY, async ($: any, on: any) => {
  const { seen } = world(on)
  await start($)
  const res = await jev($, 'classify', REQ)
  expect(res).toMatchObject({ status: 'unavailable', reason: 'no_key' })
  expect(seen.fetches).toHaveLength(0)
  expect(seen.statuses.at(-1)).toBe('Jev: off (no_key)')
})

vtest('CV_HEADLESS_CLASSIFY=1: unavailable(disabled), no fetch, no tool', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on, { env: { CV_HEADLESS_CLASSIFY: '1' } })
  await start($)
  const res = await jev($, 'classify', REQ)
  expect(res).toMatchObject({ status: 'unavailable', reason: 'disabled' })
  expect(seen.fetches).toHaveLength(0)
  expect(seen.tools).toHaveLength(0)
  expect(await jev($, 'status', REPO)).toEqual({ on: false, reason: 'disabled' })
})

vtest('egress unanswered: unavailable(egress), one toast per session, no fetch', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on, { store: {} })
  await start($)
  expect((await jev($, 'classify', REQ)).reason).toBe('egress')
  expect((await jev($, 'classify', REQ)).reason).toBe('egress')
  expect(seen.fetches).toHaveLength(0)
  expect(seen.toasts).toHaveLength(1)
  expect(seen.toasts[0]).toMatch(/\/egress allow/)
  expect(seen.toasts[0]).toMatch(/OpenRouter/)
  expect(seen.toasts[0]).toMatch(/TypeSafe/)
})

vtest('egress deny: unavailable(egress), no fetch; allow: fetch', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on, { store: { [`egress:${REPO}`]: 'deny' } })
  await start($)
  expect(await jev($, 'classify', REQ)).toMatchObject({ status: 'unavailable', reason: 'egress' })
  expect(seen.fetches).toHaveLength(0)
  expect(seen.toasts).toHaveLength(0) // a recorded deny is an answer: no toast
  expect(await jev($, 'status', REPO)).toEqual({ on: false, reason: 'egress' })
  const out = await egressCmd($, 'allow')
  expect(out).toMatch(/allow/)
  expect(await egressCmd($, 'status')).toMatch(/: allow\.$/)
  expect(seen.statuses.at(-1)).toBe('Jev: on')
  expect((await jev($, 'classify', REQ)).status).toBe('ok')
  expect(seen.fetches).toHaveLength(1)
  expect(await jev($, 'status', REPO)).toEqual({ on: true })
})

vtest('egress command: status, deny, and an unknown word', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on, { store: {} })
  await start($)
  const egress = (args: string) => egressCmd($, args)
  expect(await egress('status')).toMatch(/: not answered\.$/)
  expect(seen.statuses.at(-1)).toBe('Jev: off (egress)')
  expect(await egress('deny')).toMatch(/deny/)
  expect(await egress('status')).toMatch(/: deny\.$/)
  expect(await egress('maybe')).toMatch(/allow\|deny\|status/)
  expect(await egress('status')).toMatch(/: deny\.$/)
  expect(await jev($, 'status', REPO)).toEqual({ on: false, reason: 'egress' })
})

const STATUS_ROWS: Array<[number, string, string]> = [
  [401, 'unavailable', 'auth'],
  [403, 'unavailable', 'auth'],
  [402, 'unavailable', 'credits'],
  [429, 'unavailable', 'rate_limited'],
  [500, 'unavailable', 'upstream'],
  [502, 'unavailable', 'upstream'],
  [524, 'unavailable', 'upstream'],
  [529, 'unavailable', 'upstream'],
  [400, 'error', 'bad_input'],
  [422, 'error', 'bad_input'],
]
for (const [code, status, reason] of STATUS_ROWS) {
  vtest(`HTTP ${code} -> ${status}(${reason}), status kept, no body copied`, WITH_KEY, async ($: any, on: any) => {
    const { seen } = world(on, { replies: [{ status: code, text: ERROR_TEXT, headers: { 'retry-after': '1' } }] })
    await start($)
    const res = await jev($, 'classify', REQ)
    expect(res).toMatchObject({ status, reason, http_status: code })
    expect(res.body).toBeUndefined()
    expect(JSON.stringify(res).includes('user_SECRET42')).toBe(false)
    expect(JSON.stringify(res).includes('Provider returned error')).toBe(false)
    expect(seen.fetches).toHaveLength(1) // hook context: never retried
  })
}

vtest('non-JSON 200 -> error(schema)', WITH_KEY, async ($: any, on: any) => {
  world(on, { replies: [{ status: 200, text: '<html>gateway</html>' }] })
  await start($)
  expect(await jev($, 'classify', REQ)).toMatchObject({ status: 'error', reason: 'schema' })
})

vtest('hook timeout at 1,500 ms -> unavailable(timeout)', WITH_KEY, async ($: any, on: any) => {
  const { clock } = world(on, { replies: ['hang'] })
  await start($)
  let res: any
  const p = jev($, 'classify', REQ).then((r: any) => { res = r })
  await clock.advance(1_499)
  expect(res).toBeUndefined()
  await clock.advance(1)
  await p
  expect(res).toMatchObject({ status: 'unavailable', reason: 'timeout' })
  expect(res.latency_ms).toBe(1_500)
})

vtest('offline timeout at 5,000 ms -> unavailable(timeout)', WITH_KEY, async ($: any, on: any) => {
  const { clock } = world(on, { replies: ['hang'] })
  await start($)
  let res: any
  const p = jev($, 'classify', { ...REQ, context: 'offline', timeout_ms: 5_000 }).then((r: any) => { res = r })
  await clock.advance(4_999)
  expect(res).toBeUndefined()
  await clock.advance(1)
  await p
  expect(res).toMatchObject({ status: 'unavailable', reason: 'timeout' })
})

vtest('offline 429 with retry-after <= 1 s: one retry', WITH_KEY, async ($: any, on: any) => {
  const { clock, seen } = world(on, {
    replies: [{ status: 429, headers: { 'retry-after': '1' } }, { status: 200, text: JSON.stringify(OK_BODY) }],
  })
  await start($)
  let res: any
  const p = jev($, 'classify', { ...REQ, context: 'offline' }).then((r: any) => { res = r })
  await clock.advance(1_000)
  await p
  expect(seen.fetches).toHaveLength(2)
  expect(res.status).toBe('ok')
})

vtest('offline 429 with retry-after absent or > 1 s: no retry', WITH_KEY, async ($: any, on: any) => {
  const { seen } = world(on, {
    replies: [{ status: 429 }, { status: 429, headers: { 'retry-after': '2' } }],
  })
  await start($)
  expect(await jev($, 'classify', { ...REQ, context: 'offline' })).toMatchObject({ reason: 'rate_limited' })
  expect(await jev($, 'classify', { ...REQ, context: 'offline' })).toMatchObject({ reason: 'rate_limited' })
  expect(seen.fetches).toHaveLength(2)
})

vtest('a route that is not https is refused before any fetch', { plugins: [CONSUMER], options: { openrouter_key: KEY, route: 'http://example.test/x' } }, async ($: any, on: any) => {
  const { seen } = world(on)
  await start($)
  expect(await jev($, 'classify', REQ)).toMatchObject({ status: 'error', reason: 'bad_input' })
  expect(seen.fetches).toHaveLength(0)
})

vtest('jev_classify: writes the response beside the request, 0600, and returns its path', WITH_KEY, async ($: any, on: any) => {
  const { seen, files } = world(on)
  await start($)
  const out = await toolCall($, REQ_FILE)
  expect(out.result).toBe(RESP_FILE)
  const written = JSON.parse(files[RESP_FILE]!.text!)
  expect(written.status).toBe('ok')
  expect(written.body.usage.cost).toBeUndefined()
  expect(seen.writes.map(w => w.path)).toEqual([RESP_FILE])
  expect(seen.argv).toContainEqual(['/bin/chmod', '600', RESP_FILE])
  expectNoKeyOutsideFetchAuth(seen, [out])
})

vtest('jev_classify: an error body is never written to the response file', WITH_KEY, async ($: any, on: any) => {
  const { seen, files } = world(on, { replies: [{ status: 400, text: ERROR_TEXT }] })
  await start($)
  const out = await toolCall($, REQ_FILE)
  expect(out.result).toBe(RESP_FILE)
  const text = files[RESP_FILE]!.text!
  expect(JSON.parse(text)).toMatchObject({ status: 'error', reason: 'bad_input', http_status: 400 })
  expect(text.includes('user_SECRET42')).toBe(false)
  expectNoKeyOutsideFetchAuth(seen, [out])
})

const REFUSALS: Array<[string, string, Record<string, File>]> = [
  ['a ../ spelling', `${DD}/req/../../../../etc/passwd.req.json`, {}],
  ['a symbolic link', `${DD}/req/link.req.json`, { [`${DD}/req/link.req.json`]: { isLink: true, realPath: `${DD}/req/x.req.json`, text: '{}' } }],
  ['a file outside req/', `${DD}/resp/abc.req.json`, { [`${DD}/resp/abc.req.json`]: { text: JSON.stringify(REQ) } }],
  ['a file outside the data root', `${REPO}/abc.req.json`, { [`${REPO}/abc.req.json`]: { text: JSON.stringify(REQ) } }],
  ['a path whose real path leaves the root', `${DD}/req/moved.req.json`, { [`${DD}/req/moved.req.json`]: { realPath: '/tmp/moved.req.json', text: '{}' } }],
  ['a directory', `${DD}/req/dir.req.json`, { [`${DD}/req/dir.req.json`]: { kind: 'dir' } }],
  ['a relative path', 'req/abc.req.json', {}],
]
for (const [what, path, extra] of REFUSALS) {
  vtest(`jev_classify refuses ${what}`, WITH_KEY, async ($: any, on: any) => {
    const { seen } = world(on, { files: extra })
    await start($)
    const out = await toolCall($, path)
    expect(String(out.result)).toMatch(/^refused: /)
    expect(seen.fetches).toHaveLength(0)
    expect(seen.writes).toHaveLength(0)
  })
}

vtest('session.append replaces the key with [redacted] in text and tool results', WITH_KEY, async ($: any, on: any) => {
  world(on)
  const stored: any[] = []
  // The test's hook stands for the store: it records the row as the chain hands it down. Nothing
  // beneath a test answers session.append, so the call itself rejects once the row is recorded.
  on('session.append', ($$: any, e: any, next: any) => {
    stored.push(e.message)
    return next(e)
  })
  await start($)
  const swallow = () => undefined
  await $.session.append({
    message: { type: 'user', role: 'user', isMeta: false, content: [{ type: 'text', text: `my key is ${KEY} ok` }] },
    door: 'prompt',
    origin: { kind: 'composer' },
    uuid: 'u1',
  }).catch(swallow)
  await $.session.append({
    message: {
      type: 'user',
      role: 'user',
      isMeta: false,
      content: [{ type: 'tool_result', tool_use_id: 't1', content: [{ type: 'text', text: `env: ${KEY}` }] }],
    },
    door: 'tool-result',
    origin: { kind: 'tool', tool: 'Bash' },
    uuid: 'u2',
  }).catch(swallow)
  expect(stored).toHaveLength(2)
  const text = JSON.stringify(stored)
  expect(text.includes(KEY)).toBe(false)
  expect(text).toMatch(/my key is \[redacted\] ok/)
  expect(text).toMatch(/env: \[redacted\]/)
})
