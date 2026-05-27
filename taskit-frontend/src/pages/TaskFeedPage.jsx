import { useMemo, useState } from 'react'
import { useInfiniteQuery, useQuery } from '@tanstack/react-query'
import { Grid2X2, ListFilter, Loader2, Map as MapIcon } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Circle, MapContainer, Marker, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import TaskCard from '../components/TaskCard.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { SkeletonCard } from '../components/Skeleton.jsx'
import { getCategories, getTasks } from '../api/tasks.js'
import { getTaskPosition, JKUAT_CENTER, LANDMARKS } from '../constants/landmarks.js'
import { JKUAT_GEOFENCE_CENTER, JKUAT_SERVICE_RADIUS_METERS } from '../constants/geofence.js'
import { GENDER_PREFERENCES } from '../constants/genderPreference.js'

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

const defaultFilters = {
  category: '',
  location_landmark: '',
  budget_min: 0,
  budget_max: 5000,
  preferred_tasker_gender: '',
  schedule_type: '',
}

export default function TaskFeedPage() {
  const [filters, setFilters] = useState(defaultFilters)
  const [viewMode, setViewMode] = useState('list')

  const queryFilters = useMemo(
    () => ({
      ...(filters.category && { category: filters.category }),
      ...(filters.location_landmark && { location_landmark: filters.location_landmark }),
      ...(filters.preferred_tasker_gender && { preferred_tasker_gender: filters.preferred_tasker_gender }),
      ...(filters.schedule_type && { schedule_type: filters.schedule_type }),
      budget_min: filters.budget_min,
      budget_max: filters.budget_max,
    }),
    [filters],
  )

  const categoriesQuery = useQuery({
    queryKey: ['task-categories'],
    queryFn: getCategories,
  })

  const tasksQuery = useInfiniteQuery({
    queryKey: ['tasks', queryFilters],
    queryFn: ({ pageParam = 1 }) => getTasks({ ...queryFilters, page: pageParam }),
    getNextPageParam: (lastPage, pages) => (lastPage.next ? pages.length + 1 : undefined),
    initialPageParam: 1,
  })

  const tasks = tasksQuery.data?.pages.flatMap((page) => page.results ?? []) ?? []

  const updateFilter = (key, value) => {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  return (
    <section className="grid gap-6">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-secondary">
              <ListFilter size={16} />
              Find tasks
            </p>
            <h1 className="mt-2 text-3xl font-bold text-primary">Open campus tasks</h1>
          </div>

          <div className="flex rounded-md border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              onClick={() => setViewMode('list')}
              className={`inline-flex items-center gap-2 rounded px-3 py-2 text-sm font-medium ${viewMode === 'list' ? 'bg-primary text-white' : 'text-text-muted'}`}
            >
              <Grid2X2 size={16} />
              List
            </button>
            <button
              type="button"
              onClick={() => setViewMode('map')}
              className={`inline-flex items-center gap-2 rounded px-3 py-2 text-sm font-medium ${viewMode === 'map' ? 'bg-primary text-white' : 'text-text-muted'}`}
            >
              <MapIcon size={16} />
              Map
            </button>
          </div>
        </div>

        <div className="mt-5 grid gap-4 md:grid-cols-5">
          <label className="grid gap-1.5">
            <span className="text-sm font-medium">Category</span>
            <select value={filters.category} onChange={(event) => updateFilter('category', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
              <option value="">All categories</option>
              {(categoriesQuery.data ?? []).map((category) => (
                <option key={category.slug} value={category.slug}>{category.name}</option>
              ))}
            </select>
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium">Location</span>
            <select value={filters.location_landmark} onChange={(event) => updateFilter('location_landmark', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
              <option value="">All locations</option>
              {LANDMARKS.map((landmark) => (
                <option key={landmark.name} value={landmark.name}>{landmark.name}</option>
              ))}
            </select>
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium">Tasker preference</span>
            <select value={filters.preferred_tasker_gender} onChange={(event) => updateFilter('preferred_tasker_gender', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
              {GENDER_PREFERENCES.map((preference) => (
                <option key={preference.value || 'all'} value={preference.value}>{preference.label}</option>
              ))}
            </select>
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium">Timing</span>
            <select value={filters.schedule_type} onChange={(event) => updateFilter('schedule_type', event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
              <option value="">ASAP and scheduled</option>
              <option value="ASAP">ASAP only</option>
              <option value="SCHEDULED">Scheduled only</option>
            </select>
          </label>

          <label className="grid gap-1.5 md:col-span-1">
            <span className="text-sm font-medium">Budget range: KES {filters.budget_min} - {filters.budget_max}</span>
            <div className="grid gap-2 sm:grid-cols-2">
              <input type="range" min="0" max="5000" step="50" value={filters.budget_min} onChange={(event) => updateFilter('budget_min', Number(event.target.value))} />
              <input type="range" min="0" max="5000" step="50" value={filters.budget_max} onChange={(event) => updateFilter('budget_max', Number(event.target.value))} />
            </div>
          </label>
        </div>

        <button type="button" onClick={() => setFilters(defaultFilters)} className="mt-4 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-text-dark hover:bg-slate-50">
          Clear filters
        </button>
      </div>

      {tasksQuery.isLoading && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((item) => <SkeletonCard key={item} />)}
        </div>
      )}

      {!tasksQuery.isLoading && tasks.length === 0 && (
        <EmptyState title="No tasks found. Be the first to post one!" actionLabel="Post a Task" actionTo="/tasks/new" />
      )}

      {viewMode === 'list' && tasks.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tasks.map((task) => <TaskCard key={task.id} task={task} />)}
        </div>
      )}

      {viewMode === 'map' && tasks.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
          <MapContainer center={JKUAT_CENTER} zoom={12} className="h-[560px] w-full">
            <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <Circle
              center={JKUAT_GEOFENCE_CENTER}
              radius={JKUAT_SERVICE_RADIUS_METERS}
              pathOptions={{ color: '#2563eb', fillColor: '#60a5fa', fillOpacity: 0.08, weight: 2 }}
            />
            {tasks.map((task) => (
              <Marker key={task.id} position={getTaskPosition(task)}>
                <Popup>
                  <div className="grid gap-2">
                    <strong>{task.title}</strong>
                    <span>KES {task.budget_min} - {task.budget_max}</span>
                    <Link to={`/tasks/${task.id}`} className="rounded bg-primary px-3 py-1 text-center text-white">View Task</Link>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>
      )}

      {tasksQuery.hasNextPage && (
        <button
          type="button"
          onClick={() => tasksQuery.fetchNextPage()}
          disabled={tasksQuery.isFetchingNextPage}
          className="mx-auto inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 font-medium text-text-dark"
        >
          {tasksQuery.isFetchingNextPage && <Loader2 size={18} className="animate-spin" />}
          Load more
        </button>
      )}
    </section>
  )
}
