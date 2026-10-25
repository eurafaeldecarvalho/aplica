// Mock of window.aplica to run the renderer in a plain browser (no Electron),
// used for development / visual preview. In production the preload provides the real API.
import { DEFAULT_CONFIG, BLANK_PROFILE } from './mockData'

const MOCK_APPS = [
  { id: 1, date: '2026-10-24', company: 'Acme', title: 'Backend Engineer', source: 'ATS greenhouse', status: 'applied', fit: 88, resume: 'backend', url: 'https://x/1' },
  { id: 2, date: '2026-10-22', company: 'Globex', title: 'Node.js Developer', source: 'LinkedIn', status: 'interview', fit: 91, resume: 'backend', url: 'https://x/2' },
  { id: 3, date: '2026-10-20', company: 'Initech', title: 'TypeScript Engineer', source: 'Remotive', status: 'in-process', fit: 79, resume: 'fullstack', url: 'https://x/3' },
  { id: 4, date: '2026-10-18', company: 'Umbrella', title: 'Platform Engineer', source: 'ATS ashby', status: 'rejected', fit: 72, resume: 'backend', url: 'https://x/4' },
  { id: 5, date: '2026-10-10', company: 'Hooli', title: 'Staff Engineer', source: 'LinkedIn', status: 'no-reply', fit: 84, resume: 'fullstack', url: 'https://x/5' }
]

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
    dbCheck: async () => ok({ stdout: 'applications: 5\nOK' }),
    dbReport: async () => ok({ stdout: '# Summary (mock)\n\n## Applications (3)\n- Acme — Backend Engineer — applied — ATS\n- Globex — Node.js Developer — interview — LinkedIn\n- Initech — TypeScript Engineer — in-process — Remotive\n\n## Needs you (1 open)\n- #1 Complete your profile on Gupy' }),
    dbToday: async () => ok({ stdout: 'APPLICATIONS_COUNTED=2\nid\tcompany\ttitle\tstatus\n1\tAcme\tBackend Engineer\tapplied' }),
    dbStuck: async () => ({ travadas: '(none)', pendencias: '#1\tComplete your profile on Gupy' }),
    dbMetrics: async () => ok({ stdout: '# Metrics — 24 applications (excludes uncertain)\nReply rate: 29% (7) | Interview rate: 12% (3)\n\nsource\tapplications\treplies\treply_rate\tinterviews\tinterview_rate\nLinkedIn\t14\t5\t36%\t2\t14%\nATS\t7\t2\t29%\t1\t14%\n\nresume\tapplications\treplies\treply_rate\tinterviews\tinterview_rate\nbackend\t16\t6\t38%\t3\t19%\nfullstack\t8\t1\t13%\t0\t0%' }),
    dbMetricsJson: async () => ({ code: 0, stdout: JSON.stringify({ total: 24, replies: 7, interviews: 3, by_source: [{ name: 'LinkedIn', applications: 14, replies: 5, interviews: 2 }, { name: 'ATS', applications: 7, replies: 2, interviews: 1 }], by_resume: [{ name: 'backend', applications: 16, replies: 6, interviews: 3 }, { name: 'fullstack', applications: 8, replies: 1, interviews: 0 }] }), stderr: '' }),
    dbFollowups: async () => ok({ stdout: 'id\tdate\tcompany\ttitle\tstatus\n5\t2026-10-10\tHooli\tStaff Engineer\tno-reply' }),
    dbApplications: async () => MOCK_APPS,
    dbSetStatus: async () => ok(),
    dbContacts: async () => ([
      { id: 'jane-roe', name: 'Jane Roe', company: 'Globex', role: 'Recruiter', profile_url: 'https://linkedin.com/in/jane', email: '', notes: '', last_date: '2026-10-22', touches: 3, sent: 1, received: 2, last_touch: 'linkedin-dm · received — scheduling a call', application_id: 2 },
      { id: 'sam-poe', name: 'Sam Poe', company: 'Acme', role: 'Eng Manager', profile_url: '', email: '', notes: '', last_date: '2026-10-21', touches: 1, sent: 0, received: 1, last_touch: 'email · received — intro', application_id: 1 }
    ]),
    dbContactHistory: async () => ([{ id: 1, date: '2026-10-22', channel: 'linkedin-dm', direction: 'received', company: 'Globex', summary: 'scheduling a call', application_id: 2 }]),
    dbDrafts: async () => ([{ id: 1, date: '2026-10-22', kind: 'cover-letter', application_id: 2, company: 'Globex', title: 'Node.js Developer', path: '~/.config/aplica/drafts/cover-letter-globex.txt', status: 'draft' }]),
    dbDraftMarkSent: async () => ok(),
    openDraft: async () => ({ ok: true }),
    notifyDesktop: async () => ({ ok: true }),
    listNotifications: async () => ([
      { level: 'error', title: 'LinkedIn needs your attention', detail: 'BLOCKED since 2026-10-24 — verify in Chrome' },
      { level: 'warn', title: 'Needs you', detail: 'Complete your profile on Gupy', action: 'dashboard' },
      { level: 'info', title: 'Run: ats-boards', detail: '5 applications — sources: Greenhouse, Ashby' }
    ]),
    dbBackup: async () => ok({ stdout: 'OK backup (mock)' }),
    pickFile: async () => ({ ok: true, dest: '~/.config/aplica/resume.pdf' }),
    openConfigDir: async () => ({ ok: true }),
    openExternal: async () => ({ ok: true }),
    detectChrome: async () => ({ chromeFound: true, extFound: false }),
    checkPlugin: async () => ({ ok: true, installed: false }),
    installPlugin: async () => ({ ok: true, output: 'Installed aplica@aplica (mock)' }),
    runRoutine: async () => ({ ok: true, code: 0 }),
    stopRoutine: async () => ({ ok: true }),
    isRunning: async () => ({ running: false }),
    onRoutineOutput: (cb: (c: string) => void) => {
      const t = setTimeout(() => cb('[mock] sample run…\n[run finished with code 0]\n'), 400)
      return () => clearTimeout(t)
    },
    runDraft: async () => ({ ok: true, code: 0 }),
    isDraftRunning: async () => ({ running: false }),
    onDraftOutput: (cb: (c: string) => void) => {
      const t = setTimeout(() => cb('[mock] drafting…\nOK draft id=1\n[run finished with code 0]\n'), 400)
      return () => clearTimeout(t)
    }
  }
}
