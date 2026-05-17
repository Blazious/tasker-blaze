export const GENDER_PREFERENCES = [
  { value: '', label: 'All preferences' },
  { value: 'ANY', label: 'Any verified student' },
  { value: 'FEMALE', label: 'Female preferred' },
  { value: 'MALE', label: 'Male preferred' },
]

export const TASK_GENDER_PREFERENCE_LABELS = {
  ANY: 'Any verified student',
  FEMALE: 'Female tasker preferred',
  MALE: 'Male tasker preferred',
}

export const USER_GENDER_LABELS = {
  NOT_SPECIFIED: 'Not specified',
  FEMALE: 'Female',
  MALE: 'Male',
  OTHER: 'Other',
}

export function getTaskGenderPreferenceLabel(value) {
  return TASK_GENDER_PREFERENCE_LABELS[value] ?? TASK_GENDER_PREFERENCE_LABELS.ANY
}

export function taskerMatchesPreference(taskPreference, userGender) {
  if (!taskPreference || taskPreference === 'ANY') return true
  return taskPreference === userGender
}
