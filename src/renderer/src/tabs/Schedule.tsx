import React from 'react'
import { Card, Toggle, SaveBar } from '../ui'
import { Icon } from '../icons'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

const LABELS: Record<string, string> = {
  ats: 'ATS / boards',
  linkedin_jobs: 'LinkedIn Jobs',
  recruiters: 'Recruiters (inbox + Gmail)',
  feed: 'LinkedIn feed',
  summary: 'Daily summary'
}

export default function Schedule(props: { config: any; onSave: (c: any) => Promise<void>; embedded?: boolean; onDirty?: (v: boolean) => void }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const sch = c.schedule || {}
  const touch = (): void => { setSaved(false); props.onDirty?.(true) }

  const setEnabled = (k: string, v: boolean): void => { const n = clone(c); n.schedule = { ...(n.schedule || {}), [k]: { ...(n.schedule?.[k] || {}), enabled: v } }; setC(n); touch() }
  const setTimes = (k: string, times: string[]): void => { const n = clone(c); n.schedule = { ...(n.schedule || {}), [k]: { ...(n.schedule?.[k] || {}), times } }; setC(n); touch() }

  // salva só a fatia desta seção (schedule) sobre o config mais recente.
  const save = async (): Promise<void> => {
    const n = clone(props.config); n.schedule = c.schedule
    await props.onSave(n); setC(n); setSaved(true); props.onDirty?.(false)
  }

  return (
    <>
      <div className="page-head">
        <h2>Schedule</h2>
        <p>Times for each routine. The app saves the schedule; Claude Code turns it into real tasks.</p>
      </div>

      <div className="banner info">
        <Icon.info />
        <div>The schedule is saved to your config. To apply it, run <code>/aplica-schedule</code> in Claude Code — it reads these
        times and creates/updates the routines' scheduled tasks (the app can't create tasks on its own).</div>
      </div>

      {Object.keys(LABELS).map((k) => (
        <Card key={k} title={LABELS[k]}>
          <Toggle label="Enabled" checked={sch[k]?.enabled} onChange={(v) => setEnabled(k, v)} />
          <div className="field" style={{ marginTop: 10 }}>
            <label>Times (HH:MM, comma-separated)</label>
            <input
              type="text"
              value={(sch[k]?.times || []).join(', ')}
              placeholder="e.g. 09:00, 15:00"
              onChange={(e) => setTimes(k, e.target.value.split(',').map((x) => x.trim()).filter(Boolean))}
            />
          </div>
        </Card>
      ))}

      <SaveBar onSave={save} saved={saved} embedded={props.embedded} />
    </>
  )
}
