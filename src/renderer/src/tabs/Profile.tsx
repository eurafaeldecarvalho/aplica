import React from 'react'
import { Card, Field, TextArea, TagInput, SaveBar } from '../ui'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

// As perguntas abertas recorrentes em formulários de vaga (mapeadas no apply-engine).
// Viram o banco de respostas reutilizáveis (open_answers.qa), consultado pelo agente.
const COMMON_QUESTIONS = [
  'Tell us about yourself',
  'Why do you want to work at this company?',
  'Why are you a good fit for this role?',
  'What are you looking for in your next role?',
  'Describe a project you are proud of',
  'What is your greatest strength?',
  'Are you willing to relocate?',
  'When can you start? / notice period',
  'Anything else you would like us to know?'
]
const isCommon = (k: string): boolean => COMMON_QUESTIONS.includes(k)
const omitCommon = (qa: Record<string, string>): Record<string, string> =>
  Object.fromEntries(Object.entries(qa || {}).filter(([k]) => !isCommon(k)))
const pickCommon = (qa: Record<string, string>): Record<string, string> =>
  Object.fromEntries(Object.entries(qa || {}).filter(([k]) => isCommon(k)))

export default function Profile(props: { profile: any; onSave: (p: any) => Promise<void>; embedded?: boolean }): JSX.Element {
  const [p, setP] = React.useState<any>(() => clone(props.profile))
  const [answers, setAnswers] = React.useState('')
  const [saved, setSaved] = React.useState(false)

  React.useEffect(() => { window.aplica.readAnswers().then((r: any) => setAnswers(r?.text || '')) }, [])

  const set = (path: string[], value: any): void => {
    const next = clone(p)
    let cur = next
    for (let i = 0; i < path.length - 1; i++) { cur[path[i]] = cur[path[i]] ?? {}; cur = cur[path[i]] }
    cur[path[path.length - 1]] = value
    setP(next); setSaved(false)
  }
  const g = (path: string[], fallback: any = ''): any => {
    let cur = p
    for (const k of path) { cur = cur?.[k]; if (cur === undefined) return fallback }
    return cur ?? fallback
  }
  const save = async (): Promise<void> => { await props.onSave(p); await window.aplica.writeAnswers(answers); setSaved(true) }

  return (
    <>
      <div className="page-head">
        <h2>Your data</h2>
        <p>Everything here is yours and stays on your computer. Use real, truthful data — the engine never invents or inflates.</p>
      </div>

      <Card title="Identity">
        <div className="grid">
          <Field label="Full name" value={g(['identity', 'full_name'])} onChange={(v) => set(['identity', 'full_name'], v)} />
          <Field label="Email" type="email" value={g(['identity', 'email'])} onChange={(v) => set(['identity', 'email'], v)} />
          <Field label="Phone (E.164, e.g. +15550001234)" value={g(['identity', 'phone_e164'])} onChange={(v) => set(['identity', 'phone_e164'], v)} />
          <Field label="Birth date" value={g(['identity', 'birth_date'])} onChange={(v) => set(['identity', 'birth_date'], v)} placeholder="YYYY-MM-DD" />
          <Field label="Nationality" value={g(['identity', 'nationality'])} onChange={(v) => set(['identity', 'nationality'], v)} />
        </div>
      </Card>

      <Card title="Address">
        <div className="grid">
          <Field label="Street" value={g(['address', 'line1'])} onChange={(v) => set(['address', 'line1'], v)} />
          <Field label="City" value={g(['address', 'city'])} onChange={(v) => set(['address', 'city'], v)} />
          <Field label="State/region" value={g(['address', 'state'])} onChange={(v) => set(['address', 'state'], v)} />
          <Field label="Country" value={g(['address', 'country'])} onChange={(v) => set(['address', 'country'], v)} />
          <Field label="Postal code" value={g(['address', 'postal_code'])} onChange={(v) => set(['address', 'postal_code'], v)} />
        </div>
      </Card>

      <Card title="Links">
        <div className="grid">
          <Field label="LinkedIn" value={g(['links', 'linkedin'])} onChange={(v) => set(['links', 'linkedin'], v)} />
          <Field label="GitHub" value={g(['links', 'github'])} onChange={(v) => set(['links', 'github'], v)} />
          <Field label="Portfolio" value={g(['links', 'portfolio'])} onChange={(v) => set(['links', 'portfolio'], v)} />
        </div>
      </Card>

      <Card title="Work authorization">
        <TagInput label="Authorized countries" values={g(['work_authorization', 'authorized_countries'], [])} onChange={(v) => set(['work_authorization', 'authorized_countries'], v)} placeholder="e.g. Brazil" />
        <div className="grid">
          <Field label="Needs visa sponsorship? (yes/no)" value={g(['work_authorization', 'needs_sponsorship']) ? 'yes' : 'no'} onChange={(v) => set(['work_authorization', 'needs_sponsorship'], v.toLowerCase().startsWith('y'))} />
          <Field label="Disability (optional)" value={g(['work_authorization', 'disability'])} onChange={(v) => set(['work_authorization', 'disability'], v)} />
          <Field label="Veteran (optional)" value={g(['work_authorization', 'veteran'])} onChange={(v) => set(['work_authorization', 'veteran'], v)} />
        </div>
      </Card>

      <Card title="Self-identification (EEO, optional)" hint="Never required and never invented.">
        <div className="grid">
          <Field label="Gender" value={g(['eeo', 'gender'])} onChange={(v) => set(['eeo', 'gender'], v)} />
          <Field label="Pronouns" value={g(['eeo', 'pronouns'])} onChange={(v) => set(['eeo', 'pronouns'], v)} />
          <Field label="Race/ethnicity" value={g(['eeo', 'race'])} onChange={(v) => set(['eeo', 'race'], v)} />
        </div>
      </Card>

      <Card title="Preferences & salary">
        <div className="grid">
          <Field label="Headline" value={g(['preferences', 'headline'])} onChange={(v) => set(['preferences', 'headline'], v)} placeholder="e.g. Senior Backend Engineer — Node.js" />
          <Field label="Seniority" value={g(['preferences', 'seniority'])} onChange={(v) => set(['preferences', 'seniority'], v)} />
          <Field label="Work model" value={g(['preferences', 'work_model'])} onChange={(v) => set(['preferences', 'work_model'], v)} />
          <Field label="Start availability" value={g(['preferences', 'start_availability'])} onChange={(v) => set(['preferences', 'start_availability'], v)} />
          <Field label="Notice period" value={g(['preferences', 'notice_period'])} onChange={(v) => set(['preferences', 'notice_period'], v)} />
        </div>
        <TagInput label="Contract types" values={g(['preferences', 'contract_types'], [])} onChange={(v) => set(['preferences', 'contract_types'], v)} placeholder="e.g. Contractor, CLT, PJ" />
        <SalaryEditor value={g(['preferences', 'salary'], {})} onChange={(v) => set(['preferences', 'salary'], v)} />
      </Card>

      <Card title="Experience">
        <div className="grid">
          <Field label="Total years" type="number" value={g(['experience', 'total_years'], 0)} onChange={(v) => set(['experience', 'total_years'], Number(v) || 0)} />
          <Field label="Current role" value={g(['experience', 'current_role'])} onChange={(v) => set(['experience', 'current_role'], v)} />
        </div>
        <TagInput label="Stacks" values={g(['experience', 'stacks'], [])} onChange={(v) => set(['experience', 'stacks'], v)} placeholder="e.g. Node.js" />
        <TextArea label="Bio (EN)" value={g(['experience', 'bio', 'en'])} onChange={(v) => set(['experience', 'bio', 'en'], v)} />
        <TextArea label="Bio (PT)" value={g(['experience', 'bio', 'pt'])} onChange={(v) => set(['experience', 'bio', 'pt'], v)} />
        <KeyNumEditor label="Years per technology" value={g(['experience', 'years_by_tech'], {})} onChange={(v) => set(['experience', 'years_by_tech'], v)} keyPlaceholder="technology" />
      </Card>

      <Card title="Languages">
        <RowsEditor rows={g(['languages'], [])} cols={[{ k: 'language', label: 'Language' }, { k: 'level', label: 'Level' }]} onChange={(v) => set(['languages'], v)} />
      </Card>

      <Card title="Education & certifications">
        <RowsEditor
          rows={g(['education'], [])}
          cols={[
            { k: 'kind', label: 'Type (degree/course/certification)' }, { k: 'title', label: 'Title' },
            { k: 'institution', label: 'Institution' }, { k: 'year', label: 'Year' },
            { k: 'status', label: 'Status' }, { k: 'credential_id', label: 'Credential ID' }
          ]}
          onChange={(v) => set(['education'], v)}
        />
      </Card>

      <Card title="Open answers" hint="Pitch and the voice the agent writes in on your behalf.">
        <TextArea label="Pitch (one or two sentences about you)" value={g(['open_answers', 'pitch'])} onChange={(v) => set(['open_answers', 'pitch'], v)} />
        <TextArea label="Writing style (the voice/level the agent writes in for you)" value={g(['open_answers', 'writing_style'])} onChange={(v) => set(['open_answers', 'writing_style'], v)} placeholder="e.g. First person, simple words, short sentences, around B2 English. No corporate polish." />
      </Card>

      <Card title="Common application questions" hint="The recurring open questions on job forms. Answer in your own voice — the agent reuses these verbatim.">
        {COMMON_QUESTIONS.map((q) => (
          <TextArea key={q} label={q} value={g(['open_answers', 'qa', q])} onChange={(v) => set(['open_answers', 'qa', q], v)} rows={3} />
        ))}
      </Card>

      <Card title="Other questions" hint="Add any extra question/answer the common list doesn't cover.">
        <KeyTextEditor label="Custom question → answer" value={omitCommon(g(['open_answers', 'qa'], {}))} onChange={(v) => set(['open_answers', 'qa'], { ...pickCommon(g(['open_answers', 'qa'], {})), ...v })} />
        <TextArea label="Free notes (answers.md) — long-form context the agent can draw from" value={answers} onChange={(v) => { setAnswers(v); setSaved(false) }} rows={8} />
      </Card>

      <SaveBar onSave={save} saved={saved} embedded={props.embedded} />
    </>
  )
}

