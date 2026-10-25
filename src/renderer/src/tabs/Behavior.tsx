import React from 'react'
import { Card, Field, Toggle, SaveBar } from '../ui'
import { Icon } from '../icons'

const clone = (o: any): any => JSON.parse(JSON.stringify(o))

export default function Behavior(props: { config: any; onSave: (c: any) => Promise<void>; embedded?: boolean; onDirty?: (v: boolean) => void }): JSX.Element {
  const [c, setC] = React.useState<any>(() => clone(props.config))
  const [saved, setSaved] = React.useState(false)
  const b = c.behavior || {}
  const caps = c.caps || {}
  const touch = (): void => { setSaved(false); props.onDirty?.(true) }

  const setB = (k: string, v: any): void => { const n = clone(c); n.behavior = { ...(n.behavior || {}), [k]: v }; setC(n); touch() }
  const setSocial = (k: string, v: boolean): void => { const n = clone(c); const base = n.behavior || (n.behavior = {}); base.social = { ...(base.social || {}), [k]: v }; setC(n); touch() }
  const setCap = (k: string, v: any): void => { const n = clone(c); n.caps = { ...(n.caps || {}), [k]: v }; setC(n); touch() }

  const save = async (): Promise<void> => { await props.onSave(c); setSaved(true); props.onDirty?.(false) }
  const socialOn = (b.social && (b.social.comment || b.social.connect || b.social.dm || b.social.like)) || b.feed_mode === 'full'

  return (
    <>
      <div className="page-head">
        <h2>Behavior</h2>
        <p>Choose what Aplica may do. Social actions ship off — they're the biggest risk to your account.</p>
      </div>

      {socialOn && (
        <div className="banner warn">
          <Icon.alert />
          <div><strong>Social actions on.</strong> Commenting, connecting and DMing on LinkedIn sharply raise the risk of account
          restriction. Keep the caps low and stop immediately if LinkedIn asks for verification.</div>
        </div>
      )}

      <Card title="Applying">
        <Toggle label="Sign in with Google (SSO)" desc="Try 'Continue with Google' on new sites." checked={b.sso_google} onChange={(v) => setB('sso_google', v)} />
        <Toggle label="Create new accounts" desc="On sites without SSO. Passwords are never stored in plain text." checked={b.create_account} onChange={(v) => setB('create_account', v)} />
        <Toggle label="Email résumé" desc="When a recruiter/post asks for the CV by email." checked={b.email_resume} onChange={(v) => setB('email_resume', v)} />
        <Toggle label="Email daily summary" desc="The summary routine emails the day's report to your own address." checked={b.email_summary} onChange={(v) => setB('email_summary', v)} />
        <Toggle label="'I'm interested' on company page" desc="Privately signals interest for high-fit roles on LinkedIn." checked={b.im_interested} onChange={(v) => setB('im_interested', v)} />
      </Card>

      <Card title="LinkedIn — feed & social" hint="feed_mode: off = don't enter the feed; apply_only = apply via links only; full = full social within caps.">
        <div className="field">
          <label>Feed mode</label>
          <select value={b.feed_mode || 'off'} onChange={(e) => setB('feed_mode', e.target.value)}>
            <option value="off">off (recommended)</option>
            <option value="apply_only">apply_only</option>
            <option value="full">full</option>
          </select>
        </div>
        <Toggle label="Like" checked={b.social?.like} onChange={(v) => setSocial('like', v)} />
        <Toggle label="Comment" checked={b.social?.comment} onChange={(v) => setSocial('comment', v)} />
        <Toggle label="Connect" checked={b.social?.connect} onChange={(v) => setSocial('connect', v)} />
        <Toggle label="DM" checked={b.social?.dm} onChange={(v) => setSocial('dm', v)} />
      </Card>

      <Card title="Caps & cadence" hint="Anti-detection guards enforced by script. Lower = safer.">
        <div className="grid">
          <Field label="Applications per day" type="number" value={caps.applications_per_day ?? 15} onChange={(v) => setCap('applications_per_day', Number(v) || 0)} />
          <Field label="Max batches per run" type="number" value={caps.max_batches ?? 10} onChange={(v) => setCap('max_batches', Number(v) || 1)} />
          <Field label="Batch size" type="number" value={caps.batch_size ?? 5} onChange={(v) => setCap('batch_size', Number(v) || 1)} />
          <Field label="Social actions per day" type="number" value={caps.social_per_day ?? 0} onChange={(v) => setCap('social_per_day', Number(v) || 0)} />
          <Field label="'I'm interested' per day" type="number" value={caps.interest_per_day ?? 0} onChange={(v) => setCap('interest_per_day', Number(v) || 0)} />
        </div>
        <div className="grid">
          <Field label="Cadence min (s)" type="number" value={(caps.cadence_seconds || [45, 240])[0]} onChange={(v) => setCap('cadence_seconds', [Number(v) || 0, (caps.cadence_seconds || [45, 240])[1]])} />
          <Field label="Cadence max (s)" type="number" value={(caps.cadence_seconds || [45, 240])[1]} onChange={(v) => setCap('cadence_seconds', [(caps.cadence_seconds || [45, 240])[0], Number(v) || 0])} />
          <Field label="Active hours — start (HH:MM, optional)" value={caps.active_hours?.start || ''} onChange={(v) => setCap('active_hours', { ...(caps.active_hours || {}), start: v })} />
          <Field label="Active hours — end (HH:MM, optional)" value={caps.active_hours?.end || ''} onChange={(v) => setCap('active_hours', { ...(caps.active_hours || {}), end: v })} />
        </div>
        <p className="hint" style={{ marginTop: 10, marginBottom: 0 }}>Empty active hours = no restriction. When set, the agent avoids acting outside that window (more human).</p>
      </Card>

      <SaveBar onSave={save} saved={saved} embedded={props.embedded} />
    </>
  )
}
