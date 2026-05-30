import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import TaskitAssistant from './components/TaskitAssistant.jsx'
import ProtectedRoute from './routes/ProtectedRoute.jsx'
import ChatPage from './pages/ChatPage.jsx'
import BillingPage from './pages/BillingPage.jsx'
import AdminPanelPage from './pages/AdminPanelPage.jsx'
import CreateTaskPage from './pages/CreateTaskPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import EarningsPage from './pages/EarningsPage.jsx'
import LandingPage from './pages/LandingPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import NotificationsPage from './pages/NotificationsPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'
import PublicProfilePage from './pages/PublicProfilePage.jsx'
import EditProfilePage from './pages/EditProfilePage.jsx'
import MyTasksPage from './pages/MyTasksPage.jsx'
import RegisterPage from './pages/RegisterPage.jsx'
import TaskDetailPage from './pages/TaskDetailPage.jsx'
import TaskFeedPage from './pages/TaskFeedPage.jsx'
import VerifyEmailPage from './pages/VerifyEmailPage.jsx'

function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <TaskitAssistant />
      <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/admin-panel" element={<AdminPanelPage />} />
            <Route path="/my-tasks" element={<MyTasksPage />} />
            <Route path="/tasks" element={<TaskFeedPage />} />
            <Route path="/tasks/:id" element={<TaskDetailPage />} />
            <Route path="/tasks/new" element={<CreateTaskPage />} />
            <Route path="/profile/edit" element={<EditProfilePage />} />
            <Route path="/profile/:id" element={<PublicProfilePage />} />
            <Route path="/chat/:taskId" element={<ChatPage />} />
            <Route path="/billing" element={<BillingPage />} />
            <Route path="/earnings" element={<EarningsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App
