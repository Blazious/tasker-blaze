import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, Banknote, CheckCircle2, ClipboardList, Flag, Loader2, ShieldCheck, UsersRound } from 'lucide-react'
import {
  getAdminOverview,
  getAdminKycSubmissions,
  getAdminPlatformInvoices,
  getAdminSupportTickets,
  getAdminUserReports,
  updateAdminKycSubmission,
  updateAdminPlatformInvoice,
  updateAdminSupportTicket,
  updateAdminUserReport,
} from '../api/admin.js'
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

const statusOptions = ['ALL', 'OPEN', 'REVIEWING', 'RESOLVED', 'CLOSED']
const priorityOptions = ['ALL', 'LOW', 'NORMAL', 'HIGH', 'URGENT']
const reportStatusOptions = ['ALL', 'OPEN', 'REVIEWING', 'RESOLVED', 'DISMISSED']
const reportReasonOptions = ['ALL', 'HARASSMENT', 'SAFETY_CONCERN', 'NO_SHOW', 'POOR_WORK', 'PAYMENT_ISSUE', 'INAPPROPRIATE_CONTENT', 'OTHER']
const visibilityOptions = ['ALL', 'PUBLIC', 'PRIVATE']
const kycStatusOptions = ['ALL', 'PENDING_REVIEW', 'NEEDS_RETRY', 'FACE_MISMATCH', 'APPROVED', 'REJECTED']
const invoiceStatusOptions = ['ALL', 'PENDING', 'PAID', 'WAIVED', 'CANCELLED']

