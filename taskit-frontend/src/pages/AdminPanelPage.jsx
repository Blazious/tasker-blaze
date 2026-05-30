import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Banknote, CheckCircle2, ClipboardList, Loader2, ShieldCheck, UsersRound } from 'lucide-react'
import { getAdminOverview } from '../api/admin.js'
import { useAuthStore } from '../store/authStore.js'

function MetricCard({ title, value, note, Icon }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text-muted">{title}</p>
          <p className="mt-2 text-3xl font-black text-primary">{value}</p>
          {note && <p className="mt-1 text-sm text-text-muted">{note}</p>}
        </div>
        <span className="rounded-md bg-emerald-50 p-2 text-primary">
          <Icon size={20} />
        </span>
      </div>
    </div>
  )
}

export default function AdminPanelPage() {
  const user = useAuthStore((state) => state.user)
  const isAdmin = Boolean(user?.is_staff || user?.is_superuser)
  const overviewQuery = useQuery({
    queryKey: ['admin-overview'],
    queryFn: getAdminOverview,
    enabled: isAdmin,
  })

  if (!isAdmin) {
    return (
      <section className="rounded-lg border border-red-100 bg-red-50 p-6 text-red-700">
        <h1 className="text-xl font-bold">Admin access only</h1>
        <p className="mt-2 text-sm">This workspace is restricted to TaskiT staff accounts.</p>
      </section>
    )
  }

  if (overviewQuery.isLoading) {
    return <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
  }

  if (overviewQuery.isError) {
    return (
      <section className="rounded-lg border border-red-100 bg-red-50 p-6 text-red-700">
        <h1 className="text-xl font-bold">Admin overview unavailable</h1>
        <p className="mt-2 text-sm">Refresh the page or check the backend admin endpoint.</p>
      </section>
    )
  }

  const overview = overviewQuery.data

  return (
    <section className="grid gap-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-secondary">
          <ShieldCheck size={16} />
          Admin operations
        </p>
        <h1 className="mt-2 text-3xl font-black text-primary">TaskiT Admin Panel</h1>
        <p className="mt-2 text-sm text-text-muted">Operational overview for support, trust, billing, users, and platform activity.</p>
        {overview?.admin_email && <p className="mt-3 text-sm font-semibold text-text-dark">Admin inbox: {overview.admin_email}</p>}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Total Users" value={overview.users.total} note={`${overview.users.verified_email} email verified`} Icon={UsersRound} />
        <MetricCard title="KYC Verified" value={overview.users.kyc_verified} note={`${overview.ops.kyc_pending_review} pending review`} Icon={CheckCircle2} />
        <MetricCard title="Open Support" value={overview.ops.support_tickets_open} note={`${overview.ops.user_reports_open} user reports open`} Icon={ClipboardList} />
        <MetricCard title="Payment Disputes" value={overview.ops.payment_disputes} note={`${overview.tasks.disputed} disputed tasks`} Icon={AlertTriangle} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-bold text-text-dark">Task Activity</h2>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-text-muted">Open</dt><dd className="font-bold text-text-dark">{overview.tasks.open}</dd></div>
            <div><dt className="text-text-muted">Assigned</dt><dd className="font-bold text-text-dark">{overview.tasks.assigned}</dd></div>
            <div><dt className="text-text-muted">In progress</dt><dd className="font-bold text-text-dark">{overview.tasks.in_progress}</dd></div>
            <div><dt className="text-text-muted">Completed</dt><dd className="font-bold text-text-dark">{overview.tasks.completed}</dd></div>
            <div><dt className="text-text-muted">Bids</dt><dd className="font-bold text-text-dark">{overview.tasks.bids}</dd></div>
            <div><dt className="text-text-muted">Active taskers</dt><dd className="font-bold text-text-dark">{overview.users.taskers}</dd></div>
          </dl>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="inline-flex items-center gap-2 text-xl font-bold text-text-dark">
            <Banknote size={20} />
            Billing Snapshot
          </h2>
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-text-muted">Pending invoices</dt><dd className="font-bold text-text-dark">{overview.billing.pending_invoices}</dd></div>
            <div><dt className="text-text-muted">Pending invoice total</dt><dd className="font-bold text-text-dark">KES {overview.billing.pending_invoice_total}</dd></div>
            <div><dt className="text-text-muted">Escrowed total</dt><dd className="font-bold text-text-dark">KES {overview.billing.escrowed_total}</dd></div>
            <div><dt className="text-text-muted">Released total</dt><dd className="font-bold text-text-dark">KES {overview.billing.released_total}</dd></div>
          </dl>
        </div>
      </div>
    </section>
  )
}
