import React from 'react'
import { Card } from '../ui'
import { Icon } from '../icons'
import { commonAnsweredCount } from '../questions'

type Prereqs = {
  python: boolean; pythonBin: string | null
  claude: boolean; claudeBin: string | null
  configDir: string; enginePresent: boolean
  resumePresent: boolean; photoPresent: boolean; configPresent: boolean; profilePresent: boolean
}

const LINKS = {
  python: 'https://www.python.org/downloads/',
  claude: 'https://docs.claude.com/en/docs/claude-code/overview',
  extension: 'https://support.claude.com/en/articles/12012173',
  store: 'https://chromewebstore.google.com/search/Claude'
}

type Check = { label: string; done: boolean; go: () => void }

export default function Onboarding(props: {
  configDir: string; config: any; profile: any; onReload: () => void; onOpenSettings: (s?: string) => void
}): JSX.Element {
  const [pr, setPr] = React.useState<Prereqs | null>(null)
  const [dbMsg, setDbMsg] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const [chrome, setChrome] = React.useState<{ chromeFound: boolean; extFound: boolean } | null>(null)

  const refresh = React.useCallback(async () => { setPr(await window.aplica.checkPrereqs()) }, [])
  const recheckChrome = React.useCallback(async () => { setChrome(await window.aplica.detectChrome()) }, [])
  React.useEffect(() => { refresh(); recheckChrome() }, [refresh, recheckChrome])
  // re-checa os pré-requisitos quando config/profile mudam (ex.: após salvar no modal de Settings)
  React.useEffect(() => { refresh() }, [props.config, props.profile, refresh])

  const initDb = async (): Promise<void> => {
    setBusy(true)
    const r = await window.aplica.dbInit()
    const c = await window.aplica.dbCheck()
    setDbMsg((r.stdout || r.stderr) + '\n' + (c.stdout || c.stderr))
    setBusy(false)
    refresh()
  }
  const pick = async (kind: 'resume' | 'photo'): Promise<void> => { await window.aplica.pickFile(kind); refresh() }
  const open = (url: string): void => { window.aplica.openExternal(url) }

  const prof = props.profile || {}
  const tgt = (props.config || {}).target || {}
  const settings = props.onOpenSettings
  const nonEmpty = (v: any): boolean => Array.isArray(v) ? v.length > 0 : v && Object.keys(v).length > 0
  const commonAnswered = commonAnsweredCount(prof.open_answers?.qa || {})
  const checks: Check[] = [
    { label: 'Name', done: !!prof.identity?.full_name, go: () => settings('profile') },
    { label: 'Email', done: !!prof.identity?.email, go: () => settings('profile') },
    { label: 'Phone', done: !!prof.identity?.phone_e164, go: () => settings('profile') },
    { label: 'Location', done: !!(prof.address?.city && prof.address?.country), go: () => settings('profile') },
    { label: 'Links', done: !!(prof.links?.linkedin || prof.links?.github), go: () => settings('profile') },
    { label: 'Work authorization', done: nonEmpty(prof.work_authorization?.authorized_countries), go: () => settings('profile') },
    { label: 'Salary', done: nonEmpty(prof.preferences?.salary), go: () => settings('profile') },
    { label: 'Experience', done: !!(prof.experience?.total_years > 0 && nonEmpty(prof.experience?.stacks)), go: () => settings('profile') },
    { label: 'Years per tech', done: nonEmpty(prof.experience?.years_by_tech), go: () => settings('profile') },
    { label: 'Languages', done: nonEmpty(prof.languages), go: () => settings('profile') },
    { label: 'Pitch & answers', done: !!(prof.open_answers?.pitch && commonAnswered >= 3), go: () => settings('profile') },
    { label: 'Résumé', done: !!pr?.resumePresent, go: () => pick('resume') },
    { label: 'Search titles', done: nonEmpty(tgt.titles_search), go: () => settings('target') },
    { label: 'Target markets', done: nonEmpty(tgt.geo_allow), go: () => settings('target') }
  ]
  const done = checks.filter((c) => c.done).length
  const pct = Math.round((done / checks.length) * 100)
  const missing = checks.filter((c) => !c.done)

  const Row = (p: { ok: boolean; icon: () => JSX.Element; title: string; detail?: React.ReactNode; action?: React.ReactNode }): JSX.Element => (
    <div className={'check-row ' + (p.ok ? 'ok' : 'bad')}>
      <span className="ico-wrap">{p.ok ? <Icon.check /> : <p.icon />}</span>
      <div className="grow">
        <strong>{p.title}</strong>
        {p.detail && <small>{p.detail}</small>}
      </div>
      {!p.ok && p.action}
      <span className={'badge ' + (p.ok ? 'ok' : 'bad')}>{p.ok ? 'ready' : 'missing'}</span>
    </div>
  )

  return (
    <>
      <div className="page-head">
        <h2>Welcome to Aplica</h2>
        <p>Aplica applies to your jobs in your own browser, with your own data. Complete the steps below to get started.</p>
      </div>

      <div className="banner warn">
        <Icon.alert />
        <div>
          <strong>Read before you use it.</strong> Boards like LinkedIn, Indeed and Glassdoor restrict automation in their
          terms — your account can be limited or banned. Social actions (comment/DM/connect) and high volume are the biggest
          triggers, so they ship <strong>off by default</strong>. You run it on your own account, at your own risk.
        </div>
      </div>

      <Card title="Profile completeness">
        <div className="progress-head">
          <div className="pct">{pct}<small>% complete</small></div>
          <div className="count">{done} of {checks.length} done</div>
        </div>
        <div className="progress-track"><div className={'progress-fill' + (pct === 100 ? ' done' : '')} style={{ width: `${pct}%` }} /></div>
        {missing.length > 0 ? (
          <div className="missing-list">
            {missing.map((m) => (
              <span key={m.label} className="missing-chip" onClick={m.go}><span className="dot" />{m.label}</span>
            ))}
          </div>
        ) : (
          <div className="all-done"><Icon.check />Profile complete — you're ready to run.</div>
        )}
      </Card>

      <Card title="Prerequisites">
        {pr ? (
          <>
            <Row ok={pr.python} icon={Icon.python} title="Python 3.11+ on PATH"
              detail={pr.pythonBin ? `found: ${pr.pythonBin}` : 'required to run the engine'}
              action={<button className="btn secondary" onClick={() => open(LINKS.python)}><Icon.download size={14} />Get Python</button>} />
            <Row ok={pr.claude} icon={Icon.bolt} title="Claude Code CLI (`claude`) on PATH"
              detail={pr.claudeBin ? `found: ${pr.claudeBin}` : 'install Claude Code and sign in (paid plan)'}
              action={<button className="btn secondary" onClick={() => open(LINKS.claude)}><Icon.external size={14} />Install Claude Code</button>} />
            <Row ok={pr.enginePresent} icon={Icon.bolt} title="Aplica engine" detail="bundled with the app" />
            <Row ok={pr.configPresent} icon={Icon.target} title="Job preferences (config.json)"
              detail="set what you're looking for and how it behaves"
              action={<button className="btn secondary" onClick={() => props.onOpenSettings('target')}><Icon.settings size={14} />Open settings</button>} />
            <Row ok={pr.profilePresent} icon={Icon.user} title="Your data (profile.json)"
              detail="your real candidate data"
              action={<button className="btn secondary" onClick={() => props.onOpenSettings('profile')}><Icon.settings size={14} />Open settings</button>} />
            <Row ok={pr.resumePresent} icon={Icon.download} title="Résumé (resume.pdf)"
              detail="attached to every application"
              action={<button className="btn secondary" onClick={() => pick('resume')}><Icon.folder size={14} />Choose file</button>} />
            <div className="btn-row" style={{ marginTop: 14 }}>
              <button className="btn secondary" onClick={() => { refresh(); recheckChrome() }}><Icon.refresh size={14} />Re-check</button>
              <button className="btn ghost" onClick={() => window.aplica.openConfigDir()}><Icon.folder size={14} />Open config folder</button>
              <button className="btn ghost" onClick={() => pick('photo')}>Choose photo</button>
            </div>
          </>
        ) : <p className="muted">Checking…</p>}
      </Card>

      <Card title="Claude in Chrome extension" hint="Required so Aplica can act in your browser. Needs a paid Claude plan; keep your accounts (LinkedIn, Google) signed in.">
        <div className={'check-row ' + (chrome?.extFound ? 'ok' : chrome?.chromeFound === false ? 'bad' : '')}>
          <span className="ico-wrap">{chrome?.extFound ? <Icon.check /> : <Icon.chrome />}</span>
          <div className="grow">
            <strong>{chrome?.extFound ? 'Extension detected' : chrome?.chromeFound ? 'Not detected in your Chrome profiles' : 'Could not check (Chrome not found)'}</strong>
            <small>{chrome?.extFound ? 'The Claude extension looks installed.' : 'Install it from the Chrome Web Store, then sign in and pin it.'}</small>
          </div>
          {!chrome?.extFound && (
            <button className="btn" onClick={() => open(LINKS.store)}><Icon.download size={14} />Install extension</button>
          )}
          <span className={'badge ' + (chrome?.extFound ? 'ok' : 'warn')}>{chrome?.extFound ? 'ready' : 'action'}</span>
        </div>
        <div className="btn-row" style={{ marginTop: 12 }}>
          <button className="btn secondary" onClick={recheckChrome}><Icon.refresh size={14} />Re-check</button>
          <button className="btn ghost" onClick={() => open(LINKS.extension)}><Icon.external size={14} />Setup guide</button>
        </div>
      </Card>

      <Card title="Local database" hint="Creates the local state DB (applications, dedup, stuck jobs) in your config folder.">
        <div className="btn-row">
          <button className="btn" onClick={initDb} disabled={busy || !pr?.python}><Icon.bolt size={14} />Initialize / check database</button>
        </div>
        {dbMsg && <pre className="console" style={{ marginTop: 14 }}>{dbMsg}</pre>}
      </Card>
    </>
  )
}
