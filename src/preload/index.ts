import { contextBridge, ipcRenderer } from 'electron'

const api = {
  // config / profile / answers
  getConfigDir: () => ipcRenderer.invoke('config:dir'),
  readConfig: () => ipcRenderer.invoke('config:read'),
  writeConfig: (data: unknown) => ipcRenderer.invoke('config:write', data),
  defaults: () => ipcRenderer.invoke('config:defaults'),
  readProfile: () => ipcRenderer.invoke('profile:read'),
  writeProfile: (data: unknown) => ipcRenderer.invoke('profile:write', data),
  readAnswers: () => ipcRenderer.invoke('answers:read'),
  writeAnswers: (text: string) => ipcRenderer.invoke('answers:write', text),

  // prereqs & db
  checkPrereqs: () => ipcRenderer.invoke('prereqs:check'),
  dbInit: () => ipcRenderer.invoke('db:init'),
  dbCheck: () => ipcRenderer.invoke('db:check'),
  dbReport: (date?: string) => ipcRenderer.invoke('db:report', date),
  dbToday: (date?: string) => ipcRenderer.invoke('db:today', date),
  dbStuck: () => ipcRenderer.invoke('db:stuck'),
  dbBackup: () => ipcRenderer.invoke('db:backup'),

  // files & shell
  pickFile: (kind: 'resume' | 'photo') => ipcRenderer.invoke('file:pick', kind),
  openConfigDir: () => ipcRenderer.invoke('open:configDir'),

  // routine run (stream)
  runRoutine: (source: string) => ipcRenderer.invoke('routine:run', source),
  onRoutineOutput: (cb: (chunk: string) => void) => {
    const handler = (_e: unknown, chunk: string): void => cb(chunk)
    ipcRenderer.on('routine:output', handler)
    return () => ipcRenderer.removeListener('routine:output', handler)
  }
}

contextBridge.exposeInMainWorld('aplica', api)

export type AplicaApi = typeof api
