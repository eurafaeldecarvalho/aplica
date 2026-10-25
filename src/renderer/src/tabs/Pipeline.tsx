import React from 'react'
import { Icon } from '../icons'

type Appl = {
  id: number; date: string; company: string; title: string; source: string
  status: string; fit: number | null; resume: string | null; url: string | null
}

// The pipeline columns, in funnel order. 'uncertain' is folded into 'applied' for display
// but can still be set. Each status maps to one column.
const COLUMNS: { id: string; label: string }[] = [
  { id: 'applied', label: 'Applied' },
  { id: 'in-process', label: 'In process' },
  { id: 'interview', label: 'Interview' },
  { id: 'offer', label: 'Offer' },
  { id: 'rejected', label: 'Rejected / no reply' }
]
// which real statuses live under each column
const COLUMN_OF: Record<string, string> = {
  applied: 'applied', uncertain: 'applied',
  'test-pending': 'in-process', 'in-process': 'in-process',
  interview: 'interview', offer: 'offer',
  rejected: 'rejected', 'no-reply': 'rejected', withdrawn: 'rejected'
}

export default function Pipeline(props: { onGenerateDraft: (kind: string, id: number, label: string) => void }): JSX.Element {
  const [apps, setApps] = React.useState<Appl[]>([])
  const [loading, setLoading] = React.useState(false)
  const [err, setErr] = React.useState('')
  const [drag, setDrag] = React.useState<number | null>(null)
  const [over, setOver] = React.useState<string | null>(null)

  const load = React.useCallback(async () => {
    setLoading(true); setErr('')
    const check = await window.aplica.dbCheck()
    if (!(check.stdout || '').trim().endsWith('OK')) {
      setErr('Database not initialized. Go to Home → Initialize database.'); setApps([]); setLoading(false); return
    }
    try { setApps(await window.aplica.dbApplications()) } catch { setErr('Could not read applications.') }
    setLoading(false)
  }, [])
  React.useEffect(() => { load() }, [load])

  const move = async (id: number, column: string): Promise<void> => {
    const app = apps.find((a) => a.id === id)
    if (!app || COLUMN_OF[app.status] === column) return
    // optimistic: set to the column's canonical status
    setApps((xs) => xs.map((a) => (a.id === id ? { ...a, status: column } : a)))
    const r = await window.aplica.dbSetStatus(id, column)
    if (!(r.stdout || '').startsWith('OK')) { setErr(r.stderr || 'Could not update status.'); load() }
  }

  const byColumn = (col: string): Appl[] => apps.filter((a) => (COLUMN_OF[a.status] || 'applied') === col)
  const total = apps.length

  return (
    <>
      <div className="page-head">
        <h2>Pipeline</h2>
        <p>Every application as a board. Drag a card to update its status, or generate a grounded draft for it.</p>
      </div>

      <div className="btn-row" style={{ marginBottom: 16 }}>
        <button className="btn secondary" onClick={load} disabled={loading}><Icon.refresh size={14} />{loading ? 'Loading…' : 'Refresh'}</button>
        <span className="badge">{total} application{total === 1 ? '' : 's'}</span>
      </div>

      {err && <div className="banner warn"><Icon.alert /><div>{err}</div></div>}

      {total === 0 && !err ? (
        <div className="empty-state">
          <div className="e-ico"><Icon.grid /></div>
          <strong>No applications yet</strong>
          <p className="muted" style={{ marginTop: 4 }}>Run a round from the Run tab; applied jobs show up here.</p>
        </div>
      ) : (
        <div className="kanban">
          {COLUMNS.map((col) => {
            const items = byColumn(col.id)
            return (
              <div
                key={col.id}
                className={'kanban-col' + (over === col.id ? ' over' : '')}
                onDragOver={(e) => { e.preventDefault(); if (over !== col.id) setOver(col.id) }}
                onDragLeave={() => setOver((o) => (o === col.id ? null : o))}
                onDrop={() => { if (drag != null) move(drag, col.id); setDrag(null); setOver(null) }}
              >
                <div className="kanban-head"><span>{col.label}</span><span className="kanban-count">{items.length}</span></div>
                <div className="kanban-body">
                  {items.map((a) => (
                    <div
                      key={a.id}
                      className="kanban-card"
                      draggable
                      onDragStart={() => setDrag(a.id)}
                      onDragEnd={() => { setDrag(null); setOver(null) }}
                    >
                      <div className="kc-top">
                        <strong>{a.company}</strong>
                        {a.fit != null && <span className={'fit ' + (a.fit >= 85 ? 'hi' : a.fit >= 70 ? 'mid' : 'lo')}>{a.fit}</span>}
                      </div>
                      <div className="kc-title">{a.title}</div>
                      <div className="kc-meta">
                        {a.source?.split(' ')[0] || '—'}{a.resume ? ` · ${a.resume}` : ''} · {a.date}
                      </div>
                      <div className="kc-actions">
                        {a.url && <button title="Open job" onClick={() => window.aplica.openExternal(a.url!)}><Icon.external size={13} /></button>}
                        <button title="Draft cover letter" onClick={() => props.onGenerateDraft('cover', a.id, `${a.company} — ${a.title}`)}>Cover</button>
                        <button title="Draft follow-up" onClick={() => props.onGenerateDraft('followup', a.id, `${a.company} — ${a.title}`)}>Follow-up</button>
                        <button title="Interview prep" onClick={() => props.onGenerateDraft('prep', a.id, `${a.company} — ${a.title}`)}>Prep</button>
                      </div>
                    </div>
                  ))}
                  {items.length === 0 && <div className="kanban-empty">—</div>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
