import { expect, mock, test } from 'claude-code/testing'

// hooks/jev-t3.tsx asks Jev the T3 question in shadow, after the triage hook (the classic
// UserPromptSubmit chain beneath it) has decided. Every test checks the one invariant that matters
// most: the module hands back the classic result it was given, deep-equal, whatever Jev answered.

const REPO = '/repo'
const SID = 'sess-1'
const PLUGIN_ROOT_SCRIPT = /\/scripts\/compound-v-(jev|project-config)\.py$/
const DD = '/home/u/.claude/compound-v-jev/0123456789abcdef'
const PENDING = `${DD}/pending-abc.json`
const REQ_FILE = `${DD}/req/r1.req.json`
const RESP_FILE = `${DD}/resp/r1.resp.json`
const REQUEST_TEXT = 'Change the checkout button label to Buy now'
const REQ = {
  point: 't3',
  catalogue_hash: '0123456789abcdef',
  model: 'typesafe/jev-1.13',
  body: { model: 'typesafe/jev-1.13', state: { request: REQUEST_TEXT, paths: ['web/Checkout.tsx'], hints: [] }, questions: {} },
  timeout_ms: 1500,
  context: 'hook',
  repo: REPO,
}
const DESCRIPTOR = {
  pre_eval_id: 'pe-1',
  request_file: REQ_FILE,
  t3_reason: 'demotion',
  claude_category: 'user-facing-minor',
  backend: 'claude',
  proj: REPO,
  sid: SID,
}
const OK = { status: 'ok', latency_ms: 312, body: { model: 'typesafe/jev-1.13-20260917', answers: {} } }
const RES = { additionalContext: ['Compound V triage: SCOPED (pre-eval pe-1)'] }

// The fake vault: an inline plugin that adds the `jev` noun the way compound-v-vault does. An inline
// plugin runs in an environment of its own and sees no variable of this file, so its noun is
// self-contained: `status` says on for exactly REPO's path (proving the module asks about the
// project), and `classify` is answered beneath every plugin by the test's own `jev.classify` hook.
const FAKE_VAULT_ON = {
  name: 'fake-vault',
  register: (on: any) => {
    on('engine.create', async ($: any, e: any, next: any) => ({
      ...(await next(e)),
      jev: {
        classify: async () => ({ status: 'unavailable', reason: 'no_vault', latency_ms: 0 }),
        status: async (repo: string) => (repo === '/repo' ? { on: true } : { on: false, reason: 'repo' }),
      },
    }))
  },
}
const FAKE_VAULT_OFF = {
  name: 'fake-vault',
  register: (on: any) => {
    on('engine.create', async ($: any, e: any, next: any) => ({
      ...(await next(e)),
      jev: {
        classify: async () => ({ status: 'unavailable', reason: 'no_vault', latency_ms: 0 }),
        status: async () => ({ on: false, reason: 'egress' }),
      },
    }))
  },
}
const WITH_VAULT = { plugins: [FAKE_VAULT_ON] }
const WITH_VAULT_OFF = { plugins: [FAKE_VAULT_OFF] }

type Vault = { answer: unknown; throws: boolean; classified: unknown[] }
let vault: Vault = { answer: OK, throws: false, classified: [] }

type WorldOptions = { env?: Record<string, string>; mode?: string; descriptor?: object | null; vault?: boolean }

