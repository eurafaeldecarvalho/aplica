import { app, shell, BrowserWindow, ipcMain, dialog, Notification } from 'electron'
import { join, isAbsolute } from 'path'
import { homedir } from 'os'
import { promises as fs } from 'fs'
import { spawn, spawnSync, type ChildProcess } from 'child_process'
import {
  configDir, configFile, profileFile, answersFile,
  enginePath, jobdbScript, findPython, findClaude, fileExists, needsShell
} from './paths'
import { DEFAULT_CONFIG, BLANK_PROFILE } from './defaults'

let mainWindow: BrowserWindow | null = null
let runningRoutine: ChildProcess | null = null
let runningDraft: ChildProcess | null = null

/** Recursive merge (mirrors engine/config.py _deep_merge): null in the file never overrides a default. */
function deepMerge(base: any, over: any): any {
  if (over === null || over === undefined) return base
  if (typeof base !== 'object' || base === null || Array.isArray(base)) return over
  const out: any = { ...base }
  for (const [k, v] of Object.entries(over)) {
    if (v === null || v === undefined) continue
    out[k] = (typeof v === 'object' && !Array.isArray(v) && typeof base[k] === 'object' && !Array.isArray(base[k]))
      ? deepMerge(base[k], v)
      : v
  }
  return out
}

function resolveInConfig(rel: string): string {
  return isAbsolute(rel) ? rel : join(configDir(), rel)
}

/** Safe (truncated) summary of a tool's input, to audit the run without leaking data. */
function toolHint(c: any): string {
  const inp = c.input || {}
  let hint = ''
  if (c.name === 'Bash' && typeof inp.command === 'string') hint = inp.command.split('\n')[0]
  else if (typeof inp.url === 'string') { try { hint = new URL(inp.url).host } catch { hint = inp.url } }
  else if (typeof inp.action === 'string') hint = inp.action
  else if (typeof inp.description === 'string') hint = inp.description
  if (!hint) return ''
  return ` (${hint.slice(0, 80)})`
}

/** Convert a line of claude's stream-json into readable text for the UI (or '' if irrelevant). */
function formatStreamLine(line: string): string {
  const t = line.trim()
  if (!t) return ''
  let o: any
  try { o = JSON.parse(t) } catch { return t + '\n' }
  if (o.type === 'assistant' && o.message?.content) {
    const parts = o.message.content.map((c: any) =>
      c.type === 'text' ? c.text : c.type === 'tool_use' ? `\n· ${c.name}${toolHint(c)}` : '').join('')
    return parts ? parts + '\n' : ''
  }
  if (o.type === 'result') return `\n${o.result || '(no result)'}\n`
  if (o.type === 'system' && o.subtype === 'init') return '[session started]\n'
  return ''
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 820,
    minWidth: 900,
    minHeight: 640,
    show: false,
    autoHideMenuBar: true,
    title: 'Aplica',
    backgroundColor: '#0f1115',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false
    }
  })

  mainWindow.on('ready-to-show', () => mainWindow?.show())
  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  if (!app.isPackaged && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// ---------- helpers ----------
async function ensureConfigDir(): Promise<string> {
  const dir = configDir()
  await fs.mkdir(dir, { recursive: true })
  return dir
}

async function readJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const raw = await fs.readFile(path, 'utf-8')
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

async function writeJson(path: string, data: unknown): Promise<void> {
  await ensureConfigDir()
  await fs.writeFile(path, JSON.stringify(data, null, 2) + '\n', 'utf-8')
}

/** Run the engine (jobdb.py) with args and return its output. */
function runEngine(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const py = findPython()
    if (!py) {
      resolve({ code: -1, stdout: '', stderr: 'Python was not found on PATH.' })
      return
    }
    const env = { ...process.env, APLICA_HOME: configDir() }
    const child = spawn(py, [jobdbScript(), ...args], { env })
    let stdout = '', stderr = '', done = false
    const finish = (r: { code: number; stdout: string; stderr: string }): void => { if (done) return; done = true; clearTimeout(timer); resolve(r) }
    // the engine must never hang a caller: kill a stuck process after 2 min
    const timer = setTimeout(() => { try { child.kill() } catch { /* ignore */ } finish({ code: -1, stdout, stderr: stderr + '\n[timeout]' }) }, 120000)
    child.stdout.on('data', (d) => (stdout += d.toString()))
    child.stderr.on('data', (d) => (stderr += d.toString()))
    child.on('error', (e) => finish({ code: -1, stdout, stderr: String(e) }))
    child.on('close', (code) => finish({ code: code ?? -1, stdout, stderr }))
  })
}

