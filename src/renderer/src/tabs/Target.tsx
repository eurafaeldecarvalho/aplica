import React from 'react'
import { Card, Field, TagInput, Toggle, SaveBar } from '../ui'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

export default function Target(props: { config: any; onSave: (c: any) => Promise<void>; embedded?: boolean }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const t = c.target || {}

  const setT = (k: string, v: any): void => { const n = clone(c); n.target = { ...(n.target || {}), [k]: v }; setC(n); setSaved(false) }
  const setMode = (k: string, v: boolean): void => { const n = clone(c); const base = n.target || (n.target = {}); base.work_modes = { ...(base.work_modes || {}), [k]: v }; setC(n); setSaved(false) }
  const setSource = (k: string, v: boolean): void => { const n = clone(c); n.sources = { ...(n.sources || {}), [k]: v }; setC(n); setSaved(false) }

  const save = async (): Promise<void> => { await props.onSave(c); setSaved(true) }
  const sourceLabels: Record<string, string> = { ats: 'ATS boards (Lever/Greenhouse/Ashby)', linkedin_jobs: 'LinkedIn Jobs', freehire: 'freehire aggregator', linkedin_feed: 'LinkedIn feed' }

  return (
    <>
      <div className="page-head">
        <h2>Job preferences</h2>
        <p>Define exactly the role you want. This is what the engine searches for and uses for its knockouts.</p>
      </div>

      <Card title="What to look for">
        <TagInput label="Search terms (titles)" values={t.titles_search || []} onChange={(v) => setT('titles_search', v)} placeholder="e.g. Senior Backend Engineer" />
        <Field label="Accepted-title regex (title_ok)" value={t.title_ok || ''} onChange={(v) => setT('title_ok', v)} />
        <Field label="Rejected-title regex (title_bad)" value={t.title_bad || ''} onChange={(v) => setT('title_bad', v)} />
      </Card>

      <Card title="Stack" hint="stack_target = what you want; stack_out = languages that, as the main stack, knock a job out.">
        <Field label="Target stack (regex)" value={t.stack_target || ''} onChange={(v) => setT('stack_target', v)} placeholder="e.g. node\\.?js|typescript|nestjs" />
        <KeyRegex label="Out-of-scope stacks (name → regex)" value={t.stack_out || {}} onChange={(v) => setT('stack_out', v)} />
      </Card>

      <Card title="Geography & language">
        <TagInput label="Accepted markets (geo_allow)" values={t.geo_allow || []} onChange={(v) => setT('geo_allow', v)} placeholder="e.g. remote, latam, brazil, usa" />
        <TagInput label="Blocked markets (geo_block)" values={t.geo_block || []} onChange={(v) => setT('geo_block', v)} placeholder="e.g. india, poland" />
        <TagInput label="Blocked companies / recruiters (company_block)" values={t.company_block || []} onChange={(v) => setT('company_block', v)} placeholder="e.g. Evil Staffing" />
        <TagInput label="Working languages" values={t.work_language || []} onChange={(v) => setT('work_language', v)} placeholder="e.g. english, portuguese" />
        <Field label="Required-language knockout (regex, optional)" value={t.language_required_block || ''} onChange={(v) => setT('language_required_block', v)} />
        <Field label="Your city (on-site/hybrid only accepted here)" value={t.home_city || ''} onChange={(v) => setT('home_city', v)} />
      </Card>

      <Card title="Work modes">
        <Toggle label="Remote" checked={t.work_modes?.remote} onChange={(v) => setMode('remote', v)} />
        <Toggle label="Hybrid" checked={t.work_modes?.hybrid} onChange={(v) => setMode('hybrid', v)} />
        <Toggle label="On-site" checked={t.work_modes?.onsite} onChange={(v) => setMode('onsite', v)} />
      </Card>

      <Card title="Sources" hint="Which searches the engine uses.">
        {Object.keys(c.sources || {}).map((k) => (
          <Toggle key={k} label={sourceLabels[k] || k} checked={c.sources[k]} onChange={(v) => setSource(k, v)} />
        ))}
      </Card>

      <SaveBar onSave={save} saved={saved} embedded={props.embedded} />
    </>
  )
}

function KeyRegex(props: { label: string; value: Record<string, string>; onChange: (v: any) => void }): JSX.Element {
  const entries = Object.entries(props.value || {})
  const add = (): void => { const k = prompt('stack name (e.g. java)'); if (!k) return; props.onChange({ ...props.value, [k]: '' }) }
  return (
    <div className="field">
      <label>{props.label}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span className="tag" style={{ minWidth: 90, justifyContent: 'space-between' }}>{k}<button onClick={() => { const n = { ...props.value }; delete n[k]; props.onChange(n) }}>×</button></span>
          <input style={{ flex: 1 }} value={v} placeholder="regex" onChange={(e) => props.onChange({ ...props.value, [k]: e.target.value })} />
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Add stack</button>
    </div>
  )
}
