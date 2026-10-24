import React from 'react'
import { Card } from '../ui'

type Prereqs = {
  python: boolean; pythonBin: string | null
  claude: boolean; claudeBin: string | null
  configDir: string; enginePresent: boolean
  resumePresent: boolean; configPresent: boolean; profilePresent: boolean
}

export default function Onboarding(props: { configDir: string; onReload: () => void }): JSX.Element {
  const [pr, setPr] = React.useState<Prereqs | null>(null)
  const [dbMsg, setDbMsg] = React.useState('')
  const [busy, setBusy] = React.useState(false)

  const refresh = React.useCallback(async () => {
    setPr(await window.aplica.checkPrereqs())
  }, [])
  React.useEffect(() => { refresh() }, [refresh])

  const initDb = async (): Promise<void> => {
    setBusy(true)
    const r = await window.aplica.dbInit()
    const c = await window.aplica.dbCheck()
    setDbMsg((r.stdout || r.stderr) + '\n' + (c.stdout || c.stderr))
    setBusy(false)
    refresh()
  }

  const pick = async (kind: 'resume' | 'photo'): Promise<void> => {
    await window.aplica.pickFile(kind)
    refresh()
  }

  const Row = (p: { ok: boolean; title: string; detail?: string }): JSX.Element => (
    <div className="check-row">
      <span className={'dot ' + (p.ok ? 'ok' : 'bad')} />
      <div className="grow">
        {p.title}
        {p.detail && <small>{p.detail}</small>}
      </div>
      <span className={'badge ' + (p.ok ? 'ok' : 'bad')}>{p.ok ? 'ok' : 'falta'}</span>
    </div>
  )

  return (
    <>
      <div className="page-head">
        <h2>Bem-vindo ao Aplica</h2>
        <p>O Aplica se candidata às suas vagas no seu próprio navegador, com os seus dados. Configure os passos abaixo.</p>
      </div>

      <div className="banner warn">
        <strong>Leia antes de usar.</strong> Boards como LinkedIn, Indeed e Glassdoor restringem automação nos termos de uso —
        sua conta pode ser limitada ou banida. Ações sociais (comentar/DM/conectar) e volume alto são os maiores gatilhos, por
        isso vêm <strong>desligadas</strong> por padrão. Você usa na sua conta, por sua conta e risco.
      </div>

      <Card title="Pré-requisitos">
        {pr ? (
          <>
            <Row ok={pr.python} title="Python 3.11+ no PATH" detail={pr.pythonBin ? `encontrado: ${pr.pythonBin}` : 'instale em python.org e reabra o app'} />
            <Row ok={pr.claude} title="Claude Code CLI (`claude`) no PATH" detail={pr.claudeBin ? `encontrado: ${pr.claudeBin}` : 'instale o Claude Code e faça login (plano pago)'} />
            <Row ok={pr.enginePresent} title="Motor do Aplica" detail="empacotado com o app" />
            <Row ok={pr.configPresent} title="config.json (preferências de vaga)" detail="preencha em Preferências de vaga e Comportamento, depois Salvar" />
            <Row ok={pr.profilePresent} title="profile.json (seus dados)" detail="preencha em Meus dados e Salvar" />
            <Row ok={pr.resumePresent} title="Currículo (resume.pdf)" detail="selecione abaixo" />
            <div className="btn-row">
              <button className="btn secondary" onClick={refresh}>Reverificar</button>
              <button className="btn secondary" onClick={() => window.aplica.openConfigDir()}>Abrir pasta de config</button>
            </div>
          </>
        ) : <p className="muted">Verificando…</p>}
      </Card>

      <Card title="Extensão Claude in Chrome" hint="Necessária para o Aplica agir no navegador. Instale e deixe suas contas logadas.">
        <ul className="muted" style={{ margin: 0, paddingLeft: 18 }}>
          <li>Plano Claude pago (Pro, Max, Team ou Enterprise) — não funciona no Free.</li>
          <li>Instale a extensão <strong>Claude</strong> (Claude in Chrome) na Chrome Web Store.</li>
          <li>Deixe LinkedIn, Google/Gmail e os boards que você usa logados no Chrome.</li>
        </ul>
      </Card>

      <Card title="Currículo e foto">
        <div className="btn-row">
          <button className="btn secondary" onClick={() => pick('resume')}>Selecionar currículo (PDF)</button>
          <button className="btn secondary" onClick={() => pick('photo')}>Selecionar foto</button>
        </div>
      </Card>

      <Card title="Banco de dados local">
        <p className="hint">Cria o banco de estado (candidaturas, dedup, travadas) no seu config dir.</p>
        <div className="btn-row">
          <button className="btn" onClick={initDb} disabled={busy || !pr?.python}>Inicializar / verificar banco</button>
        </div>
        {dbMsg && <pre className="console" style={{ marginTop: 12 }}>{dbMsg}</pre>}
      </Card>
    </>
  )
}
