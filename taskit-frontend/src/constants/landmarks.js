export const JKUAT_CENTER = [-1.1017, 37.0143]

export const LANDMARKS = [
  { name: 'Main Gate', lat: -1.1017, lng: 37.0143 },
  { name: 'Back Gate', lat: -1.0948, lng: 37.0121 },
  { name: 'Library', lat: -1.0999, lng: 37.0129 },
  { name: 'Administration Block', lat: -1.1011, lng: 37.0132 },
  { name: 'Engineering Block', lat: -1.1026, lng: 37.0165 },
  { name: 'ICT Centre', lat: -1.1006, lng: 37.0154 },
  { name: 'Health Centre', lat: -1.1031, lng: 37.0122 },
  { name: 'Hostels Block A', lat: -1.0968, lng: 37.0168 },
  { name: 'Hostels Block B', lat: -1.0974, lng: 37.0175 },
  { name: 'Hostels Block C', lat: -1.0982, lng: 37.0181 },
  { name: 'Hostels Block D', lat: -1.099, lng: 37.0186 },
  { name: 'Mess/Dining Hall', lat: -1.1001, lng: 37.017 },
  { name: 'Sports Ground', lat: -1.1045, lng: 37.0158 },
  { name: 'JKUAT Town Stage', lat: -1.106, lng: 37.0108 },
  { name: 'Other (specify in notes)', lat: -1.1017, lng: 37.0143 },
]

export const getLandmarkPosition = (name) => {
  const landmark = LANDMARKS.find((item) => item.name === name)
  return landmark ? [landmark.lat, landmark.lng] : JKUAT_CENTER
}

export const getTaskPosition = (task) => {
  const lat = Number(task?.location_latitude)
  const lng = Number(task?.location_longitude)
  if (Number.isFinite(lat) && Number.isFinite(lng)) {
    return [lat, lng]
  }
  return getLandmarkPosition(task?.location_landmark)
}
