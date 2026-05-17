import { useState } from 'react'

export default function CampusBackdrop({ image, children, align = 'center' }) {
  const primaryImage = typeof image === 'string' ? image : image.src
  const fallbackImage = typeof image === 'string' ? '' : image.fallback
  const [activeImage, setActiveImage] = useState(primaryImage)

  return (
    <section className="-mx-4 -my-6 min-h-[calc(100vh-4.5rem)] overflow-hidden bg-[#071c15] sm:-mx-6 lg:-mx-8">
      <div className="relative min-h-[calc(100vh-4.5rem)] px-4 py-10 sm:px-6 lg:px-8">
        <img
          src={activeImage}
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-95"
          style={{ objectPosition: align }}
          onError={() => {
            if (fallbackImage && activeImage !== fallbackImage) {
              setActiveImage(fallbackImage)
            }
          }}
        />
        <div className="absolute inset-0 bg-[linear-gradient(115deg,rgba(3,13,9,0.78)_0%,rgba(7,28,21,0.58)_48%,rgba(3,13,9,0.28)_100%)]" />
        <div className="absolute inset-0 bg-black/10" />
        <div className="relative mx-auto flex min-h-[calc(100vh-9rem)] w-full max-w-6xl items-center">
          {children}
        </div>
      </div>
    </section>
  )
}
