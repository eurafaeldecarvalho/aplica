import React from 'react'
import Onboarding from './tabs/Onboarding'
import Profile from './tabs/Profile'
import Target from './tabs/Target'
import Behavior from './tabs/Behavior'
import Schedule from './tabs/Schedule'
import Dashboard from './tabs/Dashboard'
import Run from './tabs/Run'

type TabId = 'onboarding' | 'profile' | 'target' | 'behavior' | 'schedule' | 'dashboard' | 'run'

const TABS: { id: TabId; label: string; ico: string }[] = [
  { id: 'onboarding', label: 'Início', ico: '◆' },
  { id: 'profile', label: 'Meus dados', ico: '●' },
  { id: 'target', label: 'Preferências de vaga', ico: '◎' },
  { id: 'behavior', label: 'Comportamento', ico: '◈' },
  { id: 'schedule', label: 'Agenda', ico: '◷' },
  { id: 'dashboard', label: 'Painel', ico: '▦' },
  { id: 'run', label: 'Executar', ico: '▶' }
]

export default function App(): JSX.Element {
  const [tab, setTab] = React.useState<TabId>('onboarding')
  const [config, setConfig] = React.useState<any | null>(null)
  const [profile, setProfile] = React.useState<any | null>(null)
  const [configDir, setConfigDir] = React.useState('')

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

  const saveConfig = async (next: any): Promise<void> => {
    setConfig(next)
    await window.aplica.writeConfig(next)
  }
  const saveProfile = async (next: any): Promise<void> => {
    setProfile(next)
    await window.aplica.writeProfile(next)
  }

  if (!config || !profile) {
    return <div className="app"><div className="content"><p className="muted">Carregando…</p></div></div>
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="logo">A</div>
          <div>
            <h1>Aplica</h1>
            <small>for Claude Code</small>
          </div>
        </div>
        {TABS.map((t) => (
          <div
            key={t.id}
            className={'nav-item' + (tab === t.id ? ' active' : '')}
            onClick={() => setTab(t.id)}
          >
            <span className="ico">{t.ico}</span>
            <span>{t.label}</span>
          </div>
        ))}
        <div className="nav-spacer" />
        <div className="nav-foot">
          {configDir ? `config: ${configDir}` : ''}
          <br />v0.1.0 · MIT
        </div>
      </aside>

      <main className="content">
        {tab === 'onboarding' && <Onboarding configDir={configDir} onReload={loadAll} />}
        {tab === 'profile' && <Profile profile={profile} onSave={saveProfile} />}
        {tab === 'target' && <Target config={config} onSave={saveConfig} />}
        {tab === 'behavior' && <Behavior config={config} onSave={saveConfig} />}
        {tab === 'schedule' && <Schedule config={config} onSave={saveConfig} />}
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'run' && <Run config={config} />}
      </main>
    </div>
  )
}