function SalaryEditor(props: { value: any; onChange: (v: any) => void }): JSX.Element {
  const mods = Object.keys(props.value || {})
  const upd = (mod: string, field: string, val: string): void => {
    const next = clone(props.value || {})
    next[mod] = next[mod] || { currency: '', period: 'month', mid: 0 }
    next[mod][field] = (field === 'mid' || field === 'min' || field === 'max') ? Number(val) || 0 : val
    props.onChange(next)
  }
  const addMod = (): void => {
    const name = prompt('Modality name (e.g. international, clt_br, pj_br):')
    if (!name) return
    props.onChange({ ...clone(props.value || {}), [name]: { currency: 'USD', period: 'month', min: 0, mid: 0, max: 0 } })
  }
  return (
    <div className="field">
      <label>Salary expectation by modality</label>
      {mods.map((m) => (
        <div key={m} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
          <span className="tag" style={{ minWidth: 110, justifyContent: 'space-between' }}>{m}<button onClick={() => { const n = clone(props.value); delete n[m]; props.onChange(n) }}>×</button></span>
          <input style={{ width: 80 }} placeholder="currency" value={props.value[m]?.currency || ''} onChange={(e) => upd(m, 'currency', e.target.value)} />
          <select style={{ width: 100 }} value={props.value[m]?.period || 'month'} onChange={(e) => upd(m, 'period', e.target.value)}>
            <option value="month">month</option><option value="year">year</option><option value="hour">hour</option>
          </select>
          <input style={{ width: 95 }} type="number" placeholder="min" value={props.value[m]?.min ?? ''} onChange={(e) => upd(m, 'min', e.target.value)} />
          <input style={{ width: 95 }} type="number" placeholder="mid" value={props.value[m]?.mid ?? ''} onChange={(e) => upd(m, 'mid', e.target.value)} />
          <input style={{ width: 95 }} type="number" placeholder="max" value={props.value[m]?.max ?? ''} onChange={(e) => upd(m, 'max', e.target.value)} />
        </div>
      ))}
      <button className="btn secondary" onClick={addMod}>Add modality</button>
    </div>
  )
}

