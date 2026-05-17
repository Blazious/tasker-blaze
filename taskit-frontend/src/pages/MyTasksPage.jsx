import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { getMyAssignments, getMyTasks } from '../api/tasks.js'

const statusStyles = {
  OPEN: 'bg-blue-100 text-blue-700',
  ASSIGNED: 'bg-orange-100 text-orange-700',
  IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-emerald-100 text-primary',
  CANCELLED: 'bg-slate-100 text-slate-700',
  DISPUTED: 'bg-red-100 text-red-700',
}

function TaskList({ tasks }) {
  if (!tasks.length) return <p className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-text-muted">No tasks here yet.</p>
  return (
    <div className="grid gap-3">
      {tasks.map((task) => (
        <Link key={task.id} to={`/tasks/${task.id}`} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm hover:border-primary/40">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-semibold text-text-dark">{task.title}</h2>
              <p className="text-sm text-text-muted">{task.location_landmark} - KES {task.budget_min} to {task.budget_max}</p>
            </div>
            <span className={`w-fit rounded-full px-3 py-1 text-sm font-semibold ${statusStyles[task.status] ?? 'bg-slate-100 text-slate-700'}`}>{task.status}</span>
          </div>
        </Link>
      ))}
    </div>
  )
}

export default function MyTasksPage() {
  const [tab, setTab] = useState('posted')
  const postedQuery = useQuery({ queryKey: ['my-tasks'], queryFn: getMyTasks })
  const assignmentsQuery = useQuery({ queryKey: ['my-assignments'], queryFn: getMyAssignments })
  const loading = postedQuery.isLoading || assignmentsQuery.isLoading
  const posted = postedQuery.data?.results ?? []
  const assignments = assignmentsQuery.data?.results ?? []

  return (
    <section className="grid gap-5">
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h1 className="text-3xl font-bold text-primary">My Tasks</h1>
        <div className="mt-4 flex gap-2">
          <button onClick={() => setTab('posted')} className={`rounded-md px-4 py-2 font-medium ${tab === 'posted' ? 'bg-primary text-white' : 'bg-slate-100 text-text-dark'}`}>Posted by me</button>
          <button onClick={() => setTab('assignments')} className={`rounded-md px-4 py-2 font-medium ${tab === 'assignments' ? 'bg-primary text-white' : 'bg-slate-100 text-text-dark'}`}>My Assignments</button>
        </div>
      </div>
      {loading ? <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div> : <TaskList tasks={tab === 'posted' ? posted : assignments} />}
    </section>
  )
}
