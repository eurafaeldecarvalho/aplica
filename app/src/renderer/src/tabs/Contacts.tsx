import React from 'react'
import { Card } from '../ui'
import { Icon } from '../icons'

type Person = {
  id: string; name: string; company: string | null; role: string | null
  profile_url: string | null; email: string | null; notes: string | null
  last_date: string | null; touches: number; sent: number; received: number
  last_touch: string | null; application_id: number | null
}
type Interaction = { id: number; date: string; channel: string; direction: string; company: string | null; summary: string | null }

export default function Contacts(): JSX.Element {
  const [people, setPeople] = React.useState<Person[]>([])
  const [loading, setLoading] = React.useState(false)
  const [err, setErr] = React.useState('')
  const [q, setQ] = React.useState('')
  const [open, setOpen] = React.useState<string | null>(null)
  const [history, setHistory] = React.useState<Interaction[]>([])

  const load = React.useCallback(async () => {
    setLoading(true); setErr('')
    const check = await window.aplica.dbCheck()
    if (!(check.stdout || '').trim().endsWith('OK')) {
      setErr('Database not initialized. Go to Home → Initialize database.'); setPeople([]); setLoading(false); return
    }
    try { setPeople(await window.aplica.dbContacts()) } catch { setErr('Could not read contacts.') }
    setLoading(false)
  }, [])
  React.useEffect(() => { load() }, [load])

  const toggle = async (id: string): Promise<void> => {
    if (open === id) { setOpen(null); return }
    setOpen(id)
    try { setHistory(await window.aplica.dbContactHistory(id)) } catch { setHistory([]) }
  }

  const filtered = people.filter((p) => {
    const s = q.trim().toLowerCase()
    return !s || [p.name, p.company, p.role, p.notes].some((x) => (x || '').toLowerCase().includes(s))
  })

  return (
    <>
      <div className="page-head">
        <h2>Contacts</h2>
        <p>Everyone Aplica has talked to — recruiters and hiring managers, with your whole history per person.</p>
      </div>

      <div className="btn-row" style={{ marginBottom: 16 }}>
        <button className="btn secondary" onClick={load} disabled={loading}><Icon.refresh size={14} />{loading ? 'Loading…' : 'Refresh'}</button>
        <span className="badge">{people.length} {people.length === 1 ? 'person' : 'people'}</span>
      </div>

      {err && <div className="banner warn"><Icon.alert /><div>{err}</div></div>}

      {people.length > 0 && (
        <div className="field" style={{ marginBottom: 14 }}>
          <input type="text" value={q} placeholder="Search by name, company, role…" onChange={(e) => setQ(e.target.value)} />
        </div>
      )}

      {filtered.length === 0 && !err ? (
        <div className="empty-state">
          <div className="e-ico"><Icon.user /></div>
          <strong>No contacts yet</strong>
          <p className="muted" style={{ marginTop: 4 }}>Recruiter replies and connections are logged here as the routines run.</p>
        </div>
      ) : (
        filtered.map((p) => (
          <Card key={p.id}>
            <div className="contact-row" onClick={() => toggle(p.id)}>
              <div className="c-avatar">{(p.name || '?').slice(0, 1).toUpperCase()}</div>
              <div className="c-main">
                <div className="c-name">
                  <strong>{p.name}</strong>
                  {p.role && <span className="muted"> · {p.role}</span>}
                  {p.company && <span className="muted"> · {p.company}</span>}
                </div>
                <div className="c-last">{p.last_touch || 'no interactions recorded'}</div>
              </div>
              <div className="c-side">
                <span className="badge">{p.touches} touch{p.touches === 1 ? '' : 'es'}</span>
                {p.last_date && <span className="muted" style={{ fontSize: 12 }}>{p.last_date}</span>}
              </div>
            </div>
            {open === p.id && (
              <div className="c-detail">
                <div className="c-links">
                  {p.profile_url && <button className="btn secondary" onClick={() => window.aplica.openExternal(p.profile_url!)}><Icon.external size={13} />LinkedIn</button>}
                  {p.email && <button className="btn secondary" onClick={() => window.aplica.openExternal(`mailto:${p.email}`)}>Email</button>}
                </div>
                {p.notes && <p className="hint" style={{ marginTop: 8 }}>{p.notes}</p>}
                <table className="mini-table">
                  <tbody>
                    {history.map((h) => (
                      <tr key={h.id}>
                        <td className="muted" style={{ whiteSpace: 'nowrap' }}>{h.date}</td>
                        <td>{h.channel}</td>
                        <td>{h.direction === 'sent' ? '→ sent' : '← received'}</td>
                        <td>{h.summary || ''}</td>
                      </tr>
                    ))}
                    {history.length === 0 && <tr><td className="muted" colSpan={4}>No interactions recorded.</td></tr>}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        ))
      )}
    </>
  )
}
