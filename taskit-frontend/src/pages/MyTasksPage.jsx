import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { Archive, CheckCircle2, Clock3, Loader2 } from 'lucide-react'
import { forgetTask, getMyAssignments, getMyTasks } from '../api/tasks.js'

const statusStyles = {
  OPEN: 'bg-blue-100 text-blue-700',
  ASSIGNED: 'bg-orange-100 text-orange-700',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-emerald-100 text-primary',
  CANCELLED: 'bg-slate-100 text-slate-700',
  DISPUTED: 'bg-red-100 text-red-700',
}

function getTaskApprovalState(task, listType) {
  const taskerMarkedComplete = Boolean(task.tasker_completed_at)
  const paymentReleased = task.payment_status === 'RELEASED' || task.status === 'COMPLETED'
  const awaitingApproval = task.status === 'IN_PROGRESS' && taskerMarkedComplete && !paymentReleased

  if (!awaitingApproval) return null

  if (listType === 'posted') {
    return {
      label: 'Awaiting your approval',
      message: 'The tasker marked this complete. Review the work and release escrow.',
      Icon: CheckCircle2,
      tone: 'border-primary/30 bg-emerald-50 text-primary',
    }
  }

  return {
    label: 'Waiting for client approval',
    message: 'Completion was sent to the client. Escrow releases after they approve.',
    Icon: Clock3,
    tone: 'border-amber-200 bg-amber-50 text-amber-700',
  }
}

function TaskList({ tasks, listType, onForget, forgettingId }) {
  const navigate = useNavigate()
  if (!tasks.length) return <p className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-text-muted">No tasks here yet.</p>
  return (
    <div className="grid gap-3">
      {tasks.map((task) => {
        const approvalState = getTaskApprovalState(task, listType)
        const ApprovalIcon = approvalState?.Icon

        return (
          <div
            key={task.id}
            role="link"
            tabIndex={0}
            onClick={() => navigate(`/tasks/${task.id}`)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                navigate(`/tasks/${task.id}`)
              }
            }}
            className={`cursor-pointer rounded-lg border bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary/30 ${approvalState ? 'border-primary/40 ring-1 ring-primary/10' : 'border-slate-200'}`}
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="font-semibold text-text-dark">{task.title}</p>
                <p className="text-sm text-text-muted">{task.location_landmark} - KES {task.budget_min} to {task.budget_max}</p>
                {approvalState && (
                  <div className={`mt-3 flex max-w-xl items-start gap-2 rounded-md border px-3 py-2 text-sm ${approvalState.tone}`}>
                    {ApprovalIcon && <ApprovalIcon size={18} className="mt-0.5 shrink-0" />}
                    <div>
                      <p className="font-semibold">{approvalState.label}</p>
                      <p className="text-current/80">{approvalState.message}</p>
                    </div>
                  </div>
                )}
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                <span className={`w-fit rounded-full px-3 py-1 text-sm font-semibold ${approvalState && listType === 'posted' ? 'bg-emerald-100 text-primary' : statusStyles[task.status] ?? 'bg-slate-100 text-slate-700'}`}>
                  {approvalState && listType === 'posted' ? 'NEEDS APPROVAL' : task.status}
                </span>
                {approvalState && listType === 'posted' && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation()
                      navigate(`/tasks/${task.id}`)
                    }}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-sm font-semibold text-white"
                  >
                    <CheckCircle2 size={15} />
                    Review & Release
                  </button>
                )}
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation()
                    onForget(task.id)
                  }}
                  disabled={forgettingId === task.id}
                  className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 px-3 py-1.5 text-sm font-semibold text-text-muted hover:border-primary hover:text-primary disabled:opacity-60"
                >
                  {forgettingId === task.id ? <Loader2 size={15} className="animate-spin" /> : <Archive size={15} />}
                  Forget
                </button>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function sortTasksForList(tasks, listType) {
  return [...tasks].sort((a, b) => {
    const aNeedsAttention = getTaskApprovalState(a, listType) ? 1 : 0
    const bNeedsAttention = getTaskApprovalState(b, listType) ? 1 : 0
    if (aNeedsAttention !== bNeedsAttention) return bNeedsAttention - aNeedsAttention
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  })
}

export default function MyTasksPage() {
  const [tab, setTab] = useState('posted')
  const queryClient = useQueryClient()
  const postedQuery = useQuery({ queryKey: ['my-tasks'], queryFn: getMyTasks })
  const assignmentsQuery = useQuery({ queryKey: ['my-assignments'], queryFn: getMyAssignments })
  const forgetMutation = useMutation({
    mutationFn: forgetTask,
    onSuccess: () => {
      toast.success('Task hidden from this list')
      queryClient.invalidateQueries({ queryKey: ['my-tasks'] })
      queryClient.invalidateQueries({ queryKey: ['my-assignments'] })
    },
  })
  const loading = postedQuery.isLoading || assignmentsQuery.isLoading
  const posted = sortTasksForList(postedQuery.data?.results ?? [], 'posted')
  const assignments = sortTasksForList(assignmentsQuery.data?.results ?? [], 'assignments')

  return (
    <section className="grid gap-5">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="text-3xl font-bold text-primary">My Tasks</h1>
        <div className="mt-4 flex gap-2">
          <button onClick={() => setTab('posted')} className={`rounded-md px-4 py-2 font-medium ${tab === 'posted' ? 'bg-primary text-white' : 'bg-slate-100 text-text-dark'}`}>Posted by me</button>
          <button onClick={() => setTab('assignments')} className={`rounded-md px-4 py-2 font-medium ${tab === 'assignments' ? 'bg-primary text-white' : 'bg-slate-100 text-text-dark'}`}>My Assignments</button>
        </div>
      </div>
      {loading ? (
        <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
      ) : (
        <TaskList
          tasks={tab === 'posted' ? posted : assignments}
          listType={tab}
          onForget={(taskId) => forgetMutation.mutate(taskId)}
          forgettingId={forgetMutation.variables}
        />
      )}
    </section>
  )
}
