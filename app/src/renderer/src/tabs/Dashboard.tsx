import React from 'react'
import { Card } from '../ui'
import { Icon } from '../icons'

export default function Dashboard(): JSX.Element {
  const [report, setReport] = React.useState('')
  const [today, setToday] = React.useState('')
  const [stuck, setStuck] = React.useState<{ travadas: string; pendencias: string } | null>(null)
  const [metrics, setMetrics] = React.useState('')
  const [followups, setFollowups] = React.useState('')
  const [drafts, setDrafts] = React.useState<any[]>([])
  const [err, setErr] = React.useState('')
  const [loading, setLoading] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true); setErr('')
    const check = await window.aplica.dbCheck()
    if (!(check.stdout || '').trim().endsWith('OK')) {
      setErr('Database not initialized. Go to Home → Initialize database.')
      setLoading(false); return
    }
    const [r, t, s, m, f, d] = await Promise.all([
      window.aplica.dbReport(), window.aplica.dbToday(), window.aplica.dbStuck(),
      window.aplica.dbMetrics(), window.aplica.dbFollowups(7), window.aplica.dbDrafts()
    ])
    setReport(r.stdout || r.stderr)
    setToday(t.stdout || t.stderr)
    setStuck(s)
    setMetrics(m.stdout || m.stderr)
    setFollowups(f.stdout || f.stderr)
    setDrafts(Array.isArray(d) ? d : [])
    setLoading(false)
  }, [])

  React.useEffect(() => { load() }, [load])

  const countToday = (): string => {
    const m = /APPLICATIONS_COUNTED=(\d+)/.exec(today)
    return m ? m[1] : '—'
  }

  return (
    <>
      <div className="page-head">
        <h2>Dashboard</h2>
        <p>Your local database — applications, response rate, stuck jobs and what needs you.</p>
      </div>

      <div className="btn-row" style={{ marginBottom: 18 }}>
        <button className="btn secondary" onClick={load} disabled={loading}><Icon.refresh size={14} />{loading ? 'Loading…' : 'Refresh'}</button>
        <span className="badge">Applications today: {countToday()}</span>
      </div>

      {err && <div className="banner warn"><Icon.alert /><div>{err}</div></div>}

      <Card title="Response rate by source & résumé">
        <pre className="console">{metrics || '(no data)'}</pre>
      </Card>

      {drafts.length > 0 && (
        <Card title="Drafts">
          <table className="mini-table">
            <tbody>
              {drafts.map((d) => (
                <tr key={d.id}>
                  <td style={{ whiteSpace: 'nowrap' }}>{d.kind}</td>
                  <td>{d.company || ''}{d.title ? ` — ${d.title}` : ''}</td>
                  <td className="muted" style={{ whiteSpace: 'nowrap' }}>{d.status}</td>
                  <td style={{ whiteSpace: 'nowrap' }}>
                    <button className="btn secondary" onClick={() => window.aplica.openDraft(d.path)}><Icon.file size={13} />Open</button>
                    {d.status === 'draft' && <button className="btn secondary" style={{ marginLeft: 6 }} onClick={async () => { await window.aplica.dbDraftMarkSent(d.id); load() }}>Mark sent</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}

      <Card title="Today's summary">
        <pre className="console">{report || '(no data)'}</pre>
      </Card>

      <Card title="Suggested follow-ups (no reply for 7+ days)">
        <pre className="console">{followups || '(none)'}</pre>
      </Card>

      {stuck && (
        <div className="grid">
          <Card title="Stuck jobs (you finish by hand)">
            <pre className="console">{stuck.travadas || '(none)'}</pre>
          </Card>
          <Card title="Needs you">
            <pre className="console">{stuck.pendencias || '(none)'}</pre>
          </Card>
        </div>
      )}
    </>
  )
}
