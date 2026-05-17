import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { BriefcaseBusiness, CheckCircle2, HandCoins, Loader2, Plus, Search, Star, Wifi } from 'lucide-react'
import { activateTasker, getMe, getStats, updateAvailability } from '../api/auth.js'
import { useAuthStore } from '../store/authStore.js'
import { CAMPUS_BACKGROUNDS } from '../constants/campusImages.js'
import LocationShareButton from '../components/LocationShareButton.jsx'
import { AVAILABILITY_OPTIONS, getAvailabilityClass, getAvailabilityLabel } from '../constants/availability.js'

const statCards = [
  { key: 'tasks_posted', label: 'Tasks Posted', icon: BriefcaseBusiness },
  { key: 'tasks_completed', label: 'Tasks Completed', icon: CheckCircle2 },
  { key: 'active_bids', label: 'Active Bids', icon: Star },
  { key: 'total_earned', label: 'Total Earned', icon: HandCoins, prefix: 'KES ' },
]

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const accessToken = useAuthStore((state) => state.accessToken)
  const refreshToken = useAuthStore((state) => state.refreshToken)
  const [dashboardImage, setDashboardImage] = useState(CAMPUS_BACKGROUNDS.walkway.src)
  const [availabilityNote, setAvailabilityNote] = useState(user?.availability_note ?? '')

  const statsQuery = useQuery({
    queryKey: ['auth-stats'],
    queryFn: getStats,
  })

  const activateMutation = useMutation({
    mutationFn: activateTasker,
    onSuccess: async () => {
      const freshUser = await getMe()
      setAuth(freshUser, { access: accessToken, refresh: refreshToken })
      queryClient.invalidateQueries({ queryKey: ['auth-stats'] })
      toast.success('Tasker mode activated')
    },
  })

  const availabilityMutation = useMutation({
    mutationFn: updateAvailability,
    onSuccess: (freshUser) => {
      setAuth(freshUser, { access: accessToken, refresh: refreshToken })
      setAvailabilityNote(freshUser.availability_note ?? '')
      toast.success('Availability updated')
    },
  })

  const stats = statsQuery.data ?? {
    tasks_posted: 0,
    tasks_completed: 0,
    active_bids: 0,
    total_earned: '0.00',
  }

  return (
    <section className="grid gap-6">
      <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-[#071c15] p-6 shadow-sm">
        <img
          src={dashboardImage}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-90"
          onError={() => {
            if (dashboardImage !== CAMPUS_BACKGROUNDS.walkway.fallback) {
              setDashboardImage(CAMPUS_BACKGROUNDS.walkway.fallback)
            }
          }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(3,13,9,0.78),rgba(3,13,9,0.42))]" />
        <div className="relative">
        <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Dashboard · Ingine Mwecheche</p>
        <h1 className="mt-2 text-3xl font-black text-white">
          Welcome back, {user?.full_name ?? 'student'}!
        </h1>
        <p className="mt-2 max-w-2xl text-slate-200">Here is your TaskiT campus work snapshot. Campus errands, but with that mwecheche touch.</p>

        <div className="mt-5 flex flex-wrap gap-3">
          <Link to="/tasks/new" className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-medium text-white">
            <Plus size={18} />
            Post a Task
          </Link>
          <Link to="/tasks" className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 font-medium text-text-dark hover:bg-slate-50">
            <Search size={18} />
            Browse Tasks
          </Link>
          <Link to="/profile/edit" className="inline-flex items-center gap-2 rounded-md border border-white/30 bg-white/10 px-4 py-2 font-medium text-white backdrop-blur hover:bg-white/20">
            Edit Profile
          </Link>
        </div>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.key} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-text-muted">{card.label}</span>
                <Icon size={20} className="text-primary" />
              </div>
              <p className="mt-3 text-2xl font-bold text-text-dark">
                {statsQuery.isLoading ? '...' : `${card.prefix ?? ''}${stats[card.key]}`}
              </p>
            </div>
          )
        })}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-text-dark">Become a Tasker</h2>
            {user?.is_tasker_active ? (
              <p className="mt-2 text-text-muted">You can receive tasks and place bids around campus.</p>
            ) : (
              <p className="mt-2 text-text-muted">
                Taskers help fellow students with errands, deliveries, printing, cleaning, tutoring, and more.
              </p>
            )}
          </div>

          {user?.is_tasker_active ? (
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-primary">
              Tasker Mode Active
            </span>
          ) : (
            <button
              type="button"
              onClick={() => activateMutation.mutate()}
              disabled={activateMutation.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-md bg-secondary px-4 py-2 font-semibold text-white disabled:opacity-70"
            >
              {activateMutation.isPending && <Loader2 size={18} className="animate-spin" />}
              Activate Tasker Mode
            </button>
          )}
        </div>
      </div>

      {user?.is_tasker_active && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h2 className="inline-flex items-center gap-2 text-xl font-semibold text-text-dark">
                <Wifi size={20} className="text-primary" />
                Tasker Availability
              </h2>
              <p className="mt-2 text-text-muted">
                Let clients know if you are ready for errands, busy, or taking a break.
              </p>
              <span className={`mt-3 inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${getAvailabilityClass(user?.availability_status)}`}>
                {getAvailabilityLabel(user?.availability_status)}
              </span>
            </div>
            <div className="grid w-full gap-3 lg:max-w-md">
              <div className="grid grid-cols-3 gap-2">
                {AVAILABILITY_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => availabilityMutation.mutate({ availability_status: option.value, availability_note: availabilityNote })}
                    disabled={availabilityMutation.isPending}
                    className={`rounded-md border px-3 py-2 text-sm font-semibold ${user?.availability_status === option.value ? getAvailabilityClass(option.value) : 'border-slate-200 bg-white text-text-muted'}`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
              <label className="grid gap-1.5">
                <span className="text-sm font-medium text-text-dark">Availability note</span>
                <input
                  value={availabilityNote}
                  onChange={(event) => setAvailabilityNote(event.target.value)}
                  onBlur={() => availabilityMutation.mutate({ availability_note: availabilityNote })}
                  maxLength={255}
                  placeholder="Example: Free after 4pm, near hostels"
                  className="rounded-md border border-slate-300 px-3 py-2"
                />
              </label>
            </div>
          </div>
        </div>
      )}

      <LocationShareButton contextLabel="Dashboard safety check-in" />
    </section>
  )
}
