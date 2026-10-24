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
  const preRef = React.useRef<HTMLPreElement>(null)

  React.useEffect(() => {
    const off = window.aplica.onRoutineOutput((chunk) => {
      setOutput((o) => o + chunk)
      requestAnimationFrame(() => { if (preRef.current) preRef.current.scrollTop = preRef.current.scrollHeight })
    })
    return off
  }, [])

  const run = async (): Promise<void> => {
    setOutput(''); setRunning(true)
    const r = await window.aplica.runRoutine(source)
    if (!r.ok) setOutput((o) => o + `\n[erro] ${r.error}\n`)
    setRunning(false)
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

      <Card title="Rodar agora">
        <div className="field">
          <label>Fonte</label>
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            {SOURCES.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </div>
        {feedWarn && <div className="banner warn" style={{ marginTop: 0 }}>O feed está em modo <strong>off</strong> no Comportamento; essa rotina não fará nada.</div>}
        <div className="btn-row">
          <button className="btn" onClick={run} disabled={running}>{running ? 'Rodando…' : 'Rodar'}</button>
        </div>
      </Card>

      <Card title="Saída">
        <pre className="console" ref={preRef}>{output || '(a saída da execução aparece aqui)'}</pre>
      </Card>
    </>
  )
}
