export function getApiErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const data = error?.response?.data

  if (!data) {
    return fallback
  }

  if (typeof data === 'string') {
    if (data.trim().startsWith('<!DOCTYPE html') || data.includes('<html')) {
      return fallback
    }
    return data
  }

  if (data.detail) {
    return data.detail
  }

  const firstKey = Object.keys(data)[0]
  const firstValue = data[firstKey]
  if (Array.isArray(firstValue)) {
    return firstValue[0]
  }
  if (typeof firstValue === 'string') {
    return firstValue
  }

  return fallback
}
