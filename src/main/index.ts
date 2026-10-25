import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
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

/** Merge recursivo (espelha engine/config.py _deep_merge): null do arquivo não sobrescreve default. */
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

/** Resumo seguro (e truncado) do input de uma tool, para auditar a execução sem vazar dados. */
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

/** Converte uma linha do stream-json do claude em texto legível para a UI (ou '' se irrelevante). */
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
  if (o.type === 'result') return `\n${o.result || '(sem resultado)'}\n`
  if (o.type === 'system' && o.subtype === 'init') return '[sessão iniciada]\n'
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

/** Roda o motor (jobdb.py) com args e devolve a saída. */
function runEngine(args: string[]): Promise<{ code: number; stdout: string; stderr: string }> {
  return new Promise((resolve) => {
    const py = findPython()
    if (!py) {
      resolve({ code: -1, stdout: '', stderr: 'Python não encontrado no PATH.' })
      return
    }
    const env = { ...process.env, APLICA_HOME: configDir() }
    const child = spawn(py, [jobdbScript(), ...args], { env })
    let stdout = '', stderr = '', done = false
    const finish = (r: { code: number; stdout: string; stderr: string }): void => { if (done) return; done = true; clearTimeout(timer); resolve(r) }
    // a engine nunca deve pendurar um caller: mata um processo preso após 2 min
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

  // pré-requisitos
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

  // banco
  ipcMain.handle('db:init', async () => runEngine(['init']))
  ipcMain.handle('db:check', async () => runEngine(['check']))
  ipcMain.handle('db:report', async (_e, date?: string) =>
    runEngine(date ? ['relatorio', '--data', date] : ['relatorio']))
  ipcMain.handle('db:today', async (_e, date?: string) =>
    runEngine(date ? ['hoje', '--data', date] : ['hoje']))
  ipcMain.handle('db:metrics', async () => runEngine(['metricas']))
  ipcMain.handle('db:followups', async (_e, dias?: number) =>
    runEngine(['followups', '--dias', String(dias ?? 7)]))
  ipcMain.handle('db:stuck', async () => {
    const trav = await runEngine(['travada', 'list'])
    const pend = await runEngine(['pendencia', 'list'])
    return { travadas: trav.stdout, pendencias: pend.stdout }
  })
  ipcMain.handle('db:backup', async () => runEngine(['backup']))

  // notificações agregadas dos sinais que o motor registra (login/bloqueio, pendências, runs)
  ipcMain.handle('notifications:list', async () => {
    const out: Array<{ level: string; title: string; detail: string; action?: string }> = []
    const check = await runEngine(['check'])
    if (!(check.stdout || '').trim().endsWith('OK')) {
      return [{ level: 'warn', title: 'Database not initialized', detail: 'Open Home to initialize the local database.', action: 'home' }]
    }
    const motivoLabel: Record<string, string> = {
      'linkedin-bloqueio': 'LinkedIn blocked or needs verification',
      'sso-google-indisponivel': 'Google sign-in unavailable — check you are logged in to Chrome',
      'email-nao-chegou': 'Verification email did not arrive',
      'conta-ja-existe-senha-invalida': 'Account exists but sign-in failed',
      '2fa-celular': '2FA on your phone required',
      'captcha-persistente': 'CAPTCHA blocked',
      'bloqueio-regional': 'Regional block',
      'exige-documento': 'Document required',
      'paywall-assinatura': 'Paywall / subscription'
    }
    const li = await runEngine(['linkedin-status'])
    const liBlocked = (li.stdout || '').trim().startsWith('BLOQUEADO')
    if (liBlocked) {
      out.push({ level: 'error', title: 'LinkedIn needs your attention', detail: li.stdout.trim() })
    }
    const sites = await runEngine(['sites-ativos'])
    for (const line of (sites.stdout || '').split('\n')) {
      const c = line.split('\t')
      if (c.length >= 4 && c[2] === 'bloqueado') {
        if (liBlocked && c[3] === 'linkedin-bloqueio') continue // já reportado acima
        const label = motivoLabel[c[3]] || c[3]
        out.push({ level: 'warn', title: `${c[1]}: ${label}`, detail: `last seen ${c[5] || ''} ${c[6] || ''}`.trim() })
      }
    }
    const pend = await runEngine(['pendencia', 'list'])
    for (const r of (pend.stdout || '').split('\n').filter((l) => /^\d+\t/.test(l))) {
      const c = r.split('\t')
      out.push({ level: 'warn', title: 'Needs you', detail: c[3] || r, action: 'dashboard' })
    }
    const trav = await runEngine(['travada', 'list'])
    const trows = (trav.stdout || '').split('\n').filter((l) => /^\d+\t/.test(l))
    if (trows.length) out.push({ level: 'info', title: `${trows.length} stuck job${trows.length > 1 ? 's' : ''}`, detail: 'Jobs you finish by hand — see the Dashboard.', action: 'dashboard' })
    const logs = await runEngine(['logs'])
    for (const r of (logs.stdout || '').split('\n').filter((l) => l.includes('\t')).slice(-6)) {
      const c = r.split('\t')
      if (c.length >= 3 && c[1] !== 'tipo') out.push({ level: 'info', title: `Run: ${c[1]}`, detail: c[2] })
    }
    return out
  })

  // seleção de arquivo (currículo / foto) → copia pro config dir
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

  // abre um link externo (só http/https) no navegador padrão
  ipcMain.handle('open:external', async (_e, url: string) => {
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
      await shell.openExternal(url)
      return { ok: true }
    }
    return { ok: false }
  })

  // detecta (best-effort) a extensão Claude in Chrome lendo os perfis do Chrome
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
                  // resolve o nome localizado pelo default_locale (fallback en)
                  const locales = [man.default_locale, 'en', 'en_US'].filter(Boolean)
                  for (const loc of locales) {
                    try {
                      const msgs = JSON.parse(await fs.readFile(join(base, '_locales', loc, 'messages.json'), 'utf-8'))
                      const entry = msgs[m[1]] || msgs[m[1].toLowerCase()]
                      if (entry?.message) { name = String(entry.message); break }
                    } catch { /* próximo locale */ }
                  }
                }
              } catch { /* manifesto ilegível */ }
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

  // execução de rotina via claude -p (stream)
  const SOURCES = new Set(['all', 'ats', 'linkedin', 'freehire', 'recruiters', 'feed'])
  ipcMain.handle('routine:run', async (e, source: string) => {
    if (runningRoutine) return { ok: false, error: 'Já há uma execução em andamento.' }
    const claude = findClaude()
    if (!claude) return { ok: false, error: 'CLI `claude` não encontrado no PATH.' }
    const src = SOURCES.has(source) ? source : 'all'
    const env = { ...process.env, APLICA_HOME: configDir() }
    const prompt = `/aplica-run ${src}`
    // O usuário está offline durante a execução → modo autônomo (bypassPermissions) para que o
    // agente possa usar Bash, o navegador (mcp__claude-in-chrome__*) e subagentes sem prompt de
    // aprovação (impossível em -p). stream-json + verbose dá saída ao vivo. O prompt vai por STDIN
    // (evita word-split do shell no Windows e injeção via argv).
    const args = ['-p', '--permission-mode', 'bypassPermissions', '--output-format', 'stream-json', '--verbose']
    const child = spawn(claude, args, { env, shell: needsShell() })
    runningRoutine = child
    try { child.stdin?.write(prompt + '\n'); child.stdin?.end() } catch { /* ignore */ }
    const send = (chunk: string): void => e.sender.send('routine:output', chunk)
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
    return await new Promise((resolve) => {
      child.on('error', (err) => { runningRoutine = null; send(`\n[erro] ${err}\n`); resolve({ ok: false, error: String(err) }) })
      child.on('close', (code) => { runningRoutine = null; send(`\n[execução terminou com código ${code}]\n`); resolve({ ok: true, code }) })
    })
  })
  ipcMain.handle('routine:stop', async () => {
    if (!runningRoutine) return { ok: false, error: 'nada em execução' }
    const pid = runningRoutine.pid
    // No Windows o processo guardado é o wrapper cmd.exe (shell:true); kill() só mata o wrapper e
    // deixa o claude/node órfão. taskkill /T mata a árvore inteira — o kill switch precisa valer.
    if (process.platform === 'win32' && pid) {
      try { spawnSync('taskkill', ['/PID', String(pid), '/T', '/F']) } catch { /* ignore */ }
    } else {
      try { runningRoutine.kill('SIGTERM') } catch { /* ignore */ }
    }
    return { ok: true }
  })
  ipcMain.handle('routine:running', async () => ({ running: !!runningRoutine }))
}

/** Cria o banco local do app (motor empacotado) se ainda não existir. O DB é sempre o do app,
 * isolado em APLICA_HOME; nunca aponta para um banco pré-existente na máquina do usuário. */
async function ensureDatabase(): Promise<void> {
  try {
    await ensureConfigDir()
    const dbPath = join(configDir(), 'state.db')
    if (fileExists(dbPath)) return
    if (!findPython()) return // sem Python o onboarding guia a instalação; init manual depois
    await runEngine(['init'])
  } catch { /* o onboarding mostra o estado do banco de qualquer forma */ }
}

app.whenReady().then(() => {
  registerIpc()
  createWindow() // a UI aparece sempre; o init do banco não bloqueia a janela
  void ensureDatabase() // fire-and-forget; o onboarding reflete o estado do banco
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
