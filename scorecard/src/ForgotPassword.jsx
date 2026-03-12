import { useState } from 'react'
import { Link } from 'react-router-dom'
import AuthService from './services/AuthService'
import './ForgotPassword.css'
import logo from './assets/logo.svg'

function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await AuthService.forgotPassword(email)
      setSuccess(true)
      
      // For development, show the debug token
      if (response.debug_token) {
        console.log('Reset Token:', response.debug_token)
        console.log('Reset Link: http://localhost:5173/#/reset-password?token=' + response.debug_token)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">
            <img src={logo} alt="Cricket Scorecard Logo" />
          </div>
          
          <div className="success-message">
            <div className="success-icon">✓</div>
            <h1 className="auth-title">Check Your Email</h1>
            <p className="auth-subtitle">
              If an account exists with that email, we've sent password reset instructions.
            </p>
            <p className="auth-hint">
              Check your spam folder if you don't see it within a few minutes.
            </p>
          </div>

          <div className="auth-footer">
            <p>
              Remember your password?{' '}
              <Link to="/login">Sign in</Link>
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Cricket Scorecard Logo" />
        </div>
        
        <h1 className="auth-title">Forgot Password?</h1>
        <p className="auth-subtitle">
          Enter your email and we'll send you a link to reset your password
        </p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                setError('')
              }}
              placeholder="Enter your email"
              required
            />
          </div>

          {error && (
            <div className="error-banner">
              <span>⚠</span> {error}
            </div>
          )}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Remember your password?{' '}
            <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

export default ForgotPassword
