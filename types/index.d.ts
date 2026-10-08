export type HudJob = {
  id: string
  status: string
  backend: string | null
  tier: string | null
  model: string | null
  effort: string | null
  attention: boolean
}

export type HudWave = { n: string | null; jobs: HudJob[] }

export type HudRun = {
  id: string
  phase: string
  run_dir: string
  done: number
  total: number
  running: number
  state_error: boolean
  waves: HudWave[]
}

export type Live = { liveness: string; idle_s: number | null }

export type Band = {
  run: HudRun | null
  /** job id -> liveness; null when the probe did not answer (ages print as `?`). */
  live: Record<string, Live> | null
  /** `<job>:<reason>` keys already toasted, so a transition is announced once. */
  alerted: string[]
  /** The closing line of a run that just left the active set, and when it expires (ms). */
  closing: { text: string; until: number } | null
  /** Set when the reader could not answer; drawn dim, never as data. */
  error: string | null
}

/**
 * What `hooks/jev-t3.tsx` uses of the `jev` noun the separate compound-v-vault plugin adds to `$`.
 * A local structural copy, deliberately NOT declared on `EngineInterface`: the vault is optional,
 * so the module reaches the noun only through a guarded call (`$.jev.status(...)` inside try/catch,
 * which throws without the vault; the engine refuses an `'jev' in $` test) and compiles and
 * validates with or without the vault installed.
 */
export type JevT3Noun = {
  classify: (req: unknown) => Promise<JevT3Response>
  status: (repo: string) => Promise<{ on: boolean; reason?: string }>
}

/** The vault's answer for one request, as it is written to the response file. */
export type JevT3Response = {
  status: 'ok' | 'unavailable' | 'error'
  reason?: string
  http_status?: number
  latency_ms: number
  body?: unknown
}

/**
 * The pending descriptor `hooks/triage-prompt-nudge.sh` leaves in the Jev data directory after a
 * decided T3 consultation, when `CV_JEV_T3=1`: `pending-<digest>.json`, read and deleted by the module.
 */
export type JevT3Descriptor = {
  pre_eval_id: string
  request_file: string
  t3_reason: string
  claude_category: string
  backend: string
  proj: string
  sid: string
  /**
   * The headless classify's measure as compact JSON (`JevT3ClaudeMeasure`), or "" when none was read.
   * Optional so a descriptor written before the key existed still pairs.
   */
  claude_measure?: string
}

/** The Claude-side measure `pair --claude-measure-json` stores: milliseconds and tokens, never money. */
export type JevT3ClaudeMeasure = {
  wall_ms: number | null
  duration_ms: number | null
  duration_api_ms: number | null
  tokens: {
    input_tokens: number | null
    output_tokens: number | null
    cache_read_input_tokens: number | null
    cache_creation_input_tokens: number | null
  }
  model: string | null
}

declare module 'claude-code' {
  interface PluginState {
    'superpowers-v': { band: Band | null; spin: number }
  }
}
