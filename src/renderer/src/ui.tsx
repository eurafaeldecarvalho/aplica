import React from 'react'

export function Card(props: { title?: string; hint?: string; children: React.ReactNode }): JSX.Element {
  return (
    <div className="card">
      {props.title && <h3>{props.title}</h3>}
      {props.hint && <p className="hint">{props.hint}</p>}
      {props.children}
    </div>
  )
}

export function Field(props: {
  label: string
  value: string | number
  onChange: (v: string) => void
  placeholder?: string
  type?: string
}): JSX.Element {
  return (
    <div className="field">
      <label>{props.label}</label>
      <input
        type={props.type || 'text'}
        value={props.value ?? ''}
        placeholder={props.placeholder}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </div>
  )
}

export function TextArea(props: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder?: string
  rows?: number
}): JSX.Element {
  return (
    <div className="field">
      <label>{props.label}</label>
      <textarea
        value={props.value ?? ''}
        placeholder={props.placeholder}
        rows={props.rows}
        onChange={(e) => props.onChange(e.target.value)}
      />
    </div>
  )
}

export function Toggle(props: {
  label: string
  desc?: string
  checked: boolean
  onChange: (v: boolean) => void
}): JSX.Element {
  return (
    <div className="toggle">
      <div className="meta">
        <strong>{props.label}</strong>
        {props.desc && <span>{props.desc}</span>}
      </div>
      <label className="switch">
        <input type="checkbox" checked={!!props.checked} onChange={(e) => props.onChange(e.target.checked)} />
        <span className="slider" />
      </label>
    </div>
  )
}

/** Lista editável de strings (chips). */
export function TagInput(props: {
  label: string
  values: string[]
  onChange: (v: string[]) => void
  placeholder?: string
}): JSX.Element {
  const [draft, setDraft] = React.useState('')
  const add = (): void => {
    const v = draft.trim()
    if (v && !props.values.includes(v)) props.onChange([...props.values, v])
    setDraft('')
  }
  return (
    <div className="field">
      <label>{props.label}</label>
      <div className="tag-list" style={{ marginBottom: 8 }}>
        {props.values.map((v) => (
          <span className="tag" key={v}>
            {v}
            <button onClick={() => props.onChange(props.values.filter((x) => x !== v))} aria-label={`remover ${v}`}>
              ×
            </button>
          </span>
        ))}
        {props.values.length === 0 && <span className="muted" style={{ fontSize: 12 }}>nenhum</span>}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          type="text"
          value={draft}
          placeholder={props.placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); add() }
          }}
        />
        <button className="btn secondary" onClick={add}>Adicionar</button>
      </div>
    </div>
  )
}

export function SaveBar(props: { onSave: () => void; saved: boolean; busy?: boolean; extra?: React.ReactNode }): JSX.Element {
  return (
    <div className="save-bar">
      <button className="btn" onClick={props.onSave} disabled={props.busy}>Salvar</button>
      {props.extra}
      {props.saved && <span className="saved">✓ salvo</span>}
    </div>
  )
}
