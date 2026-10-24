import React from 'react'
import { Card } from '../ui'

const SOURCES = [
  { id: 'all', label: 'Tudo' },
  { id: 'ats', label: 'ATS / boards' },
  { id: 'linkedin', label: 'LinkedIn Jobs' },
  { id: 'freehire', label: 'Freehire' },
  { id: 'recruiters', label: 'Recrutadores' },
  { id: 'feed', label: 'Feed' }
]

export default function Run(props: { config: any }): JSX.Element {
  const [source, setSource] = React.useState('all')
  const [output, setOutput] = React.useState('')
  const [running, setRunning] = React.useState(false)
  const [blockers, setBlockers] = React.useState<string[]>([])
  const preRef = React.useRef<HTMLPreElement>(null)

  React.useEffect(() => {
    (async () => {
      const b: string[] = []
      const pr: any = await window.aplica.checkPrereqs()
      if (!pr.claude) b.push('Claude Code CLI (`claude`) não encontrado no PATH')
      if (!pr.python) b.push('Python não encontrado no PATH')
      if (!pr.configPresent) b.push('config.json ausente — preencha Preferências de vaga/Comportamento e Salve')
      if (!pr.profilePresent) b.push('profile.json ausente — preencha Meus dados e Salve')
      const chk: any = await window.aplica.dbCheck()
      if (!(chk.stdout || '').trim().endsWith('OK')) b.push('Banco não inicializado — Início → Inicializar banco')
      setBlockers(b)
    })()
  }, [])

  React.useEffect(() => {
    const off = window.aplica.onRoutineOutput((chunk) => {
      setOutput((o) => o + chunk)
      requestAnimationFrame(() => { if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight })
    })
    return off
  }, [])

  React.useEffect(() => {
    window.aplica.isRunning().then((s: any) => setRunning(!!s?.running))
  }, [])

  const run = async (): Promise<void> => {
    setOutput(''); setRunning(true)
    const r = await window.aplica.runRoutine(source)
    if (!r.ok) setOutput((o) => o + `\n[erro] ${r.error}\n`)
    setRunning(false)
  }

  const stop = async (): Promise<void> => {
    await window.aplica.stopRoutine()
  }

  const feedWarn = source === 'feed' && props.config?.behavior?.feed_mode === 'off'

  return (
    <>
      <div className="page-head">
        <h2>Executar</h2>
        <p>Roda uma rodada agora, pelo Claude Code, no seu navegador. Você pode acompanhar a saída ao vivo.</p>
      </div>

      <div className="banner info">
        A execução usa o plugin <strong>aplica</strong> instalado no Claude Code (<code>/aplica-run</code>) e a extensão Claude in Chrome.
        Confirme no Início que <code>claude</code> está no PATH e que o plugin está instalado.
      </div>
      <div className="banner warn">
        A rodada roda em <strong>modo autônomo</strong> (sem pedir aprovação de cada ação) para poder operar sem você. As travas são
        as regras das skills (honestidade, parar no LinkedIn, nunca pagar/enviar documento) — não há um segundo gate. Rode só com as
        suas contas, revise os defaults e use <strong>Parar</strong> se precisar interromper.
      </div>

      <Card title="Rodar agora">
        <div className="field">
          <label>Fonte</label>
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            {SOURCES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </div>
        {feedWarn && <div className="banner warn" style={{ marginTop: 0 }}>O feed está em modo <strong>off</strong> no Comportamento; essa rotina não fará nada.</div>}
        {blockers.length > 0 && (
          <div className="banner warn" style={{ marginTop: 0 }}>
            Complete o Início antes de rodar:
            <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>{blockers.map((b) => <li key={b}>{b}</li>)}</ul>
          </div>
        )}
        <div className="btn-row">
          <button className="btn" onClick={run} disabled={running || blockers.length > 0}>{running ? 'Rodando…' : 'Rodar'}</button>
          {running && <button className="btn secondary" onClick={stop}>Parar</button>}
        </div>
      </Card>

      <Card title="Saída">
        <pre className="console" ref={preRef}>{output || '(a saída da execução aparece aqui)'}</pre>
      </Card>
    </>
  )
}
