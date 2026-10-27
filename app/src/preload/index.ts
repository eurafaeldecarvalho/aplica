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
  checkPlugin: () => ipcRenderer.invoke('plugin:check'),
  installPlugin: () => ipcRenderer.invoke('plugin:install'),
  dbInit: () => ipcRenderer.invoke('db:init'),
  dbCheck: () => ipcRenderer.invoke('db:check'),
  dbReport: (date?: string) => ipcRenderer.invoke('db:report', date),
  dbToday: (date?: string) => ipcRenderer.invoke('db:today', date),
  dbStuck: () => ipcRenderer.invoke('db:stuck'),
  dbMetrics: () => ipcRenderer.invoke('db:metrics'),
  dbMetricsJson: () => ipcRenderer.invoke('db:metricsJson'),
  dbFollowups: (days?: number) => ipcRenderer.invoke('db:followups', days),
  dbBackup: () => ipcRenderer.invoke('db:backup'),
  dbApplications: () => ipcRenderer.invoke('db:applications'),
  dbSetStatus: (id: number, status: string) => ipcRenderer.invoke('db:setStatus', id, status),
  dbContacts: () => ipcRenderer.invoke('db:contacts'),
  dbContactHistory: (person: string) => ipcRenderer.invoke('db:contactHistory', person),
  dbDrafts: () => ipcRenderer.invoke('db:drafts'),
  dbDraftMarkSent: (id: number) => ipcRenderer.invoke('db:draftMarkSent', id),
  openDraft: (path: string) => ipcRenderer.invoke('draft:open', path),
  notifyDesktop: (items: unknown) => ipcRenderer.invoke('notify:desktop', items),
  listNotifications: () => ipcRenderer.invoke('notifications:list'),

  // files & shell
  pickFile: (kind: 'resume' | 'photo') => ipcRenderer.invoke('file:pick', kind),
  openConfigDir: () => ipcRenderer.invoke('open:configDir'),
  openExternal: (url: string) => ipcRenderer.invoke('open:external', url),
  detectChrome: () => ipcRenderer.invoke('chrome:detect'),

  // routine run (stream)
  runRoutine: (source: string) => ipcRenderer.invoke('routine:run', source),
  stopRoutine: () => ipcRenderer.invoke('routine:stop'),
  isRunning: () => ipcRenderer.invoke('routine:running'),
  onRoutineOutput: (cb: (chunk: string) => void) => {
    const handler = (_e: unknown, chunk: string): void => cb(chunk)
    ipcRenderer.on('routine:output', handler)
    return (): void => {
      ipcRenderer.removeListener('routine:output', handler)
    }
  },

  // grounded draft generation (stream)
  runDraft: (kind: string, applicationId: number) => ipcRenderer.invoke('draft:run', kind, applicationId),
  isDraftRunning: () => ipcRenderer.invoke('draft:running'),
  onDraftOutput: (cb: (chunk: string) => void) => {
    const handler = (_e: unknown, chunk: string): void => cb(chunk)
    ipcRenderer.on('draft:output', handler)
    return (): void => {
      ipcRenderer.removeListener('draft:output', handler)
    }
  }
}

contextBridge.exposeInMainWorld('aplica', api)

export type AplicaApi = typeof api
