export function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex gap-4">
        <div className="h-11 w-11 rounded-md bg-slate-200" />
        <div className="flex-1">
          <div className="h-4 w-24 rounded bg-slate-200" />
          <div className="mt-3 h-5 w-3/4 rounded bg-slate-200" />
          <div className="mt-4 h-4 w-1/2 rounded bg-slate-200" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonDetail() {
  return (
    <div className="animate-pulse rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="h-5 w-32 rounded bg-slate-200" />
      <div className="mt-4 h-8 w-2/3 rounded bg-slate-200" />
      <div className="mt-5 grid gap-3">
        <div className="h-4 w-full rounded bg-slate-200" />
        <div className="h-4 w-5/6 rounded bg-slate-200" />
        <div className="h-4 w-1/2 rounded bg-slate-200" />
      </div>
    </div>
  )
}
