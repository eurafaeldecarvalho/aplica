import React from 'react'
import { Card, Toggle, SaveBar } from '../ui'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

const LABELS: Record<string, string> = {
  ats: 'ATS / boards',
  linkedin_jobs: 'LinkedIn Jobs',
  recruiters: 'Recrutadores (inbox + Gmail)',
  feed: 'Feed do LinkedIn',
  summary: 'Resumo diário'
}

export default function Schedule(props: { config: any; onSave: (c: any) => Promise<void> }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const sch = c.schedule || {}

  const setEnabled = (k: string, v: boolean): void => { const n = clone(c); n.schedule = { ...n.schedule, [k]: { ...n.schedule[k], enabled: v } }; setC(n); setSaved(false) }
  const setTimes = (k: string, times: string[]): void => { const n = clone(c); n.schedule = { ...n.schedule, [k]: { ...n.schedule[k], times } }; setC(n); setSaved(false) }

  const save = async (): Promise<void> => { await props.onSave(c); setSaved(true) }

  return (
    <>
      <div className="page-head">
        <h2>Agenda</h2>
        <p>Horários de cada rotina. A criação das tarefas agendadas é feita pelo Claude Code; aqui você define quando e o quê.</p>
      </div>

      <div className="banner info">
        A agenda é salva no seu config. Para efetivar as tarefas agendadas, rode o assistente no Claude Code (o app passará estes horários ao plugin).
      </div>

      {Object.keys(LABELS).map((k) => (
        <Card key={k} title={LABELS[k]}>
          <Toggle label="Ligada" checked={sch[k]?.enabled} onChange={(v) => setEnabled(k, v)} />
          <div className="field" style={{ marginTop: 8 }}>
            <label>Horários (HH:MM, separados por vírgula)</label>
            <input
              type="text"
              value={(sch[k]?.times || []).join(', ')}
              placeholder="ex. 09:00, 15:00"
              onChange={(e) => setTimes(k, e.target.value.split(',').map((s) => s.trim()).filter(Boolean))}
            />
          </div>
        </Card>
      ))}

      <SaveBar onSave={save} saved={saved} />
    </>
  )
}
