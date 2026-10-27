import React from 'react'
import { Icon } from '../icons'

export type Notif = { level: string; title: string; detail: string; action?: string }

export default function Notifications(props: { items: Notif[]; loading: boolean; onRefresh: () => void; onGo: (tab: string) => void }): JSX.Element {
  const iconFor = (lvl: string): JSX.Element => (lvl === 'error' ? <Icon.alert /> : lvl === 'warn' ? <Icon.alert /> : <Icon.info />)
  return (
    <>
      <div className="page-head">
        <h2>Notifications</h2>
        <p>Sign-in issues (LinkedIn, Gmail), blocked sites, things that need you, and recent routine runs.</p>
      </div>

      <div className="btn-row" style={{ marginBottom: 18 }}>
        <button className="btn secondary" onClick={props.onRefresh} disabled={props.loading}>
          <Icon.refresh size={14} />{props.loading ? 'Loading…' : 'Refresh'}
        </button>
      </div>

      {props.items.length === 0 ? (
        <div className="empty-state">
          <div className="e-ico"><Icon.check /></div>
          <strong>All clear</strong>
          <p className="muted" style={{ marginTop: 4 }}>No sign-in issues or pending items right now.</p>
        </div>
      ) : (
        props.items.map((n, i) => (
          <div key={i} className={'notif ' + n.level}>
            <span className="n-ico">{iconFor(n.level)}</span>
            <div className="n-body">
              <strong>{n.title}</strong>
              <p>{n.detail}</p>
              {n.action && (
                <button className="btn secondary n-act" onClick={() => props.onGo(n.action!)}>
                  {n.action === 'dashboard' ? 'Open dashboard' : 'Open home'}
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </>
  )
}
