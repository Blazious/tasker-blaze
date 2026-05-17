import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section className="flex min-h-[65vh] items-center justify-center">
      <div className="max-w-lg rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        <svg viewBox="0 0 180 120" className="mx-auto h-28 w-40" aria-hidden="true">
          <circle cx="90" cy="60" r="42" fill="#ecfdf5" />
          <path d="M68 70c12-18 32-18 44 0" stroke="#1a4731" strokeWidth="7" strokeLinecap="round" fill="none" />
          <circle cx="72" cy="50" r="5" fill="#1a4731" />
          <circle cx="108" cy="50" r="5" fill="#1a4731" />
        </svg>
        <h1 className="mt-4 text-2xl font-bold text-primary">This page doesn't exist</h1>
        <p className="mt-2 text-text-muted">Maybe it was a task that got completed!</p>
        <Link to="/tasks" className="mt-5 inline-flex rounded-md bg-primary px-4 py-2 text-white">Back to the feed</Link>
      </div>
    </section>
  )
}
