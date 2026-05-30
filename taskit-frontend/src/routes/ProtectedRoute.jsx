import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore.js'

function ProtectedRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  const isAdmin = Boolean(user?.is_staff || user?.is_superuser)
  const adminCanAccess =
    location.pathname === '/admin-panel'
    || /^\/profile\/\d+$/.test(location.pathname)

  if (isAdmin && !adminCanAccess) {
    return <Navigate to="/admin-panel" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
