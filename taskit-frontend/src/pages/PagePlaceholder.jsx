function PagePlaceholder({ title }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-4 h-2 w-16 rounded-full bg-secondary" />
      <h1 className="text-2xl font-semibold text-text-dark">{title}</h1>
      <div className="mt-4 rounded-md bg-primary p-4 text-white">
        Tailwind is working.
      </div>
    </section>
  )
}

export default PagePlaceholder