function TicketBadge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-700',
    green: 'bg-emerald-50 text-emerald-700',
    yellow: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
  }
  return (
    <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${tones[tone]}`}>
      {children}
    </span>
  )
}

function ModerationQueue({ enabled }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('ALL')
  const [reason, setReason] = useState('ALL')
  const [visibility, setVisibility] = useState('ALL')
  const [notesByReport, setNotesByReport] = useState({})
  const reportsQuery = useQuery({
    queryKey: ['admin-user-reports', status, reason, visibility],
    queryFn: () => getAdminUserReports({ status, reason, visibility }),
    enabled,
  })
  const updateReportMutation = useMutation({
    mutationFn: ({ id, data }) => updateAdminUserReport(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-user-reports'] })
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] })
      toast.success('Report updated')
    },
    onError: () => toast.error('Could not update report'),
  })

  const updateReport = (report, data) => {
    updateReportMutation.mutate({
      id: report.id,
      data: {
        status: report.status,
        is_public: report.is_public,
        admin_notes: report.admin_notes || '',
        ...data,
      },
    })
  }

  const reports = reportsQuery.data || []

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="inline-flex items-center gap-2 text-xl font-bold text-text-dark">
            <Flag size={20} />
            Report Moderation
          </h2>
          <p className="mt-1 text-sm text-text-muted">Review reported users, publish serious verified reports, and document decisions.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {reportStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <select value={reason} onChange={(event) => setReason(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {reportReasonOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <select value={visibility} onChange={(event) => setVisibility(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {visibilityOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </div>

      {reportsQuery.isLoading && (
        <div className="flex justify-center py-8 text-primary">
          <Loader2 className="animate-spin" size={24} />
        </div>
      )}

      {reportsQuery.isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not load user reports.</p>
      )}

      {!reportsQuery.isLoading && reports.length === 0 && (
        <p className="mt-5 rounded-md bg-slate-50 px-3 py-4 text-sm text-text-muted">No reports match these filters.</p>
      )}

      <div className="mt-5 grid gap-4">
        {reports.map((report) => {
          const statusTone = report.status === 'RESOLVED' || report.status === 'DISMISSED' ? 'green' : report.status === 'REVIEWING' ? 'yellow' : 'red'
          return (
            <article key={report.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-text-dark">{report.reason.replaceAll('_', ' ')}</h3>
                    <TicketBadge tone={statusTone}>{report.status}</TicketBadge>
                    <TicketBadge tone={report.is_public ? 'red' : 'slate'}>{report.is_public ? 'PUBLIC' : 'PRIVATE'}</TicketBadge>
                  </div>
                  <p className="mt-2 max-w-3xl text-sm text-text-muted">{report.details}</p>
                  <div className="mt-3 grid gap-1 text-xs font-semibold text-text-muted">
                    <span>Reporter: {report.reporter?.full_name || report.reporter?.email} · {report.reporter?.email}</span>
                    <span>
                      Reported: {report.reported_user?.full_name || report.reported_user?.email} · {report.reported_user?.email}
                      {report.reported_user?.id && (
                        <Link to={`/profile/${report.reported_user.id}`} className="ml-2 text-primary underline-offset-2 hover:underline">Open profile</Link>
                      )}
                    </span>
                    {report.task_title && <span>Task: {report.task_title}</span>}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => updateReport(report, { status: 'REVIEWING' })} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50">Review</button>
                  <button type="button" onClick={() => updateReport(report, { status: 'RESOLVED' })} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-900">Resolve</button>
                  <button type="button" onClick={() => updateReport(report, { status: 'DISMISSED', is_public: false })} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50">Dismiss</button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[180px_1fr_auto] lg:items-end">
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Visibility
                  <select
                    value={report.is_public ? 'PUBLIC' : 'PRIVATE'}
                    onChange={(event) => updateReport(report, { is_public: event.target.value === 'PUBLIC' })}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  >
                    <option value="PRIVATE">PRIVATE</option>
                    <option value="PUBLIC">PUBLIC</option>
                  </select>
                </label>
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Admin notes
                  <textarea
                    value={notesByReport[report.id] ?? report.admin_notes ?? ''}
                    onChange={(event) => setNotesByReport((current) => ({ ...current, [report.id]: event.target.value }))}
                    rows={2}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => updateReport(report, { admin_notes: notesByReport[report.id] ?? report.admin_notes ?? '' })}
                  className="rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-emerald-50"
                >
                  Save Notes
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function KycReviewQueue({ enabled }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('PENDING_REVIEW')
  const [notesBySubmission, setNotesBySubmission] = useState({})
  const kycQuery = useQuery({
    queryKey: ['admin-kyc-submissions', status],
    queryFn: () => getAdminKycSubmissions({ status }),
    enabled,
  })
  const updateKycMutation = useMutation({
    mutationFn: ({ id, data }) => updateAdminKycSubmission(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-kyc-submissions'] })
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] })
      toast.success('KYC updated')
    },
    onError: () => toast.error('Could not update KYC submission'),
  })

  const updateKyc = (submission, data) => {
    updateKycMutation.mutate({
      id: submission.id,
      data: {
        status: submission.status,
        reviewer_notes: submission.reviewer_notes || '',
        ...data,
      },
    })
  }

  const submissions = kycQuery.data || []

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="inline-flex items-center gap-2 text-xl font-bold text-text-dark">
            <ShieldCheck size={20} />
            KYC Review Queue
          </h2>
          <p className="mt-1 text-sm text-text-muted">Approve verified student IDs, reject bad submissions, or request a clearer retry.</p>
        </div>
        <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
          {kycStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
        </select>
      </div>

      {kycQuery.isLoading && (
        <div className="flex justify-center py-8 text-primary">
          <Loader2 className="animate-spin" size={24} />
        </div>
      )}

      {kycQuery.isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not load KYC submissions.</p>
      )}

      {!kycQuery.isLoading && submissions.length === 0 && (
        <p className="mt-5 rounded-md bg-slate-50 px-3 py-4 text-sm text-text-muted">No KYC submissions match this status.</p>
      )}

      <div className="mt-5 grid gap-4">
        {submissions.map((submission) => {
          const statusTone = submission.status === 'APPROVED' ? 'green' : submission.status === 'PENDING_REVIEW' ? 'yellow' : 'red'
          const summary = submission.verification_summary || {}
          return (
            <article key={submission.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-text-dark">{submission.user?.full_name || submission.user?.email}</h3>
                    <TicketBadge tone={statusTone}>{submission.status}</TicketBadge>
                    {submission.face_match_confidence !== null && <TicketBadge tone={submission.face_match_confidence >= 75 ? 'green' : 'red'}>{submission.face_match_confidence}% face</TicketBadge>}
                  </div>
                  <p className="mt-2 text-sm text-text-muted">{submission.user?.email}</p>
                  <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                    <div><dt className="text-text-muted">Extracted name</dt><dd className="font-semibold text-text-dark">{submission.extracted_full_name || 'Missing'}</dd></div>
                    <div><dt className="text-text-muted">Student ID</dt><dd className="font-semibold text-text-dark">{submission.extracted_student_id || 'Missing'}</dd></div>
                    <div><dt className="text-text-muted">School</dt><dd className="font-semibold text-text-dark">{submission.extracted_school || 'Missing'}</dd></div>
                    <div><dt className="text-text-muted">Course</dt><dd className="font-semibold text-text-dark">{submission.extracted_degree || 'Missing'}</dd></div>
                    <div><dt className="text-text-muted">ID photo</dt><dd className="font-semibold text-text-dark">{submission.id_photo_detected ? 'Detected' : 'Not detected'}</dd></div>
                    <div><dt className="text-text-muted">JKUAT evidence</dt><dd className="font-semibold text-text-dark">{summary.has_jkuat_evidence ? 'Yes' : 'No'}</dd></div>
                  </dl>
                  <div className="mt-3 flex flex-wrap gap-3 text-sm font-semibold">
                    {submission.id_front_image && <a href={submission.id_front_image} target="_blank" rel="noreferrer" className="text-primary underline-offset-2 hover:underline">Front ID</a>}
                    {submission.live_face_image && <a href={submission.live_face_image} target="_blank" rel="noreferrer" className="text-primary underline-offset-2 hover:underline">Live face</a>}
                    {submission.id_back_image && <a href={submission.id_back_image} target="_blank" rel="noreferrer" className="text-primary underline-offset-2 hover:underline">Back ID</a>}
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => updateKyc(submission, { status: 'APPROVED' })} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-900">Approve</button>
                  <button type="button" onClick={() => updateKyc(submission, { status: 'NEEDS_RETRY' })} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50">Ask Retry</button>
                  <button type="button" onClick={() => updateKyc(submission, { status: 'REJECTED' })} className="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50">Reject</button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Reviewer notes
                  <textarea
                    value={notesBySubmission[submission.id] ?? submission.reviewer_notes ?? ''}
                    onChange={(event) => setNotesBySubmission((current) => ({ ...current, [submission.id]: event.target.value }))}
                    rows={2}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => updateKyc(submission, { reviewer_notes: notesBySubmission[submission.id] ?? submission.reviewer_notes ?? '' })}
                  className="rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-emerald-50"
                >
                  Save Notes
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function PlatformBillingQueue({ enabled }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('PENDING')
  const [overdueOnly, setOverdueOnly] = useState(false)
  const [notesByInvoice, setNotesByInvoice] = useState({})
  const invoicesQuery = useQuery({
    queryKey: ['admin-platform-invoices', status, overdueOnly],
    queryFn: () => getAdminPlatformInvoices({ status, overdue: overdueOnly ? 'true' : undefined }),
    enabled,
  })
  const updateInvoiceMutation = useMutation({
    mutationFn: ({ id, data }) => updateAdminPlatformInvoice(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-platform-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] })
      toast.success('Invoice updated')
    },
    onError: () => toast.error('Could not update invoice'),
  })

  const updateInvoice = (invoice, data) => {
    updateInvoiceMutation.mutate({
      id: invoice.id,
      data: {
        status: invoice.status,
        notes: invoice.notes || '',
        ...data,
      },
    })
  }

  const invoices = invoicesQuery.data || []

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="inline-flex items-center gap-2 text-xl font-bold text-text-dark">
            <Banknote size={20} />
            Platform Billing
          </h2>
          <p className="mt-1 text-sm text-text-muted">Manage TaskiT platform invoices only. Escrow funds remain read-only and external.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {invoiceStatusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <label className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark">
            <input type="checkbox" checked={overdueOnly} onChange={(event) => setOverdueOnly(event.target.checked)} />
            Overdue
          </label>
        </div>
      </div>

      {invoicesQuery.isLoading && (
        <div className="flex justify-center py-8 text-primary">
          <Loader2 className="animate-spin" size={24} />
        </div>
      )}

      {invoicesQuery.isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not load platform invoices.</p>
      )}

      {!invoicesQuery.isLoading && invoices.length === 0 && (
        <p className="mt-5 rounded-md bg-slate-50 px-3 py-4 text-sm text-text-muted">No platform invoices match these filters.</p>
      )}

      <div className="mt-5 grid gap-4">
        {invoices.map((invoice) => {
          const statusTone = invoice.status === 'PAID' ? 'green' : invoice.status === 'PENDING' ? (invoice.is_overdue ? 'red' : 'yellow') : 'slate'
          return (
            <article key={invoice.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-text-dark">KES {invoice.amount}</h3>
                    <TicketBadge tone={statusTone}>{invoice.status}</TicketBadge>
                    {invoice.is_overdue && <TicketBadge tone="red">OVERDUE</TicketBadge>}
                    {invoice.latest_payment_status && <TicketBadge>{invoice.latest_payment_status}</TicketBadge>}
                  </div>
                  <p className="mt-2 text-sm text-text-muted">
                    {invoice.tasker?.full_name || invoice.tasker?.email} · {invoice.tasker?.email}
                  </p>
                  <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                    <div><dt className="text-text-muted">Billing month</dt><dd className="font-semibold text-text-dark">{invoice.billing_month}</dd></div>
                    <div><dt className="text-text-muted">Due date</dt><dd className="font-semibold text-text-dark">{invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : 'Missing'}</dd></div>
                    <div><dt className="text-text-muted">Paid at</dt><dd className="font-semibold text-text-dark">{invoice.paid_at ? new Date(invoice.paid_at).toLocaleDateString() : 'Not paid'}</dd></div>
                    <div><dt className="text-text-muted">Fee items</dt><dd className="font-semibold text-text-dark">{invoice.usages?.length || 0}</dd></div>
                  </dl>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => updateInvoice(invoice, { status: 'WAIVED' })} disabled={invoice.status === 'PAID'} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50">Waive</button>
                  <button type="button" onClick={() => updateInvoice(invoice, { status: 'CANCELLED' })} disabled={invoice.status === 'PAID'} className="rounded-md border border-red-200 px-3 py-2 text-sm font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50">Cancel</button>
                  <button type="button" onClick={() => updateInvoice(invoice, { status: 'PENDING' })} disabled={invoice.status === 'PAID'} className="rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-50">Reopen</button>
                </div>
              </div>

              {invoice.usages?.length > 0 && (
                <div className="mt-4 overflow-hidden rounded-md border border-slate-200">
                  <div className="grid grid-cols-[1fr_90px_90px_100px] gap-2 bg-slate-50 px-3 py-2 text-xs font-bold uppercase text-text-muted">
                    <span>Task</span>
                    <span>Task</span>
                    <span>Fee</span>
                    <span>Status</span>
                  </div>
                  {invoice.usages.slice(0, 5).map((usage) => (
                    <div key={usage.id} className="grid grid-cols-[1fr_90px_90px_100px] gap-2 border-t border-slate-200 px-3 py-2 text-sm">
                      <span className="truncate text-text-dark">{usage.task_title}</span>
                      <span className="font-semibold text-text-dark">KES {usage.task_amount}</span>
                      <span className="font-semibold text-text-dark">KES {usage.fee_amount}</span>
                      <span className="text-text-muted">{usage.status}</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-4 grid gap-3 lg:grid-cols-[1fr_auto] lg:items-end">
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Admin notes
                  <textarea
                    value={notesByInvoice[invoice.id] ?? invoice.notes ?? ''}
                    onChange={(event) => setNotesByInvoice((current) => ({ ...current, [invoice.id]: event.target.value }))}
                    rows={2}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => updateInvoice(invoice, { notes: notesByInvoice[invoice.id] ?? invoice.notes ?? '' })}
                  className="rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-emerald-50"
                >
                  Save Notes
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </div>
  )
}

function SupportQueue({ enabled }) {
  const queryClient = useQueryClient()
  const [status, setStatus] = useState('ALL')
  const [priority, setPriority] = useState('ALL')
  const [notesByTicket, setNotesByTicket] = useState({})
  const ticketsQuery = useQuery({
    queryKey: ['admin-support-tickets', status, priority],
    queryFn: () => getAdminSupportTickets({ status, priority }),
    enabled,
  })
  const updateTicketMutation = useMutation({
    mutationFn: ({ id, data }) => updateAdminSupportTicket(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-support-tickets'] })
      queryClient.invalidateQueries({ queryKey: ['admin-overview'] })
      toast.success('Ticket updated')
    },
    onError: () => toast.error('Could not update ticket'),
  })

  const updateTicket = (ticket, data) => {
    updateTicketMutation.mutate({
      id: ticket.id,
      data: {
        status: ticket.status,
        priority: ticket.priority,
        admin_notes: ticket.admin_notes || '',
        ...data,
      },
    })
  }

  const tickets = ticketsQuery.data || []

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-dark">Support Queue</h2>
          <p className="mt-1 text-sm text-text-muted">Handle escalated issues, priority changes, and resolution notes.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select value={status} onChange={(event) => setStatus(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {statusOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
          <select value={priority} onChange={(event) => setPriority(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2 text-sm">
            {priorityOptions.map((option) => <option key={option} value={option}>{option}</option>)}
          </select>
        </div>
      </div>

      {ticketsQuery.isLoading && (
        <div className="flex justify-center py-8 text-primary">
          <Loader2 className="animate-spin" size={24} />
        </div>
      )}

      {ticketsQuery.isError && (
        <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">Could not load support tickets.</p>
      )}

      {!ticketsQuery.isLoading && tickets.length === 0 && (
        <p className="mt-5 rounded-md bg-slate-50 px-3 py-4 text-sm text-text-muted">No support tickets match these filters.</p>
      )}

      <div className="mt-5 grid gap-4">
        {tickets.map((ticket) => {
          const priorityTone = ticket.priority === 'URGENT' || ticket.priority === 'HIGH' ? 'red' : ticket.priority === 'NORMAL' ? 'yellow' : 'slate'
          const statusTone = ticket.status === 'RESOLVED' || ticket.status === 'CLOSED' ? 'green' : ticket.status === 'REVIEWING' ? 'yellow' : 'red'
          return (
            <article key={ticket.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-text-dark">{ticket.title}</h3>
                    <TicketBadge tone={statusTone}>{ticket.status}</TicketBadge>
                    <TicketBadge tone={priorityTone}>{ticket.priority}</TicketBadge>
                  </div>
                  <p className="mt-2 max-w-3xl text-sm text-text-muted">{ticket.description}</p>
                  <p className="mt-3 text-xs font-semibold text-text-muted">
                    {ticket.user?.full_name || ticket.user?.email} · {ticket.user?.email}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => updateTicket(ticket, { status: 'REVIEWING' })} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50">Review</button>
                  <button type="button" onClick={() => updateTicket(ticket, { status: 'RESOLVED' })} className="rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-900">Resolve</button>
                  <button type="button" onClick={() => updateTicket(ticket, { status: 'CLOSED' })} className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-text-dark hover:bg-slate-50">Close</button>
                </div>
              </div>
              <div className="mt-4 grid gap-3 lg:grid-cols-[180px_1fr_auto] lg:items-end">
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Priority
                  <select value={ticket.priority} onChange={(event) => updateTicket(ticket, { priority: event.target.value })} className="rounded-md border border-slate-300 px-3 py-2">
                    {priorityOptions.filter((option) => option !== 'ALL').map((option) => <option key={option} value={option}>{option}</option>)}
                  </select>
                </label>
                <label className="grid gap-1 text-sm font-medium text-text-dark">
                  Admin notes
                  <textarea
                    value={notesByTicket[ticket.id] ?? ticket.admin_notes ?? ''}
                    onChange={(event) => setNotesByTicket((current) => ({ ...current, [ticket.id]: event.target.value }))}
                    rows={2}
                    className="rounded-md border border-slate-300 px-3 py-2"
                  />
                </label>
                <button
                  type="button"
                  onClick={() => updateTicket(ticket, { admin_notes: notesByTicket[ticket.id] ?? ticket.admin_notes ?? '' })}
                  className="rounded-md border border-primary px-3 py-2 text-sm font-semibold text-primary hover:bg-emerald-50"
                >
                  Save Notes
                </button>
              </div>
            </article>
          )
        })}
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
            <div><dt className="text-text-muted">Overdue invoices</dt><dd className="font-bold text-text-dark">{overview.billing.overdue_invoices}</dd></div>
            <div><dt className="text-text-muted">Pending invoice total</dt><dd className="font-bold text-text-dark">KES {overview.billing.pending_invoice_total}</dd></div>
            <div><dt className="text-text-muted">Paid platform total</dt><dd className="font-bold text-text-dark">KES {overview.billing.paid_invoice_total}</dd></div>
            <div><dt className="text-text-muted">Waived platform total</dt><dd className="font-bold text-text-dark">KES {overview.billing.waived_invoice_total}</dd></div>
            <div><dt className="text-text-muted">Uninvoiced tracked fees</dt><dd className="font-bold text-text-dark">KES {overview.billing.tracked_fee_total}</dd></div>
          </dl>
        </div>
      </div>

      <PlatformBillingQueue enabled={isAdmin} />
      <SupportQueue enabled={isAdmin} />
      <ModerationQueue enabled={isAdmin} />
      <KycReviewQueue enabled={isAdmin} />
    </section>
  )
}
