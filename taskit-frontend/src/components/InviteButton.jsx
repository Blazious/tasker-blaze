import { MessageCircle } from 'lucide-react'

export default function InviteButton({ className = '' }) {
  const appUrl = import.meta.env.VITE_PUBLIC_APP_URL
    || (typeof window !== 'undefined' ? window.location.origin : '')
  const inviteText = `Join me on TaskiT, the JKUAT student task app for errands, deliveries, laundry, tutoring, and campus gigs: ${appUrl}`
  const whatsappUrl = `https://wa.me/?text=${encodeURIComponent(inviteText)}`

  return (
    <a
      href={whatsappUrl}
      target="_blank"
      rel="noreferrer"
      className={className || 'inline-flex items-center gap-2 rounded-md bg-[#25D366] px-4 py-2 font-medium text-white hover:bg-[#1ebe5d]'}
    >
      <MessageCircle size={18} />
      Invite
    </a>
  )
}
