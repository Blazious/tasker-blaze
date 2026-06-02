import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarClock, CreditCard, Loader2, ReceiptText, ShieldAlert, Smartphone } from 'lucide-react'
import toast from 'react-hot-toast'
import { createTestPlatformInvoice, generatePlatformInvoice, getPlatformBilling, getPlatformInvoicePaymentStatus, payPlatformInvoice } from '../api/payments.js'
import { useAuthStore } from '../store/authStore.js'
import { getApiErrorMessage } from '../utils/apiError.js'

export default function BillingPage() {
  const user = useAuthStore((state) => state.user)
  const queryClient = useQueryClient()
  const billingQuery = useQuery({
    queryKey: ['platform-billing'],
    queryFn: getPlatformBilling,
    enabled: Boolean(user),
  })
  const invoiceMutation = useMutation({
    mutationFn: generatePlatformInvoice,
    onSuccess: (data) => {
      queryClient.setQueryData(['platform-billing'], data)
      toast.success(data.generated_invoice_id ? 'Invoice generated.' : 'No billable fees yet.')
    },
  })
  const payInvoiceMutation = useMutation({
    mutationFn: (invoiceId) => payPlatformInvoice(invoiceId),
    onSuccess: (data) => {
      toast.success(data.message || 'STK push sent.')
      queryClient.invalidateQueries({ queryKey: ['platform-billing'] })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Could not start invoice payment.'))
    },
  })
  const checkInvoiceMutation = useMutation({
    mutationFn: getPlatformInvoicePaymentStatus,
    onSuccess: (data) => {
      toast.success(data.invoice_status === 'PAID' ? 'Invoice paid.' : `Payment status: ${data.payment_status || 'Not started'}`)
      queryClient.invalidateQueries({ queryKey: ['platform-billing'] })
    },
  })
  const testInvoiceMutation = useMutation({
    mutationFn: () => createTestPlatformInvoice(70),
    onSuccess: (data) => {
      queryClient.setQueryData(['platform-billing'], data)
      toast.success('Test invoice created.')
    },
  })

  const billing = billingQuery.data
  const overdue = Number(billing?.overdue_balance ?? 0)
  const currentDue = Number(billing?.current_month_due ?? 0)

  if (billingQuery.isLoading) {
    return <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
  }

  return (
    <section className="grid gap-6">
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="bg-gradient-to-br from-slate-950 via-primary to-emerald-500 p-6 text-white">
          <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-white/75">
            <ReceiptText size={16} /> TaskiT billing
          </p>
          <h1 className="mt-2 text-3xl font-black">Post-paid platform fees</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/80">
            TaskiT tracks the 10% tasker platform fee after completed paid tasks. Trial usage is waived, and invoices get a {billing?.grace_period_days ?? 3}-day grace period.
          </p>
        </div>

        <div className="grid gap-3 p-4 md:grid-cols-4">
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Trial status</p>
            <p className="mt-1 text-xl font-bold text-text-dark">{billing?.is_trial_active ? 'Active' : 'Ended'}</p>
            <p className="text-xs text-text-muted">{billing?.trial_ends_at ? `Ends ${new Date(billing.trial_ends_at).toLocaleDateString()}` : 'No date'}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">This month</p>
            <p className="mt-1 text-xl font-bold text-text-dark">KES {billing?.current_month_due ?? '0.00'}</p>
            <p className="text-xs text-text-muted">{currentDue > 0 ? 'Ready for invoice' : 'No billable fees'}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Overdue</p>
            <p className={`mt-1 text-xl font-bold ${overdue > 0 ? 'text-red-700' : 'text-text-dark'}`}>KES {billing?.overdue_balance ?? '0.00'}</p>
            <p className="text-xs text-text-muted">{billing?.can_bid === false ? 'Bidding paused' : 'Bidding allowed'}</p>
          </div>
          <div className="rounded-lg bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">Trial waived</p>
            <p className="mt-1 text-xl font-bold text-text-dark">KES {billing?.trial_waived_task_volume ?? '0.00'}</p>
            <p className="text-xs text-text-muted">Task volume during trial</p>
          </div>
        </div>
      </div>

      {overdue > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <p className="inline-flex items-center gap-2 font-semibold"><ShieldAlert size={18} /> Payment overdue</p>
          <p className="mt-1 text-sm">Settle your pending invoice to continue placing bids.</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-200 p-4">
            <h2 className="font-bold text-text-dark">Tracked tasks</h2>
            <div className="flex flex-wrap gap-2">
              {billing?.test_billing_tools_enabled && (
                <button
                  type="button"
                  onClick={() => testInvoiceMutation.mutate()}
                  disabled={testInvoiceMutation.isPending}
                  className="inline-flex items-center gap-2 rounded-md border border-primary px-3 py-2 text-xs font-bold text-primary disabled:opacity-60"
                >
                  {testInvoiceMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <CreditCard size={14} />}
                  Test KES 70
                </button>
              )}
              <button
                type="button"
                onClick={() => invoiceMutation.mutate()}
                disabled={invoiceMutation.isPending}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-xs font-bold text-white disabled:opacity-60"
              >
                {invoiceMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <CalendarClock size={14} />}
                Generate invoice
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="bg-slate-50 text-text-muted">
                <tr>
                  {['Task', 'Amount', 'Fee', 'Status', 'Tracked'].map((head) => <th key={head} className="px-4 py-3">{head}</th>)}
                </tr>
              </thead>
              <tbody>
                {(billing?.tracked_tasks ?? []).map((item) => (
                  <tr key={item.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-text-dark">{item.task_title}</td>
                    <td className="px-4 py-3">KES {item.task_amount}</td>
                    <td className="px-4 py-3">KES {item.fee_amount}</td>
                    <td className="px-4 py-3">{item.is_trial_usage ? 'Trial waived' : item.status}</td>
                    <td className="px-4 py-3">{new Date(item.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
                {(billing?.tracked_tasks ?? []).length === 0 && (
                  <tr><td colSpan="5" className="px-4 py-8 text-center text-text-muted">No tracked platform fees this month.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="inline-flex items-center gap-2 font-bold text-text-dark"><CreditCard size={18} /> Pending invoices</h2>
          <div className="mt-4 grid gap-3">
            {(billing?.pending_invoices ?? []).map((invoice) => (
              <div key={invoice.id} className={`rounded-lg border p-3 ${invoice.is_overdue ? 'border-red-200 bg-red-50' : 'border-slate-200 bg-slate-50'}`}>
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-text-dark">KES {invoice.amount}</p>
                  <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold">{invoice.status}</span>
                </div>
                <p className={`mt-2 text-sm ${invoice.is_overdue ? 'text-red-700' : 'text-text-muted'}`}>
                  Due {new Date(invoice.due_date).toLocaleString()}
                </p>
                {invoice.latest_payment_status && (
                  <p className="mt-1 text-xs font-semibold text-text-muted">Payment: {invoice.latest_payment_status}</p>
                )}
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => payInvoiceMutation.mutate(invoice.id)}
                    disabled={payInvoiceMutation.isPending}
                    className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-xs font-bold text-white disabled:opacity-60"
                  >
                    {payInvoiceMutation.isPending ? <Loader2 size={14} className="animate-spin" /> : <Smartphone size={14} />}
                    Pay Invoice
                  </button>
                  <button
                    type="button"
                    onClick={() => checkInvoiceMutation.mutate(invoice.id)}
                    disabled={checkInvoiceMutation.isPending}
                    className="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-text-dark disabled:opacity-60"
                  >
                    Check
                  </button>
                </div>
              </div>
            ))}
            {(billing?.pending_invoices ?? []).length === 0 && <p className="rounded-lg bg-slate-50 p-4 text-sm text-text-muted">No pending invoices.</p>}
          </div>
        </div>
      </div>
    </section>
  )
}
