// Mock de window.aplica para rodar o renderer num navegador comum (sem Electron),
// usado em desenvolvimento/preview visual. Em produção o preload fornece a API real.
import { DEFAULT_CONFIG, BLANK_PROFILE } from './mockData'

if (typeof window !== 'undefined' && !(window as any).aplica) {
  let config = JSON.parse(JSON.stringify(DEFAULT_CONFIG))
  let profile = JSON.parse(JSON.stringify(BLANK_PROFILE))
  let answers = ''
  const ok = (extra: any = {}): any => ({ code: 0, stdout: '', stderr: '', ...extra })
  ;(window as any).aplica = {
    getConfigDir: async () => '~/.config/aplica (mock)',
    readConfig: async () => ({ exists: true, data: config }),
    writeConfig: async (d: any) => { config = d; return { ok: true } },
    defaults: async () => DEFAULT_CONFIG,
    readProfile: async () => ({ exists: true, data: profile }),
    writeProfile: async (d: any) => { profile = d; return { ok: true } },
    readAnswers: async () => ({ exists: true, text: answers }),
    writeAnswers: async (t: string) => { answers = t; return { ok: true } },
    checkPrereqs: async () => ({
      python: true, pythonBin: 'python', claude: false, claudeBin: null,
      configDir: '~/.config/aplica (mock)', enginePresent: true,
      resumePresent: false, configPresent: true, profilePresent: true
    }),
    dbInit: async () => ok({ stdout: 'OK schema (mock)' }),
    dbCheck: async () => ok({ stdout: 'candidaturas: 3\nOK' }),
    dbReport: async () => ok({ stdout: '# Resumo (mock)\n\n## Candidaturas (3)\n- Acme — Backend Engineer — aplicada — ATS\n- Globex — Node.js Developer — entrevista — LinkedIn\n- Initech — TypeScript Engineer — incerta — Remotive\n\n## Precisa de você (1 abertas)\n- #1 Completar perfil na Gupy' }),
    dbToday: async () => ok({ stdout: 'CANDIDATURAS_CONTAM=2\nid\tempresa\ttitulo\tstatus\n1\tAcme\tBackend Engineer\taplicada' }),
    dbStuck: async () => ({ travadas: '(nenhuma)', pendencias: '#1\tCompletar perfil na Gupy' }),
    dbBackup: async () => ok({ stdout: 'OK backup (mock)' }),
    pickFile: async () => ({ ok: true, dest: '~/.config/aplica/resume.pdf' }),
    openConfigDir: async () => ({ ok: true }),
    runRoutine: async () => ({ ok: true, code: 0 }),
    onRoutineOutput: (cb: (c: string) => void) => {
      const t = setTimeout(() => cb('[mock] execução de exemplo…\n[execução terminou com código 0]\n'), 400)
      return () => clearTimeout(t)
    }
  }
}
