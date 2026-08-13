import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import AdminGuard from './AdminGuard'
import AdminLayout from '../components/layout/AdminLayout'

const AdminLoginPage = lazy(() => import('../pages/AdminLoginPage'))
const AccessDeniedPage = lazy(() => import('../pages/AccessDeniedPage'))
const AdminDashboardPage = lazy(() => import('../pages/admin/AdminDashboardPage'))
const AdminUsersPage = lazy(() => import('../pages/admin/AdminUsersPage'))
const AdminUserDataPage = lazy(() => import('../pages/admin/AdminUserDataPage'))

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<div className="auth-loading">Loading...</div>}>
        <Routes>
          <Route path="/login" element={<AdminLoginPage />} />
          <Route path="/access-denied" element={<AccessDeniedPage />} />
          <Route element={<AdminGuard />}>
            <Route element={<AdminLayout />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              <Route path="/admin/users" element={<AdminUsersPage />} />
              <Route path="/admin/user-data" element={<AdminUserDataPage />} />
            </Route>
          </Route>
          <Route path="/" element={<Navigate to="/admin" replace />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
