import React from 'react'
import { Card, Field, TextArea, TagInput, SaveBar } from '../ui'

// clone simples para edição imutável
const clone = (o: any): any => JSON.parse(JSON.stringify(o))

export default function Profile(props: { profile: any; onSave: (p: any) => Promise<void> }): JSX.Element {
  const [p, setP] = React.useState<any>(() => clone(props.profile))
  const [saved, setSaved] = React.useState(false)

  const set = (path: string[], value: any): void => {
    const next = clone(p)
    let cur = next
    for (let i = 0; i < path.length - 1; i++) {
      cur[path[i]] = cur[path[i]] ?? {}
      cur = cur[path[i]]
    }
    cur[path[path.length - 1]] = value
    setP(next)
    setSaved(false)
  }
  const g = (path: string[], fallback: any = ''): any => {
    let cur = p
    for (const k of path) { cur = cur?.[k]; if (cur === undefined) return fallback }
    return cur ?? fallback
  }

  const save = async (): Promise<void> => {
    await props.onSave(p)
    setSaved(true)
  }

  return (
    <>
      <div className="page-head">
        <h2>Meus dados</h2>
        <p>Tudo aqui é seu e fica só no seu computador. Use dados reais e verdadeiros — o motor nunca inventa nem infla.</p>
      </div>

      <Card title="Identidade">
        <div className="grid">
          <Field label="Nome completo" value={g(['identity', 'full_name'])} onChange={(v) => set(['identity', 'full_name'], v)} />
          <Field label="E-mail" type="email" value={g(['identity', 'email'])} onChange={(v) => set(['identity', 'email'], v)} />
          <Field label="Telefone (E.164, ex. +5541999999999)" value={g(['identity', 'phone_e164'])} onChange={(v) => set(['identity', 'phone_e164'], v)} />
          <Field label="Nascimento" value={g(['identity', 'birth_date'])} onChange={(v) => set(['identity', 'birth_date'], v)} placeholder="AAAA-MM-DD" />
          <Field label="Nacionalidade" value={g(['identity', 'nationality'])} onChange={(v) => set(['identity', 'nationality'], v)} />
        </div>
      </Card>

      <Card title="Endereço">
        <div className="grid">
          <Field label="Logradouro" value={g(['address', 'line1'])} onChange={(v) => set(['address', 'line1'], v)} />
          <Field label="Cidade" value={g(['address', 'city'])} onChange={(v) => set(['address', 'city'], v)} />
          <Field label="Estado" value={g(['address', 'state'])} onChange={(v) => set(['address', 'state'], v)} />
          <Field label="País" value={g(['address', 'country'])} onChange={(v) => set(['address', 'country'], v)} />
          <Field label="CEP / postal" value={g(['address', 'postal_code'])} onChange={(v) => set(['address', 'postal_code'], v)} />
        </div>
      </Card>

      <Card title="Links">
        <div className="grid">
          <Field label="LinkedIn" value={g(['links', 'linkedin'])} onChange={(v) => set(['links', 'linkedin'], v)} />
          <Field label="GitHub" value={g(['links', 'github'])} onChange={(v) => set(['links', 'github'], v)} />
          <Field label="Portfólio" value={g(['links', 'portfolio'])} onChange={(v) => set(['links', 'portfolio'], v)} />
        </div>
      </Card>

      <Card title="Autorização de trabalho">
        <TagInput label="Países autorizados" values={g(['work_authorization', 'authorized_countries'], [])} onChange={(v) => set(['work_authorization', 'authorized_countries'], v)} placeholder="ex. Brazil" />
        <div className="grid">
          <Field label="Precisa de patrocínio de visto? (sim/não)" value={g(['work_authorization', 'needs_sponsorship']) ? 'sim' : 'não'} onChange={(v) => set(['work_authorization', 'needs_sponsorship'], v.toLowerCase().startsWith('s'))} />
          <Field label="PCD (opcional)" value={g(['work_authorization', 'disability'])} onChange={(v) => set(['work_authorization', 'disability'], v)} />
          <Field label="Veterano (opcional)" value={g(['work_authorization', 'veteran'])} onChange={(v) => set(['work_authorization', 'veteran'], v)} />
        </div>
      </Card>

      <Card title="Autodeclaração (EEO, opcional)" hint="Nunca é obrigatório e nunca é inventado.">
        <div className="grid">
          <Field label="Gênero" value={g(['eeo', 'gender'])} onChange={(v) => set(['eeo', 'gender'], v)} />
          <Field label="Pronomes" value={g(['eeo', 'pronouns'])} onChange={(v) => set(['eeo', 'pronouns'], v)} />
          <Field label="Raça/cor" value={g(['eeo', 'race'])} onChange={(v) => set(['eeo', 'race'], v)} />
        </div>
      </Card>

      <Card title="Preferências e salário">
        <div className="grid">
          <Field label="Headline" value={g(['preferences', 'headline'])} onChange={(v) => set(['preferences', 'headline'], v)} placeholder="ex. Senior Backend Engineer — Node.js" />
          <Field label="Senioridade" value={g(['preferences', 'seniority'])} onChange={(v) => set(['preferences', 'seniority'], v)} />
          <Field label="Modelo de trabalho" value={g(['preferences', 'work_model'])} onChange={(v) => set(['preferences', 'work_model'], v)} />
          <Field label="Início disponível" value={g(['preferences', 'start_availability'])} onChange={(v) => set(['preferences', 'start_availability'], v)} />
          <Field label="Aviso prévio" value={g(['preferences', 'notice_period'])} onChange={(v) => set(['preferences', 'notice_period'], v)} />
        </div>
        <TagInput label="Tipos de contrato" values={g(['preferences', 'contract_types'], [])} onChange={(v) => set(['preferences', 'contract_types'], v)} placeholder="ex. Contractor, CLT, PJ" />
        <SalaryEditor value={g(['preferences', 'salary'], {})} onChange={(v) => set(['preferences', 'salary'], v)} />
      </Card>

      <Card title="Experiência">
        <div className="grid">
          <Field label="Anos de experiência" type="number" value={g(['experience', 'total_years'], 0)} onChange={(v) => set(['experience', 'total_years'], Number(v) || 0)} />
          <Field label="Cargo atual" value={g(['experience', 'current_role'])} onChange={(v) => set(['experience', 'current_role'], v)} />
        </div>
        <TagInput label="Stacks" values={g(['experience', 'stacks'], [])} onChange={(v) => set(['experience', 'stacks'], v)} placeholder="ex. Node.js" />
        <TextArea label="Bio (EN)" value={g(['experience', 'bio', 'en'])} onChange={(v) => set(['experience', 'bio', 'en'], v)} />
        <TextArea label="Bio (PT)" value={g(['experience', 'bio', 'pt'])} onChange={(v) => set(['experience', 'bio', 'pt'], v)} />
        <KeyNumEditor label="Anos por tecnologia" value={g(['experience', 'years_by_tech'], {})} onChange={(v) => set(['experience', 'years_by_tech'], v)} keyPlaceholder="tecnologia" />
      </Card>

      <Card title="Idiomas">
        <RowsEditor
          rows={g(['languages'], [])}
          cols={[{ k: 'language', label: 'Idioma' }, { k: 'level', label: 'Nível' }]}
          onChange={(v) => set(['languages'], v)}
        />
      </Card>

      <Card title="Formação e certificações">
        <RowsEditor
          rows={g(['education'], [])}
          cols={[
            { k: 'kind', label: 'Tipo (degree/course/certification)' },
            { k: 'title', label: 'Título' },
            { k: 'institution', label: 'Instituição' },
            { k: 'year', label: 'Ano' },
            { k: 'status', label: 'Status' },
            { k: 'credential_id', label: 'Credential ID' }
          ]}
          onChange={(v) => set(['education'], v)}
        />
      </Card>

      <Card title="Respostas abertas">
        <TextArea label="Pitch" value={g(['open_answers', 'pitch'])} onChange={(v) => set(['open_answers', 'pitch'], v)} />
        <TextArea label="Estilo de escrita (idioma/voz com que o agente escreve por você)" value={g(['open_answers', 'writing_style'])} onChange={(v) => set(['open_answers', 'writing_style'], v)} />
      </Card>

      <SaveBar onSave={save} saved={saved} />
    </>
  )
}

