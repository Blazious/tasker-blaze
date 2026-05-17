import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { CalendarClock, CreditCard, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { generatePlatformInvoice, getMyEarnings, getPlatformBilling } from '../api/payments.js'
import { getMyBids } from '../api/tasks.js'
import { getUserProfile } from '../api/reviews.js'
import { useAuthStore } from '../store/authStore.js'

export default function EarningsPage() {
  const user = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()
  const earningsQuery = useQuery({ queryKey: ['my-earnings'], queryFn: getMyEarnings, enabled: Boolean(user?.is_tasker_active) })
  const billingQuery = useQuery({ queryKey: ['platform-billing'], queryFn: getPlatformBilling, enabled: Boolean(user?.is_tasker_active) })
  const bidsQuery = useQuery({ queryKey: ['my-bids'], queryFn: getMyBids, enabled: Boolean(user?.is_tasker_active) })
  const profileQuery = useQuery({ queryKey: ['public-profile', user?.id], queryFn: () => getUserProfile(user.id), enabled: Boolean(user?.id && user?.is_tasker_active) })
  const invoiceMutation = useMutation({
    mutationFn: generatePlatformInvoice,
    onSuccess: (data) => {
      queryClient.setQueryData(['platform-billing'], data)
      toast.success(data.generated_invoice_id ? 'Invoice generated.' : 'No billable fees yet.')
    },
  })

  if (!user?.is_tasker_active) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
        <p className="text-lg font-semibold text-text-dark">Activate tasker mode from your dashboard to start earning.</p>
        <Link to="/dashboard" className="mt-4 inline-flex rounded-md bg-primary px-4 py-2 text-white">Go to Dashboard</Link>
      </div>
    )
  }

  if (earningsQuery.isLoading) {
    return <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
  }

  const earnings = earningsQuery.data ?? { total_earned: '0.00', pending_payout: '0.00', total_tasks: 0, transactions: [] }
  const billing = billingQuery.data
  const bids = bidsQuery.data?.results ?? []

  return (
    <section className="grid gap-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Tasker wallet</p>
        <h1 className="mt-2 text-3xl font-bold text-primary">Earnings</h1>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {[
          ['Total Earned', `KES ${earnings.total_earned}`],
          ['Pending Payout', `KES ${earnings.pending_payout}`],
          ['Tasks Completed', earnings.total_tasks],
          ['Average Rating', profileQuery.data?.average_rating ?? 0],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-text-muted">{label}</p>
            <p className="mt-2 text-2xl font-bold text-text-dark">{value}</p>
          </div>
        ))}
      </div>
      <div className={`rounded-lg border p-5 shadow-sm ${Number(billing?.overdue_balance ?? 0) > 0 ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-white'}`}>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-secondary">
              <CreditCard size={16} /> Platform billing
            </p>
            <h2 className="mt-2 text-xl font-bold text-text-dark">Post-paid tasker fees</h2>
            <p className="mt-1 max-w-3xl text-sm text-text-muted">
              TaskiT tracks billable completed tasks and invoices the 10% platform fee at month end. You have {billing?.grace_period_days ?? 3} days after an invoice is due before bidding is paused.
            </p>
          </div>
          <button
            type="button"
            onClick={() => invoiceMutation.mutate()}
            disabled={invoiceMutation.isPending}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {invoiceMutation.isPending ? <Loader2 className="mr-2 animate-spin" size={16} /> : <CalendarClock className="mr-2" size={16} />}
            Generate invoice
          </button>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <div className="rounded-md bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-text-muted">Trial</p>
            <p className="mt-1 font-semibold text-text-dark">{billing?.is_trial_active ? 'Active' : 'Ended'}</p>
            <p className="text-xs text-text-muted">{billing?.trial_ends_at ? `Ends ${new Date(billing.trial_ends_at).toLocaleDateString()}` : 'Loading...'}</p>
          </div>
          <div className="rounded-md bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-text-muted">This month due</p>
            <p className="mt-1 font-semibold text-text-dark">KES {billing?.current_month_due ?? '0.00'}</p>
            <p className="text-xs text-text-muted">Month: {billing?.current_month ? new Date(billing.current_month).toLocaleDateString() : 'Current'}</p>
          </div>
          <div className="rounded-md bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-text-muted">Trial volume waived</p>
            <p className="mt-1 font-semibold text-text-dark">KES {billing?.trial_waived_task_volume ?? '0.00'}</p>
            <p className="text-xs text-text-muted">No fee charged during trial</p>
          </div>
          <div className="rounded-md bg-slate-50 p-4">
            <p className="text-xs uppercase tracking-wide text-text-muted">Overdue</p>
            <p className={`mt-1 font-semibold ${Number(billing?.overdue_balance ?? 0) > 0 ? 'text-red-700' : 'text-text-dark'}`}>KES {billing?.overdue_balance ?? '0.00'}</p>
            <p className="text-xs text-text-muted">{billing?.can_bid === false ? 'Bidding paused' : 'Bidding allowed'}</p>
          </div>
        </div>
        {billing?.pending_invoices?.length > 0 && (
          <div className="mt-4 rounded-md border border-slate-200 bg-white">
            {billing.pending_invoices.map((invoice) => (
              <div key={invoice.id} className="flex flex-col gap-2 border-b border-slate-100 p-3 text-sm last:border-b-0 md:flex-row md:items-center md:justify-between">
                <span className="font-semibold">Invoice #{invoice.id} · KES {invoice.amount}</span>
                <span className={invoice.is_overdue ? 'text-red-700' : 'text-text-muted'}>
                  Due {new Date(invoice.due_date).toLocaleString()} · {invoice.status}
                </span>
              </div>
            ))}
          </div>
        )}
        <div className="mt-4 overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-50 text-text-muted">
              <tr>
                {['Tracked task', 'Task amount', 'Platform fee', 'Billing status'].map((head) => <th key={head} className="px-4 py-3">{head}</th>)}
              </tr>
            </thead>
            <tbody>
              {(billing?.tracked_tasks ?? []).map((item) => (
                <tr key={item.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium">{item.task_title}</td>
                  <td className="px-4 py-3">KES {item.task_amount}</td>
                  <td className="px-4 py-3">KES {item.fee_amount}</td>
                  <td className="px-4 py-3">{item.is_trial_usage ? 'Trial waived' : item.status}</td>
                </tr>
              ))}
              {(billing?.tracked_tasks ?? []).length === 0 && (
                <tr><td colSpan="4" className="px-4 py-5 text-center text-text-muted">No tracked platform fees this month.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 p-4"><h2 className="font-semibold">Transaction History</h2></div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-text-muted">
              <tr>
                {['Task', 'Client', 'Agreed', 'Fee', 'Payout', 'Date', 'Status'].map((head) => <th key={head} className="px-4 py-3">{head}</th>)}
              </tr>
            </thead>
            <tbody>
              {earnings.transactions.map((item) => (
                <tr key={`${item.task_title}-${item.created_at}`} className="border-t border-slate-100">
                  <td className="px-4 py-3 font-medium">{item.task_title}</td>
                  <td className="px-4 py-3">{item.client_name}</td>
                  <td className="px-4 py-3">KES {item.agreed_amount}</td>
                  <td className="px-4 py-3">KES {item.platform_fee}</td>
                  <td className="px-4 py-3">KES {item.tasker_payout}</td>
                  <td className="px-4 py-3">{new Date(item.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">{item.status === 'ESCROWED' ? 'Escrowed' : item.status === 'RELEASED' ? 'Released' : item.status}</td>
                </tr>
              ))}
              {earnings.transactions.length === 0 && <tr><td colSpan="7" className="px-4 py-6 text-center text-text-muted">No earnings yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-text-dark">My Active Bids</h2>
        <div className="mt-3 grid gap-3">
          {bids.length === 0 && <p className="text-text-muted">No bids placed yet.</p>}
          {bids.map((bid) => (
            <Link key={bid.id} to={`/tasks/${bid.task}`} className="flex items-center justify-between rounded-lg border border-slate-200 p-4 hover:border-primary/40">
              <div>
                <p className="font-semibold">{bid.task_title}</p>
                <p className="text-sm text-text-muted">KES {bid.amount}</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-text-dark">{bid.status}</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