function world(on: any, opts: WorldOptions = {}) {
  mock.clock(on, { now: 1_000_000 })
  vault = { answer: OK, throws: false, classified: [] }
  // run-band shares this plugin: turned off here so its poller stays out of these tests.
  const env: Record<string, string | undefined> = { CV_DISABLED_HOOKS: 'run-band', ...(opts.env ?? {}) }
  const files: Record<string, string> = { [REQ_FILE]: JSON.stringify(REQ) }
  if (opts.descriptor !== null) files[PENDING] = JSON.stringify(opts.descriptor ?? DESCRIPTOR)
  const seen = {
    argv: [] as string[][],
    writes: [] as Array<{ path: string; text: string }>,
    sets: [] as string[],
    flagBeneath: [] as Array<string | undefined>,
  }

  on('session.start', () => ({ cwd: REPO }))
  on('session.cwd', () => ({ value: REPO }))
  on('session.root', () => ({ value: REPO }))
  on('env.get', ($$: any, e: any) => ({ value: env[e.name] }))
  on('env.set', ($$: any, e: any) => {
    seen.sets.push(`${e.name}=${e.value ?? ''}`)
    env[e.name] = e.value

    return { value: undefined }
  })
  on('fs.stat', ($$: any, e: any) => {
    const isDir = e.path === REPO || e.path === DD
    if (!isDir && !(e.path in files)) throw new Error(`ENOENT: ${e.path}`)

    return {
      value: { kind: isDir ? 'dir' : 'file', size: 1, mtimeMs: 1, isLink: false, ...(e.resolve ? { realPath: e.path } : {}) },
    }
  })
  on('fs.exists', ($$: any, e: any) => ({ value: e.path === `${REPO}/.git` || e.path in files }))
  on('fs.list', ($$: any, e: any) => ({
    value: Object.keys(files)
      .filter(p => p.startsWith(`${e.path}/`) && !p.slice(e.path.length + 1).includes('/'))
      .map(p => ({ name: p.slice(e.path.length + 1), kind: 'file', size: 1, mtimeMs: 1, isLink: false })),
  }))
  on('fs.read', ($$: any, e: any) => {
    if (!(e.path in files)) throw new Error(`ENOENT: ${e.path}`)

    return { value: files[e.path] }
  })
  on('fs.write', ($$: any, e: any) => {
    seen.writes.push({ path: e.path, text: e.text })
    files[e.path] = e.text

    return { value: undefined }
  })
  on('process.run', ($$: any, e: any) => {
    const argv = [...e.argv]
    seen.argv.push(argv)
    let stdout = ''
    if (argv.some(a => a.endsWith('compound-v-project-config.py'))) {
      stdout = JSON.stringify({ jev: { enabled: true, model: 'typesafe/jev-1.13', t3: { mode: opts.mode ?? 'shadow' } } })
    } else if (argv.includes('data-dir')) {
      stdout = JSON.stringify({ status: 'ok', data_dir: DD })
    } else if (argv.includes('parse') || argv.includes('pair')) {
      stdout = JSON.stringify({ status: 'ok' })
    } else if (argv[0] === '/bin/rm') {
      delete files[argv[argv.length - 1]!]
    }

    return { value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  // The vault's classify, as the noun's event reaches beneath every plugin.
  if (opts.vault !== false) {
    on('jev.classify', ($$: any, e: any) => {
      vault.classified.push(e)
      if (vault.throws) throw new Error('vault down')

      return { value: vault.answer }
    })
  }
  // Stands for the hooks beneath (the triage hook): records the flag their environment carries.
  on('classic.UserPromptSubmit', () => {
    seen.flagBeneath.push(env.CV_JEV_T3)

    return RES
  })

  return { env, files, seen }
}

async function start($: any) {
  await $.session.start({ cwd: REPO, surface: 'terminal', isInteractive: true })
}

async function prompt($: any) {
  return $.classic.UserPromptSubmit({ prompt: REQUEST_TEXT, session_id: SID, cwd: REPO })
}

// The Jev subcommands the module ran, in order, by name.
function jevCalls(argv: string[][]): string[] {
  return argv.filter(a => a.some(x => x.endsWith('compound-v-jev.py'))).map(a => a[a.findIndex(x => x.endsWith('.py')) + 1]!)
}

function flagOf(argv: string[], flag: string): string | undefined {
  const i = argv.indexOf(flag)

  return i < 0 ? undefined : argv[i + 1]
}

test('no $.jev: CV_JEV_T3 is unset and the classic result passes through untouched', async ($, on) => {
  const { env, seen } = world(on, { env: { CV_JEV_T3: '1' }, vault: false })
  await start($)
  const out = await prompt($)
  expect(env.CV_JEV_T3).toBeUndefined()
  expect(seen.flagBeneath).toEqual([undefined])
  expect(out).toEqual(RES)
  expect(jevCalls(seen.argv)).toEqual([])
  // no vault, no config process either
  expect(seen.argv.some(a => a.some(x => x.endsWith('compound-v-project-config.py')))).toBe(false)
})

test('vault on and t3.mode shadow: CV_JEV_T3=1 is set before the hooks beneath run', WITH_VAULT, async ($, on) => {
  const { seen } = world(on)
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(seen.flagBeneath).toEqual(['1'])
  const config = seen.argv.find(a => a.some(x => x.endsWith('compound-v-project-config.py')))!
  expect(config[config.length - 1]).toBe(REPO)
  // the config is read once per project per load
  await prompt($)
  expect(seen.flagBeneath).toEqual(['1', '1'])
  expect(seen.argv.filter(a => a.some(x => x.endsWith('compound-v-project-config.py')))).toHaveLength(1)
})

test('t3.mode off: CV_JEV_T3 is unset', WITH_VAULT, async ($, on) => {
  const { env } = world(on, { mode: 'off', env: { CV_JEV_T3: '1' } })
  await start($)
  expect(await prompt($)).toEqual(RES)
  expect(env.CV_JEV_T3).toBeUndefined()
})

test('vault off for the repository: CV_JEV_T3 is unset', WITH_VAULT_OFF, async ($, on) => {
  const { env, seen } = world(on, { env: { CV_JEV_T3: '1' } })
  await start($)
  expect(await prompt($)).toEqual(RES)
  expect(env.CV_JEV_T3).toBeUndefined()
  expect(seen.flagBeneath).toEqual([undefined])
  expect(vault.classified).toHaveLength(0)
})

test('descriptor present: one classify, then parse and pair in order, result deep-equal', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on)
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(vault.classified).toHaveLength(1)
  expect(vault.classified[0]).toMatchObject({ point: 't3', context: 'hook', repo: REPO })
  expect(jevCalls(seen.argv)).toEqual(['data-dir', 'parse', 'pair'])

  const parse = seen.argv.find(a => a.includes('parse'))!
  expect(flagOf(parse, '--response-file')).toBe(RESP_FILE)
  expect(flagOf(parse, '--request-file')).toBe(REQ_FILE)
  expect(flagOf(parse, '--mode')).toBe('shadow')
  expect(flagOf(parse, '--repo')).toBe(REPO)
  expect(flagOf(parse, '--hook-budget-left-ms')).toMatch(/^\d+$/)
  const pair = seen.argv.find(a => a.includes('pair'))!
  expect(flagOf(pair, '--request-file')).toBe(REQ_FILE)
  expect(flagOf(pair, '--claude-category')).toBe('user-facing-minor')
  expect(flagOf(pair, '--backend')).toBe('claude')
  expect(flagOf(pair, '--t3-reason')).toBe('demotion')

  // a descriptor without `claude_measure` (the Task route, or an older hook) pairs without one
  expect(pair.includes('--claude-measure-json')).toBe(false)

  expect(JSON.parse(files[RESP_FILE]!)).toEqual(OK)
  expect(seen.argv).toContainEqual(['/bin/chmod', '600', RESP_FILE])
  expect(seen.argv).toContainEqual(['/bin/rm', '-f', PENDING])
  expect(PENDING in files).toBe(false)
  // the request text never reaches an argv
  expect(JSON.stringify(seen.argv).includes(REQUEST_TEXT)).toBe(false)
})

const MEASURE = {
  wall_ms: 9900,
  duration_ms: 6168,
  duration_api_ms: 2360,
  tokens: { input_tokens: 2, output_tokens: 6, cache_read_input_tokens: 0, cache_creation_input_tokens: 53136 },
  model: 'claude-sonnet-4-5-20250929',
}

test('a descriptor with claude_measure: pair gets it as validated compact JSON', WITH_VAULT, async ($, on) => {
  const { seen } = world(on, { descriptor: { ...DESCRIPTOR, claude_measure: JSON.stringify(MEASURE) } })
  await start($)
  expect(await prompt($)).toEqual(RES)
  const pair = seen.argv.find(a => a.includes('pair'))!
  expect(JSON.parse(flagOf(pair, '--claude-measure-json')!)).toEqual(MEASURE)
})

test('a codex measure (wall_ms only) is completed with nulls, never zeros', WITH_VAULT, async ($, on) => {
  const { seen } = world(on, { descriptor: { ...DESCRIPTOR, backend: 'codex', claude_measure: '{"wall_ms":4100}' } })
  await start($)
  expect(await prompt($)).toEqual(RES)
  const pair = seen.argv.find(a => a.includes('pair'))!
  expect(JSON.parse(flagOf(pair, '--claude-measure-json')!)).toMatchObject({ wall_ms: 4100, duration_api_ms: null, model: null })
})

for (const bad of ['not json', '{"wall_ms":-1}', '{"wall_ms":1.5}', '{"cost":1}', '{"model":"a b"}', '{"tokens":{"x":1}}']) {
  test(`a malformed claude_measure (${bad}) never drops the pair: it is written without it`, WITH_VAULT, async ($, on) => {
    const { files, seen } = world(on, { descriptor: { ...DESCRIPTOR, claude_measure: bad } })
    await start($)
    expect(await prompt($)).toEqual(RES)
    expect(jevCalls(seen.argv)).toEqual(['data-dir', 'parse', 'pair'])
    const pair = seen.argv.find(a => a.includes('pair'))!
    expect(pair.includes('--claude-measure-json')).toBe(false)
    expect(PENDING in files).toBe(false)
  })
}

test('a non-string claude_measure makes the descriptor unreadable, and it is removed unsent', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on, { descriptor: { ...DESCRIPTOR, claude_measure: MEASURE } })
  await start($)
  expect(await prompt($)).toEqual(RES)
  expect(vault.classified).toHaveLength(0)
  expect(PENDING in files).toBe(false)
  expect(jevCalls(seen.argv)).toEqual(['data-dir'])
})

