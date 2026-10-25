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
  // dirty por seção — as seções ficam montadas (não perdem edição ao trocar);
  // avisa antes de fechar se houver mudança não salva.
  const [dirty, setDirty] = React.useState<Record<string, boolean>>({})
  const setSectionDirty = React.useCallback((id: string, v: boolean) => {
    setDirty((d) => (d[id] === v ? d : { ...d, [id]: v }))
  }, [])
  const anyDirty = Object.values(dirty).some(Boolean)

  const tryClose = React.useCallback(() => {
    if (anyDirty && !window.confirm('You have unsaved changes. Close without saving?')) return
    props.onClose()
  }, [anyDirty, props])

  const closeRef = React.useRef(tryClose)
  closeRef.current = tryClose
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent): void => { if (e.key === 'Escape') closeRef.current() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const s = props.section
  return (
    <div className="overlay" onMouseDown={(e) => { if (e.target === e.currentTarget) tryClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-label="Settings">
        <div className="modal-head">
          <h2>Settings</h2>
          <button className="icon-btn" onClick={tryClose} aria-label="Close"><Icon.x /></button>
        </div>
        <div className="modal-body-wrap">
          <nav className="modal-nav">
            {SECTIONS.map((sec) => (
              <div key={sec.id} className={'nav-item' + (s === sec.id ? ' active' : '')} onClick={() => props.onSection(sec.id)}>
                <sec.icon /><span>{sec.label}</span>
                {dirty[sec.id] && <span className="nav-count" style={{ background: 'var(--warn)', color: '#151515', minWidth: 8, width: 8, height: 8, padding: 0 }} aria-label="unsaved" />}
              </div>
            ))}
          </nav>
          <div className="modal-body">
            <div hidden={s !== 'profile'}><Profile profile={props.profile} onSave={props.onSaveProfile} embedded onDirty={(v) => setSectionDirty('profile', v)} /></div>
            <div hidden={s !== 'target'}><Target config={props.config} onSave={props.onSaveConfig} embedded onDirty={(v) => setSectionDirty('target', v)} /></div>
            <div hidden={s !== 'behavior'}><Behavior config={props.config} onSave={props.onSaveConfig} embedded onDirty={(v) => setSectionDirty('behavior', v)} /></div>
            <div hidden={s !== 'schedule'}><Schedule config={props.config} onSave={props.onSaveConfig} embedded onDirty={(v) => setSectionDirty('schedule', v)} /></div>
          </div>
        </div>
      </div>
    </div>
  )
}