function SalaryEditor(props: { value: any; onChange: (v: any) => void }): JSX.Element {
  const mods = Object.keys(props.value || {})
  const upd = (mod: string, field: string, val: string): void => {
    const next = clone(props.value || {})
    next[mod] = next[mod] || { currency: '', period: 'month', mid: 0 }
    next[mod][field] = field === 'mid' || field === 'min' || field === 'max' ? Number(val) || 0 : val
    props.onChange(next)
  }
  const addMod = (): void => {
    const name = prompt('Nome da modalidade (ex. international, clt_br, pj_br):')
    if (!name) return
    const next = clone(props.value || {})
    next[name] = { currency: 'USD', period: 'month', min: 0, mid: 0, max: 0 }
    props.onChange(next)
  }
  return (
    <div className="field">
      <label>Pretensão por modalidade</label>
      {mods.map((m) => (
        <div key={m} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6, flexWrap: 'wrap' }}>
          <span className="tag" style={{ minWidth: 110, justifyContent: 'space-between' }}>
            {m}<button onClick={() => { const n = clone(props.value); delete n[m]; props.onChange(n) }}>×</button>
          </span>
          <input style={{ width: 80 }} placeholder="moeda" value={props.value[m]?.currency || ''} onChange={(e) => upd(m, 'currency', e.target.value)} />
          <select style={{ width: 110 }} value={props.value[m]?.period || 'month'} onChange={(e) => upd(m, 'period', e.target.value)}>
            <option value="month">mês</option><option value="year">ano</option><option value="hour">hora</option>
          </select>
          <input style={{ width: 100 }} type="number" placeholder="mínimo" value={props.value[m]?.min ?? ''} onChange={(e) => upd(m, 'min', e.target.value)} />
          <input style={{ width: 100 }} type="number" placeholder="médio" value={props.value[m]?.mid ?? ''} onChange={(e) => upd(m, 'mid', e.target.value)} />
          <input style={{ width: 100 }} type="number" placeholder="máximo" value={props.value[m]?.max ?? ''} onChange={(e) => upd(m, 'max', e.target.value)} />
        </div>
      ))}
      <button className="btn secondary" onClick={addMod}>Adicionar modalidade</button>
    </div>
  )
}

