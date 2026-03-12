import { useNavigate, useLocation } from 'react-router-dom'
import AuthService from './services/AuthService'
import './BottomNav.css'

function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = AuthService.getUser()
  const isAdmin = user?.isAdmin || false

  const isActive = (path) => {
    return location.pathname === path || location.hash.includes(path)
  }

  return (
    <div className="bottom-nav">
      <button 
        className={`nav-item ${isActive('/dashboard') ? 'active' : ''}`}
        onClick={() => navigate('/dashboard')}
      >
        <span className="nav-icon">🏠</span>
        <span className="nav-label">Home</span>
      </button>

      {isAdmin && (
        <button 
          className={`nav-item ${isActive('/admin') ? 'active' : ''}`}
          onClick={() => navigate('/admin')}
        >
          <span className="nav-icon">⚙️</span>
          <span className="nav-label">Admin</span>
        </button>
      )}

      <button 
        className={`nav-item ${isActive('/profile') ? 'active' : ''}`}
        onClick={() => navigate('/profile')}
      >
        {user?.profilePicture ? (
          <img src={user.profilePicture} alt="Profile" className="nav-profile-pic" />
        ) : (
          <span className="nav-icon">👤</span>
        )}
        <span className="nav-label">Profile</span>
      </button>
    </div>
  )
}

export default BottomNav
