import React from 'react'
import { Card, Field, Toggle, SaveBar } from '../ui'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

export default function Behavior(props: { config: any; onSave: (c: any) => Promise<void> }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const b = c.behavior || {}
  const caps = c.caps || {}

  const setB = (k: string, v: any): void => { const n = clone(c); n.behavior = { ...(n.behavior || {}), [k]: v }; setC(n); setSaved(false) }
  const setSocial = (k: string, v: boolean): void => { const n = clone(c); const base = n.behavior || (n.behavior = {}); base.social = { ...(base.social || {}), [k]: v }; setC(n); setSaved(false) }
  const setCap = (k: string, v: number): void => { const n = clone(c); n.caps = { ...(n.caps || {}), [k]: v }; setC(n); setSaved(false) }

  const save = async (): Promise<void> => { await props.onSave(c); setSaved(true) }

  const socialOn = b.social && (b.social.comment || b.social.connect || b.social.dm || b.social.like) || b.feed_mode === 'full'

  return (
    <>
      <div className="page-head">
        <h2>Comportamento</h2>
        <p>Escolha o que o Aplica pode fazer. Ações sociais vêm desligadas — são o maior risco para a sua conta.</p>
      </div>

      {socialOn && (
        <div className="banner warn">
          <strong>Ações sociais ligadas.</strong> Comentar, conectar e DM no LinkedIn aumentam muito o risco de restrição de conta.
          Mantenha os tetos baixos e pare na hora se o LinkedIn pedir verificação.
        </div>
      )}

      <Card title="Candidatura">
        <Toggle label="Login com Google (SSO)" desc="Tentar 'Continuar com Google' em sites novos." checked={b.sso_google} onChange={(v) => setB('sso_google', v)} />
        <Toggle label="Criar conta nova" desc="Em sites sem SSO. Senha nunca é guardada em texto plano." checked={b.create_account} onChange={(v) => setB('create_account', v)} />
        <Toggle label="Enviar currículo por e-mail" desc="Quando um recrutador/post pedir o CV por e-mail." checked={b.email_resume} onChange={(v) => setB('email_resume', v)} />
        <Toggle label="'I'm interested' na empresa" desc="Sinaliza interesse privado em vagas de fit alto no LinkedIn." checked={b.im_interested} onChange={(v) => setB('im_interested', v)} />
      </Card>

      <Card title="LinkedIn — feed e social" hint="feed_mode: off = não entra no feed; apply_only = só candidatura por link; full = social completo dentro dos tetos.">
        <div className="field">
          <label>Modo do feed</label>
          <select value={b.feed_mode || 'off'} onChange={(e) => setB('feed_mode', e.target.value)}>
            <option value="off">off (recomendado)</option>
            <option value="apply_only">apply_only</option>
            <option value="full">full</option>
          </select>
        </div>
        <Toggle label="Curtir" checked={b.social?.like} onChange={(v) => setSocial('like', v)} />
        <Toggle label="Comentar" checked={b.social?.comment} onChange={(v) => setSocial('comment', v)} />
        <Toggle label="Conectar" checked={b.social?.connect} onChange={(v) => setSocial('connect', v)} />
        <Toggle label="DM" checked={b.social?.dm} onChange={(v) => setSocial('dm', v)} />
      </Card>

      <Card title="Tetos e cadência" hint="Proteções anti-detecção aplicadas por script. Valores menores = mais seguro.">
        <div className="grid">
          <Field label="Candidaturas por dia" type="number" value={caps.applications_per_day ?? 15} onChange={(v) => setCap('applications_per_day', Number(v) || 0)} />
          <Field label="Lotes por rodada (máx)" type="number" value={caps.max_batches ?? 10} onChange={(v) => setCap('max_batches', Number(v) || 1)} />
          <Field label="Tamanho do lote" type="number" value={caps.batch_size ?? 5} onChange={(v) => setCap('batch_size', Number(v) || 1)} />
          <Field label="Ações sociais por dia" type="number" value={caps.social_per_day ?? 0} onChange={(v) => setCap('social_per_day', Number(v) || 0)} />
          <Field label="'I'm interested' por dia" type="number" value={caps.interest_per_day ?? 0} onChange={(v) => setCap('interest_per_day', Number(v) || 0)} />
        </div>
        <div className="grid">
          <Field label="Cadência mín (s)" type="number" value={(caps.cadence_seconds || [45, 240])[0]} onChange={(v) => setCap('cadence_seconds', [Number(v) || 0, (caps.cadence_seconds || [45, 240])[1]] as any)} />
          <Field label="Cadência máx (s)" type="number" value={(caps.cadence_seconds || [45, 240])[1]} onChange={(v) => setCap('cadence_seconds', [(caps.cadence_seconds || [45, 240])[0], Number(v) || 0] as any)} />
          <Field label="Horário ativo — início (HH:MM, opcional)" value={caps.active_hours?.start || ''} onChange={(v) => setCap('active_hours', { ...(caps.active_hours || {}), start: v } as any)} />
          <Field label="Horário ativo — fim (HH:MM, opcional)" value={caps.active_hours?.end || ''} onChange={(v) => setCap('active_hours', { ...(caps.active_hours || {}), end: v } as any)} />
        </div>
        <p className="hint">Horário ativo vazio = sem restrição. Preenchido, o agente evita agir fora da janela (parece mais humano).</p>
      </Card>

      <SaveBar onSave={save} saved={saved} />
    </>
  )
}