function KeyNumEditor(props: { label: string; value: Record<string, number>; onChange: (v: any) => void; keyPlaceholder?: string }): JSX.Element {
  const entries = Object.entries(props.value || {})
  const add = (): void => { const k = prompt(props.keyPlaceholder || 'key'); if (!k) return; props.onChange({ ...props.value, [k]: 0 }) }
  return (
    <div className="field">
      <label>{props.label}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span className="tag" style={{ minWidth: 140, justifyContent: 'space-between' }}>{k}<button onClick={() => { const n = { ...props.value }; delete n[k]; props.onChange(n) }}>×</button></span>
          <input style={{ width: 95 }} type="number" value={v} onChange={(e) => props.onChange({ ...props.value, [k]: Number(e.target.value) || 0 })} />
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Add</button>
    </div>
  )
}

function KeyTextEditor(props: { label: string; value: Record<string, string>; onChange: (v: any) => void }): JSX.Element {
  const entries = Object.entries(props.value || {})
  const add = (): void => { const k = prompt('Question (exact form text):'); if (!k) return; props.onChange({ ...props.value, [k]: '' }) }
  return (
    <div className="field">
      <label>{props.label}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
          <span className="tag" style={{ minWidth: 160, justifyContent: 'space-between' }}>{k.length > 24 ? k.slice(0, 24) + '…' : k}<button onClick={() => { const n = { ...props.value }; delete n[k]; props.onChange(n) }}>×</button></span>
          <textarea style={{ flex: 1, minHeight: 48 }} value={v} placeholder="answer" onChange={(e) => props.onChange({ ...props.value, [k]: e.target.value })} />
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Add question/answer</button>
    </div>
  )
}

function RowsEditor(props: { rows: any[]; cols: { k: string; label: string }[]; onChange: (v: any[]) => void }): JSX.Element {
  const rows = props.rows || []
  const upd = (i: number, k: string, val: string): void => { const next = clone(rows); next[i] = { ...next[i], [k]: val }; props.onChange(next) }
  const add = (): void => props.onChange([...rows, Object.fromEntries(props.cols.map((c) => [c.k, '']))])
  return (
    <div className="field">
      {rows.map((row, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          {props.cols.map((c) => (
            <input key={c.k} style={{ flex: 1, minWidth: 120 }} placeholder={c.label} value={row[c.k] || ''} onChange={(e) => upd(i, c.k, e.target.value)} />
          ))}
          <button className="btn secondary" onClick={() => props.onChange(rows.filter((_, j) => j !== i))}>remove</button>
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Add row</button>
    </div>
  )
}
