export const AVAILABILITY_OPTIONS = [
  { value: 'AVAILABLE', label: 'Available', tone: 'emerald' },
  { value: 'BUSY', label: 'Busy', tone: 'amber' },
  { value: 'OFFLINE', label: 'Offline', tone: 'slate' },
]

export const AVAILABILITY_LABELS = {
  AVAILABLE: 'Available now',
  BUSY: 'Busy',
  OFFLINE: 'Offline',
}

export function getAvailabilityLabel(value) {
  return AVAILABILITY_LABELS[value] ?? AVAILABILITY_LABELS.OFFLINE
}

export function getAvailabilityClass(value) {
  if (value === 'AVAILABLE') return 'bg-emerald-50 text-emerald-700 border-emerald-200'
  if (value === 'BUSY') return 'bg-amber-50 text-amber-700 border-amber-200'
  return 'bg-slate-100 text-slate-600 border-slate-200'
}
