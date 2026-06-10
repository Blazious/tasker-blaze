import { Link } from 'react-router-dom'
import {
  BadgeCheck,
  Bike,
  CheckCircle2,
  Clock3,
  LockKeyhole,
  MapPin,
  MessageCircle,
  Package,
  ShieldCheck,
  Sparkles,
  Star,
  Utensils,
  WashingMachine,
} from 'lucide-react'
import { CAMPUS_BACKGROUNDS } from '../constants/campusImages.js'

const heroImages = [
  CAMPUS_BACKGROUNDS.walkway.src,
  CAMPUS_BACKGROUNDS.gate.src,
  CAMPUS_BACKGROUNDS.pau.src,
  'https://images.pexels.com/photos/6238198/pexels-photo-6238198.jpeg?auto=compress&cs=tinysrgb&w=1800',
  'https://images.pexels.com/photos/7972313/pexels-photo-7972313.jpeg?auto=compress&cs=tinysrgb&w=1800',
]

const taskStories = [
  {
    title: 'Laundry runs',
    copy: 'Post pickup, washing, drying, or ironing tasks and choose the student bid that feels right.',
    icon: WashingMachine,
    image:
      'https://images.pexels.com/photos/6238009/pexels-photo-6238009.jpeg?auto=compress&cs=tinysrgb&w=900',
  },
  {
    title: 'Food pickup',
    copy: 'Get meals from the mess, town stage, or nearby spots without leaving your study session.',
    icon: Utensils,
    image:
      'https://images.unsplash.com/photo-1526367790999-0150786686a2?auto=format&fit=crop&w=900&q=80',
  },
  {
    title: 'Errands and delivery',
    copy: 'Move parcels, printouts, thrift finds, and quick campus errands between landmarks.',
    icon: Bike,
    image:
      'https://images.pexels.com/photos/7683730/pexels-photo-7683730.jpeg?auto=compress&cs=tinysrgb&w=900',
  },
  {
    title: 'Room cleaning',
    copy: 'Ask for help with cleaning tasks while keeping safety notes hidden until a tasker is assigned.',
    icon: Sparkles,
    image:
      'https://images.pexels.com/photos/7972313/pexels-photo-7972313.jpeg?auto=compress&cs=tinysrgb&w=900',
  },
]

const steps = [
  ['Post', 'Set the task, campus landmark, budget range, and deadline.'],
  ['Compare', 'Verified users bid with their price and pitch.'],
  ['Pay safely', 'Funds move into escrow after you accept a bid.'],
  ['Complete', 'Chat, finish the task, release payment, then review.'],
]

const trustSignals = [
  [BadgeCheck, 'Email-verified access', 'Users can register with any valid email and verify it before using TaskiT.'],
  [LockKeyhole, 'Escrow-first payments', 'TaskiT holds payment until the client confirms completion.'],
  [ShieldCheck, 'Safety controls', 'SOS access, home-visit warnings, gender preference, and disputes are built in.'],
  [MessageCircle, 'Real-time chat', 'Coordinate details after a bid is accepted without leaving the platform.'],
]

const stats = [
  ['20 min', 'typical small errand window'],
  ['10%', 'clear platform fee'],
  ['24/7', 'campus task posting'],
]

