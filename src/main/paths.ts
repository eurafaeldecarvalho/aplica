import { app } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'
import { homedir } from 'os'
import { spawnSync } from 'child_process'

/** Config dir do usuário (mesma lógica de engine/config.py). */
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

/** Pasta engine/ (dev: ao lado do projeto; empacotado: em resources/engine). */
export function enginePath(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, 'engine')
  }
  return join(app.getAppPath(), 'engine')
}

export function jobdbScript(): string {
  return join(enginePath(), 'jobdb.py')
}

let cachedPython: string | null | undefined
/** Acha um Python utilizável, testando candidatos. Cacheia. null = não achou. */
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
      /* próximo */
    }
  }
  cachedPython = null
  return null
}

let cachedClaude: string | null | undefined
/** Acha o CLI `claude` no PATH. */
export function findClaude(): string | null {
  if (cachedClaude !== undefined) return cachedClaude
  const bin = process.platform === 'win32' ? 'claude.cmd' : 'claude'
  for (const c of [bin, 'claude']) {
    try {
      const r = spawnSync(c, ['--version'], { encoding: 'utf-8' })
      if (r.status === 0) {
        cachedClaude = c
        return c
      }
    } catch {
      /* próximo */
    }
  }
  cachedClaude = null
  return null
}

export function fileExists(p: string): boolean {
  try {
    return existsSync(p)
  } catch {
    return false
  }
}