// ---------- IPC ----------
function registerIpc(): void {
  ipcMain.handle('config:dir', () => configDir())

  ipcMain.handle('config:read', async () => {
    if (!fileExists(configFile())) return { exists: false, data: DEFAULT_CONFIG }
    const fileCfg = await readJson(configFile(), {})
    return { exists: true, data: deepMerge(DEFAULT_CONFIG, fileCfg) }
  })
  ipcMain.handle('config:write', async (_e, data) => {
    await writeJson(configFile(), data)
    return { ok: true }
  })
  ipcMain.handle('config:defaults', () => DEFAULT_CONFIG)

  ipcMain.handle('profile:read', async () => {
    if (!fileExists(profileFile())) return { exists: false, data: BLANK_PROFILE }
    const fileProfile = await readJson(profileFile(), {})
    return { exists: true, data: deepMerge(BLANK_PROFILE, fileProfile) }
  })
  ipcMain.handle('profile:write', async (_e, data) => {
    await writeJson(profileFile(), data)
    return { ok: true }
  })

  ipcMain.handle('answers:read', async () => {
    try {
      return { exists: true, text: await fs.readFile(answersFile(), 'utf-8') }
    } catch {
      return { exists: false, text: '' }
    }
  })
  ipcMain.handle('answers:write', async (_e, text: string) => {
    await ensureConfigDir()
    await fs.writeFile(answersFile(), text, 'utf-8')
    return { ok: true }
  })

  // prerequisites
  ipcMain.handle('prereqs:check', async () => {
    const py = findPython()
    const claude = findClaude()
    const cfg = await readJson<any>(configFile(), DEFAULT_CONFIG)
    const paths = cfg?.paths || {}
    return {
      python: !!py,
      pythonBin: py,
      claude: !!claude,
      claudeBin: claude,
      configDir: configDir(),
      enginePresent: fileExists(jobdbScript()),
      resumePresent: fileExists(resolveInConfig(paths.resume || 'resume.pdf')),
      photoPresent: fileExists(resolveInConfig(paths.photo || 'photo.jpg')),
      configPresent: fileExists(configFile()),
      profilePresent: fileExists(profileFile())
    }
  })

  // database
  ipcMain.handle('db:init', async () => runEngine(['init']))
  ipcMain.handle('db:check', async () => runEngine(['check']))
  ipcMain.handle('db:report', async (_e, date?: string) =>
    runEngine(date ? ['report', '--date', date] : ['report']))
  ipcMain.handle('db:today', async (_e, date?: string) =>
    runEngine(date ? ['today', '--date', date] : ['today']))
  ipcMain.handle('db:metrics', async () => runEngine(['metrics']))
  ipcMain.handle('db:metricsJson', async () => runEngine(['metrics', '--json']))
  ipcMain.handle('db:followups', async (_e, days?: number) =>
    runEngine(['followups', '--days', String(days ?? 7)]))
  ipcMain.handle('db:stuck', async () => {
    const stuck = await runEngine(['stuck', 'list'])
    const todo = await runEngine(['todo', 'list'])
    return { travadas: stuck.stdout, pendencias: todo.stdout }
  })
  ipcMain.handle('db:backup', async () => runEngine(['backup']))

  // pipeline / CRM / drafts (JSON — parsed by the renderer)
  const parseJson = (r: { code: number; stdout: string }): any[] => {
    try { return JSON.parse((r.stdout || '').trim() || '[]') } catch { return [] }
  }
  ipcMain.handle('db:applications', async () => parseJson(await runEngine(['applications', '--json', '--limit', '500'])))
  ipcMain.handle('db:setStatus', async (_e, id: number, status: string) =>
    runEngine(['update-application', '--id', String(id), '--status', status]))
  ipcMain.handle('db:contacts', async () => parseJson(await runEngine(['contacts', '--json'])))
  ipcMain.handle('db:contactHistory', async (_e, person: string) =>
    parseJson(await runEngine(['contact-history', '--person', person, '--json'])))
  ipcMain.handle('db:drafts', async () => parseJson(await runEngine(['draft', 'list', '--json'])))
  ipcMain.handle('db:draftMarkSent', async (_e, id: number) => runEngine(['draft', 'sent', '--id', String(id)]))
  ipcMain.handle('draft:open', async (_e, path: string) => { if (path) shell.openPath(path); return { ok: true } })

  // is the `aplica` plugin installed in Claude Code? Runs `claude plugin list --json` and looks
  // for a plugin named "aplica". Best-effort: any failure returns {ok:false} and the UI shows the
  // manual install steps.
  const runClaudeCli = (args: string[], timeoutMs = 20000): Promise<{ code: number; stdout: string; stderr: string }> =>
    new Promise((resolve) => {
      const claude = findClaude()
      if (!claude) { resolve({ code: -1, stdout: '', stderr: 'claude CLI not found' }); return }
      const child = spawn(claude, args, { env: process.env, shell: needsShell() })
      let stdout = '', stderr = '', done = false
      const finish = (r: { code: number; stdout: string; stderr: string }): void => { if (done) return; done = true; clearTimeout(timer); resolve(r) }
      const timer = setTimeout(() => { try { child.kill() } catch { /* ignore */ } finish({ code: -1, stdout, stderr: stderr + '\n[timeout]' }) }, timeoutMs)
      child.stdout?.on('data', (d) => (stdout += d.toString()))
      child.stderr?.on('data', (d) => (stderr += d.toString()))
      child.on('error', (e) => finish({ code: -1, stdout, stderr: String(e) }))
      child.on('close', (code) => finish({ code: code ?? -1, stdout, stderr }))
    })

  ipcMain.handle('plugin:check', async () => {
    if (!findClaude()) return { ok: false, installed: false, reason: 'no-claude' }
    const r = await runClaudeCli(['plugin', 'list', '--json'])
    if (r.code !== 0 && !r.stdout.trim()) return { ok: false, installed: false, reason: 'cli-error', detail: (r.stderr || '').trim().slice(0, 200) }
    try {
      const list = JSON.parse(r.stdout.trim() || '[]')
      const arr = Array.isArray(list) ? list : (list?.plugins || [])
      const installed = arr.some((p: any) => {
        const name = String(p?.name || p?.plugin || p?.id || '').toLowerCase()
        return name === 'aplica' || name.startsWith('aplica@')
      })
      return { ok: true, installed }
    } catch {
      return { ok: false, installed: false, reason: 'parse-error' }
    }
  })

  ipcMain.handle('plugin:install', async () => {
    if (!findClaude()) return { ok: false, error: 'claude CLI not found on PATH' }
    const add = await runClaudeCli(['plugin', 'marketplace', 'add', 'eurafaeldecarvalho/aplica'], 40000)
    const inst = await runClaudeCli(['plugin', 'install', 'aplica@aplica'], 40000)
    const out = [add.stdout, add.stderr, inst.stdout, inst.stderr].filter(Boolean).join('\n').trim()
    return { ok: inst.code === 0, output: out }
  })

  // native desktop notifications — the renderer passes the items it just saw as new
  ipcMain.handle('notify:desktop', async (_e, items: Array<{ level: string; title: string; detail: string }>) => {
    const cfg = await readJson<any>(configFile(), DEFAULT_CONFIG)
    if (cfg?.app?.desktop_notifications === false) return { ok: false }
    if (!Notification.isSupported()) return { ok: false }
    for (const n of (items || []).slice(0, 5)) {
      try {
        const note = new Notification({ title: `Aplica — ${n.title}`, body: n.detail || '' })
        note.on('click', () => { mainWindow?.show(); mainWindow?.focus() })
        note.show()
      } catch { /* ignore */ }
    }
    return { ok: true }
  })

  // aggregated notifications from the signals the engine records (sign-in/block, to-dos, runs)
  ipcMain.handle('notifications:list', async () => {
    const out: Array<{ level: string; title: string; detail: string; action?: string }> = []
    const check = await runEngine(['check'])
    if (!(check.stdout || '').trim().endsWith('OK')) {
      return [{ level: 'warn', title: 'Database not initialized', detail: 'Open Home to initialize the local database.', action: 'home' }]
    }
    const reasonLabel: Record<string, string> = {
      'linkedin-block': 'LinkedIn blocked or needs verification',
      'google-sso-unavailable': 'Google sign-in unavailable — check you are logged in to Chrome',
      'email-not-received': 'Verification email did not arrive',
      'account-exists-bad-password': 'Account exists but sign-in failed',
      '2fa-phone': '2FA on your phone required',
      'captcha-persistent': 'CAPTCHA blocked',
      'regional-block': 'Regional block',
      'document-required': 'Document required',
      paywall: 'Paywall / subscription'
    }
    const li = await runEngine(['linkedin-status'])
    const liBlocked = (li.stdout || '').trim().startsWith('BLOCKED')
    if (liBlocked) {
      out.push({ level: 'error', title: 'LinkedIn needs your attention', detail: li.stdout.trim() })
    }
    const sites = await runEngine(['active-sites'])
    for (const line of (sites.stdout || '').split('\n')) {
      const c = line.split('\t')
      if (c.length >= 4 && c[2] === 'blocked') {
        if (liBlocked && c[3] === 'linkedin-block') continue // already reported above
        const label = reasonLabel[c[3]] || c[3]
        out.push({ level: 'warn', title: `${c[1]}: ${label}`, detail: `last seen ${c[5] || ''} ${c[6] || ''}`.trim() })
      }
    }
    const todo = await runEngine(['todo', 'list'])
    for (const r of (todo.stdout || '').split('\n').filter((l) => /^\d+\t/.test(l))) {
      const c = r.split('\t')
      out.push({ level: 'warn', title: 'Needs you', detail: c[3] || r, action: 'dashboard' })
    }
    const trav = await runEngine(['stuck', 'list'])
    const trows = (trav.stdout || '').split('\n').filter((l) => /^\d+\t/.test(l))
    if (trows.length) out.push({ level: 'info', title: `${trows.length} stuck job${trows.length > 1 ? 's' : ''}`, detail: 'Jobs you finish by hand — see the Dashboard.', action: 'dashboard' })
    const logs = await runEngine(['logs'])
    for (const r of (logs.stdout || '').split('\n').filter((l) => l.includes('\t')).slice(-6)) {
      const c = r.split('\t')
      if (c.length >= 3 && c[0] !== 'ts') out.push({ level: 'info', title: `Run: ${c[1]}`, detail: c[2] })
    }
    return out
  })

  // file selection (résumé / photo) → copy into the config dir
  ipcMain.handle('file:pick', async (_e, kind: 'resume' | 'photo') => {
    const filters = kind === 'resume'
      ? [{ name: 'PDF', extensions: ['pdf'] }]
      : [{ name: 'Imagem', extensions: ['jpg', 'jpeg', 'png'] }]
    const res = await dialog.showOpenDialog(mainWindow!, { properties: ['openFile'], filters })
    if (res.canceled || !res.filePaths[0]) return { ok: false }
    await ensureConfigDir()
    const dest = join(configDir(), kind === 'resume' ? 'resume.pdf' : 'photo.jpg')
    await fs.copyFile(res.filePaths[0], dest)
    return { ok: true, dest }
  })

  ipcMain.handle('open:configDir', async () => {
    await ensureConfigDir()
    shell.openPath(configDir())
    return { ok: true }
  })

  // open an external link (http/https only) in the default browser
  ipcMain.handle('open:external', async (_e, url: string) => {
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
      await shell.openExternal(url)
      return { ok: true }
    }
    return { ok: false }
  })

  // best-effort detection of the Claude in Chrome extension by reading the Chrome profiles
  ipcMain.handle('chrome:detect', async () => {
    const roots: string[] = []
    if (process.platform === 'win32') {
      const la = process.env.LOCALAPPDATA
      if (la) roots.push(join(la, 'Google', 'Chrome', 'User Data'))
    } else if (process.platform === 'darwin') {
      roots.push(join(homedir(), 'Library', 'Application Support', 'Google', 'Chrome'))
    } else {
      roots.push(join(homedir(), '.config', 'google-chrome'))
      roots.push(join(homedir(), '.config', 'chromium'))
    }
    let chromeFound = false
    let extFound = false
    for (const root of roots) {
      if (!fileExists(root)) continue
      chromeFound = true
      try {
        const profiles = await fs.readdir(root, { withFileTypes: true })
        for (const prof of profiles) {
          if (!prof.isDirectory()) continue
          const extDir = join(root, prof.name, 'Extensions')
          if (!fileExists(extDir)) continue
          const ids = await fs.readdir(extDir, { withFileTypes: true }).catch(() => [])
          for (const id of ids) {
            if (!id.isDirectory()) continue
            const verDir = join(extDir, id.name)
            const vers = await fs.readdir(verDir, { withFileTypes: true }).catch(() => [])
            for (const v of vers) {
              if (!v.isDirectory()) continue
              const base = join(verDir, v.name)
              let name = ''
              try {
                const man = JSON.parse(await fs.readFile(join(base, 'manifest.json'), 'utf-8'))
                name = String(man.name || '')
                const m = /^__MSG_(.+)__$/.exec(name)
                if (m) {
                  // resolve the localized name via default_locale (fallback en)
                  const locales = [man.default_locale, 'en', 'en_US'].filter(Boolean)
                  for (const loc of locales) {
                    try {
                      const msgs = JSON.parse(await fs.readFile(join(base, '_locales', loc, 'messages.json'), 'utf-8'))
                      const entry = msgs[m[1]] || msgs[m[1].toLowerCase()]
                      if (entry?.message) { name = String(entry.message); break }
                    } catch { /* next locale */ }
                  }
                }
              } catch { /* unreadable manifest */ }
              if (/claude/i.test(name)) { extFound = true; break }
            }
            if (extFound) break
          }
          if (extFound) break
        }
      } catch { /* ignore */ }
      if (extFound) break
    }
    return { chromeFound, extFound }
  })

  // Launch `claude -p` with a slash-command prompt and stream its output to `channel`.
  // The user is offline during a run → autonomous mode (bypassPermissions) so the agent can use
  // Bash, the browser (mcp__claude-in-chrome__*) and subagents with no approval prompt (impossible
  // in -p). stream-json + verbose gives live output. The prompt goes over STDIN (avoids shell
  // word-splitting on Windows and argv injection).
  // `chrome: true` turns ON Claude in Chrome for the subprocess — WITHOUT `--chrome` +
  // CLAUDE_CODE_ENABLE_CFC=1 a `claude -p` child has NO browser tools at all, so the run can scan
  // but never actually apply. Requires claude.ai (OAuth) auth; an ANTHROPIC_API_KEY in the
  // environment silently disables Chrome, so we strip it from the child's env for a browser run.
  const launchClaude = (e: Electron.IpcMainInvokeEvent, prompt: string, channel: string,
    opts: { extraArgs?: string[]; chrome?: boolean } = {}): { child: ChildProcess; done: Promise<any> } => {
    const env: NodeJS.ProcessEnv = { ...process.env, APLICA_HOME: configDir() }
    const args = ['-p', '--permission-mode', 'bypassPermissions', '--output-format', 'stream-json', '--verbose']
    if (opts.chrome) {
      env.CLAUDE_CODE_ENABLE_CFC = '1'
      delete env.ANTHROPIC_API_KEY // an API key disables Chrome even with --chrome (OAuth auth required)
      args.push('--chrome')
    }
    args.push(...(opts.extraArgs || []))
    const child = spawn(findClaude() as string, args, { env, shell: needsShell() })
    const send = (chunk: string): void => e.sender.send(channel, chunk)
    try { child.stdin?.write(prompt + '\n'); child.stdin?.end() } catch { /* ignore */ }
    let buf = ''
    child.stdout?.on('data', (d) => {
      buf += d.toString()
      let nl: number
      while ((nl = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, nl)
        buf = buf.slice(nl + 1)
        const text = formatStreamLine(line)
        if (text) send(text)
      }
    })
    child.stderr?.on('data', (d) => send(d.toString()))
    const done = new Promise<any>((resolve) => {
      child.on('error', (err) => { send(`\n[error] ${err}\n`); resolve({ ok: false, error: String(err) }) })
      child.on('close', (code) => { send(`\n[run finished with code ${code}]\n`); resolve({ ok: true, code }) })
    })
    return { child, done }
  }

  // routine run via claude -p (stream)
  const SOURCES = new Set(['all', 'ats', 'linkedin', 'freehire', 'recruiters', 'feed'])
  ipcMain.handle('routine:run', async (e, source: string) => {
    if (runningRoutine) return { ok: false, error: 'A run is already in progress.' }
    if (runningDraft) return { ok: false, error: 'A draft is being generated — wait for it to finish (one browser at a time).' }
    if (!findClaude()) return { ok: false, error: 'The `claude` CLI was not found on PATH.' }
    const src = SOURCES.has(source) ? source : 'all'
    const { child, done } = launchClaude(e, `/aplica-run ${src}`, 'routine:output', { chrome: true })
    runningRoutine = child
    const r = await done
    runningRoutine = null
    return r
  })
  ipcMain.handle('routine:stop', async () => {
    if (!runningRoutine) return { ok: false, error: 'nothing running' }
    const pid = runningRoutine.pid
    // On Windows the stored process is the cmd.exe wrapper (shell:true); kill() only kills the
    // wrapper and leaves claude/node orphaned. taskkill /T kills the whole tree — the kill switch must hold.
    if (process.platform === 'win32' && pid) {
      try { spawnSync('taskkill', ['/PID', String(pid), '/T', '/F']) } catch { /* ignore */ }
    } else {
      try { runningRoutine.kill('SIGTERM') } catch { /* ignore */ }
    }
    return { ok: true }
  })
  ipcMain.handle('routine:running', async () => ({ running: !!runningRoutine }))

  // grounded draft generation via claude -p (/aplica-draft). The draft flow reads/writes only the
  // local DB and draft files — it must NEVER touch the browser. We hard-disable the Chrome MCP tools
  // (defense in depth: the skill also forbids it) so a prompt injection in the grounding JSON / a
  // re-fetched job page cannot drive the browser to exfiltrate data under bypassPermissions. It is
  // also made mutually exclusive with a routine run, preserving the "one browser at a time" invariant.
  const DRAFT_KINDS = new Set(['cover', 'followup', 'prep'])
  const DRAFT_NO_BROWSER = ['--disallowedTools', 'mcp__claude-in-chrome__*']
  ipcMain.handle('draft:run', async (e, kind: string, applicationId: number) => {
    if (runningDraft) return { ok: false, error: 'A draft is already being generated.' }
    if (runningRoutine) return { ok: false, error: 'A run is in progress — wait for it to finish.' }
    if (!findClaude()) return { ok: false, error: 'The `claude` CLI was not found on PATH.' }
    const k = DRAFT_KINDS.has(kind) ? kind : 'cover'
    // no `chrome: true` → the draft subprocess has no browser tools at all; DRAFT_NO_BROWSER is
    // belt-and-suspenders in case the environment enables Chrome by default.
    const { child, done } = launchClaude(e, `/aplica-draft ${k} ${Number(applicationId) || 0}`, 'draft:output', { extraArgs: DRAFT_NO_BROWSER })
    runningDraft = child
    const r = await done
    runningDraft = null
    return r
  })
  ipcMain.handle('draft:running', async () => ({ running: !!runningDraft }))
}

/** Create the app's local database (bundled engine) if it does not exist yet. The DB is always the
 * app's own, isolated in APLICA_HOME; it never points at a pre-existing database on the user's machine. */
async function ensureDatabase(): Promise<void> {
  try {
    await ensureConfigDir()
    const dbPath = join(configDir(), 'state.db')
    if (fileExists(dbPath)) return
    if (!findPython()) return // without Python the onboarding guides the install; manual init later
    await runEngine(['init'])
  } catch { /* the onboarding reflects the database state either way */ }
}

app.whenReady().then(() => {
  registerIpc()
  createWindow() // the UI always shows; the database init does not block the window
  void ensureDatabase() // fire-and-forget; the onboarding reflects the database state
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