export default function LandingPage() {
  return (
    <div className="landing-cinema -mx-4 -mt-6 overflow-hidden bg-[#081f17] text-white sm:-mx-6 lg:-mx-8">
      <section className="relative min-h-[calc(100vh-4.5rem)] px-4 py-10 sm:px-6 lg:px-8">
        <div className="absolute inset-0">
          {heroImages.map((image, index) => (
            <img
              key={image}
              src={image}
              alt=""
              className="hero-slide absolute inset-0 h-full w-full object-cover"
              style={{ animationDelay: `${index * 5}s` }}
            />
          ))}
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(8,31,23,0.92)_0%,rgba(8,31,23,0.76)_44%,rgba(8,31,23,0.34)_100%)]" />
          <div className="absolute inset-0 bg-black/20" />
          <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#081f17] to-transparent" />
        </div>

        <div className="relative mx-auto flex min-h-[calc(100vh-9rem)] max-w-6xl items-center pt-8">
          <div className="animate-rise max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-3 py-1 text-sm font-semibold text-amber-100 shadow-lg shadow-black/20 backdrop-blur">
              <MapPin size={16} />
              Ingine Mwecheche · Built around JKUAT campus life
            </div>
            <h1 className="mt-6 max-w-4xl text-5xl font-black leading-[1.02] text-white sm:text-6xl lg:text-7xl">
              Get it done on campus, without chasing favors.
            </h1>
            <p className="mt-4 max-w-2xl text-2xl font-black text-secondary sm:text-3xl">
              Ingine Mwecheche.
            </p>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-100 sm:text-xl">
              TaskiT connects verified users who need quick help with people ready to earn from laundry,
              delivery, printing, cleaning, tutoring, errands, and food pickup.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/register"
                className="rounded-md bg-secondary px-6 py-3 font-bold text-[#111827] shadow-xl shadow-amber-900/25 transition hover:-translate-y-0.5 hover:bg-amber-400"
              >
                Get Started
              </Link>
              <Link
                to="/tasks"
                className="rounded-md border border-white/25 bg-white/10 px-6 py-3 font-bold text-white backdrop-blur transition hover:-translate-y-0.5 hover:bg-white/20"
              >
                Browse Tasks
              </Link>
              <Link
                to="/login"
                className="rounded-md px-6 py-3 font-bold text-white/90 transition hover:bg-white/10"
              >
                Login
              </Link>
            </div>
            <div className="mt-10 grid max-w-2xl grid-cols-3 gap-3">
              {stats.map(([value, label]) => (
                <div key={label} className="rounded-lg border border-white/10 bg-white/10 p-4 backdrop-blur">
                  <div className="text-2xl font-black text-white">{value}</div>
                  <div className="mt-1 text-xs font-semibold uppercase text-slate-300">{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {taskStories.map((story) => {
            const Icon = story.icon
            return (
              <article key={story.title} className="group overflow-hidden rounded-xl bg-white text-text-dark shadow-xl shadow-black/10">
                <div className="relative h-52 overflow-hidden">
                  <img
                    src={story.image}
                    alt={`${story.title} task example`}
                    className="h-full w-full object-cover transition duration-700 group-hover:scale-110"
                  />
                  <div className="absolute left-4 top-4 flex h-11 w-11 items-center justify-center rounded-md bg-white text-primary shadow-lg">
                    <Icon size={22} />
                  </div>
                </div>
                <div className="p-5">
                  <h2 className="text-xl font-black">{story.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-text-muted">{story.copy}</p>
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="bg-white px-4 py-16 text-text-dark sm:px-6 lg:px-8">
        <div className="mx-auto grid max-w-6xl gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <p className="text-sm font-black uppercase text-secondary">How TaskiT works</p>
            <h2 className="mt-3 text-4xl font-black text-primary">One clean flow from request to review.</h2>
            <p className="mt-4 text-lg leading-8 text-text-muted">
              No group-chat chaos. No awkward payment follow-ups. Every task has a status, a chat, a payment trail,
              and a reputation record.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {steps.map(([title, copy], index) => (
              <div key={title} className="rounded-xl border border-slate-200 bg-surface p-5">
                <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary text-sm font-black text-white">
                  {index + 1}
                </div>
                <h3 className="mt-4 text-xl font-black">{title}</h3>
                <p className="mt-2 leading-7 text-text-muted">{copy}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        <div className="grid gap-5 lg:grid-cols-4">
          {trustSignals.map(([Icon, title, copy]) => (
            <div key={title} className="rounded-xl border border-white/10 bg-white/10 p-5 backdrop-blur">
              <Icon className="text-secondary" size={28} />
              <h3 className="mt-4 text-xl font-black text-white">{title}</h3>
              <p className="mt-2 leading-7 text-slate-300">{copy}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="relative mx-auto max-w-6xl px-4 pb-20 sm:px-6 lg:px-8">
        <div className="overflow-hidden rounded-2xl bg-primary shadow-2xl shadow-black/25">
          <div className="grid lg:grid-cols-[1.05fr_0.95fr]">
            <div className="p-8 sm:p-10 lg:p-12">
              <div className="flex items-center gap-2 text-amber-100">
                <Star size={18} fill="currentColor" />
                <span className="text-sm font-black uppercase">Earn while helping campus move</span>
              </div>
              <h2 className="mt-4 text-4xl font-black text-white">Be the student someone can rely on today.</h2>
              <p className="mt-4 max-w-2xl text-lg leading-8 text-emerald-50">
                Activate tasker mode, bid on nearby tasks, chat after assignment, and build trust through visible
                reviews and badges.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Link to="/register" className="rounded-md bg-white px-5 py-3 font-black text-primary">
                  Join TaskiT
                </Link>
                <Link to="/login" className="rounded-md border border-white/25 px-5 py-3 font-black text-white">
                  I already have an account
                </Link>
              </div>
            </div>
            <div className="relative min-h-80">
              <img
                src="https://images.pexels.com/photos/6238198/pexels-photo-6238198.jpeg?auto=compress&cs=tinysrgb&w=1000"
                alt="Student completing a task with phone coordination"
                className="absolute inset-0 h-full w-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-primary/70 to-transparent" />
              <div className="absolute bottom-5 left-5 right-5 grid gap-3 rounded-xl bg-white/90 p-4 text-text-dark shadow-xl backdrop-blur">
                <div className="flex items-center gap-3">
                  <CheckCircle2 className="text-primary" />
                  <span className="font-black">Verified tasker assigned</span>
                </div>
                <div className="flex items-center gap-3">
                  <Clock3 className="text-secondary" />
                  <span className="font-black">Payment secured before work begins</span>
                </div>
                <div className="flex items-center gap-3">
                  <Package className="text-primary" />
                  <span className="font-black">Campus handoff tracked by task status</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
