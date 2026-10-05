// The contract of the compound-v-vault plugin: the `jev` noun it adds to `$`.
// Self-contained (no import, no reference), as a plugin noun's contract must be.

/**
 * One System One request, as `scripts/compound-v-jev.py build` writes it to a request file.
 * `body` is sent to OpenRouter as is; every other field stays on this machine.
 */
export type JevRequest = {
  point: string
  catalogue_hash: string
  model: string
  body: { model: string; state: unknown; questions: Record<string, unknown> }
  timeout_ms: number
  context: 'hook' | 'offline'
  repo: string
}

/**
 * What the vault answers for one request, and what it writes to a response file.
 * `body` is present only on `ok`; it is OpenRouter's JSON with `usage.cost` removed.
 * A non-2xx answer carries `http_status` and never any part of the error body.
 */
export type JevResponse = {
  status: 'ok' | 'unavailable' | 'error'
  reason?: string
  http_status?: number
  latency_ms: number
  body?: unknown
}

/**
 * The vault's noun on `$`: the only HTTP client for Jev.
 */
export type Jev = {
  /** Sends one request to the System One route and maps the answer; never rejects. */
  classify: (req: JevRequest) => Promise<JevResponse>
  /** Whether a call for this repository would be sent now, and why not when it would not. */
  status: (repo: string) => Promise<{ on: boolean; reason?: string }>
}

declare module 'claude-code' {
  interface EngineInterface {
    jev: Jev
  }
}
