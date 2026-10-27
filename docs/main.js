// Aplica landing: downloads for this system, clips that play only while seen, the pinned feature screen, the questions.
(() => {
  const REPO = 'eurafaeldecarvalho/aplica'
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches

  // downloads: the latest release, the row for this system marked; every link falls back to the releases page
  const ua = navigator.userAgent
  const os = /Windows/i.test(ua) ? 'exe' : /Linux|X11/i.test(ua) && !/Android/i.test(ua) ? 'AppImage' : null
  fetch(`https://api.github.com/repos/${REPO}/releases/latest`)
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((rel) => {
      const tag = document.querySelector('[data-tag]')
      if (tag) tag.textContent = rel.tag_name
      const find = (kind) => (rel.assets || []).find((a) => (kind === 'exe' ? /Setup-.*\.exe$/ : new RegExp(`\\.${kind}$`)).test(a.name))
      document.querySelectorAll('[data-asset]').forEach((row) => {
        const a = find(row.dataset.asset)
        if (a) row.href = a.browser_download_url
        if (row.dataset.asset === os) row.classList.add('is-you')
      })
      const mine = os && find(os)
      if (mine) document.querySelectorAll('[data-download]').forEach((a) => {
        a.href = mine.browser_download_url
        if (a.classList.contains('button')) a.textContent = `Download for ${os === 'exe' ? 'Windows' : 'Linux'}`
      })
    })
    .catch(() => {})

  // clips play only while on screen, never under reduced motion
  const play = (v, on) => { if (reduce) return; if (on) { v.preload = 'auto'; v.play().catch(() => {}) } else v.pause() }
  const seen = new IntersectionObserver((es) => es.forEach((e) => play(e.target, e.isIntersecting)), { threshold: 0.35 })
  document.querySelectorAll('[data-auto], .feat-media video').forEach((v) => seen.observe(v))

  const hero = document.querySelector('[data-auto]')
  const pause = document.querySelector('[data-pause]')
  pause?.addEventListener('click', () => {
    if (hero.paused) { hero.play(); pause.textContent = 'Pause' } else { hero.pause(); pause.textContent = 'Play' }
  })
  if (reduce && pause) pause.textContent = 'Play'

  // pinned stage: the description in the middle of the screen picks the clip
  const stage = [...document.querySelectorAll('[data-stage]')]
  const feats = [...document.querySelectorAll('[data-feat]')]
  let current = -1
  const pick = (i) => {
    if (i === current) return
    current = i
    feats.forEach((f, k) => f.classList.toggle('is-on', k === i))
    stage.forEach((v, k) => { v.classList.toggle('is-on', k === i); if (k === i) { v.currentTime = 0; play(v, true) } else v.pause() })
  }
  const midline = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) pick(Number(e.target.dataset.feat)) }), { rootMargin: '-45% 0px -45% 0px' })
  feats.forEach((f) => midline.observe(f))
  pick(0)
  const stageBox = document.querySelector('.feat-stage')
  if (stageBox) new IntersectionObserver((es) => es.forEach((e) => { const v = stage[current]; if (v) play(v, e.isIntersecting) }), { threshold: 0.2 }).observe(stageBox)

  // questions: one answer at a time, by click, hover or the arrow keys
  const qs = [...document.querySelectorAll('[data-q]')]
  const as = [...document.querySelectorAll('[data-a]')]
  const ask = (i, focus) => {
    qs.forEach((q, k) => { q.setAttribute('aria-selected', String(k === i)); q.tabIndex = k === i ? 0 : -1 })
    as.forEach((a, k) => { a.hidden = k !== i })
    if (focus) qs[i].focus()
  }
  qs.forEach((q, i) => {
    q.addEventListener('click', () => ask(i))
    q.addEventListener('mouseenter', () => ask(i))
    q.addEventListener('keydown', (e) => {
      const d = e.key === 'ArrowDown' ? 1 : e.key === 'ArrowUp' ? -1 : 0
      if (d) { e.preventDefault(); ask((i + d + qs.length) % qs.length, true) }
    })
  })
  ask(0)

  // entrances: heading, text, then picture, once
  if (!reduce && 'IntersectionObserver' in window) {
    const parts = document.querySelectorAll('.hero-copy > *, .hero-media, .features .h2, .feat, .never-copy, .never-list li, .q-head, .q-list li, .close-copy > *, .dl')
    parts.forEach((p, k) => { p.classList.add('rise'); p.style.transitionDelay = `${(k % 5) * 70}ms` })
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target) } }), { threshold: 0.12 })
    parts.forEach((p) => io.observe(p))
  }
})()
