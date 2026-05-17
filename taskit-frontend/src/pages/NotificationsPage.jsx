import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Bell,
  CheckCircle2,
  CreditCard,
  Loader2,
  MessageSquare,
  Star,
  TriangleAlert,
} from 'lucide-react'
import { getNotifications, markAllRead, markRead } from '../api/notifications.js'
import EmptyState from '../components/EmptyState.jsx'

const iconMap = {
  NEW_BID: Bell,
  BID_ACCEPTED: CheckCircle2,
  PAYMENT_RECEIVED: CreditCard,
  TASK_COMPLETED: CheckCircle2,
  NEW_MESSAGE: MessageSquare,
  REVIEW_RECEIVED: Star,
  TASK_DISPUTED: TriangleAlert,
}

function timeAgo(value) {
  const seconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  if (seconds < 60) return 'just now'
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} minutes ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hours ago`
  return `${Math.floor(hours / 24)} days ago`
}

export default function NotificationsPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const notificationsQuery = useQuery({
    queryKey: ['notifications'],
    queryFn: getNotifications,
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] })
    queryClient.invalidateQueries({ queryKey: ['notifications-unread-count'] })
  }

  const markReadMutation = useMutation({
    mutationFn: markRead,
    onSuccess: refresh,
  })

  const markAllReadMutation = useMutation({
    mutationFn: markAllRead,
    onSuccess: refresh,
  })

  const notifications = notificationsQuery.data?.results ?? []

  const handleClick = async (notification) => {
    if (!notification.is_read) {
      await markReadMutation.mutateAsync(notification.id)
    }
    if (notification.related_task) {
      navigate(`/tasks/${notification.related_task}`)
    }
  }

  return (
    <section className="mx-auto max-w-4xl">
      <div className="mb-5 flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Updates</p>
          <h1 className="mt-1 text-3xl font-bold text-primary">Notifications</h1>
        </div>
        <button
          type="button"
          onClick={() => markAllReadMutation.mutate()}
          className="rounded-md border border-slate-300 px-4 py-2 font-medium text-text-dark hover:bg-slate-50"
        >
          Mark all as read
        </button>
      </div>

      {notificationsQuery.isLoading && (
        <div className="flex justify-center py-12 text-primary">
          <Loader2 className="animate-spin" size={32} />
        </div>
      )}

      {!notificationsQuery.isLoading && notifications.length === 0 && (
        <EmptyState title="No notifications yet." />
      )}

      <div className="grid gap-3">
        {notifications.map((notification) => {
          const Icon = iconMap[notification.notification_type] ?? Bell
          return (
            <button
              type="button"
              key={notification.id}
              onClick={() => handleClick(notification)}
              className="flex gap-4 rounded-lg border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-primary/40 hover:shadow-md"
            >
              <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-primary">
                <Icon size={21} />
                {!notification.is_read && (
                  <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full bg-red-500" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                  <h2 className="font-semibold text-text-dark">{notification.title}</h2>
                  <span className="shrink-0 text-xs text-text-muted">{timeAgo(notification.created_at)}</span>
                </div>
                <p className="mt-1 text-sm text-text-muted">{notification.body}</p>
              </div>
            </button>
          )
        })}
      </div>
    </section>
  )
}
