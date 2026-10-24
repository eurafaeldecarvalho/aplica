import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
import { join, isAbsolute } from 'path'
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
    let stdout = '', stderr = ''
    child.stdout.on('data', (d) => (stdout += d.toString()))
    child.stderr.on('data', (d) => (stderr += d.toString()))
    child.on('error', (e) => resolve({ code: -1, stdout, stderr: String(e) }))
    child.on('close', (code) => resolve({ code: code ?? -1, stdout, stderr }))
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

app.whenReady().then(() => {
  registerIpc()
  createWindow()
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
