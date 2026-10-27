// Recurring open-ended questions on job forms (mapped in apply-engine).
// Shared between the editor (Profile) and the completeness meter (Onboarding).
export const COMMON_QUESTIONS = [
  'Tell us about yourself',
  'Why do you want to work at this company?',
  'Why are you a good fit for this role?',
  'What are you looking for in your next role?',
  'Describe a project you are proud of',
  'What is your greatest strength?',
  'Are you willing to relocate?',
  'When can you start? / notice period',
  'Anything else you would like us to know?'
]

export const isCommon = (k: string): boolean => COMMON_QUESTIONS.includes(k)

export const omitCommon = (qa: Record<string, string>): Record<string, string> =>
  Object.fromEntries(Object.entries(qa || {}).filter(([k]) => !isCommon(k)))

export const pickCommon = (qa: Record<string, string>): Record<string, string> =>
  Object.fromEntries(Object.entries(qa || {}).filter(([k]) => isCommon(k)))

export const commonAnsweredCount = (qa: Record<string, string>): number =>
  Object.entries(qa || {}).filter(([k, v]) => isCommon(k) && typeof v === 'string' && v.trim()).length
