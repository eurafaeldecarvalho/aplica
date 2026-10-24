import { app, shell, BrowserWindow, ipcMain, dialog } from 'electron'
import { join } from 'path'
import { promises as fs } from 'fs'
import { spawn, spawnSync } from 'child_process'
import {
  configDir, configFile, profileFile, answersFile,
  enginePath, jobdbScript, findPython, findClaude, fileExists
} from './paths'
import { DEFAULT_CONFIG, BLANK_PROFILE } from './defaults'

let mainWindow: BrowserWindow | null = null

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
    return { exists: true, data: await readJson(configFile(), DEFAULT_CONFIG) }
  })
  ipcMain.handle('config:write', async (_e, data) => {
    await writeJson(configFile(), data)
    return { ok: true }
  })
  ipcMain.handle('config:defaults', () => DEFAULT_CONFIG)

  ipcMain.handle('profile:read', async () => {
    if (!fileExists(profileFile())) return { exists: false, data: BLANK_PROFILE }
    return { exists: true, data: await readJson(profileFile(), BLANK_PROFILE) }
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
    return {
      python: !!py,
      pythonBin: py,
      claude: !!claude,
      claudeBin: claude,
      configDir: configDir(),
      enginePresent: fileExists(jobdbScript()),
      resumePresent: fileExists(join(configDir(), (await readJson<any>(configFile(), DEFAULT_CONFIG)).paths?.resume || 'resume.pdf')),
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
  ipcMain.handle('routine:run', async (e, source: string) => {
    const claude = findClaude()
    if (!claude) return { ok: false, error: 'CLI `claude` não encontrado no PATH.' }
    const env = { ...process.env, APLICA_HOME: configDir() }
    const prompt = `/aplica-run ${source || 'all'}`
    const child = spawn(claude, ['-p', prompt], { env })
    const send = (chunk: string): void => e.sender.send('routine:output', chunk)
    child.stdout.on('data', (d) => send(d.toString()))
    child.stderr.on('data', (d) => send(d.toString()))
    return await new Promise((resolve) => {
      child.on('error', (err) => { send(`\n[erro] ${err}\n`); resolve({ ok: false, error: String(err) }) })
      child.on('close', (code) => { send(`\n[execução terminou com código ${code}]\n`); resolve({ ok: true, code }) })
    })
  })
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
