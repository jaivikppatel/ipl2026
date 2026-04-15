import { useState, useEffect, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import './VerifyEmail.css'
import logo from './assets/logo.svg'

function VerifyEmail() {
  const [status, setStatus] = useState('loading') // loading | success | error
  const [message, setMessage] = useState('')
  const [resendEmail, setResendEmail] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const verifyCalledRef = useRef(false)
  const navigate = useNavigate()

  useEffect(() => {
    // Guard against React StrictMode double-invocation
    if (verifyCalledRef.current) return
    verifyCalledRef.current = true

    const params = new URLSearchParams(window.location.hash.split('?')[1] || '')
    const token = params.get('token')

    if (!token) {
      setStatus('error')
      setMessage('No verification token found. Please use the link from your email.')
      return
    }

    AuthService.verifyEmail(token)
      .then(() => {
        setStatus('success')
      })
      .catch((err) => {
        setStatus('error')
        setMessage(err.message || 'Invalid or expired verification link.')
      })
  }, [])

  const handleResend = async (e) => {
    e.preventDefault()
    if (!resendEmail) return
    setResendLoading(true)
    setResendMessage('')
    try {
      await AuthService.resendVerification(resendEmail)
      setResendMessage('A new verification email has been sent. Please check your inbox.')
    } catch (err) {
      setResendMessage('Failed to send. Please try again.')
    } finally {
      setResendLoading(false)
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Cricket Scorecard Logo" />
        </div>

        {status === 'loading' && (
          <div className="verify-loading">
            <p className="auth-subtitle">Verifying your email...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="success-message">
            <div className="success-icon">✓</div>
            <h1 className="auth-title">Email Verified!</h1>
            <p className="auth-subtitle">
              Your email address has been verified. You can now log in to your account.
            </p>
            <button
              className="auth-button"
              onClick={() => navigate('/login')}
              style={{ marginTop: '24px' }}
            >
              Go to Login
            </button>
          </div>
        )}

        {status === 'error' && (
          <div>
            <div className="error-state">
              <div className="error-icon">✕</div>
              <h1 className="auth-title">Verification Failed</h1>
              <p className="auth-subtitle">{message}</p>
            </div>

            <div className="resend-section">
              <p className="resend-label">Need a new verification link?</p>
              <form onSubmit={handleResend} className="auth-form">
                <div className="form-group">
                  <label htmlFor="resendEmail">Your email address</label>
                  <input
                    type="email"
                    id="resendEmail"
                    value={resendEmail}
                    onChange={(e) => setResendEmail(e.target.value)}
                    placeholder="Enter your email"
                    required
                  />
                </div>
                {resendMessage && (
                  <div className={resendMessage.includes('Failed') ? 'error-banner' : 'success-banner'}>
                    {resendMessage}
                  </div>
                )}
                <button
                  type="submit"
                  className="auth-button"
                  disabled={resendLoading}
                >
                  {resendLoading ? 'Sending...' : 'Resend verification email'}
                </button>
              </form>
            </div>
          </div>
        )}

        <div className="auth-footer">
          <p><Link to="/login">Back to Login</Link></p>
        </div>
      </div>
    </div>
  )
}

export default VerifyEmail
