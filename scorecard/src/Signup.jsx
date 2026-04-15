import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import AuthService from './services/AuthService'
import './Signup.css'
import logo from './assets/logo.svg'

function Signup() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showTooltip, setShowTooltip] = useState(false)
  const [requirements, setRequirements] = useState(null)
  const [success, setSuccess] = useState(false)
  const [successEmail, setSuccessEmail] = useState('')
  const [resendLoading, setResendLoading] = useState(false)
  const [resendMessage, setResendMessage] = useState('')
  const [passwordStrength, setPasswordStrength] = useState({
    minLength: false,
    uppercase: false,
    lowercase: false,
    digit: false,
    special: false
  })

  useEffect(() => {
    // Fetch password requirements from backend
    AuthService.getPasswordRequirements()
      .then(data => setRequirements(data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (requirements) {
      setPasswordStrength({
        minLength: password.length >= requirements.minLength,
        uppercase: requirements.requireUppercase ? /[A-Z]/.test(password) : true,
        lowercase: requirements.requireLowercase ? /[a-z]/.test(password) : true,
        digit: requirements.requireDigit ? /\d/.test(password) : true,
        special: requirements.requireSpecial ? /[!@#$%^&*(),.?":{}|<>]/.test(password) : true
      })
    }
  }, [password, requirements])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)

    try {
      const data = await AuthService.signup(name, email, password)
      setSuccessEmail(data.email || email)
      setSuccess(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setResendLoading(true)
    setResendMessage('')
    try {
      await AuthService.resendVerification(successEmail)
      setResendMessage('Verification email sent!')
    } catch (err) {
      setResendMessage('Failed to resend. Please try again.')
    } finally {
      setResendLoading(false)
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
              We sent a verification link to <strong>{successEmail}</strong>.
              Please verify your email before logging in.
            </p>
            <p style={{ fontSize: '0.9rem', color: '#666', marginTop: '12px' }}>
              The link expires in 24 hours.
            </p>
          </div>
          {resendMessage && (
            <div className={resendMessage.includes('Failed') ? 'error-banner' : 'success-banner'}>
              {resendMessage}
            </div>
          )}
          <button
            className="auth-button"
            onClick={handleResend}
            disabled={resendLoading}
            style={{ marginTop: '16px' }}
          >
            {resendLoading ? 'Sending...' : 'Resend verification email'}
          </button>
          <div className="auth-footer">
            <p>Already verified? <Link to="/login">Sign In</Link></p>
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
        <h1 className="auth-title">Create Account</h1>
        <p className="auth-subtitle">Sign up to get started</p>
        
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="name">
              Display Name
              <span 
                className="info-icon" 
                onClick={(e) => {
                  e.preventDefault()
                  setShowTooltip(!showTooltip)
                }}
              >
                <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                  <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" strokeWidth="1.5"/>
                  <text x="8" y="12" fontSize="10" fontWeight="bold" textAnchor="middle" fill="currentColor">i</text>
                </svg>
                {showTooltip && (
                  <span className="tooltip">This name will be visible to other users</span>
                )}
              </span>
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                setError('')
              }}
              placeholder="Choose your display name"
              required
            />
          </div>

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

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? "text" : "password"}
                id="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                placeholder="Create a password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                aria-label="Toggle password visibility"
              >
                <svg
                  className={`eye-icon ${showPassword ? 'open' : 'closed'}`}
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {showPassword ? (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </>
                  ) : (
                    <>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </>
                  )}
                </svg>
              </button>
            </div>
          </div>

          {requirements && password && (
            <div className="password-requirements">
              <div className="requirement-title">Password must contain:</div>
              <div className={`requirement ${passwordStrength.minLength ? 'met' : ''}`}>
                {passwordStrength.minLength ? '✓' : '○'} At least {requirements.minLength} characters
              </div>
              {requirements.requireUppercase && (
                <div className={`requirement ${passwordStrength.uppercase ? 'met' : ''}`}>
                  {passwordStrength.uppercase ? '✓' : '○'} One uppercase letter
                </div>
              )}
              {requirements.requireLowercase && (
                <div className={`requirement ${passwordStrength.lowercase ? 'met' : ''}`}>
                  {passwordStrength.lowercase ? '✓' : '○'} One lowercase letter
                </div>
              )}
              {requirements.requireDigit && (
                <div className={`requirement ${passwordStrength.digit ? 'met' : ''}`}>
                  {passwordStrength.digit ? '✓' : '○'} One number
                </div>
              )}
              {requirements.requireSpecial && (
                <div className={`requirement ${passwordStrength.special ? 'met' : ''}`}>
                  {passwordStrength.special ? '✓' : '○'} One special character (!@#$%^&*...)
                </div>
              )}
            </div>
          )}

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <div className="password-input-wrapper">
              <input
                type={showConfirmPassword ? "text" : "password"}
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value)
                  setError('')
                }}
                placeholder="Confirm your password"
                required
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                aria-label="Toggle confirm password visibility"
              >
                <svg
                  className={`eye-icon ${showConfirmPassword ? 'open' : 'closed'}`}
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {showConfirmPassword ? (
                    <>
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                      <circle cx="12" cy="12" r="3" />
                    </>
                  ) : (
                    <>
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                      <line x1="1" y1="1" x2="23" y2="23" />
                    </>
                  )}
                </svg>
              </button>
            </div>
          </div>

          {error && (
            <div className="error-banner">
              <span>⚠</span> {error}
            </div>
          )}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <div className="auth-footer">
          <p>Already have an account? <Link to="/login">Sign In</Link></p>
        </div>
      </div>
    </div>
  )
}

export default Signup
