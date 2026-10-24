import React from 'react'
import { Card } from '../ui'

export default function Dashboard(): JSX.Element {
  const [report, setReport] = React.useState('')
  const [today, setToday] = React.useState('')
  const [stuck, setStuck] = React.useState<{ travadas: string; pendencias: string } | null>(null)
  const [metrics, setMetrics] = React.useState('')
  const [followups, setFollowups] = React.useState('')
  const [err, setErr] = React.useState('')
  const [loading, setLoading] = React.useState(false)

  const load = React.useCallback(async () => {
    setLoading(true); setErr('')
    const check = await window.aplica.dbCheck()
    if (!(check.stdout || '').trim().endsWith('OK')) {
      setErr('Banco não inicializado. Vá em Início → Inicializar banco.')
      setLoading(false); return
    }
    const [r, t, s, m, f] = await Promise.all([
      window.aplica.dbReport(), window.aplica.dbToday(), window.aplica.dbStuck(),
      window.aplica.dbMetrics(), window.aplica.dbFollowups(7)
    ])
    setReport(r.stdout || r.stderr)
    setToday(t.stdout || t.stderr)
    setStuck(s)
    setMetrics(m.stdout || m.stderr)
    setFollowups(f.stdout || f.stderr)
    setLoading(false)
  }, [])

  React.useEffect(() => { load() }, [load])

  const countToday = (): string => {
    const m = /CANDIDATURAS_CONTAM=(\d+)/.exec(today)
    return m ? m[1] : '—'
  }

  return (
    <>
      <div className="page-head">
        <h2>Painel</h2>
        <p>Estado do seu banco local — candidaturas, travadas e o que precisa de você.</p>
      </div>

      <div className="btn-row" style={{ marginBottom: 16 }}>
        <button className="btn secondary" onClick={load} disabled={loading}>{loading ? 'Carregando…' : 'Atualizar'}</button>
        <span className="badge">Candidaturas hoje: {countToday()}</span>
      </div>

      {err && <div className="banner warn">{err}</div>}

      <Card title="Métricas — taxa de resposta por fonte">
        <pre className="console">{metrics || '(sem dados)'}</pre>
      </Card>

      <Card title="Resumo do dia">
        <pre className="console">{report || '(sem dados)'}</pre>
      </Card>

      <Card title="Follow-ups sugeridos (sem retorno há 7+ dias)">
        <pre className="console">{followups || '(nenhum)'}</pre>
      </Card>

      {stuck && (
        <div className="grid">
          <Card title="Vagas travadas (você termina na mão)">
            <pre className="console">{stuck.travadas || '(nenhuma)'}</pre>
          </Card>
          <Card title="Precisa de você">
            <pre className="console">{stuck.pendencias || '(nenhuma)'}</pre>
          </Card>
        </div>
      )}
    </>
  )
}
