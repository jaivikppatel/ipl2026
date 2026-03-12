import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import AuthService from './services/AuthService'
import './ResetPassword.css'
import logo from './assets/logo.svg'

function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(true)
  const [tokenValid, setTokenValid] = useState(false)
  const [requirements, setRequirements] = useState(null)
  const [passwordStrength, setPasswordStrength] = useState({
    minLength: false,
    uppercase: false,
    lowercase: false,
    digit: false,
    special: false
  })

  const token = searchParams.get('token')

  useEffect(() => {
    if (!token) {
      setError('Invalid reset link')
      setValidating(false)
      return
    }

    // Validate token
    AuthService.validateResetToken(token)
      .then(data => {
        setTokenValid(data.valid)
        if (!data.valid) {
          setError('This reset link has expired or is invalid')
        }
      })
      .catch(() => {
        setError('Invalid reset link')
        setTokenValid(false)
      })
      .finally(() => {
        setValidating(false)
      })

    // Get password requirements
    AuthService.getPasswordRequirements()
      .then(data => setRequirements(data))
      .catch(() => {})
  }, [token])

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
      await AuthService.resetPassword(token, password)
      setSuccess(true)
      setTimeout(() => {
        navigate('/login')
      }, 3000)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (validating) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="loading">Validating reset link...</div>
        </div>
      </div>
    )
  }

  if (!tokenValid && !validating) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-logo">
            <img src={logo} alt="Cricket Scorecard Logo" />
          </div>
          
          <div className="error-state">
            <div className="error-icon">✕</div>
            <h1 className="auth-title">Link Expired</h1>
            <p className="auth-subtitle">{error}</p>
            <Link to="/forgot-password" className="auth-button">
              Request New Link
            </Link>
          </div>
        </div>
      </div>
    )
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
            <h1 className="auth-title">Password Reset!</h1>
            <p className="auth-subtitle">
              Your password has been successfully reset.
            </p>
            <p className="auth-hint">Redirecting to login...</p>
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
        
        <h1 className="auth-title">Reset Password</h1>
        <p className="auth-subtitle">Enter your new password</p>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="password">New Password</label>
            <div className="password-input-wrapper">
              <input
                type={showPassword ? 'text' : 'password'}
                id="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value)
                  setError('')
                }}
                placeholder="Enter new password"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="password-toggle"
              >
                <span className={`eye-icon ${showPassword ? 'open' : 'closed'}`}>
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </span>
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
                type={showConfirmPassword ? 'text' : 'password'}
                id="confirmPassword"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value)
                  setError('')
                }}
                placeholder="Confirm new password"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="password-toggle"
              >
                <span className={`eye-icon ${showConfirmPassword ? 'open' : 'closed'}`}>
                  {showConfirmPassword ? '👁️' : '👁️‍🗨️'}
                </span>
              </button>
            </div>
          </div>

          {error && (
            <div className="error-banner">
              <span>⚠</span> {error}
            </div>
          )}

          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? 'Resetting...' : 'Reset Password'}
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

export default ResetPassword
