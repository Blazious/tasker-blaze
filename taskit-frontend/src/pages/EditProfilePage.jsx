import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AlertTriangle, BadgeCheck, Camera, CheckCircle2, FileScan, IdCard, Loader2, RefreshCw, Save, ShieldCheck, UploadCloud } from 'lucide-react'
import { getKycStatus, getMe, prefillProfileFromKyc, submitKyc, updateProfile } from '../api/auth.js'
import { useAuthStore } from '../store/authStore.js'
import { getApiErrorMessage } from '../utils/apiError.js'

export default function EditProfilePage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const accessToken = useAuthStore((state) => state.accessToken)
  const refreshToken = useAuthStore((state) => state.refreshToken)
  const [error, setError] = useState('')
  const [kycError, setKycError] = useState('')
  const [form, setForm] = useState({
    full_name: user?.full_name ?? '',
    phone_number: user?.phone_number ?? '',
    gender: user?.gender ?? 'NOT_SPECIFIED',
    student_id: user?.student_id ?? '',
    bio: user?.bio ?? '',
    department: user?.department ?? '',
    year_of_study: user?.year_of_study ?? '',
    profile_photo: null,
  })
  const [kycForm, setKycForm] = useState({
    id_front_image: null,
    id_back_image: null,
    live_face_image: null,
  })
  const [kycPreviewUrls, setKycPreviewUrls] = useState({
    id_front_image: '',
    id_back_image: '',
    live_face_image: '',
  })

  const kycQuery = useQuery({
    queryKey: ['kyc-status'],
    queryFn: getKycStatus,
  })

  const mutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: async () => {
      const freshUser = await getMe()
      setAuth(freshUser, { access: accessToken, refresh: refreshToken })
      toast.success('Profile updated')
      navigate(`/profile/${freshUser.id}`)
    },
    onError: (err) => setError(getApiErrorMessage(err, 'Could not update profile.')),
  })

  const kycMutation = useMutation({
    mutationFn: submitKyc,
    onSuccess: (data) => {
      queryClient.setQueryData(['kyc-status'], data)
      toast.success('KYC submitted and processed')
      setKycError('')
    },
    onError: (err) => setKycError(getApiErrorMessage(err, 'Could not submit KYC documents.')),
  })

  const prefillMutation = useMutation({
    mutationFn: prefillProfileFromKyc,
    onSuccess: (freshUser) => {
      setAuth(freshUser, { access: accessToken, refresh: refreshToken })
      setForm((current) => ({
        ...current,
        full_name: freshUser.full_name ?? current.full_name,
        student_id: freshUser.student_id ?? current.student_id,
        department: freshUser.department ?? current.department,
      }))
      toast.success('Profile prefilled from ID details')
    },
    onError: (err) => setKycError(getApiErrorMessage(err, 'Could not prefill profile from KYC.')),
  })

  const submit = (event) => {
    event.preventDefault()
    const data = new FormData()
    Object.entries(form).forEach(([key, value]) => {
      if (value !== '' && value !== null) data.append(key, value)
    })
    mutation.mutate(data)
  }

  const submitKycForm = (event) => {
    event.preventDefault()
    setKycError('')
    const data = new FormData()
    Object.entries(kycForm).forEach(([key, value]) => {
      if (value) data.append(key, value)
    })
    kycMutation.mutate(data)
  }

  const updateKycFile = (key, file) => {
    setKycForm((current) => ({ ...current, [key]: file }))
    setKycPreviewUrls((current) => ({
      ...current,
      [key]: file ? URL.createObjectURL(file) : '',
    }))
  }

  const kyc = kycQuery.data
  const statusTone = {
    NOT_STARTED: 'bg-slate-100 text-slate-700',
    PENDING_REVIEW: 'bg-blue-100 text-blue-700',
    NEEDS_RETRY: 'bg-amber-100 text-amber-800',
    FACE_MISMATCH: 'bg-red-100 text-red-700',
    APPROVED: 'bg-emerald-100 text-primary',
    REJECTED: 'bg-red-100 text-red-700',
  }
  const canPrefill = Boolean(
    kyc?.prefill
    && (kyc.prefill.full_name || kyc.prefill.student_id || kyc.prefill.department || kyc.prefill.degree),
  )

  return (
    <section className="mx-auto grid max-w-4xl gap-6">
      <form onSubmit={submit} className="grid gap-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-2xl font-bold text-primary">Edit Profile</h1>
      {['full_name', 'phone_number', 'student_id', 'department'].map((field) => (
        <label key={field} className="grid gap-1.5">
          <span className="text-sm font-medium capitalize">{field.replace('_', ' ')}</span>
          <input value={form[field]} onChange={(e) => setForm((current) => ({ ...current, [field]: e.target.value }))} className="rounded-md border border-slate-300 px-3 py-2" />
        </label>
      ))}
      <label className="grid gap-1.5">
        <span className="text-sm font-medium">Gender</span>
        <select value={form.gender} onChange={(e) => setForm((current) => ({ ...current, gender: e.target.value }))} className="rounded-md border border-slate-300 px-3 py-2">
          <option value="NOT_SPECIFIED">Prefer not to say</option>
          <option value="FEMALE">Female</option>
          <option value="MALE">Male</option>
          <option value="OTHER">Other</option>
        </select>
      </label>
      <label className="grid gap-1.5">
        <span className="text-sm font-medium">Year of Study</span>
        <select value={form.year_of_study} onChange={(e) => setForm((current) => ({ ...current, year_of_study: e.target.value }))} className="rounded-md border border-slate-300 px-3 py-2">
          <option value="">Select year</option>
          {[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year}</option>)}
        </select>
      </label>
      <label className="grid gap-1.5">
        <span className="text-sm font-medium">Bio</span>
        <textarea value={form.bio} onChange={(e) => setForm((current) => ({ ...current, bio: e.target.value }))} rows={4} className="rounded-md border border-slate-300 px-3 py-2" />
      </label>
      <label className="grid gap-1.5">
        <span className="text-sm font-medium">Profile Photo</span>
        <input type="file" accept="image/*" onChange={(e) => setForm((current) => ({ ...current, profile_photo: e.target.files?.[0] ?? null }))} />
      </label>
      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <button disabled={mutation.isPending} className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white">
        {mutation.isPending ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
        Save Profile
      </button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-secondary">
              <ShieldCheck size={16} />
              Lightweight KYC
            </p>
            <h2 className="mt-2 text-2xl font-bold text-primary">Verify your student ID</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
              Upload the front and back of your JKUAT student ID. The OCR result can prefill your name,
              registration number, department, school, and degree. Add a live face photo when you are ready
              for face-match confidence.
            </p>
          </div>
          <span className={`inline-flex w-fit rounded-full px-3 py-1 text-sm font-semibold ${statusTone[kyc?.status] ?? statusTone.NOT_STARTED}`}>
            {kycQuery.isLoading ? 'Checking...' : kyc?.status ?? 'NOT_STARTED'}
          </span>
        </div>

        <form onSubmit={submitKycForm} className="mt-5 grid gap-4">
          <div className="grid gap-4 md:grid-cols-3">
            {[
              ['id_front_image', 'Front of student ID', IdCard, 'Required'],
              ['id_back_image', 'Back of student ID', FileScan, 'Required'],
              ['live_face_image', 'Live face capture', Camera, 'Recommended'],
            ].map(([key, label, Icon, badge]) => (
              <label key={key} className="grid cursor-pointer gap-3 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 transition hover:border-primary/50 hover:bg-emerald-50/50">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Icon className="text-primary" />
                    <span className="mt-2 block font-semibold text-text-dark">{label}</span>
                  </div>
                  <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-text-muted">{badge}</span>
                </div>
                {kycPreviewUrls[key] ? (
                  <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
                    <img src={kycPreviewUrls[key]} alt="" className="h-36 w-full object-cover" />
                    <div className="flex items-center justify-between px-3 py-2 text-xs font-semibold">
                      <span className="inline-flex items-center gap-1 text-primary"><CheckCircle2 size={14} /> Ready</span>
                      <span className="inline-flex items-center gap-1 text-text-muted"><RefreshCw size={14} /> Change</span>
                    </div>
                  </div>
                ) : (
                  <span className="rounded-md bg-white px-3 py-6 text-center text-sm text-text-muted">
                    {key === 'live_face_image' ? 'Use your camera or upload a clear selfie.' : 'Upload a clear, uncropped photo.'}
                  </span>
                )}
                <span className="text-xs text-text-muted">{kycForm[key]?.name ?? 'No file selected'}</span>
                <input
                  type="file"
                  accept="image/*"
                  capture={key === 'live_face_image' ? 'user' : undefined}
                  className="hidden"
                  onChange={(e) => updateKycFile(key, e.target.files?.[0] ?? null)}
                />
              </label>
            ))}
          </div>

          {kycError && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{kycError}</p>}

          <button
            type="submit"
            disabled={kycMutation.isPending || !kycForm.id_front_image || !kycForm.id_back_image}
            className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white disabled:opacity-60"
          >
            {kycMutation.isPending ? <Loader2 className="animate-spin" size={18} /> : <UploadCloud size={18} />}
            Submit KYC
          </button>
        </form>

        {kyc && kyc.status !== 'NOT_STARTED' && (
          <div className="mt-6 rounded-lg border border-slate-200 bg-surface p-4">
            <h3 className="font-semibold text-text-dark">Extracted ID details</h3>
            <div className="mt-3 grid gap-3 md:grid-cols-3">
              <div className={`rounded-md p-3 ${kyc.verification_summary?.has_identity_fields ? 'bg-emerald-50 text-primary' : 'bg-amber-50 text-amber-800'}`}>
                <p className="text-xs font-semibold uppercase">Student details</p>
                <p className="mt-1 font-semibold">{kyc.verification_summary?.has_identity_fields ? 'Detected' : 'Needs clearer image'}</p>
              </div>
              <div className={`rounded-md p-3 ${kyc.verification_summary?.has_jkuat_evidence ? 'bg-emerald-50 text-primary' : 'bg-amber-50 text-amber-800'}`}>
                <p className="text-xs font-semibold uppercase">JKUAT evidence</p>
                <p className="mt-1 font-semibold">{kyc.verification_summary?.has_jkuat_evidence ? 'Detected' : 'Not detected'}</p>
              </div>
              <div className={`rounded-md p-3 ${kyc.status === 'FACE_MISMATCH' ? 'bg-red-50 text-red-700' : kyc.face_match_confidence ? 'bg-emerald-50 text-primary' : 'bg-slate-100 text-slate-700'}`}>
                <p className="text-xs font-semibold uppercase">Face match</p>
                <p className="mt-1 font-semibold">
                  {kyc.face_match_confidence ? `${kyc.face_match_confidence}% ${kyc.face_match_confidence_label || ''}` : 'Not run'}
                </p>
              </div>
            </div>
            {kyc.status === 'NEEDS_RETRY' && (
              <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm font-medium text-amber-800">
                <AlertTriangle size={16} />
                KYC needs another upload. Use brighter, uncropped photos where the text and university details are readable.
              </p>
            )}
            {kyc.status === 'FACE_MISMATCH' && (
              <p className="mt-3 inline-flex items-center gap-2 rounded-md bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
                <AlertTriangle size={16} />
                The live face photo did not match the ID photo. Retake a clear selfie facing the camera.
              </p>
            )}
            <dl className="mt-3 grid gap-2 text-sm text-text-muted sm:grid-cols-2">
              <div><dt className="font-medium text-text-dark">Name</dt><dd>{kyc.extracted_full_name || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Registration number</dt><dd>{kyc.extracted_student_id || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Date of birth</dt><dd>{kyc.extracted_date_of_birth || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Issue date</dt><dd>{kyc.extracted_issue_date || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Expiration date</dt><dd>{kyc.extracted_expiration_date || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">University</dt><dd>{kyc.extracted_university_name || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Department</dt><dd>{kyc.extracted_department || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">School</dt><dd>{kyc.extracted_school || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Degree</dt><dd>{kyc.extracted_degree || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">Validity period</dt><dd>{kyc.extracted_validity_period || 'Not found yet'}</dd></div>
              <div><dt className="font-medium text-text-dark">JKUAT stamp</dt><dd>{kyc.stamp_detected ? 'Detected' : 'Not detected'}</dd></div>
              <div><dt className="font-medium text-text-dark">ID photo</dt><dd>{kyc.id_photo_detected ? 'Detected' : 'Not detected'}</dd></div>
              <div><dt className="font-medium text-text-dark">Face match</dt><dd>{kyc.face_match_confidence ? `${kyc.face_match_confidence}%` : 'Not run'}</dd></div>
            </dl>
            {canPrefill && (
              <button
                type="button"
                onClick={() => prefillMutation.mutate()}
                disabled={prefillMutation.isPending}
                className="mt-4 inline-flex items-center gap-2 rounded-md border border-primary px-4 py-2 font-semibold text-primary disabled:opacity-60"
              >
                {prefillMutation.isPending && <Loader2 className="animate-spin" size={18} />}
                Use these details on my profile
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
