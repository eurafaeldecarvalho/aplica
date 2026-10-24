import React from 'react'
import { Card, Field, TagInput, Toggle, SaveBar } from '../ui'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

export default function Target(props: { config: any; onSave: (c: any) => Promise<void> }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const t = c.target || {}

  const setT = (k: string, v: any): void => { const n = clone(c); n.target = { ...n.target, [k]: v }; setC(n); setSaved(false) }
  const setMode = (k: string, v: boolean): void => { const n = clone(c); n.target.work_modes = { ...n.target.work_modes, [k]: v }; setC(n); setSaved(false) }
  const setSource = (k: string, v: boolean): void => { const n = clone(c); n.sources = { ...n.sources, [k]: v }; setC(n); setSaved(false) }

  const save = async (): Promise<void> => { await props.onSave(c); setSaved(true) }

  return (
    <>
      <div className="page-head">
        <h2>Preferências de vaga</h2>
        <p>Defina exatamente que vaga você procura. É isto que o motor usa para buscar e para os knockouts.</p>
      </div>

      <Card title="O que procurar">
        <TagInput label="Termos de busca (cargos)" values={t.titles_search || []} onChange={(v) => setT('titles_search', v)} placeholder="ex. Senior Backend Engineer" />
        <Field label="Regex de título aceito (title_ok)" value={t.title_ok || ''} onChange={(v) => setT('title_ok', v)} />
        <Field label="Regex de título barrado (title_bad)" value={t.title_bad || ''} onChange={(v) => setT('title_bad', v)} />
      </Card>

      <Card title="Stack" hint="stack_target = o que você quer; stack_out = linguagens que, como principais, eliminam a vaga.">
        <Field label="Stack-alvo (regex)" value={t.stack_target || ''} onChange={(v) => setT('stack_target', v)} placeholder="ex. node\\.?js|typescript|nestjs" />
        <KeyRegex label="Stacks fora (nome → regex)" value={t.stack_out || {}} onChange={(v) => setT('stack_out', v)} />
      </Card>

      <Card title="Geografia e idioma">
        <TagInput label="Mercados aceitos (geo_allow)" values={t.geo_allow || []} onChange={(v) => setT('geo_allow', v)} placeholder="ex. remote, latam, brazil, usa" />
        <TagInput label="Mercados barrados (geo_block)" values={t.geo_block || []} onChange={(v) => setT('geo_block', v)} placeholder="ex. india, poland" />
        <TagInput label="Empresas/recrutadores barrados (company_block)" values={t.company_block || []} onChange={(v) => setT('company_block', v)} placeholder="ex. Evil Staffing" />
        <TagInput label="Idiomas de trabalho" values={t.work_language || []} onChange={(v) => setT('work_language', v)} placeholder="ex. english, portuguese" />
        <Field label="Idioma obrigatório que elimina (regex, opcional)" value={t.language_required_block || ''} onChange={(v) => setT('language_required_block', v)} />
        <Field label="Sua cidade (presencial/híbrido só vale aqui)" value={t.home_city || ''} onChange={(v) => setT('home_city', v)} />
      </Card>

      <Card title="Modalidades">
        <Toggle label="Remoto" checked={t.work_modes?.remote} onChange={(v) => setMode('remote', v)} />
        <Toggle label="Híbrido" checked={t.work_modes?.hybrid} onChange={(v) => setMode('hybrid', v)} />
        <Toggle label="Presencial" checked={t.work_modes?.onsite} onChange={(v) => setMode('onsite', v)} />
      </Card>

      <Card title="Fontes" hint="Quais buscas o motor usa.">
        {Object.keys(c.sources || {}).map((k) => (
          <Toggle key={k} label={k} checked={c.sources[k]} onChange={(v) => setSource(k, v)} />
        ))}
      </Card>

      <SaveBar onSave={save} saved={saved} />
    </>
  )
}

function KeyRegex(props: { label: string; value: Record<string, string>; onChange: (v: any) => void }): JSX.Element {
  const entries = Object.entries(props.value || {})
  const add = (): void => { const k = prompt('nome da stack (ex. java)'); if (!k) return; props.onChange({ ...props.value, [k]: '' }) }
  return (
    <div className="field">
      <label>{props.label}</label>
      {entries.map(([k, v]) => (
        <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
          <span className="tag" style={{ minWidth: 90, justifyContent: 'space-between' }}>{k}<button onClick={() => { const n = { ...props.value }; delete n[k]; props.onChange(n) }}>×</button></span>
          <input style={{ flex: 1 }} value={v} placeholder="regex" onChange={(e) => props.onChange({ ...props.value, [k]: e.target.value })} />
        </div>
      ))}
      <button className="btn secondary" onClick={add}>Adicionar stack fora</button>
    </div>
  )
}
