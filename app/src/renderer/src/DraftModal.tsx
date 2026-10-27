import React from 'react'
import { Icon } from './icons'

const TITLES: Record<string, string> = { cover: 'Cover letter', followup: 'Follow-up message', prep: 'Interview prep' }

/** Streams `/aplica-draft <kind> <id>` through Claude Code and shows the live output. The draft
 * itself is written to the config dir's drafts/ folder and recorded in the database; this window
 * just shows progress. Interview-prep is a study sheet, never sent. */
export default function DraftModal(props: { kind: string; applicationId: number; label: string; onClose: () => void }): JSX.Element {
  const [output, setOutput] = React.useState('')
  const [running, setRunning] = React.useState(false)
  const [started, setStarted] = React.useState(false)
  const [blocked, setBlocked] = React.useState<string | null>(null)
  const preRef = React.useRef<HTMLPreElement>(null)

  React.useEffect(() => {
    const off = window.aplica.onDraftOutput((chunk) => {
      setOutput((o) => o + chunk)
      requestAnimationFrame(() => { if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight })
    })
    window.aplica.checkPrereqs().then((pr: any) => { if (!pr.claude) setBlocked('The Claude Code CLI (`claude`) was not found on PATH.') })
    window.aplica.isDraftRunning().then((s: any) => setRunning(!!s?.running))
    return off
  }, [])

  const generate = async (): Promise<void> => {
    setStarted(true); setOutput(''); setRunning(true)
    const r = await window.aplica.runDraft(props.kind, props.applicationId)
    if (!r.ok) setOutput((o) => o + `\n[error] ${r.error}\n`)
    setRunning(false)
  }

  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget && !running) props.onClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Generate draft" style={{ maxWidth: 760 }}>
        <div className="modal-head">
          <h2>{TITLES[props.kind] || 'Draft'}</h2>
          <button className="icon-btn" onClick={() => { if (!running) props.onClose() }} aria-label="Close" disabled={running}><Icon.x /></button>
        </div>
        <div className="modal-body" style={{ padding: 20 }}>
          <p className="muted" style={{ marginTop: 0 }}>For <strong>{props.label}</strong></p>

          <div className="banner info">
            <Icon.info />
            <div>Written <strong>only</strong> from your real profile and this application's recorded facts — it never invents
            experience. Runs through Claude Code; the file is saved to <code>drafts/</code> in your config dir and listed on the Dashboard.
            {props.kind === 'prep' && ' Interview prep is a study sheet, never sent anywhere.'}</div>
          </div>

          {blocked && <div className="banner warn"><Icon.alert /><div>{blocked}</div></div>}

          {!started ? (
            <div className="btn-row">
              <button className="btn" onClick={generate} disabled={!!blocked}><Icon.bolt size={14} />Generate</button>
              <button className="btn secondary" onClick={props.onClose}>Cancel</button>
            </div>
          ) : (
            <>
              <pre className="console" ref={preRef} style={{ maxHeight: 380 }}>{output || '(starting…)'}</pre>
              <div className="btn-row" style={{ marginTop: 12 }}>
                <button className="btn secondary" onClick={props.onClose} disabled={running}>{running ? 'Working…' : 'Done'}</button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
