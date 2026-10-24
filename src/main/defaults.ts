// Defaults de fábrica (espelham engine/config.py DEFAULTS). Conservadores: social OFF, tetos baixos.
// Nenhum dado pessoal — tudo neutro, para o usuário preencher.

export const DEFAULT_CONFIG = {
  schema_version: 1,
  target: {
    titles_search: ['Software Engineer', 'Backend Engineer', 'Developer'],
    title_ok: 'engineer|developer|desenvolvedor|engenheir',
    title_bad: 'junior|j[uú]nior|jr\\b|intern|est[aá]gi|trainee',
    stack_target: '',
    stack_out: {},
    geo_allow: ['remote', 'remoto', 'worldwide', 'anywhere', 'global'],
    geo_block: [],
    company_block: [],
    work_language: ['english', 'portuguese'],
    language_required_block: '',
    home_city: '',
    work_modes: { remote: true, hybrid: false, onsite: false }
  },
  behavior: {
    feed_mode: 'off',
    social: { comment: false, connect: false, dm: false, like: false },
    im_interested: false,
    email_resume: false,
    sso_google: true,
    create_account: false
  },
  caps: {
    applications_per_day: 15,
    max_batches: 10,
    batch_size: 5,
    social_per_day: 0,
    interest_per_day: 0,
    interest_cooldown_days: 180,
    post_interval_days: 7,
    cadence_seconds: [45, 240],
    active_hours: { start: '', end: '' }
  },
  sources: { ats: true, linkedin_jobs: true, remotive: true, freehire: true, linkedin_feed: false },
  schedule: {
    ats: { enabled: false, times: ['06:00'] },
    linkedin_jobs: { enabled: false, times: ['10:00'] },
    recruiters: { enabled: false, times: ['08:30', '16:30'] },
    feed: { enabled: false, times: ['09:15', '12:15', '15:15', '18:15'] },
    summary: { enabled: false, times: ['20:30'] }
  },
  current_employer: [],
  paths: { resume: 'resume.pdf', photo: 'photo.jpg' }
}

export const BLANK_PROFILE = {
  identity: { full_name: '', email: '', phone_e164: '', birth_date: '', national_id: '', nationality: '' },
  address: { line1: '', city: '', state: '', country: '', postal_code: '' },
  links: { linkedin: '', github: '', portfolio: '', other: [] },
  work_authorization: { authorized_countries: [], needs_sponsorship: false, disability: '', veteran: '', contact_current_employer: false },
  eeo: { gender: '', pronouns: '', race: '', self_identification: '' },
  preferences: {
    headline: '', seniority: '', work_model: '', contract_types: [],
    salary: {}, start_availability: '', notice_period: ''
  },
  experience: { total_years: 0, current_role: '', stacks: [], bio: {}, years_by_tech: {} },
  languages: [],
  education: [],
  open_answers: { pitch: '', writing_style: '', qa: {} },
  references: []
}
