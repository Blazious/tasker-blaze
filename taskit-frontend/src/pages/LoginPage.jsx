import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { getMe, login } from '../api/auth.js'
import { useAuthStore } from '../store/authStore.js'
import { getApiErrorMessage } from '../utils/apiError.js'
import CampusBackdrop from '../components/CampusBackdrop.jsx'
import { CAMPUS_BACKGROUNDS } from '../constants/campusImages.js'

export default function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const updateField = (event) => {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const tokens = await login({
        email: form.email.trim().toLowerCase(),
        password: form.password,
      })
      localStorage.setItem('accessToken', tokens.access)
      localStorage.setItem('refreshToken', tokens.refresh)
      const user = await getMe()
      setAuth(user, tokens)
      navigate('/dashboard')
    } catch (loginError) {
      const message = getApiErrorMessage(loginError, 'Login failed. Please check your details.')
      setError(
        message.toLowerCase().includes('verify')
          ? 'Please verify your JKUAT email first. Check your inbox.'
          : message,
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <CampusBackdrop image={CAMPUS_BACKGROUNDS.gate} align="center">
      <div className="grid w-full gap-8 lg:grid-cols-[1fr_0.82fr] lg:items-center">
        <div className="hidden max-w-xl text-white lg:block">
          <p className="text-sm font-bold uppercase tracking-wide text-secondary">JKUAT campus tasks · Ingine Mwecheche</p>
          <h1 className="mt-4 text-5xl font-black leading-tight">
            Welcome back to the campus network that gets things done.
          </h1>
          <p className="mt-5 text-lg leading-8 text-slate-200">
            Sign in to post tasks, bid safely, chat with verified students, and keep every handoff tied to JKUAT.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="w-full rounded-xl border border-white/15 bg-white/95 p-6 shadow-2xl shadow-black/30 backdrop-blur">
          <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Welcome back</p>
          <h1 className="mt-2 text-2xl font-bold text-primary">Login to TaskiT</h1>
          <p className="mt-1 text-sm font-semibold text-text-muted">Ingine Mwecheche.</p>

        <div className="mt-6 grid gap-4">
          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Email</span>
            <input name="email" type="email" value={form.email} onChange={updateField} required className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
          </label>
          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Password</span>
            <input name="password" type="password" value={form.password} onChange={updateField} required className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
          </label>
        </div>

        {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button type="submit" disabled={isLoading} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 font-semibold text-white hover:bg-emerald-900 disabled:opacity-70">
          {isLoading && <Loader2 size={18} className="animate-spin" />}
          Login
        </button>

        <p className="mt-4 text-center text-sm text-text-muted">
          Don't have an account? <Link to="/register" className="font-medium text-primary">Register here</Link>
        </p>
        </form>
      </div>
    </CampusBackdrop>
  )
}
