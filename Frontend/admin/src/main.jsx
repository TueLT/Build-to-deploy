import React from 'react'
import ReactDOM from 'react-dom/client'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap-icons/font/bootstrap-icons.css'
import '../../src/styles.css'
import './admin.css'
import { AuthProvider } from '../../src/context/AuthContext'
import AdminRouter from './AdminRouter'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider><AdminRouter /></AuthProvider>
  </React.StrictMode>,
)
