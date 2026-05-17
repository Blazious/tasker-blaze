import { AlertTriangle, PhoneCall } from 'lucide-react'

export default function SOSButton() {
  return (
    <div className="rounded-lg border border-red-300 bg-red-50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-red-600 text-white">
            <AlertTriangle size={22} />
          </div>
          <div>
            <h2 className="font-semibold text-red-900">SOS Emergency Help</h2>
            <p className="text-sm leading-6 text-red-800">
              Call Juja Police Station for urgent help near JKUAT. Other emergency numbers:
              067-52176, 0721-200999, 999, 112.
            </p>
            <p className="mt-1 text-xs text-red-700">
              If you can, move to a public place and share your live location with someone you trust.
            </p>
          </div>
        </div>

        <a
          href="tel:0721200999"
          className="inline-flex w-fit items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-red-700"
        >
          <PhoneCall size={16} />
          Call SOS
        </a>
      </div>
    </div>
  )
}