function KeyNumEditor(props: { label: string; value: Record<string, number>; onChange: (v: any) => void; keyPlaceholder?: string }): JSX.Element {
  const entries = Object.entries(props.value || {})
  const add = (): void => {
    const k = prompt(props.keyPlaceholder || 'chave')
    if (!k) return
    props.onChange({ ...props.value, [k]: 0 })
  }
  return (
    <div className="field">
      <label>{props.label}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span className="tag" style={{ minWidth: 140, justifyContent: 'space-between' }}>
            {k}<button onClick={() => { const n = { ...props.value }; delete n[k]; props.onChange(n) }}>×</button>
          </span>
          <input style={{ width: 100 }} type="number" value={v} onChange={(e) => props.onChange({ ...props.value, [k]: Number(e.target.value) || 0 })} />
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Adicionar</button>
    </div>
  )
}

function RowsEditor(props: { rows: any[]; cols: { k: string; label: string }[]; onChange: (v: any[]) => void }): JSX.Element {
  const rows = props.rows || []
  const upd = (i: number, k: string, val: string): void => {
    const next = clone(rows); next[i] = { ...next[i], [k]: val }; props.onChange(next)
  }
  const add = (): void => props.onChange([...rows, Object.fromEntries(props.cols.map((c) => [c.k, '']))])
  return (
    <div className="field">
      {rows.map((row, i) => (
        <div key={i} style={{ display: 'flex', gap: 8, marginBottom: 6, flexWrap: 'wrap', alignItems: 'center' }}>
          {props.cols.map((c) => (
            <input key={c.k} style={{ flex: 1, minWidth: 120 }} placeholder={c.label} value={row[c.k] || ''} onChange={(e) => upd(i, c.k, e.target.value)} />
          ))}
          <button className="btn secondary" onClick={() => props.onChange(rows.filter((_, j) => j !== i))}>remover</button>
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Adicionar linha</button>
    </div>
  )
}
