import React from 'react'
import ReactDOM from 'react-dom/client'
import { GoogleOAuthProvider } from '@react-oauth/google'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import '../../src/styles.css'
import '../../src/assistant.css'
import { AuthProvider } from '../../src/context/AuthContext'
import UserRouter from './UserRouter'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID || ''}>
      <AuthProvider><UserRouter /></AuthProvider>
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
