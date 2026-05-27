import { JKUAT_CENTER } from './landmarks.js'

export const JKUAT_GEOFENCE_CENTER = JKUAT_CENTER
export const JKUAT_SERVICE_RADIUS_KM = 12
export const JKUAT_BLOCK_RADIUS_KM = 15
export const JKUAT_SERVICE_RADIUS_METERS = JKUAT_SERVICE_RADIUS_KM * 1000

const EARTH_RADIUS_KM = 6371

const toRadians = (degrees) => (degrees * Math.PI) / 180

export const getDistanceFromJkuatKm = (lat, lng) => {
  const latitude = Number(lat)
  const longitude = Number(lng)

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null

  const [centerLat, centerLng] = JKUAT_GEOFENCE_CENTER
  const deltaLat = toRadians(latitude - centerLat)
  const deltaLng = toRadians(longitude - centerLng)
  const a = Math.sin(deltaLat / 2) ** 2
    + Math.cos(toRadians(centerLat)) * Math.cos(toRadians(latitude)) * Math.sin(deltaLng / 2) ** 2

  return 2 * EARTH_RADIUS_KM * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

export const getGeofenceStatus = (lat, lng) => {
  const distanceKm = getDistanceFromJkuatKm(lat, lng)

  if (distanceKm === null) {
    return {
      level: 'unknown',
      distanceKm: null,
      title: 'Location not checked',
      message: 'We will use your selected campus landmark unless GPS is available.',
    }
  }

  if (distanceKm >= JKUAT_BLOCK_RADIUS_KM) {
    return {
      level: 'blocked',
      distanceKm,
      title: 'Outside TaskiT service area',
      message: `This location is ${distanceKm.toFixed(1)}km from JKUAT. Posting and accepting are blocked from ${JKUAT_BLOCK_RADIUS_KM}km and beyond.`,
    }
  }

  if (distanceKm > JKUAT_SERVICE_RADIUS_KM) {
    return {
      level: 'warning',
      distanceKm,
      title: 'Near the edge of TaskiT coverage',
      message: `This location is ${distanceKm.toFixed(1)}km from JKUAT. You can continue, but tasks should still be JKUAT-related.`,
    }
  }

  return {
    level: 'allowed',
    distanceKm,
    title: 'Inside TaskiT coverage',
    message: `This location is ${distanceKm.toFixed(1)}km from JKUAT and inside the 12km service area.`,
  }
}

export const getCurrentPosition = () => new Promise((resolve, reject) => {
  if (!navigator.geolocation) {
    reject(new Error('Geolocation is not supported by this browser.'))
    return
  }

  navigator.geolocation.getCurrentPosition(
    (position) => resolve({
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
    }),
    reject,
    { enableHighAccuracy: true, timeout: 10000 },
  )
})
