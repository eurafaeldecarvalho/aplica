import React from 'react'
import Onboarding from './tabs/Onboarding'
import Dashboard from './tabs/Dashboard'
import Pipeline from './tabs/Pipeline'
import Contacts from './tabs/Contacts'
import Run from './tabs/Run'
import Notifications, { type Notif } from './tabs/Notifications'
import SettingsModal from './SettingsModal'
import DraftModal from './DraftModal'
import { Logo, Icon } from './icons'

type TabId = 'home' | 'dashboard' | 'pipeline' | 'contacts' | 'run' | 'notifications'

const TABS: { id: TabId; label: string; icon: () => JSX.Element }[] = [
  { id: 'home', label: 'Home', icon: Icon.home },
  { id: 'dashboard', label: 'Dashboard', icon: Icon.grid },
  { id: 'pipeline', label: 'Pipeline', icon: Icon.columns },
  { id: 'contacts', label: 'Contacts', icon: Icon.user },
  { id: 'run', label: 'Run', icon: Icon.play },
  { id: 'notifications', label: 'Notifications', icon: Icon.alert }
]

export default function App(): JSX.Element {
  const [tab, setTab] = React.useState<TabId>('home')
  const [config, setConfig] = React.useState<any | null>(null)
  const [profile, setProfile] = React.useState<any | null>(null)
  const [configDir, setConfigDir] = React.useState('')
  const [settingsOpen, setSettingsOpen] = React.useState(false)
  const [settingsSection, setSettingsSection] = React.useState<string>('profile')
  const [notifs, setNotifs] = React.useState<Notif[]>([])
  const [notifsLoading, setNotifsLoading] = React.useState(false)
  const [draft, setDraft] = React.useState<{ kind: string; id: number; label: string } | null>(null)
  const seenNotifs = React.useRef<Set<string> | null>(null)

  const loadNotifs = React.useCallback(async () => {
    setNotifsLoading(true)
    try {
      const items: Notif[] = await window.aplica.listNotifications()
      setNotifs(items)
      // native desktop notification for newly-appeared alerts (not on the very first load)
      const keyer = (n: Notif): string => `${n.level}|${n.title}|${n.detail}`
      const alerts = items.filter((n: Notif) => n.level === 'error' || n.level === 'warn')
      if (seenNotifs.current === null) {
        seenNotifs.current = new Set(alerts.map(keyer))
      } else {
        const fresh = alerts.filter((n: Notif) => !seenNotifs.current!.has(keyer(n)))
        if (fresh.length) { window.aplica.notifyDesktop?.(fresh); fresh.forEach((n: Notif) => seenNotifs.current!.add(keyer(n))) }
      }
    } catch { /* ignore */ }
    setNotifsLoading(false)
  }, [])
  React.useEffect(() => {
    loadNotifs()
    const t = setInterval(loadNotifs, 60000)
    return () => clearInterval(t)
  }, [loadNotifs])
  const alertCount = notifs.filter((n) => n.level === 'error' || n.level === 'warn').length

  const loadAll = React.useCallback(async () => {
    const [c, p, dir] = await Promise.all([
      window.aplica.readConfig(),
      window.aplica.readProfile(),
      window.aplica.getConfigDir()
    ])
    setConfig(c.data)
    setProfile(p.data)
    setConfigDir(dir)
  }, [])

  React.useEffect(() => { loadAll() }, [loadAll])

  const saveConfig = async (next: any): Promise<void> => { setConfig(next); await window.aplica.writeConfig(next) }
  const saveProfile = async (next: any): Promise<void> => { setProfile(next); await window.aplica.writeProfile(next) }

  const openSettings = (section = 'profile'): void => { setSettingsSection(section); setSettingsOpen(true) }

  if (!config || !profile) {
    return <div className="app"><div className="content"><div className="content-inner"><p className="muted">Loading…</p></div></div></div>
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <Logo size={32} />
          <div>
            <div className="brand-name">Aplica</div>
            <div className="brand-sub">for Claude Code</div>
          </div>
        </div>

        {TABS.map((t) => (
          <div key={t.id} className={'nav-item' + (tab === t.id ? ' active' : '')} onClick={() => setTab(t.id)}>
            <t.icon />
            <span>{t.label}</span>
            {t.id === 'notifications' && alertCount > 0 && <span className="nav-count warn">{alertCount}</span>}
          </div>
        ))}

        <div className="nav-label">Configuration</div>
        <div className="nav-item" onClick={() => openSettings('profile')}>
          <Icon.settings /><span>Settings</span>
        </div>

        <div className="nav-spacer" />
        <div className="nav-foot">
          {configDir && <>config dir<br /><code>{configDir}</code><br /></>}
          v0.2.0 · MIT
        </div>
      </aside>

      <main className="content">
        <div className={'content-inner' + (tab === 'pipeline' ? ' wide' : '')}>
          {tab === 'home' && <Onboarding configDir={configDir} config={config} profile={profile} onReload={loadAll} onOpenSettings={openSettings} />}
          {tab === 'dashboard' && <Dashboard />}
          {tab === 'pipeline' && <Pipeline onGenerateDraft={(kind, id, label) => setDraft({ kind, id, label })} />}
          {tab === 'contacts' && <Contacts />}
          {tab === 'run' && <Run config={config} onOpenSettings={() => openSettings('profile')} />}
          {tab === 'notifications' && <Notifications items={notifs} loading={notifsLoading} onRefresh={loadNotifs} onGo={(t) => setTab(t as TabId)} />}
        </div>
      </main>

      {settingsOpen && (
        <SettingsModal
          config={config}
          profile={profile}
          section={settingsSection}
          onSection={setSettingsSection}
          onSaveConfig={saveConfig}
          onSaveProfile={saveProfile}
          onClose={() => { setSettingsOpen(false); loadAll() }}
        />
      )}

      {draft && <DraftModal kind={draft.kind} applicationId={draft.id} label={draft.label} onClose={() => setDraft(null)} />}
    </div>
  )
}
