import { app } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'
import { homedir } from 'os'
import { spawnSync } from 'child_process'

/** The user's config dir (same logic as engine/config.py). */
export function configDir(): string {
  const env = process.env.APLICA_HOME
  if (env) return env
  if (process.platform === 'win32') {
    return join(process.env.APPDATA || homedir(), 'aplica')
  }
  const xdg = process.env.XDG_CONFIG_HOME || join(homedir(), '.config')
  return join(xdg, 'aplica')
}

export function configFile(): string {
  return join(configDir(), 'config.json')
}
export function profileFile(): string {
  return join(configDir(), 'profile.json')
}
export function answersFile(): string {
  return join(configDir(), 'answers.md')
}

/** engine/ folder (dev: the plugin's engine at the repo root, one level up; packaged: in resources/engine). */
export function enginePath(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, 'engine')
  }
  return join(app.getAppPath(), '..', 'engine')
}

export function jobdbScript(): string {
  return join(enginePath(), 'jobdb.py')
}

let cachedPython: string | null | undefined
/** Find a usable Python by trying candidates. Cached. null = not found. */
export function findPython(): string | null {
  if (cachedPython !== undefined) return cachedPython
  const candidates = process.platform === 'win32'
    ? ['python', 'py', 'python3']
    : ['python3', 'python']
  for (const c of candidates) {
    try {
      const r = spawnSync(c, ['--version'], { encoding: 'utf-8' })
      if (r.status === 0 || (r.stdout || r.stderr || '').toLowerCase().includes('python')) {
        cachedPython = c
        return c
      }
    } catch {
      /* next */
    }
  }
  cachedPython = null
  return null
}

let cachedClaude: string | null | undefined
/** Find the `claude` CLI on PATH. On Windows it is a .cmd, which needs shell on spawn (else EINVAL). */
export function findClaude(): string | null {
  if (cachedClaude !== undefined) return cachedClaude
  const win = process.platform === 'win32'
  for (const c of win ? ['claude.cmd', 'claude'] : ['claude']) {
    try {
      const r = spawnSync(c, ['--version'], { encoding: 'utf-8', shell: win })
      if (r.status === 0) {
        cachedClaude = c
        return c
      }
    } catch {
      /* next */
    }
  }
  cachedClaude = null
  return null
}

/** Se o spawn de processos .cmd (claude no Windows) precisa de shell. */
export function needsShell(): boolean {
  return process.platform === 'win32'
}

export function fileExists(p: string): boolean {
  try {
    return existsSync(p)
  } catch {
    return false
  }
}
