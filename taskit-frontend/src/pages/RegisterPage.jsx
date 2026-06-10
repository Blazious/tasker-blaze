import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, MailCheck } from 'lucide-react'
import { register } from '../api/auth.js'
import { getApiErrorMessage } from '../utils/apiError.js'
import CampusBackdrop from '../components/CampusBackdrop.jsx'
import { CAMPUS_BACKGROUNDS } from '../constants/campusImages.js'

export default function RegisterPage() {
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone_number: '',
    gender: 'NOT_SPECIFIED',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [emailVerificationRequired, setEmailVerificationRequired] = useState(true)

  const updateField = (event) => {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    const email = form.email.trim().toLowerCase()

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsLoading(true)
    try {
      const response = await register({
        email,
        password: form.password,
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.trim(),
        gender: form.gender,
      })
      setRegisteredEmail(email)
      setSuccessMessage(response.message || 'Account created successfully.')
      setEmailVerificationRequired(response.email_verification_required !== false)
    } catch (submissionError) {
      setError(getApiErrorMessage(submissionError, 'Registration failed. Please try again.'))
    } finally {
      setIsLoading(false)
    }
  }

  if (registeredEmail) {
    return (
      <CampusBackdrop image={CAMPUS_BACKGROUNDS.walkway} align="center">
        <div className="mx-auto w-full max-w-xl rounded-xl border border-white/15 bg-white/95 p-8 text-center shadow-2xl shadow-black/30 backdrop-blur">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white">
            <MailCheck size={28} />
          </div>
          <h1 className="text-2xl font-semibold text-text-dark">
            {emailVerificationRequired ? 'Check your email!' : 'Account created!'}
          </h1>
          <p className="mt-3 text-text-muted">
            {emailVerificationRequired ? (
              <>
                We sent a verification link to <span className="font-semibold text-text-dark">{registeredEmail}</span>. Click it to activate your account.
              </>
            ) : (
              successMessage
            )}
          </p>
          <Link
            to="/login"
            className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 font-medium text-white hover:bg-emerald-900"
          >
            Back to Login
          </Link>
        </div>
      </CampusBackdrop>
    )
  }

  return (
    <CampusBackdrop image={CAMPUS_BACKGROUNDS.pau} align="center">
      <div className="grid w-full gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
      <div className="flex flex-col justify-center text-white">
        <p className="text-sm font-semibold uppercase tracking-wide text-secondary">Campus tasks · Ingine Mwecheche</p>
        <h1 className="mt-3 text-4xl font-black leading-tight sm:text-5xl">Join TaskiT with your email.</h1>
        <p className="mt-4 max-w-xl text-lg leading-8 text-slate-200">
          Post campus tasks, earn from skills, and keep every transaction tied to a verified account.
        </p>
        <p className="mt-4 w-fit rounded-full bg-white/10 px-3 py-1 text-sm font-black text-secondary backdrop-blur">
          Campus errands, lakini mwecheche.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-xl border border-white/15 bg-white/95 p-6 shadow-2xl shadow-black/30 backdrop-blur">
        <div className="grid gap-4">
          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Full Name</span>
            <input name="full_name" value={form.full_name} onChange={updateField} required className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Email</span>
            <input name="email" type="email" value={form.email} onChange={updateField} required placeholder="name@example.com" className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Phone Number</span>
            <input name="phone_number" value={form.phone_number} onChange={updateField} required className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
            <span className="text-xs text-text-muted">Used for M-Pesa payments</span>
          </label>

          <label className="grid gap-1.5">
            <span className="text-sm font-medium text-text-dark">Gender</span>
            <select name="gender" value={form.gender} onChange={updateField} className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary">
              <option value="NOT_SPECIFIED">Prefer not to say</option>
              <option value="FEMALE">Female</option>
              <option value="MALE">Male</option>
              <option value="OTHER">Other</option>
            </select>
            <span className="text-xs text-text-muted">Used only to show safety preferences when bidding.</span>
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="grid gap-1.5">
              <span className="text-sm font-medium text-text-dark">Password</span>
              <input name="password" type="password" value={form.password} onChange={updateField} required minLength={8} className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
            </label>
            <label className="grid gap-1.5">
              <span className="text-sm font-medium text-text-dark">Confirm Password</span>
              <input name="confirmPassword" type="password" value={form.confirmPassword} onChange={updateField} required minLength={8} className="rounded-md border border-slate-300 px-3 py-2 outline-none focus:border-primary" />
            </label>
          </div>
        </div>

        {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}

        <button type="submit" disabled={isLoading} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 font-semibold text-white hover:bg-emerald-900 disabled:opacity-70">
          {isLoading && <Loader2 size={18} className="animate-spin" />}
          Create Account
        </button>

        <p className="mt-4 text-center text-sm text-text-muted">
          Already verified? <Link to="/login" className="font-medium text-primary">Login here</Link>
        </p>
      </form>
      </div>
    </CampusBackdrop>
  )
}
