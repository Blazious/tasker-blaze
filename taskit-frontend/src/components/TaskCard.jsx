import { Link } from 'react-router-dom'
import { CalendarClock, Clock, Home, MapPin, MessageSquare, UserRound } from 'lucide-react'
import { getCategoryIcon } from '../constants/taskCategories.js'
import { getTaskGenderPreferenceLabel } from '../constants/genderPreference.js'

function timeSince(dateValue) {
  const seconds = Math.max(1, Math.floor((Date.now() - new Date(dateValue).getTime()) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function TaskCard({ task }) {
  const category = task.category_detail
  const Icon = getCategoryIcon(category?.slug)

  return (
    <Link
      to={`/tasks/${task.id}`}
      className="group rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
    >
      <div className="flex items-start gap-4">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-primary text-white">
          <Icon size={22} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-primary">
              {category?.name ?? 'Task'}
            </span>
            {task.requires_home_visit && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-700">
                <Home size={13} />
                Home visit
              </span>
            )}
            {task.preferred_tasker_gender && task.preferred_tasker_gender !== 'ANY' && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-xs font-semibold text-blue-700">
                <UserRound size={13} />
                {getTaskGenderPreferenceLabel(task.preferred_tasker_gender)}
              </span>
            )}
            {task.schedule_type === 'SCHEDULED' && task.scheduled_for && (
              <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2 py-0.5 text-xs font-semibold text-purple-700">
                <CalendarClock size={13} />
                Scheduled
              </span>
            )}
          </div>
          <h2 className="mt-2 line-clamp-2 text-lg font-semibold text-text-dark group-hover:text-primary">
            {task.title}
          </h2>
          <div className="mt-3 grid gap-2 text-sm text-text-muted">
            <span className="inline-flex items-center gap-1.5">
              <MapPin size={15} />
              {task.location_landmark}
            </span>
            <span className="font-semibold text-text-dark">
              KES {task.budget_min} - {task.budget_max}
            </span>
            {task.schedule_type === 'SCHEDULED' && task.scheduled_for && (
              <span className="inline-flex items-center gap-1.5 text-purple-700">
                <CalendarClock size={15} />
                {new Date(task.scheduled_for).toLocaleString()}
              </span>
            )}
          </div>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between border-t border-slate-100 pt-3 text-sm text-text-muted">
        <span className="inline-flex items-center gap-1.5">
          <Clock size={15} />
          {timeSince(task.created_at)}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <MessageSquare size={15} />
          {task.bid_count ?? task.bids?.length ?? 0} bids
        </span>
      </div>
    </Link>
  )
}
