import { useCallback, useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, CalendarClock, CheckCircle2, CreditCard, Loader2, MapPin, MessageCircle, Send, ShieldCheck, Smartphone, Star, UserRound, X } from 'lucide-react'
import { Circle, MapContainer, Marker, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png'
import markerIcon from 'leaflet/dist/images/marker-icon.png'
import markerShadow from 'leaflet/dist/images/marker-shadow.png'
import { acceptBid, getTask, getTaskBids, markTaskComplete, placeBid, rejectBid } from '../api/tasks.js'
import { confirmEscrowFunded, disputePayment, getPaymentStatus, initiatePayment, releasePayment } from '../api/payments.js'
import { activateTasker, getMe } from '../api/auth.js'
import { submitReview } from '../api/reviews.js'
import { getUserProfile } from '../api/reviews.js'
import { useAuthStore } from '../store/authStore.js'
import { getApiErrorMessage } from '../utils/apiError.js'
import { getTaskGenderPreferenceLabel, taskerMatchesPreference, USER_GENDER_LABELS } from '../constants/genderPreference.js'
import { getTaskPosition } from '../constants/landmarks.js'
import { getCurrentPosition, getGeofenceStatus, JKUAT_GEOFENCE_CENTER, JKUAT_SERVICE_RADIUS_METERS } from '../constants/geofence.js'
import { getAvailabilityClass, getAvailabilityLabel } from '../constants/availability.js'
import SOSButton from '../components/SOSButton.jsx'
import LocationShareButton from '../components/LocationShareButton.jsx'
import { SkeletonDetail } from '../components/Skeleton.jsx'

L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
})

function StatusBadge({ status }) {
  return (
    <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-primary">
      {status}
    </span>
  )
}

