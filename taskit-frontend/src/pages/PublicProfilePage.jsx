import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Edit, IdCard, Loader2, ShieldCheck, Star } from 'lucide-react'
import { useState } from 'react'
import { getUserProfile } from '../api/reviews.js'
import { getKycStatus } from '../api/auth.js'
import { useAuthStore } from '../store/authStore.js'
import LocationShareButton from '../components/LocationShareButton.jsx'
import { getAvailabilityClass, getAvailabilityLabel } from '../constants/availability.js'
import ReportUserModal from '../components/ReportUserModal.jsx'

const badgeStyles = {
  'First Task': 'bg-slate-100 text-slate-700',
  'Rising Star': 'bg-blue-100 text-blue-700',
  'Top Rated': 'bg-amber-100 text-amber-700',
  'Trusted Tasker': 'bg-emerald-100 text-primary',
}

function initials(name = '') {
  return name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase()
}

function Stars({ value }) {
  return (
    <div className="flex gap-1 text-secondary">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star key={star} size={18} className={star <= Math.round(value) ? 'fill-secondary' : 'text-slate-300'} />
      ))}
    </div>
  )
}

function RatingBreakdown({ review }) {
  const items = [
    ['Communication', review.communication_rating],
    ['Punctuality', review.punctuality_rating],
    ['Quality', review.quality_rating],
  ]

  return (
    <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
      {items.map(([label, value]) => (
        <div key={label} className="rounded-md bg-slate-50 px-3 py-2">
          <p className="text-xs font-semibold text-text-muted">{label}</p>
          <div className="mt-1 flex items-center gap-2">
            <Stars value={value ?? review.rating} />
            <span className="font-semibold text-text-dark">{value ?? review.rating}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function PublicProfilePage() {
  const { id } = useParams()
  const currentUser = useAuthStore((state) => state.user)
  const profileId = id === 'me' ? currentUser?.id : id
  const [isReportOpen, setIsReportOpen] = useState(false)

  const profileQuery = useQuery({
    queryKey: ['public-profile', profileId],
    queryFn: () => getUserProfile(profileId),
    enabled: Boolean(profileId),
  })

  const kycQuery = useQuery({
    queryKey: ['kyc-status'],
    queryFn: getKycStatus,
    enabled: Boolean(profileId) && String(profileId) === String(currentUser?.id),
  })

  if (profileQuery.isLoading) {
    return <div className="flex justify-center py-12 text-primary"><Loader2 className="animate-spin" size={32} /></div>
  }

  const profile = profileQuery.data
  if (!profile) return <div className="rounded-lg bg-white p-6">Profile not found.</div>

  const isOwnProfile = String(profileId) === String(currentUser?.id)

  return (
    <section className="grid gap-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
          <div className="flex h-28 w-28 items-center justify-center rounded-full bg-primary text-3xl font-bold text-white">
            {profile.profile_photo ? <img src={profile.profile_photo} alt="" className="h-full w-full rounded-full object-cover" /> : initials(profile.full_name)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-3xl font-bold text-primary">{profile.full_name}</h1>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-primary">
                <ShieldCheck size={16} />
                Verified JKUAT Student
              </span>
              {profile.is_tasker_active && (
                <span className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${getAvailabilityClass(profile.availability_status)}`}>
                  {getAvailabilityLabel(profile.availability_status)}
                </span>
              )}
            </div>
            <p className="mt-2 text-text-muted">{profile.department || 'Department not set'} {profile.year_of_study ? `- Year ${profile.year_of_study}` : ''}</p>
            {profile.is_tasker_active && profile.availability_note && (
              <p className="mt-2 text-sm font-medium text-text-dark">{profile.availability_note}</p>
            )}
            <p className="mt-3 max-w-2xl text-text-muted">{profile.bio || 'No bio yet.'}</p>
          </div>
          {isOwnProfile ? (
            <Link to="/profile/edit" className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-4 py-2 font-medium">
              <Edit size={18} />
              Edit Profile
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => setIsReportOpen(true)}
              className="inline-flex items-center gap-2 rounded-md border border-red-200 px-4 py-2 font-semibold text-red-700"
            >
              <AlertTriangle size={18} />
              Report User
            </button>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-text-muted">Rating</p>
          <div className="mt-2 flex items-center gap-3"><Stars value={profile.average_rating} /><span className="font-bold">{profile.average_rating}</span></div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-text-muted">Total Reviews</p>
          <p className="mt-2 text-2xl font-bold text-text-dark">{profile.total_reviews}</p>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-text-muted">Completed Tasks</p>
          <p className="mt-2 text-2xl font-bold text-text-dark">{profile.completed_tasks_count}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {[
          ['Communication', profile.rating_breakdown?.communication],
          ['Punctuality', profile.rating_breakdown?.punctuality],
          ['Quality', profile.rating_breakdown?.quality],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <p className="text-sm text-text-muted">{label}</p>
            <div className="mt-2 flex items-center gap-3"><Stars value={value ?? 0} /><span className="font-bold">{value ?? 0}</span></div>
          </div>
        ))}
      </div>

      {isOwnProfile && (
        <div className="rounded-lg border border-blue-100 bg-blue-50 p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="inline-flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-blue-700">
                <IdCard size={16} />
                Student ID KYC
              </p>
              <h2 className="mt-2 text-xl font-semibold text-blue-950">
                {kycQuery.isLoading ? 'Checking KYC status...' : `Status: ${kycQuery.data?.status ?? 'NOT_STARTED'}`}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-blue-800">
                Upload the front and back of your JKUAT student ID, then use the extracted details to prefill your profile.
              </p>
            </div>
            <Link to="/profile/edit" className="inline-flex w-fit items-center gap-2 rounded-md bg-primary px-4 py-2 font-semibold text-white">
              <IdCard size={18} />
              Open KYC
            </Link>
          </div>
        </div>
      )}

      {isOwnProfile && <LocationShareButton contextLabel="Profile safety check-in" />}

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-text-dark">Badges</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {profile.badges.length === 0 && <p className="text-text-muted">No badges yet.</p>}
          {profile.badges.map((badge) => (
            <span key={badge} className={`rounded-full px-3 py-1 text-sm font-semibold ${badgeStyles[badge] ?? 'bg-slate-100 text-slate-700'}`}>{badge}</span>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-text-dark">Completed Work</h2>
        <div className="mt-4 grid gap-3">
          {(profile.completed_task_history ?? []).length === 0 && <p className="text-text-muted">No completed task history yet.</p>}
          {(profile.completed_task_history ?? []).map((task) => (
            <Link key={task.id} to={`/tasks/${task.id}`} className="rounded-lg border border-slate-200 p-4 transition hover:border-primary/40 hover:shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-text-dark">{task.title}</p>
                {task.completed_at && <span className="text-xs text-text-muted">{new Date(task.completed_at).toLocaleDateString()}</span>}
              </div>
              <p className="mt-1 text-sm text-text-muted">{task.category} task for {task.client_name}</p>
            </Link>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-text-dark">Recent Reviews</h2>
        <div className="mt-4 grid gap-3">
          {profile.recent_reviews.length === 0 && <p className="text-text-muted">No reviews yet.</p>}
          {profile.recent_reviews.map((review) => (
            <div key={review.id} className="rounded-lg border border-slate-200 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="font-semibold text-text-dark">{review.reviewer_name}</p>
                <span className="text-sm text-text-muted">{new Date(review.created_at).toLocaleDateString()}</span>
              </div>
              <div className="mt-2"><Stars value={review.rating} /></div>
              <RatingBreakdown review={review} />
              <p className="mt-2 text-text-muted">{review.comment}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-text-dark">Community Concerns</h2>
        <p className="mt-1 text-sm text-text-muted">
          Only reports reviewed and approved by TaskiT admins are shown here.
        </p>
        <div className="mt-4 grid gap-3">
          {(profile.public_reports ?? []).length === 0 && <p className="text-text-muted">No moderated concerns on this profile.</p>}
          {(profile.public_reports ?? []).map((report) => (
            <div key={report.id} className="rounded-lg border border-red-100 bg-red-50 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-red-900">{report.reason.replaceAll('_', ' ')}</p>
                <span className="text-xs text-red-700">{new Date(report.created_at).toLocaleDateString()}</span>
              </div>
              {report.task_title && <p className="mt-1 text-xs font-medium text-red-700">Task: {report.task_title}</p>}
              <p className="mt-2 text-sm text-red-800">{report.details}</p>
            </div>
          ))}
        </div>
      </div>

      {isReportOpen && (
        <ReportUserModal
          userId={profileId}
          userName={profile.full_name}
          onClose={() => setIsReportOpen(false)}
        />
      )}
    </section>
  )
}
