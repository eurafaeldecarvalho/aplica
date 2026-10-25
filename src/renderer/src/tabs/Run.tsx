import React from 'react'
import { Card } from '../ui'
import { Icon } from '../icons'

const SOURCES = [
  { id: 'all', label: 'Everything' },
  { id: 'ats', label: 'ATS / boards' },
  { id: 'linkedin', label: 'LinkedIn Jobs' },
  { id: 'freehire', label: 'freehire' },
  { id: 'recruiters', label: 'Recruiters' },
  { id: 'feed', label: 'Feed' }
]

export default function Run(props: { config: any; onOpenSettings: () => void }): JSX.Element {
  const [source, setSource] = React.useState('all')
  const [output, setOutput] = React.useState('')
  const [running, setRunning] = React.useState(false)
  const [blockers, setBlockers] = React.useState<string[]>([])
  const preRef = React.useRef<HTMLPreElement>(null)

  const preflight = React.useCallback(async () => {
    const b: string[] = []
    const pr: any = await window.aplica.checkPrereqs()
    if (!pr.claude) b.push('Claude Code CLI (`claude`) not found on PATH')
    if (!pr.python) b.push('Python not found on PATH')
    if (!pr.configPresent) b.push('config.json missing — fill Settings → Job preferences and Save')
    if (!pr.profilePresent) b.push('profile.json missing — fill Settings → Your data and Save')
    const chk: any = await window.aplica.dbCheck()
    if (!(chk.stdout || '').trim().endsWith('OK')) b.push('Database not initialized — Home → Initialize database')
    setBlockers(b)
  }, [])

  React.useEffect(() => {
    preflight()
    window.aplica.isRunning().then((s: any) => setRunning(!!s?.running))
    const off = window.aplica.onRoutineOutput((chunk) => {
      setOutput((o) => o + chunk)
      requestAnimationFrame(() => { if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight })
    })
    return off
  }, [preflight])

  const run = async (): Promise<void> => {
    setOutput(''); setRunning(true)
    const r = await window.aplica.runRoutine(source)
    if (!r.ok) setOutput((o) => o + `\n[error] ${r.error}\n`)
    setRunning(false)
  }
  const stop = async (): Promise<void> => { await window.aplica.stopRoutine() }

  const feedWarn = source === 'feed' && props.config?.behavior?.feed_mode === 'off'

  return (
    <>
      <div className="page-head">
        <h2>Run</h2>
        <p>Run a round now, through Claude Code, in your browser. Watch the live output below.</p>
      </div>

      <div className="banner info">
        <Icon.info />
        <div>A run uses the <strong>aplica</strong> plugin installed in Claude Code (<code>/aplica-run</code>) and the Claude in Chrome extension.</div>
      </div>

      <div className="banner warn">
        <Icon.alert />
        <div>Runs are <strong>autonomous</strong> (no per-action approval, so it can work while you're away). The safeguards are the
        skill rules (honesty, stop on any LinkedIn block, never pay or send documents) — there's no second gate. Review your
        settings first and use <strong>Stop</strong> to interrupt.</div>
      </div>

      <Card title="Run now">
        <div className="field">
          <label>Source</label>
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            {SOURCES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </div>
        {feedWarn && <div className="banner warn" style={{ margin: '0 0 12px' }}><Icon.alert /><div>The feed is <strong>off</strong> in Behavior; this routine will do nothing.</div></div>}
        {blockers.length > 0 && (
          <div className="banner warn" style={{ margin: '0 0 12px' }}>
            <Icon.alert />
            <div>Finish setup before running:
              <ul>{blockers.map((b) => <li key={b}>{b}</li>)}</ul>
              <button className="btn secondary" style={{ marginTop: 8 }} onClick={props.onOpenSettings}><Icon.settings size={14} />Open settings</button>
            </div>
          </div>
        )}
        <div className="btn-row">
          <button className="btn" onClick={run} disabled={running || blockers.length > 0}><Icon.play size={14} />{running ? 'Running…' : 'Run'}</button>
          {running && <button className="btn danger" onClick={stop}><Icon.stop size={14} />Stop</button>}
        </div>
      </Card>

      <Card title="Output">
        <pre className="console" ref={preRef}>{output || '(the run output will appear here)'}</pre>
      </Card>
    </>
  )
}