function EscrowWorkflowCard({
  acceptedBid,
  checkPaymentMutation,
  confirmFundedMutation,
  isClient,
  isPaymentPending,
  isTaskerAssigned,
  markCompleteMutation,
  onOpenPayment,
  paymentMutation,
  releaseMutation,
  task,
}) {
  const fundsHeld = ['ESCROWED', 'RELEASED'].includes(task.payment_status) || ['IN_PROGRESS', 'COMPLETED'].includes(task.status)
  const workStarted = ['IN_PROGRESS', 'COMPLETED'].includes(task.status)
  const taskerMarkedComplete = Boolean(task.tasker_completed_at) || task.status === 'COMPLETED'
  const paymentReleased = task.payment_status === 'RELEASED' || task.status === 'COMPLETED'
  const canMarkComplete = isTaskerAssigned && fundsHeld && !taskerMarkedComplete && !paymentReleased
  const canApproveRelease = isClient && taskerMarkedComplete && !paymentReleased
  const steps = [
    { label: 'Funds Held', complete: fundsHeld, active: task.status === 'ASSIGNED' },
    { label: 'Work Started', complete: workStarted, active: fundsHeld && !taskerMarkedComplete },
    { label: 'Task Complete', complete: taskerMarkedComplete, active: fundsHeld && taskerMarkedComplete },
    { label: 'Payment Released', complete: paymentReleased, active: task.status === 'COMPLETED' },
  ]

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="grid gap-4 border-b border-slate-100 p-5 lg:grid-cols-[1fr_auto] lg:items-center">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Escrow workflow</p>
          <h2 className="mt-1 text-xl font-bold text-primary">Payment and completion</h2>
          <p className="mt-1 text-sm text-text-muted">
            Funds stay in escrow until the tasker marks the work complete and the client approves release.
          </p>
        </div>
        {acceptedBid && (
          <div className="rounded-md bg-emerald-50 px-4 py-3 text-left lg:text-right">
            <p className="text-xs font-semibold uppercase tracking-wide text-primary">Escrow amount</p>
            <p className="text-lg font-black text-primary">KES {acceptedBid.amount}</p>
          </div>
        )}
      </div>

      <div className="grid gap-0 p-5 sm:grid-cols-4">
        {steps.map((step, index) => (
          <div key={step.label} className="relative grid gap-2 pb-5 sm:pb-0">
            {index < steps.length - 1 && (
              <span className={`absolute left-5 top-5 h-full w-0.5 sm:left-[calc(50%+20px)] sm:top-5 sm:h-0.5 sm:w-[calc(100%-40px)] ${steps[index + 1].complete ? 'bg-primary' : 'bg-slate-200'}`} />
            )}
            <div className="relative z-10 flex items-center gap-3 sm:flex-col sm:text-center">
              <span className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border-2 text-sm font-bold ${
                step.complete
                  ? 'border-primary bg-primary text-white'
                  : step.active
                    ? 'border-secondary bg-white text-secondary'
                    : 'border-slate-200 bg-white text-text-muted'
              }`}>
                {step.complete ? <CheckCircle2 size={18} /> : index + 1}
              </span>
              <span className={`text-sm font-semibold ${step.complete || step.active ? 'text-text-dark' : 'text-text-muted'}`}>{step.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-slate-100 p-5">
        {task.status === 'ASSIGNED' && isClient && (
          <div className="grid gap-3 text-sm sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <p className="font-semibold text-text-dark">{isPaymentPending ? 'Waiting for escrow sync' : 'Fund escrow to start work'}</p>
              <p className="text-text-muted">
                {isPaymentPending ? 'TaskiT is checking eConfirm automatically after the STK prompt.' : 'The tasker should only begin once funds are safely held.'}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {isPaymentPending ? (
                <>
                  <button type="button" onClick={() => checkPaymentMutation.mutate()} disabled={checkPaymentMutation.isPending} className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold text-text-dark disabled:opacity-60">
                    {checkPaymentMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                    Check
                  </button>
                  <button type="button" onClick={onOpenPayment} disabled={paymentMutation.isPending} className="rounded-md border border-slate-200 px-3 py-2 text-xs font-semibold text-text-dark disabled:opacity-60">
                    Retry STK
                  </button>
                  <button type="button" onClick={() => confirmFundedMutation.mutate()} disabled={confirmFundedMutation.isPending} className="rounded-md bg-primary px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">
                    I Already Paid
                  </button>
                </>
              ) : (
                <button type="button" onClick={onOpenPayment} className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-bold text-white">
                  <Smartphone size={16} />
                  Pay Now
                </button>
              )}
            </div>
          </div>
        )}

        {task.status === 'ASSIGNED' && isTaskerAssigned && !fundsHeld && (
          <div className="grid gap-3 text-sm sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <p className="font-semibold text-text-dark">Waiting for escrow funding</p>
              <p className="text-text-muted">If the client has paid, TaskiT will verify escrow before sending completion to the client.</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={() => checkPaymentMutation.mutate()} disabled={checkPaymentMutation.isPending} className="inline-flex w-fit items-center gap-2 rounded-md border border-primary px-4 py-2 font-semibold text-primary disabled:opacity-70">
                {checkPaymentMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <ShieldCheck size={18} />}
                Check Escrow
              </button>
              <button type="button" onClick={() => markCompleteMutation.mutate()} disabled={markCompleteMutation.isPending} className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-70">
                {markCompleteMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
                Mark Task Complete
              </button>
            </div>
          </div>
        )}

        {canMarkComplete && (
          <div className="grid gap-3 text-sm sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <p className="font-semibold text-text-dark">Escrow funded</p>
              <p className="text-text-muted">When you finish, notify the client so they can inspect and release escrow.</p>
            </div>
            <button type="button" onClick={() => markCompleteMutation.mutate()} disabled={markCompleteMutation.isPending} className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-70">
              {markCompleteMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
              Mark Task Complete
            </button>
          </div>
        )}

        {fundsHeld && isTaskerAssigned && taskerMarkedComplete && !paymentReleased && (
          <p className="rounded-md bg-blue-50 p-3 text-sm font-medium text-blue-800">
            Completion sent to the client. Escrow will release after client approval.
          </p>
        )}

        {fundsHeld && isClient && !taskerMarkedComplete && !paymentReleased && (
          <p className="rounded-md bg-amber-50 p-3 text-sm font-medium text-amber-800">
            Funds are held. Wait for the tasker to mark the task complete before approving release.
          </p>
        )}

        {canApproveRelease && (
          <div className="grid gap-3 text-sm sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <p className="font-semibold text-text-dark">Tasker says the work is complete</p>
              <p className="text-text-muted">Review the work, then approve release if everything is okay. Rating opens immediately after release.</p>
            </div>
            <button type="button" onClick={() => releaseMutation.mutate()} disabled={releaseMutation.isPending} className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-70">
              {releaseMutation.isPending ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />}
              Approve & Release
            </button>
          </div>
        )}

        {paymentReleased && (
          <p className="rounded-md bg-emerald-50 p-3 text-sm font-medium text-primary">
            Payment has been released. Reviews are now open for both sides.
          </p>
        )}
      </div>
    </div>
  )
}

export default function TaskDetailPage() {
  const { id } = useParams()
  const taskId = Number(id)
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const accessToken = useAuthStore((state) => state.accessToken)
  const refreshToken = useAuthStore((state) => state.refreshToken)
  const [bidForm, setBidForm] = useState({ amount: '', message: '' })
  const [reviewForm, setReviewForm] = useState({ rating: 5, comment: '' })
  const [disputeReason, setDisputeReason] = useState('')
  const [disputeDetails, setDisputeDetails] = useState('')
  const [isDisputeOpen, setIsDisputeOpen] = useState(false)
  const [selectedTaskerId, setSelectedTaskerId] = useState(null)
  const [error, setError] = useState('')
  const [reviewSubmitted, setReviewSubmitted] = useState(false)
  const [paymentPollingUntil, setPaymentPollingUntil] = useState(0)
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false)

  const taskQuery = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => getTask(taskId),
  })

  const task = taskQuery.data
  const isClient = task?.client_id === user?.id
  const isTasker = Boolean(user?.is_tasker_active && !isClient)
  const canBecomeTasker = Boolean(task && user && !isClient && !user.is_tasker_active)
  const canOpenChat = Boolean(
    task
      && user
      && ['ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'DISPUTED'].includes(task.status)
      && (isClient || task.assigned_tasker_id === user.id),
  )
  const matchesGenderPreference = taskerMatchesPreference(task?.preferred_tasker_gender, user?.gender)
  const canSeeBids = Boolean(task && (isClient || isTasker))
  const taskPosition = task ? getTaskPosition(task) : null

  const bidsQuery = useQuery({
    queryKey: ['task-bids', taskId],
    queryFn: () => getTaskBids(taskId),
    enabled: canSeeBids,
  })

  const bids = useMemo(
    () => bidsQuery.data ?? task?.bids ?? [],
    [bidsQuery.data, task?.bids],
  )
  const myBid = useMemo(
    () => bids.find((bid) => bid.tasker_id === user?.id),
    [bids, user?.id],
  )
  const acceptedBid = bids.find((bid) => bid.status === 'ACCEPTED')
  const isAssignedTasker = Boolean(task?.assigned_tasker_id === user?.id || myBid?.status === 'ACCEPTED')
  const taskerProfileQuery = useQuery({
    queryKey: ['tasker-mini-profile', selectedTaskerId],
    queryFn: () => getUserProfile(selectedTaskerId),
    enabled: Boolean(selectedTaskerId),
  })
  const shouldAutoPollPayment = Boolean(
    isClient
      && task?.status === 'ASSIGNED'
      && task?.payment_status === 'PENDING_PAYMENT',
  )

  const invalidateTask = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['task', taskId] })
    queryClient.invalidateQueries({ queryKey: ['task-bids', taskId] })
  }, [queryClient, taskId])

  useEffect(() => {
    if (!paymentPollingUntil) return undefined

    const timeout = window.setTimeout(
      () => setPaymentPollingUntil(0),
      Math.max(paymentPollingUntil - Date.now(), 0),
    )
    return () => window.clearTimeout(timeout)
  }, [paymentPollingUntil])

  const paymentStatusQuery = useQuery({
    queryKey: ['payment-status', taskId],
    queryFn: () => getPaymentStatus(taskId),
    enabled: Boolean(shouldAutoPollPayment || paymentPollingUntil),
    refetchInterval: () => (shouldAutoPollPayment || Date.now() < paymentPollingUntil ? 7000 : false),
  })

  useEffect(() => {
    if (!paymentStatusQuery.data) return
    if (['ESCROWED', 'RELEASED'].includes(paymentStatusQuery.data.status)) {
      window.queueMicrotask(() => setPaymentPollingUntil(0))
      toast.success('Escrow funded. The tasker has been notified.')
      invalidateTask()
    }
  }, [invalidateTask, paymentStatusQuery.data])

  const checkPaymentMutation = useMutation({
    mutationFn: () => getPaymentStatus(taskId),
    onSuccess: (data) => {
      if (['ESCROWED', 'RELEASED'].includes(data.status)) {
        toast.success('Escrow funded. Release button is ready.')
        invalidateTask()
      } else {
        toast(data.external_status ? `eConfirm status: ${data.external_status?.data?.status || data.external_status?.status || data.status}` : `Payment status: ${data.status}`)
      }
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not check payment status.')),
  })

  const confirmFundedMutation = useMutation({
    mutationFn: () => confirmEscrowFunded(taskId),
    onSuccess: () => {
      toast.success('Escrow confirmed. Release button is ready.')
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not confirm escrow funding.')),
  })

  const bidMutation = useMutation({
    mutationFn: async () => {
      try {
        const position = await getCurrentPosition()
        const status = getGeofenceStatus(position.latitude, position.longitude)
        if (status.level === 'blocked') throw new Error(status.message)
        if (status.level === 'warning') toast(status.message)
        return placeBid(taskId, {
          ...bidForm,
          actor_latitude: Number(position.latitude).toFixed(6),
          actor_longitude: Number(position.longitude).toFixed(6),
        })
      } catch (locationError) {
        if (locationError.message?.includes('TaskiT blocks')) throw locationError
        toast('Could not confirm GPS. You can continue, but TaskiT may review unusual activity.')
        return placeBid(taskId, bidForm)
      }
    },
    onSuccess: () => {
      toast.success('Bid placed')
      setBidForm({ amount: '', message: '' })
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not place bid.')),
  })

  const activateTaskerMutation = useMutation({
    mutationFn: activateTasker,
    onSuccess: async () => {
      const freshUser = await getMe()
      setAuth(freshUser, { access: accessToken, refresh: refreshToken })
      toast.success('Tasker mode activated. You can now bid on open tasks.')
      queryClient.invalidateQueries({ queryKey: ['task-bids', taskId] })
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not activate tasker mode.')),
  })

  const acceptMutation = useMutation({
    mutationFn: async (bidId) => {
      try {
        const position = await getCurrentPosition()
        const status = getGeofenceStatus(position.latitude, position.longitude)
        if (status.level === 'blocked') throw new Error(status.message)
        if (status.level === 'warning') toast(status.message)
        return acceptBid(taskId, bidId, {
          actor_latitude: Number(position.latitude).toFixed(6),
          actor_longitude: Number(position.longitude).toFixed(6),
        })
      } catch (locationError) {
        if (locationError.message?.includes('TaskiT blocks')) throw locationError
        toast('Could not confirm GPS. You can continue, but TaskiT may review unusual activity.')
        return acceptBid(taskId, bidId)
      }
    },
    onSuccess: () => {
      toast.success('Bid accepted')
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, mutationError.message || 'Could not accept bid.')),
  })

  const rejectMutation = useMutation({
    mutationFn: (bidId) => rejectBid(taskId, bidId),
    onSuccess: () => {
      toast.success('Bid rejected')
      invalidateTask()
    },
  })

  const paymentMutation = useMutation({
    mutationFn: () => initiatePayment(taskId),
    onSuccess: (data) => {
      toast.success(data.message || 'Payment initiated')
      setIsPaymentModalOpen(false)
      if (data.payment_url) {
        window.open(data.payment_url, '_blank', 'noopener,noreferrer')
      }
      setPaymentPollingUntil(Date.now() + 120000)
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not initiate payment.')),
  })

  const releaseMutation = useMutation({
    mutationFn: () => releasePayment(taskId),
    onSuccess: () => {
      toast.success('Payment released. You can now leave a review.')
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not release payment.')),
  })

  const markCompleteMutation = useMutation({
    mutationFn: () => markTaskComplete(taskId),
    onSuccess: (data) => {
      toast.success(data.message || 'Client notified')
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not mark task complete.')),
  })

  const reviewMutation = useMutation({
    mutationFn: () => submitReview(taskId, reviewForm),
    onSuccess: () => {
      toast.success('Review submitted')
      setReviewSubmitted(true)
      invalidateTask()
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, 'Could not submit review.')),
  })

  const disputeMutation = useMutation({
    mutationFn: () => disputePayment(taskId, { reason: disputeReason || 'Other', details: disputeDetails }),
    onSuccess: () => {
      toast.success("We've flagged this task. Our team will review and contact both parties.")
      setDisputeReason('')
      setDisputeDetails('')
      setIsDisputeOpen(false)
      invalidateTask()
    },
  })

  if (taskQuery.isLoading) {
    return (
      <section className="grid gap-4">
        <SkeletonDetail />
        <SkeletonDetail />
      </section>
    )
  }

  if (!task) {
    return <div className="rounded-lg bg-white p-6 text-center">Task not found.</div>
  }

  return (
    <section className="grid gap-6">
      <SOSButton />
      <LocationShareButton contextLabel={task ? `Task: ${task.title}` : 'Task safety check-in'} />
      {task.requires_home_visit && task.status === 'OPEN' && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 font-medium text-amber-800">
          ⚠️ This task requires access to the client's space. Only accept if you're comfortable with this.
        </div>
      )}
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={task.status} />
              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-text-muted">{task.category_detail?.name}</span>
            </div>
            <h1 className="mt-3 text-3xl font-bold text-primary">{task.title}</h1>
            <p className="mt-3 text-text-muted">{task.description}</p>
          </div>
          <div className="rounded-lg bg-emerald-50 p-4 text-right">
            <p className="text-sm text-text-muted">Budget</p>
            <p className="text-xl font-bold text-primary">KES {task.budget_min} - {task.budget_max}</p>
          </div>
        </div>

        <div className="mt-5 grid gap-3 border-t border-slate-100 pt-5 text-sm text-text-muted sm:grid-cols-2">
          <span className="inline-flex items-center gap-2"><MapPin size={16} /> {task.location_landmark}</span>
          <span>{task.location_notes || 'Exact location notes are hidden until assignment'}</span>
          {task.deadline && <span>Deadline: {new Date(task.deadline).toLocaleString()}</span>}
          {task.schedule_type === 'SCHEDULED' && task.scheduled_for && (
            <span className="inline-flex items-center gap-2 text-purple-700">
              <CalendarClock size={16} />
              Scheduled for {new Date(task.scheduled_for).toLocaleString()}
            </span>
          )}
          {task.requires_home_visit && <span className="inline-flex items-center gap-2 text-amber-700"><AlertTriangle size={16} /> Requires home visit</span>}
          <span className="inline-flex items-center gap-2 text-blue-700">
            <UserRound size={16} />
            Tasker preference: {getTaskGenderPreferenceLabel(task.preferred_tasker_gender)}
          </span>
        </div>
        {taskPosition && (
          <div className="mt-5 overflow-hidden rounded-lg border border-slate-200">
            <MapContainer center={taskPosition} zoom={16} className="h-72 w-full" scrollWheelZoom={false}>
              <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
              <Circle
                center={JKUAT_GEOFENCE_CENTER}
                radius={JKUAT_SERVICE_RADIUS_METERS}
                pathOptions={{ color: '#2563eb', fillColor: '#60a5fa', fillOpacity: 0.08, weight: 2 }}
              />
              <Marker position={taskPosition} />
            </MapContainer>
          </div>
        )}
        {!task.location_latitude && !task.location_longitude && (
          <p className="mt-2 text-xs text-text-muted">
            Exact map pin is hidden until assignment. This map is centered on the selected campus landmark.
          </p>
        )}
      </div>

      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

      {canOpenChat && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-5 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="inline-flex items-center gap-2 text-lg font-semibold text-primary">
                <MessageCircle size={20} />
                Task chat is ready
              </h2>
              <p className="mt-1 text-sm text-emerald-800">
                Coordinate pickup details, timing, and handoff notes with the assigned student.
              </p>
            </div>
            <Link
              to={`/chat/${task.id}`}
              className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white"
            >
              <MessageCircle size={18} />
              Open Chat
            </Link>
          </div>
        </div>
      )}

      {isClient && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-text-dark">Bids</h2>
          {bids.length === 0 && <p className="mt-3 text-text-muted">No bids yet.</p>}
          <div className="mt-4 grid gap-3">
            {bids.map((bid) => (
              <div key={bid.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <button type="button" onClick={() => setSelectedTaskerId(bid.tasker_id)} className="font-semibold text-primary hover:underline">
                      {bid.tasker}
                    </button>
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${getAvailabilityClass(bid.tasker_availability_status)}`}>
                        {getAvailabilityLabel(bid.tasker_availability_status)}
                      </span>
                      {bid.tasker_availability_note && <span className="text-xs text-text-muted">{bid.tasker_availability_note}</span>}
                    </div>
                    <p className="mt-2 text-text-muted">{bid.message}</p>
                  </div>
                  <div className="text-left sm:text-right">
                    <p className="font-bold text-primary">KES {bid.amount}</p>
                    <p className="text-sm text-text-muted">{bid.status}</p>
                  </div>
                </div>
                {task.status === 'OPEN' && (
                  <div className="mt-3 flex gap-2">
                    <button type="button" onClick={() => acceptMutation.mutate(bid.id)} className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white">Accept Bid</button>
                    <button type="button" onClick={() => rejectMutation.mutate(bid.id)} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium">Reject</button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {['ASSIGNED', 'IN_PROGRESS', 'COMPLETED'].includes(task.status) && (acceptedBid || isClient || isAssignedTasker) && (
        <EscrowWorkflowCard
          acceptedBid={acceptedBid}
          checkPaymentMutation={checkPaymentMutation}
          confirmFundedMutation={confirmFundedMutation}
          isClient={isClient}
          isPaymentPending={task.payment_status === 'PENDING_PAYMENT'}
          isTaskerAssigned={isAssignedTasker}
          markCompleteMutation={markCompleteMutation}
          onOpenPayment={() => setIsPaymentModalOpen(true)}
          paymentMutation={paymentMutation}
          releaseMutation={releaseMutation}
          task={task}
        />
      )}

      {isTasker && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-text-dark">Your bid</h2>
          <div className={`mt-3 rounded-md p-3 text-sm ${matchesGenderPreference ? 'bg-emerald-50 text-primary' : 'bg-amber-50 text-amber-800'}`}>
            Client preference: <span className="font-semibold">{getTaskGenderPreferenceLabel(task.preferred_tasker_gender)}</span>.
            {' '}Your profile gender: <span className="font-semibold">{USER_GENDER_LABELS[user?.gender] ?? 'Not specified'}</span>.
            {!matchesGenderPreference && ' You can still bid, but the client has stated a different safety preference.'}
          </div>
          {task.schedule_type === 'SCHEDULED' && task.scheduled_for && (
            <div className="mt-3 rounded-md bg-purple-50 p-3 text-sm font-medium text-purple-800">
              This task is scheduled for {new Date(task.scheduled_for).toLocaleString()}. Only bid if you can be available then.
            </div>
          )}
          {myBid ? (
            <p className="mt-3 text-text-muted">You bid KES {myBid.amount}. Current status: <span className="font-semibold text-text-dark">{myBid.status}</span></p>
          ) : (
            <form
              onSubmit={(event) => {
                event.preventDefault()
                bidMutation.mutate()
              }}
              className="mt-4 grid gap-3"
            >
              <input type="number" min="50" placeholder="Bid amount" value={bidForm.amount} onChange={(event) => setBidForm((current) => ({ ...current, amount: event.target.value }))} className="rounded-md border border-slate-300 px-3 py-2" />
              <textarea placeholder="Tell the client why you're a good fit" value={bidForm.message} onChange={(event) => setBidForm((current) => ({ ...current, message: event.target.value }))} rows={4} className="rounded-md border border-slate-300 px-3 py-2" />
              <button type="submit" disabled={bidMutation.isPending || task.status !== 'OPEN'} className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-60">
                <Send size={18} />
                Place Bid
              </button>
            </form>
          )}
        </div>
      )}

      {canBecomeTasker && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-amber-950">Want to bid on this task?</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-amber-800">
            You are viewing this as a student account with Tasker Mode off. Activate Tasker Mode to place bids on open tasks
            around campus. This only lets you receive and bid for tasks; you can still post tasks normally.
          </p>
          <button
            type="button"
            onClick={() => activateTaskerMutation.mutate()}
            disabled={activateTaskerMutation.isPending}
            className="mt-4 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-70"
          >
            {activateTaskerMutation.isPending && <Loader2 size={18} className="animate-spin" />}
            Activate Tasker Mode
          </button>
        </div>
      )}

      {task.status === 'COMPLETED' && (isClient || task.assigned_tasker_id === user?.id) && !reviewSubmitted && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-text-dark">{isClient ? 'Rate the Tasker' : 'Rate the Client'}</h2>
          <p className="mt-1 text-sm text-text-muted">
            {isClient ? 'Share how the tasker handled the job.' : 'Share how the client handled the task.'}
          </p>
          <div className="mt-4 flex gap-1">
            {[1, 2, 3, 4, 5].map((rating) => (
              <button key={rating} type="button" onClick={() => setReviewForm((current) => ({ ...current, rating }))} aria-label={`${rating} star rating`}>
                <Star size={24} className={rating <= reviewForm.rating ? 'fill-secondary text-secondary' : 'text-slate-300'} />
              </button>
            ))}
          </div>
          <textarea value={reviewForm.comment} onChange={(event) => setReviewForm((current) => ({ ...current, comment: event.target.value }))} maxLength={500} rows={4} placeholder="Write a short review" className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2" />
          <button type="button" onClick={() => reviewMutation.mutate()} className="mt-3 rounded-md bg-primary px-4 py-2 font-semibold text-white">Submit Review</button>
        </div>
      )}

      {task.status === 'IN_PROGRESS' && isClient && task.tasker_completed_at && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-amber-950">Rate the Tasker</h2>
          <p className="mt-2 text-sm text-amber-800">
            Approve and release escrow first, then the rating form will open here.
          </p>
        </div>
      )}

      {task.status === 'IN_PROGRESS' && (isClient || task.assigned_tasker_id === user?.id) && (
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-text-dark">Report / Dispute</h2>
          <button type="button" onClick={() => setIsDisputeOpen(true)} className="mt-3 rounded-md border border-red-200 px-4 py-2 font-semibold text-red-700">Report / Dispute</button>
        </div>
      )}

      {selectedTaskerId && (
        <div className="fixed inset-0 z-40 bg-black/30" onClick={() => setSelectedTaskerId(null)}>
          <aside className="ml-auto h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl" onClick={(event) => event.stopPropagation()}>
            <button className="mb-4 text-sm font-medium text-text-muted" onClick={() => setSelectedTaskerId(null)}>Close</button>
            {taskerProfileQuery.isLoading ? <Loader2 className="animate-spin text-primary" /> : (
              <div className="grid gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary text-xl font-bold text-white">
                    {taskerProfileQuery.data?.profile_photo ? <img src={taskerProfileQuery.data.profile_photo} alt="" className="h-full w-full rounded-full object-cover" /> : taskerProfileQuery.data?.full_name?.slice(0, 2)}
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-primary">{taskerProfileQuery.data?.full_name}</h2>
                    <p className="text-sm text-text-muted">{taskerProfileQuery.data?.completed_tasks_count} completed tasks</p>
                  </div>
                </div>
                <p className="text-sm text-text-muted">
                  {taskerProfileQuery.data?.department || 'Department not set'}
                  {taskerProfileQuery.data?.year_of_study ? ` - Year ${taskerProfileQuery.data.year_of_study}` : ''}
                </p>
                <p className="text-sm text-text-muted">{taskerProfileQuery.data?.bio || 'No bio yet.'}</p>
                <p className="font-semibold">Rating: {taskerProfileQuery.data?.average_rating} / 5</p>
                <div className="flex flex-wrap gap-2">
                  {taskerProfileQuery.data?.badges?.map((badge) => <span key={badge} className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-primary">{badge}</span>)}
                </div>
                <div>
                  <h3 className="font-semibold text-text-dark">Completed work</h3>
                  <div className="mt-2 grid gap-2">
                    {(taskerProfileQuery.data?.completed_task_history ?? []).slice(0, 3).map((historyItem) => (
                      <Link key={historyItem.id} to={`/tasks/${historyItem.id}`} className="rounded-md bg-slate-50 p-3 text-sm text-text-muted hover:bg-emerald-50">
                        <span className="block font-semibold text-text-dark">{historyItem.title}</span>
                        <span>{historyItem.category} task for {historyItem.client_name}</span>
                      </Link>
                    ))}
                    {(taskerProfileQuery.data?.completed_task_history ?? []).length === 0 && (
                      <p className="rounded-md bg-slate-50 p-3 text-sm text-text-muted">No completed work yet.</p>
                    )}
                  </div>
                </div>
                <div>
                  <h3 className="font-semibold text-text-dark">Recent reviews</h3>
                  <div className="mt-2 grid gap-2">
                    {(taskerProfileQuery.data?.recent_reviews ?? []).slice(0, 3).map((review) => (
                      <p key={review.id} className="rounded-md bg-slate-50 p-3 text-sm text-text-muted">{review.comment}</p>
                    ))}
                  </div>
                </div>
                <a href={`/profile/${selectedTaskerId}`} className="rounded-md bg-primary px-4 py-2 text-center font-semibold text-white">View Full Profile</a>
              </div>
            )}
          </aside>
        </div>
      )}

      {isDisputeOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-xl font-semibold text-text-dark">Report / Dispute</h2>
            <label className="mt-4 grid gap-1.5">
              <span className="text-sm font-medium">Choose reason</span>
              <select value={disputeReason} onChange={(event) => setDisputeReason(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
                <option value="">Choose reason</option>
                <option>Tasker didn't show up</option>
                <option>Client refuses to pay</option>
                <option>Inappropriate behaviour</option>
                <option>Safety concern</option>
                <option>Other</option>
              </select>
            </label>
            <textarea value={disputeDetails} onChange={(event) => setDisputeDetails(event.target.value)} placeholder="Add details" rows={4} className="mt-3 w-full rounded-md border border-slate-300 px-3 py-2" />
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setIsDisputeOpen(false)} className="rounded-md border border-slate-300 px-4 py-2 font-medium">Cancel</button>
              <button type="button" onClick={() => disputeMutation.mutate()} className="rounded-md bg-red-600 px-4 py-2 font-semibold text-white">Submit Report</button>
            </div>
          </div>
        </div>
      )}

      {isPaymentModalOpen && acceptedBid && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md overflow-hidden rounded-xl bg-white shadow-2xl">
            <div className="relative bg-gradient-to-br from-[#073b1f] via-[#0f8f45] to-[#b6dc32] p-5 text-white">
              <button
                type="button"
                onClick={() => setIsPaymentModalOpen(false)}
                className="absolute right-3 top-3 flex h-8 w-8 items-center justify-center rounded-full bg-white/15 hover:bg-white/25"
                aria-label="Close payment"
              >
                <X size={18} />
              </button>
              <div className="flex items-center gap-3">
                <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/20">
                  <Smartphone size={24} />
                </span>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-white/75">M-Pesa STK</p>
                  <h2 className="text-2xl font-black">Secure escrow</h2>
                </div>
              </div>
              <div className="mt-6 rounded-lg bg-white/15 p-4">
                <p className="text-sm text-white/80">Amount to escrow</p>
                <p className="mt-1 text-3xl font-black">KES {acceptedBid.amount}</p>
                <p className="mt-1 text-xs text-white/75">TaskiT fees are tracked separately for post-paid billing.</p>
              </div>
            </div>
            <div className="grid gap-4 p-5">
              <div className="rounded-lg border border-slate-200 p-3 text-sm">
                <p className="font-semibold text-text-dark">{task.title}</p>
                <p className="mt-1 text-text-muted">Tasker: {acceptedBid.tasker}</p>
              </div>
              <div className="grid gap-2 text-sm text-text-muted">
                <p className="inline-flex items-center gap-2"><ShieldCheck size={16} className="text-primary" /> eConfirm holds the money until you approve completion.</p>
                <p className="inline-flex items-center gap-2"><CreditCard size={16} className="text-primary" /> STK push uses your profile phone number.</p>
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setIsPaymentModalOpen(false)} className="rounded-md border border-slate-200 px-4 py-2 text-sm font-semibold text-text-dark">Cancel</button>
                <button type="button" onClick={() => paymentMutation.mutate()} disabled={paymentMutation.isPending} className="inline-flex items-center gap-2 rounded-md bg-[#0b7f3a] px-4 py-2 text-sm font-bold text-white disabled:opacity-60">
                  {paymentMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Smartphone size={16} />}
                  Send STK Push
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <Link to="/tasks" className="text-sm font-medium text-primary">Back to task feed</Link>
    </section>
  )
}
