import React from 'react'
import Profile from './tabs/Profile'
import Target from './tabs/Target'
import Behavior from './tabs/Behavior'
import Schedule from './tabs/Schedule'
import { Icon } from './icons'

const SECTIONS: { id: string; label: string; icon: () => JSX.Element }[] = [
  { id: 'profile', label: 'Your data', icon: Icon.user },
  { id: 'target', label: 'Job preferences', icon: Icon.target },
  { id: 'behavior', label: 'Behavior', icon: Icon.sliders },
  { id: 'schedule', label: 'Schedule', icon: Icon.clock }
]

export default function SettingsModal(props: {
  config: any
  profile: any
  section: string
  onSection: (s: string) => void
  onSaveConfig: (c: any) => Promise<void>
  onSaveProfile: (p: any) => Promise<void>
  onClose: () => void
}): JSX.Element {
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent): void => { if (e.key === 'Escape') props.onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [props])

  const s = props.section
  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) props.onClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Settings">
        <div className="modal-head">
          <h2>Settings</h2>
          <button className="icon-btn" onClick={props.onClose} aria-label="Close"><Icon.x /></button>
        </div>
        <div className="modal-body-wrap">
          <nav className="modal-nav">
            {SECTIONS.map((sec) => (
              <div key={sec.id} className={'nav-item' + (s === sec.id ? ' active' : '')} onClick={() => props.onSection(sec.id)}>
                <sec.icon /><span>{sec.label}</span>
              </div>
            ))}
          </nav>
          <div className="modal-body">
            {s === 'profile' && <Profile profile={props.profile} onSave={props.onSaveProfile} embedded />}
            {s === 'target' && <Target config={props.config} onSave={props.onSaveConfig} embedded />}
            {s === 'behavior' && <Behavior config={props.config} onSave={props.onSaveConfig} embedded />}
            {s === 'schedule' && <Schedule config={props.config} onSave={props.onSaveConfig} embedded />}
          </div>
        </div>
      </div>
    </div>
  )
}
