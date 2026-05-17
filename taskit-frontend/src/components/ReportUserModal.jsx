import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { reportUser } from '../api/reviews.js'
import { getApiErrorMessage } from '../utils/apiError.js'

const REPORT_REASONS = [
  { value: 'HARASSMENT', label: 'Harassment or abusive behaviour' },
  { value: 'SAFETY_CONCERN', label: 'Safety concern' },
  { value: 'NO_SHOW', label: 'Did not show up' },
  { value: 'POOR_WORK', label: 'Poor or slow work' },
  { value: 'PAYMENT_ISSUE', label: 'Payment issue' },
  { value: 'INAPPROPRIATE_CONTENT', label: 'Inappropriate content' },
  { value: 'OTHER', label: 'Other' },
]

export default function ReportUserModal({ userId, taskId, userName = 'this user', onClose }) {
  const [reason, setReason] = useState('HARASSMENT')
  const [details, setDetails] = useState('')
  const [error, setError] = useState('')

  const reportMutation = useMutation({
    mutationFn: () => reportUser(userId, {
      reason,
      details,
      ...(taskId && { task: taskId }),
    }),
    onSuccess: () => {
      toast.success('Report submitted. Our team will review it.')
      onClose()
    },
    onError: (err) => setError(getApiErrorMessage(err, 'Could not submit report.')),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-red-50 p-2 text-red-700">
            <AlertTriangle size={22} />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-text-dark">Report {userName}</h2>
            <p className="mt-1 text-sm leading-6 text-text-muted">
              Reports go to TaskiT admins first. Only moderated reports can appear publicly on profiles.
            </p>
          </div>
        </div>

        <label className="mt-5 grid gap-1.5">
          <span className="text-sm font-medium text-text-dark">Reason</span>
          <select value={reason} onChange={(event) => setReason(event.target.value)} className="rounded-md border border-slate-300 px-3 py-2">
            {REPORT_REASONS.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>

        <label className="mt-4 grid gap-1.5">
          <span className="text-sm font-medium text-text-dark">What happened?</span>
          <textarea
            value={details}
            onChange={(event) => setDetails(event.target.value)}
            rows={5}
            maxLength={1000}
            placeholder="Add clear details. Avoid insults; explain what happened and when."
            className="rounded-md border border-slate-300 px-3 py-2"
          />
          <span className="text-xs text-text-muted">{details.length}/1000</span>
        </label>

        {error && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md border border-slate-300 px-4 py-2 font-medium">
            Cancel
          </button>
          <button
            type="button"
            onClick={() => reportMutation.mutate()}
            disabled={reportMutation.isPending || details.trim().length < 10}
            className="inline-flex items-center gap-2 rounded-md bg-red-600 px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            {reportMutation.isPending && <Loader2 size={18} className="animate-spin" />}
            Submit Report
          </button>
        </div>
      </div>
    </div>
  )
}
