import { useEffect, useState } from 'react'
import { Bell, LogOut, Menu, PlusCircle, ShieldCheck, User, X } from 'lucide-react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useAuthStore } from '../store/authStore.js'
import { getUnreadCount } from '../api/notifications.js'
import taskitLogo from '../assets/taskit-logo.svg'
import InviteButton from './InviteButton.jsx'

const navItems = [
  { label: 'Tasks', to: '/tasks' },
  { label: 'My Tasks', to: '/my-tasks' },
  { label: 'Notifications', to: '/notifications', hasBadge: true },
  { label: 'Billing', to: '/billing' },
  { label: 'KYC', to: '/profile/edit' },
  { label: 'Profile', to: '/profile/me' },
]

function Navbar() {
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const [unreadCount, setUnreadCount] = useState(0)
  const isAdmin = Boolean(user?.is_staff || user?.is_superuser)
  const visibleNavItems =
    isAdmin
      ? [{ label: 'Admin', to: '/admin-panel' }]
      : navItems

  useEffect(() => {
    if (!isAuthenticated) {
      setUnreadCount(0)
      return undefined
    }

    let isMounted = true
    const fetchCount = async () => {
      try {
        const data = await getUnreadCount()
        if (isMounted) setUnreadCount(data.count)
      } catch {
        if (isMounted) setUnreadCount(0)
      }
    }

    fetchCount()
    const intervalId = window.setInterval(fetchCount, 30000)

    return () => {
      isMounted = false
      window.clearInterval(intervalId)
    }
  }, [isAuthenticated])

  const handleLogout = () => {
    clearAuth()
    setIsOpen(false)
    toast.success('Logged out successfully')
    navigate('/login')
  }

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <Link to={isAdmin ? '/admin-panel' : '/'} className="flex items-center" aria-label="TaskiT home">
          <img src={taskitLogo} alt="TaskiT" className="h-11 w-auto" />
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `relative rounded-md px-3 py-2 text-sm font-medium ${
                  isActive
                    ? 'bg-primary text-white'
                    : 'text-text-muted hover:bg-slate-100 hover:text-text-dark'
                }`
              }
            >
              <span className="inline-flex items-center gap-1.5">
                {item.label === 'Notifications' && <Bell size={16} />}
                {item.label === 'Profile' && <User size={16} />}
                {item.label === 'Admin' && <ShieldCheck size={16} />}
                {item.label}
              </span>
              {item.hasBadge && unreadCount > 0 && (
                <span className="absolute -right-1 -top-1 min-w-5 rounded-full bg-red-500 px-1.5 text-center text-xs font-semibold text-white">
                  {unreadCount}
                </span>
              )}
            </NavLink>
          ))}
        </div>

        <div className="hidden items-center gap-2 md:flex">
          {!isAdmin && isAuthenticated && (
            <Link
              to="/tasks/new"
              className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white hover:bg-[#0f6b3c]"
            >
              <PlusCircle size={16} />
              Post Task
            </Link>
          )}
          {!isAdmin && <InviteButton className="inline-flex items-center gap-2 rounded-md bg-[#25D366] px-3 py-2 text-sm font-medium text-white hover:bg-[#1ebe5d]" />}
          {isAuthenticated ? (
            <button
              type="button"
              onClick={handleLogout}
              className="inline-flex items-center gap-2 rounded-md border border-slate-200 px-3 py-2 text-sm font-medium text-text-dark hover:bg-slate-100"
            >
              <LogOut size={16} />
              Logout
            </button>
          ) : (
            <Link
              to="/login"
              className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white"
            >
              Login
            </Link>
          )}
        </div>

        <button
          type="button"
          onClick={() => setIsOpen((value) => !value)}
          className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-text-dark md:hidden"
          aria-label="Toggle navigation"
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {isOpen && (
        <div className="border-t border-slate-200 bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col gap-2">
            {!isAdmin && isAuthenticated && (
              <Link
                to="/tasks/new"
                onClick={() => setIsOpen(false)}
                className="inline-flex items-center gap-2 rounded-md bg-primary px-3 py-2 text-sm font-semibold text-white"
              >
                <PlusCircle size={16} />
                Post Task
              </Link>
            )}
            {visibleNavItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setIsOpen(false)}
                className={({ isActive }) =>
                  `rounded-md px-3 py-2 text-sm font-medium ${
                    isActive
                      ? 'bg-primary text-white'
                      : 'text-text-muted hover:bg-slate-100 hover:text-text-dark'
                  }`
                }
              >
                {item.label}
                {item.hasBadge && unreadCount > 0 && (
                  <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-xs font-semibold text-white">
                    {unreadCount}
                  </span>
                )}
              </NavLink>
            ))}
            {!isAdmin && <InviteButton className="rounded-md bg-[#25D366] px-3 py-2 text-left text-sm font-medium text-white" />}
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md border border-slate-200 px-3 py-2 text-left text-sm font-medium text-text-dark"
            >
              Logout
            </button>
          </div>
        </div>
      )}
    </header>
  )
}

export default Navbar
