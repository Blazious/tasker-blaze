import { useEffect, useMemo, useState } from 'react'
import toast from 'react-hot-toast'
import { Copy, Loader2, MapPinned, MessageCircle, WifiOff } from 'lucide-react'

const STORAGE_KEY = 'taskit:lastKnownSafetyLocation'

function buildLocationText({ latitude, longitude, accuracy, timestamp }, contextLabel) {
  const mapsUrl = `https://maps.google.com/?q=${latitude},${longitude}`
  const accuracyText = accuracy ? ` Accuracy: about ${Math.round(accuracy)}m.` : ''
  return `TaskiT safety location${contextLabel ? ` (${contextLabel})` : ''}: ${mapsUrl}.${accuracyText} Shared at ${new Date(timestamp).toLocaleString()}.`
}

export default function LocationShareButton({ contextLabel = 'TaskiT safety check-in', compact = false }) {
  const [isLoading, setIsLoading] = useState(false)
  const [lastLocation, setLastLocation] = useState(null)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        setLastLocation(JSON.parse(stored))
      } catch {
        localStorage.removeItem(STORAGE_KEY)
      }
    }
  }, [])

  const lastLocationText = useMemo(
    () => (lastLocation ? buildLocationText(lastLocation, contextLabel) : ''),
    [contextLabel, lastLocation],
  )

  const shareToWhatsApp = (location) => {
    const text = buildLocationText(location, contextLabel)
    window.open(`https://wa.me/?text=${encodeURIComponent(text)}`, '_blank', 'noopener,noreferrer')
  }

  const saveLocation = (coords) => {
    const location = {
      latitude: Number(coords.latitude).toFixed(6),
      longitude: Number(coords.longitude).toFixed(6),
      accuracy: coords.accuracy,
      timestamp: new Date().toISOString(),
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(location))
    setLastLocation(location)
    return location
  }

  const handleShare = () => {
    if (!navigator.geolocation) {
      toast.error('Your browser does not support location sharing.')
      return
    }

    setIsLoading(true)
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const location = saveLocation(position.coords)
        setIsLoading(false)
        shareToWhatsApp(location)
      },
      () => {
        setIsLoading(false)
        if (lastLocation) {
          toast.error('Could not refresh GPS. Sharing your last saved location instead.')
          shareToWhatsApp(lastLocation)
        } else {
          toast.error('Could not get your location. Check location permission and try again.')
        }
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 30000 },
    )
  }

  const copyLastLocation = async () => {
    if (!lastLocationText) return
    await navigator.clipboard.writeText(lastLocationText)
    toast.success('Last known location copied')
  }

  if (compact) {
    return (
      <button
        type="button"
        onClick={handleShare}
        disabled={isLoading}
        className="inline-flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-semibold text-primary disabled:opacity-70"
      >
        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <MessageCircle size={16} />}
        Share Location
      </button>
    )
  }

  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary text-white">
            <MapPinned size={22} />
          </div>
          <div>
            <h2 className="font-semibold text-primary">Share My Location</h2>
            <p className="text-sm leading-6 text-emerald-900">
              Send your current map location to any WhatsApp contact you choose. Useful before home visits,
              handoffs, or late errands.
            </p>
            <p className="mt-1 inline-flex items-center gap-1.5 text-xs text-emerald-800">
              <WifiOff size={14} />
              Offline fallback: TaskiT keeps your last known location on this device so you can copy it later.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleShare}
            disabled={isLoading}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white disabled:opacity-70"
          >
            {isLoading ? <Loader2 size={16} className="animate-spin" /> : <MessageCircle size={16} />}
            WhatsApp
          </button>
          {lastLocation && (
            <button
              type="button"
              onClick={copyLastLocation}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-emerald-300 bg-white px-4 py-2 text-sm font-semibold text-primary"
            >
              <Copy size={16} />
              Copy Last
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
