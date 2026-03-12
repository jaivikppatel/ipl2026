import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import AuthService from './services/AuthService'
import ProfileService from './services/ProfileService'
import BottomNav from './BottomNav'
import './Profile.css'

function Profile() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [displayName, setDisplayName] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [activeTab, setActiveTab] = useState('profile')
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    if (!AuthService.isAuthenticated()) {
      navigate('/login')
      return
    }

    loadProfile()
  }, [navigate])

  const loadProfile = async () => {
    try {
      setLoading(true)
      const data = await ProfileService.getProfile()
      setUser(data.user)
      setDisplayName(data.user.displayName)
      localStorage.setItem('user', JSON.stringify(data.user))
    } catch (err) {
      setError(err.message)
      const userData = AuthService.getUser()
      if (userData) {
        setUser(userData)
        setDisplayName(userData.displayName)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleDisplayNameUpdate = async (e) => {
    e.preventDefault()
    setMessage('')
    setError('')

    if (displayName.trim().length < 2) {
      setError('Display name must be at least 2 characters')
      return
    }

    try {
      await ProfileService.updateDisplayName(displayName.trim())
      setMessage('Display name updated successfully!')
      setUser(prev => ({ ...prev, displayName: displayName.trim() }))
    } catch (err) {
      setError(err.message)
    }
  }

  const handlePasswordUpdate = async (e) => {
    e.preventDefault()
    setMessage('')
    setError('')

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    try {
      await ProfileService.updatePassword(currentPassword, newPassword)
      setMessage('Password updated successfully!')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setError(err.message)
    }
  }

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Validate file type
    if (!file.type.startsWith('image/')) {
      setError('Please select an image file')
      return
    }

    // Validate file size (2MB)
    if (file.size > 2 * 1024 * 1024) {
      setError('Image size must be less than 2MB')
      return
    }

    setUploading(true)
    setMessage('')
    setError('')

    try {
      const base64 = await ProfileService.fileToBase64(file)
      await ProfileService.uploadProfilePicture(base64)
      setUser(prev => ({ ...prev, profilePicture: base64 }))
      setMessage('Profile picture updated successfully!')
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDeletePicture = async () => {
    if (!window.confirm('Are you sure you want to remove your profile picture?')) {
      return
    }

    setUploading(true)
    setMessage('')
    setError('')

    try {
      await ProfileService.deleteProfilePicture()
      setUser(prev => ({ ...prev, profilePicture: null }))
      setMessage('Profile picture removed successfully!')
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const handleLogout = () => {
    AuthService.logout()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="profile-container">
        <div className="loading">Loading...</div>
      </div>
    )
  }

  return (
    <div className="profile-container">
      <div className="profile-header">
        <button onClick={() => navigate('/dashboard')} className="back-button">
          ← Back
        </button>
        <h1>My Profile</h1>
        <button onClick={handleLogout} className="logout-button-profile">
          Logout
        </button>
      </div>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      <div className="profile-content">
        <div className="profile-picture-section">
          <div className="picture-container">
            {user?.profilePicture ? (
              <img src={user.profilePicture} alt="Profile" className="profile-picture" />
            ) : (
              <div className="profile-picture-placeholder">
                <span className="placeholder-icon">
                  {user?.displayName?.charAt(0).toUpperCase() || '👤'}
                </span>
              </div>
            )}
            {uploading && <div className="upload-overlay">Uploading...</div>}
          </div>
          <div className="picture-actions">
            <button 
              onClick={() => fileInputRef.current?.click()} 
              className="btn-primary"
              disabled={uploading}
            >
              {user?.profilePicture ? 'Change Picture' : 'Upload Picture'}
            </button>
            {user?.profilePicture && (
              <button 
                onClick={handleDeletePicture} 
                className="btn-secondary"
                disabled={uploading}
              >
                Remove
              </button>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
          </div>
          <p className="picture-hint">Max size: 2MB • JPG, PNG, GIF</p>
        </div>

        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'profile' ? 'active' : ''}`}
            onClick={() => setActiveTab('profile')}
          >
            Profile Info
          </button>
          <button 
            className={`tab ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            Security
          </button>
        </div>

        {activeTab === 'profile' && (
          <form onSubmit={handleDisplayNameUpdate} className="profile-form">
            <div className="form-section">
              <h3>Profile Information</h3>
              <div className="form-group">
                <label>Email</label>
                <input type="email" value={user?.email || ''} disabled className="input-disabled" />
              </div>
              <div className="form-group">
                <label>Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Enter your display name"
                  minLength={2}
                  maxLength={100}
                  required
                />
              </div>
              <button type="submit" className="btn-submit">
                Update Profile
              </button>
            </div>
          </form>
        )}

        {activeTab === 'security' && (
          <form onSubmit={handlePasswordUpdate} className="profile-form">
            <div className="form-section">
              <h3>Change Password</h3>
              <div className="form-group">
                <label>Current Password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  required
                />
              </div>
              <div className="form-group">
                <label>New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  minLength={8}
                  required
                />
              </div>
              <div className="form-group">
                <label>Confirm New Password</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Confirm new password"
                  minLength={8}
                  required
                />
              </div>
              <button type="submit" className="btn-submit">
                Update Password
              </button>
            </div>
          </form>
        )}
      </div>

      <BottomNav />
    </div>
  )
}

export default Profile
