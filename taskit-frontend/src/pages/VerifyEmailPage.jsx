import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2, XCircle } from 'lucide-react'
import { verifyEmail } from '../api/auth.js'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState('loading')
  const token = searchParams.get('token')

  useEffect(() => {
    async function verify() {
      if (!token) {
        setStatus('error')
        return
      }

      try {
        await verifyEmail(token)
        setStatus('success')
      } catch {
        setStatus('error')
      }
    }

    verify()
  }, [token])

  return (
    <section className="flex min-h-[70vh] items-center justify-center">
      <div className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
        {status === 'loading' && (
          <>
            <Loader2 size={36} className="mx-auto animate-spin text-primary" />
            <h1 className="mt-4 text-2xl font-semibold text-text-dark">Verifying your email...</h1>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle2 size={42} className="mx-auto text-primary" />
            <h1 className="mt-4 text-2xl font-semibold text-text-dark">✅ Email verified!</h1>
            <p className="mt-2 text-text-muted">Your account is ready.</p>
            <Link to="/login" className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 font-medium text-white">
              Go to Login
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle size={42} className="mx-auto text-red-600" />
            <h1 className="mt-4 text-2xl font-semibold text-text-dark">Verification failed</h1>
            <p className="mt-2 text-text-muted">This link has expired or is invalid. Please register again.</p>
            <Link to="/register" className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 font-medium text-white">
              Register Again
            </Link>
          </>
        )}
      </div>
    </section>
  )
}
