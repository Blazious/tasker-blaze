import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Camera, Check, Crosshair, Loader2, MapPin, UploadCloud } from 'lucide-react'
import { Circle, MapContainer, Marker, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { createTask, getCategories } from '../api/tasks.js'
import { getLandmarkPosition, JKUAT_CENTER, LANDMARKS } from '../constants/landmarks.js'
import { CATEGORY_BUDGET_TIPS } from '../constants/taskCategories.js'
import { getTaskGenderPreferenceLabel } from '../constants/genderPreference.js'
import { getCurrentPosition, getGeofenceStatus, JKUAT_GEOFENCE_CENTER, JKUAT_SERVICE_RADIUS_METERS } from '../constants/geofence.js'
import { getApiErrorMessage } from '../utils/apiError.js'

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const initialForm = {
  title: '',
  category: '',
  description: '',
  task_photo: null,
  location_landmark: '',
  location_notes: '',
  location_latitude: '',
  location_longitude: '',
  requires_home_visit: false,
  preferred_tasker_gender: 'ANY',
  schedule_type: 'ASAP',
  scheduled_for: '',
  deadline: '',
  budget_min: '',
  budget_max: '',
}

function DraggableLocationMarker({ position, onChange }) {
  useMapEvents({
    click(event) {
      onChange(event.latlng.lat, event.latlng.lng)
    },
  })

  return (
    <Marker
      draggable
      position={position}
      eventHandlers={{
        dragend(event) {
          const marker = event.target
          const nextPosition = marker.getLatLng()
          onChange(nextPosition.lat, nextPosition.lng)
        },
      }}
    />
  )
}

function RecenterMap({ position }) {
  const map = useMap()
  useEffect(() => {
    map.setView(position, map.getZoom())
  }, [map, position])
  return null
}

export default function CreateTaskPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [currentLocation, setCurrentLocation] = useState(null)
  const [isPostingTask, setIsPostingTask] = useState(false)
  const postingTaskRef = useRef(false)

  const categoriesQuery = useQuery({
    queryKey: ['task-categories'],
    queryFn: getCategories,
  })

  const selectedCategory = useMemo(
    () => (categoriesQuery.data ?? []).find((category) => String(category.id) === String(form.category)),
    [categoriesQuery.data, form.category],
  )
  const pinGeofenceStatus = useMemo(
    () => getGeofenceStatus(form.location_latitude, form.location_longitude),
    [form.location_latitude, form.location_longitude],
  )

  const createMutation = useMutation({
    mutationFn: createTask,
    onSuccess: (task) => {
      toast.success('Task posted! Sit back while taskers bid.')
      navigate(`/tasks/${task.id}`)
    },
    onError: (submissionError) => {
      setError(getApiErrorMessage(submissionError, 'Could not create task. Please check the form.'))
    },
  })

  const updateField = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }))
  }

  const updatePin = (lat, lng) => {
    setForm((current) => ({
      ...current,
      location_latitude: Number(lat).toFixed(6),
      location_longitude: Number(lng).toFixed(6),
    }))
  }

  const syncPinToLandmark = (landmarkName) => {
    const [lat, lng] = getLandmarkPosition(landmarkName)
    setForm((current) => ({
      ...current,
      location_landmark: landmarkName,
      location_latitude: Number(lat).toFixed(6),
      location_longitude: Number(lng).toFixed(6),
    }))
  }

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setError('Your browser does not support current location.')
      return
    }

    getCurrentPosition()
      .then((position) => {
        setCurrentLocation(position)
        updatePin(position.latitude, position.longitude)
        toast.success('Location pin moved to your current location')
      })
      .catch(() => setError('Could not access your current location. You can drag the pin manually.'))
  }

  const validateStep = () => {
    setError('')
    if (step === 1) {
      if (!form.title.trim() || !form.category || form.description.trim().length < 20) {
        setError('Add a title, category, and description of at least 20 characters.')
        return false
      }
    }
    if (step === 2) {
      if (!form.location_landmark) {
        setError('Choose a JKUAT location landmark.')
        return false
      }
      if (pinGeofenceStatus.level === 'blocked') {
        setError(pinGeofenceStatus.message)
        return false
      }
      if (form.schedule_type === 'SCHEDULED') {
        if (!form.scheduled_for) {
          setError('Choose when the scheduled task should start.')
          return false
        }
        if (new Date(form.scheduled_for).getTime() <= Date.now()) {
          setError('Scheduled tasks must be set for a future time.')
          return false
        }
      }
      if (form.deadline && form.scheduled_for && new Date(form.deadline).getTime() < new Date(form.scheduled_for).getTime()) {
        setError('Deadline cannot be before the scheduled start time.')
        return false
      }
    }
    if (step === 3) {
      const min = Number(form.budget_min)
      const max = Number(form.budget_max)
      if (min < 50) {
        setError('Budget minimum must be at least KES 50.')
        return false
      }
      if (min >= max) {
        setError('Budget minimum must be less than budget maximum.')
        return false
      }
    }
    return true
  }

  const nextStep = () => {
    if (validateStep()) setStep((current) => Math.min(3, current + 1))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (postingTaskRef.current || isPostingTask || createMutation.isPending) {
      toast('Task is posting. Please wait.')
      return
    }
    if (!validateStep()) return
    postingTaskRef.current = true
    setIsPostingTask(true)

    let actorLocation = currentLocation
    try {
      actorLocation = await getCurrentPosition()
      setCurrentLocation(actorLocation)
      const actorStatus = getGeofenceStatus(actorLocation.latitude, actorLocation.longitude)
      if (actorStatus.level === 'blocked') {
        setError(actorStatus.message)
        postingTaskRef.current = false
        setIsPostingTask(false)
        return
      }
      if (actorStatus.level === 'warning') {
        toast(actorStatus.message)
      }
    } catch {
      toast('Could not confirm GPS. You can continue, but TaskiT may review unusual activity.')
    }

    const payload = new FormData()
    Object.entries(form).forEach(([key, value]) => {
      if (value !== '' && value !== null) payload.append(key, value)
    })
    if (actorLocation) {
      payload.append('actor_latitude', Number(actorLocation.latitude).toFixed(6))
      payload.append('actor_longitude', Number(actorLocation.longitude).toFixed(6))
    }
    createMutation.mutate(payload, {
      onSettled: () => {
        postingTaskRef.current = false
        setIsPostingTask(false)
      },
    })
  }

  const isSubmitLocked = isPostingTask || createMutation.isPending

  return (
    <section className="mx-auto max-w-4xl">
      <div className="mb-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Post a task</p>
        <h1 className="mt-2 text-3xl font-bold text-primary">Tell campus what you need done</h1>
        <div className="mt-5 grid grid-cols-3 gap-3">
          {[1, 2, 3].map((item) => (
            <div key={item} className={`h-2 rounded-full ${item <= step ? 'bg-primary' : 'bg-slate-200'}`} />
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        {step === 1 && (
          <div className="grid gap-4">
            <h2 className="text-xl font-semibold text-text-dark">Step 1 - Task details</h2>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Title</span>
              <input value={form.title} onChange={(event) => updateField('title', event.target.value)} maxLength={100} className="rounded-md border border-slate-300 px-3 py-2" />
            </label>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Category</span>
              <select value={form.category} onChange={(event) => updateField('category', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
                <option value="">Choose category</option>
                {(categoriesQuery.data ?? []).map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </label>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Description</span>
              <textarea value={form.description} onChange={(event) => updateField('description', event.target.value)} rows={5} className="rounded-md border border-slate-300 px-3 py-2" />
              <span className="text-xs text-text-muted">Minimum 20 characters</span>
            </label>
            <label
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault()
                updateField('task_photo', event.dataTransfer.files?.[0] ?? null)
              }}
              className="flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 p-6 text-center"
            >
              <UploadCloud className="text-primary" />
              <span className="mt-2 font-medium text-text-dark">Drop a photo or click to upload</span>
              <span className="text-sm text-text-muted">{form.task_photo?.name ?? 'Optional task photo'}</span>
              <input type="file" accept="image/*" className="hidden" onChange={(event) => updateField('task_photo', event.target.files?.[0] ?? null)} />
            </label>
          </div>
        )}

        {step === 2 && (
          <div className="grid gap-4">
            <h2 className="text-xl font-semibold text-text-dark">Step 2 - Location, safety & preference</h2>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Location Landmark</span>
              <select value={form.location_landmark} onChange={(event) => syncPinToLandmark(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
                <option value="">Choose landmark</option>
                {LANDMARKS.map((landmark) => (
                  <option key={landmark.name} value={landmark.name}>{landmark.name}</option>
                ))}
              </select>
            </label>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Location Notes</span>
              <input value={form.location_notes} onChange={(event) => updateField('location_notes', event.target.value)} placeholder="Near the stairs, outside the lobby..." className="rounded-md border border-slate-300 px-3 py-2" />
            </label>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="inline-flex items-center gap-2 font-semibold text-text-dark">
                    <MapPin size={18} />
                    Optional map pin
                  </h3>
                  <p className="mt-1 text-sm text-text-muted">
                    Use this when you want taskers to find the exact meeting point like a ride-hailing pickup pin.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={useCurrentLocation}
                  className="inline-flex w-fit items-center gap-2 rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary"
                >
                  <Crosshair size={16} />
                  Select current location
                </button>
              </div>
              <div className="mt-4 overflow-hidden rounded-lg border border-slate-200">
                <MapContainer
                  center={
                    form.location_latitude && form.location_longitude
                      ? [Number(form.location_latitude), Number(form.location_longitude)]
                      : form.location_landmark
                        ? getLandmarkPosition(form.location_landmark)
                        : JKUAT_CENTER
                  }
                  zoom={12}
                  className="h-72 w-full"
                  scrollWheelZoom
                >
                  <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                  <Circle
                    center={JKUAT_GEOFENCE_CENTER}
                    radius={JKUAT_SERVICE_RADIUS_METERS}
                    pathOptions={{ color: '#2563eb', fillColor: '#60a5fa', fillOpacity: 0.08, weight: 2 }}
                  />
                  <RecenterMap
                    position={
                      form.location_latitude && form.location_longitude
                        ? [Number(form.location_latitude), Number(form.location_longitude)]
                        : form.location_landmark
                          ? getLandmarkPosition(form.location_landmark)
                          : JKUAT_CENTER
                    }
                  />
                  <DraggableLocationMarker
                    position={
                      form.location_latitude && form.location_longitude
                        ? [Number(form.location_latitude), Number(form.location_longitude)]
                        : form.location_landmark
                          ? getLandmarkPosition(form.location_landmark)
                          : JKUAT_CENTER
                    }
                    onChange={updatePin}
                  />
                </MapContainer>
              </div>
              {pinGeofenceStatus.level !== 'unknown' && (
                <div className={`mt-3 rounded-md border p-3 text-sm ${
                  pinGeofenceStatus.level === 'blocked'
                    ? 'border-red-200 bg-red-50 text-red-700'
                    : pinGeofenceStatus.level === 'warning'
                      ? 'border-amber-200 bg-amber-50 text-amber-800'
                      : 'border-blue-100 bg-blue-50 text-blue-800'
                }`}>
                  <p className="font-semibold">{pinGeofenceStatus.title}</p>
                  <p className="mt-1">{pinGeofenceStatus.message}</p>
                </div>
              )}
              <p className="mt-2 text-xs text-text-muted">
                Drag the pin or click the map to adjust. The blue circle shows TaskiT's 12km JKUAT service area.
                {form.location_latitude && form.location_longitude ? ` Pin: ${form.location_latitude}, ${form.location_longitude}` : ''}
              </p>
            </div>
            <label className="flex items-center justify-between gap-4 rounded-md border border-slate-200 p-4">
              <span className="font-medium text-text-dark">Does this task require coming to your room/house?</span>
              <input type="checkbox" checked={form.requires_home_visit} onChange={(event) => updateField('requires_home_visit', event.target.checked)} className="h-5 w-5 accent-primary" />
            </label>
            <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
              <label className="grid gap-1.5">
                <span className="text-sm font-semibold text-blue-950">Tasker gender preference</span>
                <select value={form.preferred_tasker_gender} onChange={(event) => updateField('preferred_tasker_gender', event.target.value)} className="rounded-md border border-blue-200 bg-white px-3 py-2">
                  <option value="ANY">Any verified student</option>
                  <option value="FEMALE">Female student preferred</option>
                  <option value="MALE">Male student preferred</option>
                </select>
                <span className="text-xs leading-5 text-blue-800">
                  This is shown to taskers before they bid. It is a safety preference, not a hidden rule.
                </span>
              </label>
            </div>
            {form.requires_home_visit && (
              <div className="rounded-md bg-amber-50 p-3 text-sm font-medium text-amber-800">
                For safety, only share your exact room number after you've accepted a tasker
              </div>
            )}
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="font-semibold text-text-dark">When should this task happen?</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => {
                    updateField('schedule_type', 'ASAP')
                    updateField('scheduled_for', '')
                  }}
                  className={`rounded-md border px-3 py-3 text-left ${form.schedule_type === 'ASAP' ? 'border-primary bg-emerald-50 text-primary' : 'border-slate-200 text-text-muted'}`}
                >
                  <span className="block font-semibold">ASAP</span>
                  <span className="text-sm">Taskers can bid for this immediately.</span>
                </button>
                <button
                  type="button"
                  onClick={() => updateField('schedule_type', 'SCHEDULED')}
                  className={`rounded-md border px-3 py-3 text-left ${form.schedule_type === 'SCHEDULED' ? 'border-primary bg-emerald-50 text-primary' : 'border-slate-200 text-text-muted'}`}
                >
                  <span className="block font-semibold">Schedule ahead</span>
                  <span className="text-sm">Pick a future date so taskers can plan.</span>
                </button>
              </div>
              {form.schedule_type === 'SCHEDULED' && (
                <label className="mt-4 grid gap-1.5">
                  <span className="text-sm font-medium">Scheduled start time</span>
                  <input
                    type="datetime-local"
                    value={form.scheduled_for}
                    onChange={(event) => updateField('scheduled_for', event.target.value)}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
              )}
            </div>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium">Deadline to finish by</span>
              <input type="datetime-local" value={form.deadline} onChange={(event) => updateField('deadline', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2" />
            </label>
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-4">
            <h2 className="text-xl font-semibold text-text-dark">Step 3 - Budget</h2>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="grid gap-1.5">
                <span className="text-sm font-medium">Budget Min</span>
                <input type="number" min="50" value={form.budget_min} onChange={(event) => updateField('budget_min', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2" />
              </label>
              <label className="grid gap-1.5">
                <span className="text-sm font-medium">Budget Max</span>
                <input type="number" min="50" value={form.budget_max} onChange={(event) => updateField('budget_max', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2" />
              </label>
            </div>
            <p className="rounded-md bg-emerald-50 p-3 text-sm text-primary">
              Tip: tasks in this category typically go for {CATEGORY_BUDGET_TIPS[selectedCategory?.slug] ?? 'KES 100-800'}
            </p>
            <div className="rounded-lg border border-slate-200 p-4">
              <h3 className="font-semibold text-text-dark">Summary</h3>
              <dl className="mt-3 grid gap-2 text-sm text-text-muted">
                <div><dt className="font-medium text-text-dark">Task</dt><dd>{form.title}</dd></div>
                <div><dt className="font-medium text-text-dark">Category</dt><dd>{selectedCategory?.name}</dd></div>
                <div><dt className="font-medium text-text-dark">Location</dt><dd>{form.location_landmark}</dd></div>
                <div>
                  <dt className="font-medium text-text-dark">Timing</dt>
                  <dd>{form.schedule_type === 'SCHEDULED' && form.scheduled_for ? `Scheduled for ${new Date(form.scheduled_for).toLocaleString()}` : 'ASAP'}</dd>
                </div>
                {form.deadline && <div><dt className="font-medium text-text-dark">Deadline</dt><dd>{new Date(form.deadline).toLocaleString()}</dd></div>}
                {form.location_latitude && form.location_longitude && (
                  <div><dt className="font-medium text-text-dark">Map pin</dt><dd>{form.location_latitude}, {form.location_longitude}</dd></div>
                )}
                <div><dt className="font-medium text-text-dark">Tasker preference</dt><dd>{getTaskGenderPreferenceLabel(form.preferred_tasker_gender)}</dd></div>
                <div><dt className="font-medium text-text-dark">Budget</dt><dd>KES {form.budget_min} - {form.budget_max}</dd></div>
                {form.task_photo && <div className="inline-flex items-center gap-2 text-text-dark"><Camera size={16} /> {form.task_photo.name}</div>}
              </dl>
            </div>
          </div>
        )}

        {error && <p className="mt-5 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <div className="mt-6 flex justify-between">
          <button type="button" onClick={() => setStep((current) => Math.max(1, current - 1))} disabled={step === 1} className="rounded-md border border-slate-300 px-4 py-2 font-medium disabled:opacity-50">
            Back
          </button>
          {step < 3 ? (
            <button type="button" onClick={nextStep} className="rounded-md bg-primary px-4 py-2 font-semibold text-white">
              Continue
            </button>
          ) : (
            <button type="submit" disabled={isSubmitLocked} className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-70">
              {isSubmitLocked ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
              {isSubmitLocked ? 'Posting...' : 'Post Task'}
            </button>
          )}
        </div>
      </form>
    </section>
  )
}
