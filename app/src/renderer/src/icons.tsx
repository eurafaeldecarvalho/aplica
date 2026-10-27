import React from 'react'

/* Logo da Aplica — marca própria: um alvo (fit) atravessado por uma seta ascendente
   (candidatar = enviar adiante). Badge com gradiente do accent. */
export function Logo({ size = 30 }: { size?: number }): JSX.Element {
  const id = React.useId()
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8a7bff" />
          <stop offset="1" stopColor="#6a57f5" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill={`url(#${id})`} />
      <circle cx="17" cy="23" r="8.5" stroke="#fff" strokeOpacity="0.9" strokeWidth="2.6" />
      <path d="M15 25 L27 13" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" />
      <path d="M22 12.4 L28 12 L27.6 18" stroke="#fff" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

type P = { size?: number }
const S = (p: P, d: React.ReactNode): JSX.Element => (
  <svg width={p.size || 18} height={p.size || 18} viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{d}</svg>
)

export const Icon = {
  home: (p: P = {}) => S(p, <><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9.5" /></>),
  user: (p: P = {}) => S(p, <><circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.6-6 8-6s8 2 8 6" /></>),
  target: (p: P = {}) => S(p, <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4.5" /><circle cx="12" cy="12" r="0.6" fill="currentColor" /></>),
  sliders: (p: P = {}) => S(p, <><path d="M4 7h10M18 7h2M4 17h2M10 17h10" /><circle cx="16" cy="7" r="2.2" /><circle cx="8" cy="17" r="2.2" /></>),
  clock: (p: P = {}) => S(p, <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>),
  grid: (p: P = {}) => S(p, <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="13.5" width="7" height="7" rx="1.5" /></>),
  play: (p: P = {}) => S(p, <path d="M7 5.5 18.5 12 7 18.5z" fill="currentColor" stroke="none" />),
  stop: (p: P = {}) => S(p, <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none" />),
  settings: (p: P = {}) => S(p, <><circle cx="12" cy="12" r="3" /><path d="M12 2.5v3M12 18.5v3M4.2 7l2.6 1.5M17.2 15.5l2.6 1.5M19.8 7l-2.6 1.5M6.8 15.5 4.2 17M2.5 12h3M18.5 12h3" /></>),
  check: (p: P = {}) => S(p, <path d="M5 12.5 10 17.5 19.5 7" />),
  x: (p: P = {}) => S(p, <path d="M6 6l12 12M18 6 6 18" />),
  download: (p: P = {}) => S(p, <><path d="M12 3v12" /><path d="M7.5 10.5 12 15l4.5-4.5" /><path d="M4 20h16" /></>),
  folder: (p: P = {}) => S(p, <path d="M3 7a2 2 0 0 1 2-2h4l2 2.5h8a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />),
  refresh: (p: P = {}) => S(p, <><path d="M20 11a8 8 0 0 0-14-4.5L3 9" /><path d="M3 4v5h5" /><path d="M4 13a8 8 0 0 0 14 4.5L21 15" /><path d="M21 20v-5h-5" /></>),
  external: (p: P = {}) => S(p, <><path d="M14 4h6v6" /><path d="M20 4 10 14" /><path d="M19 14v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" /></>),
  alert: (p: P = {}) => S(p, <><path d="M12 3 22 20H2z" /><path d="M12 10v4" /><circle cx="12" cy="17" r="0.6" fill="currentColor" /></>),
  info: (p: P = {}) => S(p, <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><circle cx="12" cy="8" r="0.7" fill="currentColor" /></>),
  chrome: (p: P = {}) => S(p, <><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="3.4" /><path d="M12 8.6h8.4M8.9 13.8 4.7 6.6M15.1 13.8l-4.2 7.3" /></>),
  python: (p: P = {}) => S(p, <><rect x="5" y="4" width="14" height="16" rx="4" /><path d="M5 12h14" /><circle cx="9" cy="8" r="0.7" fill="currentColor" /><circle cx="15" cy="16" r="0.7" fill="currentColor" /></>),
  bolt: (p: P = {}) => S(p, <path d="M13 2 4 14h7l-1 8 9-12h-7z" />),
  columns: (p: P = {}) => S(p, <><rect x="3.5" y="4" width="5" height="16" rx="1.4" /><rect x="9.5" y="4" width="5" height="16" rx="1.4" /><rect x="15.5" y="4" width="5" height="16" rx="1.4" /></>),
  file: (p: P = {}) => S(p, <><path d="M6 3h8l4 4v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" /><path d="M13 3v5h5" /></>)
}