test('classify answers unavailable: parse still records it, result unchanged', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on)
  await start($)
  vault.answer = { status: 'unavailable', reason: 'egress', latency_ms: 0 }
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(JSON.parse(files[RESP_FILE]!)).toMatchObject({ status: 'unavailable', reason: 'egress' })
  expect(jevCalls(seen.argv)).toEqual(['data-dir', 'parse', 'pair'])
})

// A failing classify hook is skipped by the engine and the noun's own body answers (the vault's
// says `unavailable(no_vault)`): that answer is recorded like any other.
test('classify fails: what the noun answers is recorded, result unchanged', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on)
  await start($)
  vault.throws = true
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(JSON.parse(files[RESP_FILE]!)).toMatchObject({ status: 'unavailable' })
  expect(jevCalls(seen.argv)).toEqual(['data-dir', 'parse', 'pair'])
})

test('CV_HEADLESS_CLASSIFY=1: no classify, no parse, no pair, result unchanged', WITH_VAULT, async ($, on) => {
  const { seen } = world(on, { env: { CV_HEADLESS_CLASSIFY: '1' } })
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(vault.classified).toHaveLength(0)
  expect(jevCalls(seen.argv).filter(c => c !== 'data-dir')).toEqual([])
})

test('a descriptor for another session is left alone', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on, { descriptor: { ...DESCRIPTOR, sid: 'other' } })
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(vault.classified).toHaveLength(0)
  expect(PENDING in files).toBe(true)
  expect(jevCalls(seen.argv)).toEqual(['data-dir'])
})

test('a descriptor whose request file is outside req/ is dropped unread', WITH_VAULT, async ($, on) => {
  const { files, seen } = world(on, { descriptor: { ...DESCRIPTOR, request_file: '/etc/passwd' } })
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(vault.classified).toHaveLength(0)
  expect(PENDING in files).toBe(false)
  expect(jevCalls(seen.argv)).toEqual(['data-dir'])
})

test('no descriptor: result unchanged and no classify', WITH_VAULT, async ($, on) => {
  const { seen } = world(on, { descriptor: null })
  await start($)
  const out = await prompt($)
  expect(out).toEqual(RES)
  expect(vault.classified).toHaveLength(0)
  expect(seen.argv.some(a => a.some(x => PLUGIN_ROOT_SCRIPT.test(x)) && a.includes('parse'))).toBe(false)
})
