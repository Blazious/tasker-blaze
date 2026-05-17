import { Link } from 'react-router-dom'

export default function EmptyState({ title, actionLabel, actionTo }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-white p-10 text-center">
      <svg viewBox="0 0 160 120" className="mx-auto h-28 w-36" role="img" aria-hidden="true">
        <rect x="32" y="28" width="96" height="64" rx="10" fill="#ecfdf5" />
        <path d="M50 72h60M50 54h38" stroke="#1a4731" strokeWidth="7" strokeLinecap="round" />
        <circle cx="118" cy="34" r="16" fill="#f59e0b" />
      </svg>
      <p className="mt-3 text-lg font-semibold text-text-dark">{title}</p>
      {actionLabel && actionTo && (
        <Link to={actionTo} className="mt-4 inline-flex rounded-md bg-primary px-4 py-2 text-white">
          {actionLabel}
        </Link>
      )}
    </div>
  )
}
